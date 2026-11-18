from collections import deque
from dataclasses import dataclass
import threading
import numpy as np
import sounddevice as sd
from dsp_engine import RealTimeDSPEngine


@dataclass
class AudioDeviceItem:
    index: int
    name: str
    hostapi: str
    max_in: int
    max_out: int
    default_sr: float

    @property
    def label(self) -> str:
        return f"[{self.hostapi}] {self.name} (#{self.index})"


class AudioRouter:
    def __init__(self, dsp: RealTimeDSPEngine):
        self.dsp = dsp
        self.running = False
        self._stream = None
        self._in_stream = None
        self._out_stream = None
        self._mon_stream = None
        self._bridge_q: deque[np.ndarray] = deque(maxlen=16)
        self._mon_q: deque[np.ndarray] = deque(maxlen=16)
        self._mon_lock = threading.Lock()
        self.monitor_enabled = False
        self.active_sr = 48000
        self.active_block = 512

    @staticmethod
    def list_devices() -> tuple[list[AudioDeviceItem], list[AudioDeviceItem]]:
        devs = sd.query_devices()
        hostapis = sd.query_hostapis()
        inputs: list[AudioDeviceItem] = []
        outputs: list[AudioDeviceItem] = []

        for idx, d in enumerate(devs):
            api_name = hostapis[d["hostapi"]]["name"]
            # Simplifica nomes longos de Host API no Windows
            if "WASAPI" in api_name:
                api_short = "WASAPI"
            elif "DirectSound" in api_name:
                api_short = "DirectSound"
            elif "MME" in api_name:
                api_short = "MME"
            elif "WDM-KS" in api_name:
                api_short = "WDM-KS"
            else:
                api_short = api_name

            item = AudioDeviceItem(
                index=idx,
                name=d["name"],
                hostapi=api_short,
                max_in=int(d["max_input_channels"]),
                max_out=int(d["max_output_channels"]),
                default_sr=float(d["default_samplerate"]),
            )
            if item.max_in > 0:
                inputs.append(item)
            if item.max_out > 0:
                outputs.append(item)

        return inputs, outputs

    def start(
        self,
        in_idx: int,
        out_idx: int,
        blocksize: int = 512,
        monitor_enabled: bool = False,
        monitor_idx: int | None = None,
    ) -> tuple[bool, str]:
        self.stop()
        self.monitor_enabled = monitor_enabled and (monitor_idx is not None) and (monitor_idx != out_idx)
        self._bridge_q.clear()
        self._mon_q.clear()

        in_info = sd.query_devices(in_idx)
        out_info = sd.query_devices(out_idx)
        candidate_srs = []
        for sr in [48000, int(in_info["default_samplerate"]), int(out_info["default_samplerate"]), 44100]:
            if sr not in candidate_srs and sr > 0:
                candidate_srs.append(sr)

        in_ch = 1
        out_ch_opts = [1, 2] if int(out_info["max_output_channels"]) >= 2 else [1]

        last_err = ""
        # Tenta primeiro stream duplex (menor latência)
        for sr in candidate_srs:
            for out_ch in out_ch_opts:
                try:
                    self.dsp.set_sample_rate(sr)
                    self.active_sr = sr
                    self.active_block = blocksize

                    def duplex_cb(indata, outdata, frames, time_info, status):
                        mono = indata[:, 0] if indata.ndim > 1 else indata
                        processed = self.dsp.process(mono)
                        if outdata.shape[1] == 1:
                            outdata[:, 0] = processed
                        else:
                            outdata[:, 0] = processed
                            outdata[:, 1] = processed
                        if self.monitor_enabled:
                            with self._mon_lock:
                                self._mon_q.append(processed.copy())

                    self._stream = sd.Stream(
                        device=(in_idx, out_idx),
                        samplerate=sr,
                        blocksize=blocksize,
                        channels=(in_ch, out_ch),
                        dtype="float32",
                        latency="low",
                        callback=duplex_cb,
                    )
                    self._stream.start()
                    self.running = True
                    msg = f"Ativo: {sr} Hz | Bloco {blocksize} (~{blocksize * 1000 / sr:.1f} ms)"
                    if self.monitor_enabled and monitor_idx is not None:
                        self._start_monitor(monitor_idx, sr, blocksize)
                    return True, msg
                except Exception as e:
                    last_err = str(e)
                    if self._stream is not None:
                        try:
                            self._stream.close()
                        except Exception:
                            pass
                        self._stream = None

        # Fallback: dois streams separados (útil se Entrada e Saída usarem Host APIs diferentes no Windows)
        for sr in candidate_srs:
            for out_ch in out_ch_opts:
                try:
                    self.dsp.set_sample_rate(sr)
                    self.active_sr = sr
                    self.active_block = blocksize

                    def in_cb(indata, frames, time_info, status):
                        mono = indata[:, 0] if indata.ndim > 1 else indata
                        processed = self.dsp.process(mono)
                        self._bridge_q.append(processed.copy())
                        if self.monitor_enabled:
                            with self._mon_lock:
                                self._mon_q.append(processed.copy())

                    def out_cb(outdata, frames, time_info, status):
                        if len(self._bridge_q) > 0:
                            chunk = self._bridge_q.popleft()
                            if len(chunk) != frames:
                                out_buf = np.zeros(frames, dtype=np.float32)
                                m = min(len(chunk), frames)
                                out_buf[:m] = chunk[:m]
                            else:
                                out_buf = chunk
                        else:
                            out_buf = np.zeros(frames, dtype=np.float32)
                        for ch in range(outdata.shape[1]):
                            outdata[:, ch] = out_buf

                    self._in_stream = sd.InputStream(
                        device=in_idx,
                        samplerate=sr,
                        blocksize=blocksize,
                        channels=1,
                        dtype="float32",
                        callback=in_cb,
                    )
                    self._out_stream = sd.OutputStream(
                        device=out_idx,
                        samplerate=sr,
                        blocksize=blocksize,
                        channels=out_ch,
                        dtype="float32",
                        callback=out_cb,
                    )
                    self._in_stream.start()
                    self._out_stream.start()
                    self.running = True
                    msg = f"Ativo (Modo Ponte): {sr} Hz | Bloco {blocksize}"
                    if self.monitor_enabled and monitor_idx is not None:
                        self._start_monitor(monitor_idx, sr, blocksize)
                    return True, msg
                except Exception as e:
                    last_err = str(e)
                    self.stop()

        return False, f"Falha ao iniciar áudio: {last_err}"

    def _start_monitor(self, monitor_idx: int, sr: int, blocksize: int):
        try:
            info = sd.query_devices(monitor_idx)
            ch = 2 if int(info["max_output_channels"]) >= 2 else 1

            def mon_cb(outdata, frames, time_info, status):
                with self._mon_lock:
                    chunk = self._mon_q.popleft() if len(self._mon_q) > 0 else None
                if chunk is None:
                    outdata.fill(0.0)
                    return
                if len(chunk) != frames:
                    tmp = np.zeros(frames, dtype=np.float32)
                    m = min(len(chunk), frames)
                    tmp[:m] = chunk[:m]
                    chunk = tmp
                for c in range(outdata.shape[1]):
                    outdata[:, c] = chunk

            self._mon_stream = sd.OutputStream(
                device=monitor_idx,
                samplerate=sr,
                blocksize=blocksize,
                channels=ch,
                dtype="float32",
                callback=mon_cb,
            )
            self._mon_stream.start()
        except Exception:
            self._mon_stream = None

    def stop(self):
        self.running = False
        for s in (self._stream, self._in_stream, self._out_stream, self._mon_stream):
            if s is not None:
                try:
                    s.stop()
                    s.close()
                except Exception:
                    pass
        self._stream = None
        self._in_stream = None
        self._out_stream = None
        self._mon_stream = None
