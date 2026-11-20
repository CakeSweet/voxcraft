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


def _resample_linear(data: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr or len(data) == 0:
        return data
    n_out = max(1, int(round(len(data) * float(dst_sr) / float(src_sr))))
    if n_out == len(data):
        return data
    x_old = np.linspace(0.0, 1.0, len(data), endpoint=False)
    x_new = np.linspace(0.0, 1.0, n_out, endpoint=False)
    return np.interp(x_new, x_old, data).astype(np.float32)


class _SampleFifo:
    """Buffer FIFO contínuo por amostras para suportar taxas/blocos diferentes sem cortes."""

    def __init__(self, max_samples: int = 16384):
        self._chunks: deque[np.ndarray] = deque()
        self._total = 0
        self._max_samples = max_samples
        self._lock = threading.Lock()

    def clear(self):
        with self._lock:
            self._chunks.clear()
            self._total = 0

    def push(self, data: np.ndarray):
        if len(data) == 0:
            return
        with self._lock:
            self._chunks.append(data.astype(np.float32, copy=True))
            self._total += len(data)
            # Evita acúmulo de latência se o relógio de entrada/saída divergir
            while self._total > self._max_samples and len(self._chunks) > 1:
                dropped = self._chunks.popleft()
                self._total -= len(dropped)

    def pop(self, n_frames: int) -> np.ndarray:
        out = np.zeros(n_frames, dtype=np.float32)
        with self._lock:
            if self._total == 0:
                return out
            pos = 0
            while pos < n_frames and self._chunks:
                head = self._chunks[0]
                need = n_frames - pos
                if len(head) <= need:
                    out[pos:pos + len(head)] = head
                    pos += len(head)
                    self._total -= len(head)
                    self._chunks.popleft()
                else:
                    out[pos:] = head[:need]
                    self._chunks[0] = head[need:]
                    self._total -= need
                    pos = n_frames
            return out


_HOSTAPI_PRIORITY = {
    "WASAPI": 0,
    "ASIO": 1,
    "Core Audio": 1,
    "PipeWire": 1,
    "PulseAudio": 1,
    "JACK": 1,
    "ALSA": 2,
    "DirectSound": 2,
    "MME": 3,
    "WDM-KS": 9,
}

_GENERIC_DEV_WORDS = {
    "microfone",
    "microphone",
    "mic",
    "speakers",
    "alto",
    "falantes",
    "line",
    "input",
    "output",
    "audio",
    "device",
    "dispositivo",
    "realtek",
    "high",
    "definition",
    "usb",
    "headset",
    "earphone",
    "headphones",
    "fones",
    "ouvido",
}


def _short_hostapi(api_name: str) -> str:
    if "WASAPI" in api_name:
        return "WASAPI"
    if "DirectSound" in api_name:
        return "DirectSound"
    if "MME" in api_name:
        return "MME"
    if "WDM-KS" in api_name:
        return "WDM-KS"
    if "ASIO" in api_name:
        return "ASIO"
    return api_name


def _hostapi_rank(api_short: str) -> int:
    return _HOSTAPI_PRIORITY.get(api_short, 4)


def _extract_paren_part(name: str) -> str:
    start = name.find("(")
    end = name.rfind(")")
    if start != -1 and end > start + 1:
        part = name[start + 1:end].strip().lower()
    elif start != -1:
        # MME costuma truncar em 31 chars sem fechar o parêntese
        part = name[start + 1:].strip().lower()
    else:
        return ""
    # Windows adiciona prefixos como "2- " ao trocar de porta USB
    i = 0
    while i < len(part) and part[i].isdigit():
        i += 1
    if i > 0 and i < len(part):
        rest = part[i:].lstrip()
        if rest.startswith("-"):
            part = rest[1:].strip()
    return part


def _dev_name_tokens(name: str) -> set[str]:
    clean = []
    for ch in name.lower():
        clean.append(ch if ch.isalnum() else " ")
    return {
        w for w in "".join(clean).split()
        if len(w) >= 3 and w not in _GENERIC_DEV_WORDS
    }


def _name_similarity(target_name: str, cand_name: str) -> int:
    a = " ".join(target_name.lower().split())
    b = " ".join(cand_name.lower().split())
    if not a or not b:
        return 0
    if a == b:
        return 100
    # MME trunca nomes em 31 caracteres no Windows
    min_pref = min(len(a), len(b), 24)
    if min_pref >= 12 and (a[:min_pref] == b[:min_pref]):
        return 90
    pa = _extract_paren_part(a)
    pb = _extract_paren_part(b)
    if pa and pb:
        if pa == pb:
            return 85
        p_pref = min(len(pa), len(pb), 16)
        if p_pref >= 8 and pa[:p_pref] == pb[:p_pref]:
            return 80
    ta = _dev_name_tokens(a)
    tb = _dev_name_tokens(b)
    overlap = len(ta & tb)
    if overlap >= 2:
        return 65 + min(overlap, 10)
    if overlap == 1 and (len(ta) == 1 or len(tb) == 1):
        return 55
    return 0


class AudioRouter:
    def __init__(self, dsp: RealTimeDSPEngine):
        self.dsp = dsp
        self.running = False
        self._op_lock = threading.Lock()
        self._abort_event = threading.Event()
        self._stream = None
        self._in_stream = None
        self._out_stream = None
        self._mon_stream = None
        self._bridge_fifo = _SampleFifo(max_samples=16384)
        self._mon_fifo = _SampleFifo(max_samples=16384)
        self.monitor_enabled = False
        self.active_sr = 48000
        self.active_out_sr = 48000
        self.active_mon_sr = 48000
        self.active_block = 512
        self.last_used_in_idx: int | None = None
        self.last_used_out_idx: int | None = None

    def abort_start(self):
        self._abort_event.set()

    @staticmethod
    def list_devices() -> tuple[list[AudioDeviceItem], list[AudioDeviceItem]]:
        try:
            devs = sd.query_devices()
            hostapis = sd.query_hostapis()
        except Exception:
            return [], []
        inputs: list[AudioDeviceItem] = []
        outputs: list[AudioDeviceItem] = []

        for idx, d in enumerate(devs):
            api_name = hostapis[d["hostapi"]]["name"]
            api_short = _short_hostapi(api_name)

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

        # Prioriza WASAPI > DirectSound > MME > WDM-KS (evita erro -9999 do WDM-KS por padrão)
        inputs.sort(key=lambda it: (_hostapi_rank(it.hostapi), it.index))
        outputs.sort(key=lambda it: (_hostapi_rank(it.hostapi), it.index))
        return inputs, outputs

    @staticmethod
    def refresh_backend() -> tuple[list[AudioDeviceItem], list[AudioDeviceItem]]:
        """Reinicializa o PortAudio para detectar novos dispositivos USB/virtuais conectados."""
        try:
            sd._terminate()
            sd._initialize()
        except Exception:
            pass
        return AudioRouter.list_devices()

    @staticmethod
    def _candidate_rates(dev_info: dict, preferred: list[int] | None = None) -> list[int]:
        raw = []
        if preferred:
            raw.extend(preferred)
        default_sr = int(round(float(dev_info.get("default_samplerate", 48000) or 48000)))
        raw.extend([default_sr, 48000, 44100, 96000, 32000, 16000])
        out: list[int] = []
        for sr in raw:
            if sr > 0 and sr not in out:
                out.append(sr)
        return out

    @staticmethod
    def _equivalent_device_indices(target_idx: int, is_input: bool) -> list[int]:
        """Retorna índices equivalentes (WASAPI, DirectSound, MME) para o mesmo hardware caso a API selecionada falhe."""
        result = [target_idx]
        try:
            devs = sd.query_devices()
            hostapis = sd.query_hostapis()
            target_info = devs[target_idx]
        except Exception:
            return result

        target_name = str(target_info.get("name", ""))
        scored: list[tuple[int, int, int]] = []
        for idx, d in enumerate(devs):
            if idx == target_idx:
                continue
            ch_count = int(d["max_input_channels"] if is_input else d["max_output_channels"])
            if ch_count <= 0:
                continue
            api_short = _short_hostapi(str(hostapis[d["hostapi"]]["name"]))
            if api_short == "WDM-KS":
                continue
            sim = _name_similarity(target_name, str(d.get("name", "")))
            if sim >= 55:
                # Maior similaridade primeiro, depois melhor Host API (WASAPI -> DirectSound -> MME)
                scored.append((-sim, _hostapi_rank(api_short), idx))

        scored.sort()
        for _, _, idx in scored:
            if idx not in result:
                result.append(idx)
        return result

    @staticmethod
    def _find_supported_configs(
        dev_idx: int,
        is_input: bool,
        preferred_srs: list[int] | None = None,
        abort_event: threading.Event | None = None,
    ) -> list[tuple[int, int]]:
        info = sd.query_devices(dev_idx)
        max_ch = int(info["max_input_channels"] if is_input else info["max_output_channels"])
        ch_opts = [1, 2] if is_input else ([2, 1] if max_ch >= 2 else [1])
        if max_ch < 2:
            ch_opts = [1]

        rates = AudioRouter._candidate_rates(info, preferred_srs)
        valid: list[tuple[int, int]] = []
        for sr in rates:
            if abort_event is not None and abort_event.is_set():
                break
            for ch in ch_opts:
                try:
                    if is_input:
                        sd.check_input_settings(device=dev_idx, channels=ch, samplerate=sr, dtype="float32")
                    else:
                        sd.check_output_settings(device=dev_idx, channels=ch, samplerate=sr, dtype="float32")
                    valid.append((sr, ch))
                    break
                except Exception:
                    continue
        if not valid:
            def_sr = int(round(float(info.get("default_samplerate", 48000) or 48000)))
            valid.append((def_sr, ch_opts[0]))
        return valid

    def _start_pair(
        self,
        in_idx: int,
        out_idx: int,
        blocksize: int,
        monitor_idx: int | None,
        api_note: str = "",
    ) -> tuple[bool, str]:
        try:
            in_info = sd.query_devices(in_idx)
            out_info = sd.query_devices(out_idx)
        except Exception as exc:
            return False, f"Dispositivo inválido: {exc}"

        in_def = int(round(float(in_info.get("default_samplerate", 48000) or 48000)))
        out_def = int(round(float(out_info.get("default_samplerate", 48000) or 48000)))

        shared_srs = []
        for sr in [48000, in_def, out_def, 44100, 96000]:
            if sr > 0 and sr not in shared_srs:
                shared_srs.append(sr)

        in_ch_opts = [1, 2] if int(in_info["max_input_channels"]) >= 2 else [1]
        out_ch_opts = [2, 1] if int(out_info["max_output_channels"]) >= 2 else [1]

        # Tenta latência baixa com bloco pedido, depois bloco automático, depois latência alta (evita -9999 em USB/MME/WDM-KS)
        attempt_modes: list[tuple[int, str]] = []
        if blocksize > 0:
            attempt_modes.append((blocksize, "low"))
        attempt_modes.append((0, "low"))
        attempt_modes.append((0, "high"))

        in_ok_cache: dict[tuple[int, int], bool] = {}
        out_ok_cache: dict[tuple[int, int], bool] = {}

        def _check_in(sr_val: int, ch_val: int) -> bool:
            key = (sr_val, ch_val)
            if key not in in_ok_cache:
                try:
                    sd.check_input_settings(device=in_idx, channels=ch_val, samplerate=sr_val, dtype="float32")
                    in_ok_cache[key] = True
                except Exception:
                    in_ok_cache[key] = False
            return in_ok_cache[key]

        def _check_out(sr_val: int, ch_val: int) -> bool:
            key = (sr_val, ch_val)
            if key not in out_ok_cache:
                try:
                    sd.check_output_settings(device=out_idx, channels=ch_val, samplerate=sr_val, dtype="float32")
                    out_ok_cache[key] = True
                except Exception:
                    out_ok_cache[key] = False
            return out_ok_cache[key]

        last_err = ""
        # 1. Tenta stream duplex (menor latência quando Entrada e Saída aceitam a mesma taxa)
        for blk, lat_mode in attempt_modes:
            for sr in shared_srs:
                for in_ch in in_ch_opts:
                    if self._abort_event.is_set():
                        return False, "Interrompido"
                    if not _check_in(sr, in_ch):
                        continue
                    for out_ch in out_ch_opts:
                        if self._abort_event.is_set():
                            return False, "Interrompido"
                        if not _check_out(sr, out_ch):
                            continue
                        try:
                            self.dsp.set_sample_rate(sr)
                            self.active_sr = sr
                            self.active_out_sr = sr
                            self.active_block = blk if blk > 0 else blocksize

                            def duplex_cb(indata, outdata, frames, time_info, status, _sr=sr):
                                mono = indata[:, 0] if indata.ndim > 1 else indata
                                processed = self.dsp.process(mono)
                                if outdata.shape[1] == 1:
                                    outdata[:, 0] = processed
                                else:
                                    outdata[:] = processed[:, None]
                                if self.monitor_enabled:
                                    mon_chunk = _resample_linear(processed, _sr, self.active_mon_sr)
                                    self._mon_fifo.push(mon_chunk)

                            self._stream = sd.Stream(
                                device=(in_idx, out_idx),
                                samplerate=sr,
                                blocksize=blk,
                                channels=(in_ch, out_ch),
                                dtype="float32",
                                latency=lat_mode,
                                callback=duplex_cb,
                            )
                            self._stream.start()
                            self.running = True
                            self.last_used_in_idx = in_idx
                            self.last_used_out_idx = out_idx
                            eff_blk = blk if blk > 0 else blocksize
                            prefix = f"Ativo ({api_note}):" if api_note else "Ativo:"
                            msg = f"{prefix} {sr} Hz | Bloco {eff_blk} (~{eff_blk * 1000 / sr:.1f} ms)"
                            if self.monitor_enabled and monitor_idx is not None and monitor_idx != out_idx:
                                mon_err = self._start_monitor(monitor_idx, sr, blk)
                                if mon_err:
                                    self.monitor_enabled = False
                                    self._mon_fifo.clear()
                                    msg += f" | Monitor off: {mon_err}"
                            elif self.monitor_enabled and monitor_idx == out_idx:
                                self.monitor_enabled = False
                                self._mon_fifo.clear()
                            return True, msg
                        except Exception as e:
                            last_err = str(e)
                            if self._stream is not None:
                                try:
                                    self._stream.close()
                                except Exception:
                                    pass
                                self._stream = None

        if self._abort_event.is_set():
            return False, "Interrompido"

        # 2. Fallback: dois streams separados com taxa independente + resampling automático
        in_configs = self._find_supported_configs(
            in_idx, is_input=True, preferred_srs=[in_def, 48000, 44100], abort_event=self._abort_event
        )
        out_configs = self._find_supported_configs(
            out_idx, is_input=False, preferred_srs=[out_def, 48000, 44100], abort_event=self._abort_event
        )

        paired_configs: list[tuple[tuple[int, int], tuple[int, int]]] = []
        for ic in in_configs:
            for oc in out_configs:
                if ic[0] == oc[0]:
                    paired_configs.append((ic, oc))
        for ic in in_configs:
            for oc in out_configs:
                if ic[0] != oc[0]:
                    paired_configs.append((ic, oc))

        for blk, lat_mode in attempt_modes:
            for (in_sr, in_ch), (out_sr, out_ch) in paired_configs:
                if self._abort_event.is_set():
                    return False, "Interrompido"
                try:
                    self.dsp.set_sample_rate(in_sr)
                    self.active_sr = in_sr
                    self.active_out_sr = out_sr
                    self.active_block = blk if blk > 0 else blocksize
                    self._bridge_fifo.clear()

                    def in_cb(indata, frames, time_info, status, _in_sr=in_sr, _out_sr=out_sr):
                        mono = indata[:, 0] if indata.ndim > 1 else indata
                        processed = self.dsp.process(mono)
                        out_chunk = _resample_linear(processed, _in_sr, _out_sr)
                        self._bridge_fifo.push(out_chunk)
                        if self.monitor_enabled:
                            mon_chunk = _resample_linear(processed, _in_sr, self.active_mon_sr)
                            self._mon_fifo.push(mon_chunk)

                    def out_cb(outdata, frames, time_info, status):
                        out_buf = self._bridge_fifo.pop(frames)
                        if outdata.shape[1] == 1:
                            outdata[:, 0] = out_buf
                        else:
                            outdata[:] = out_buf[:, None]

                    self._in_stream = sd.InputStream(
                        device=in_idx,
                        samplerate=in_sr,
                        blocksize=blk,
                        channels=in_ch,
                        dtype="float32",
                        latency=lat_mode,
                        callback=in_cb,
                    )
                    self._out_stream = sd.OutputStream(
                        device=out_idx,
                        samplerate=out_sr,
                        blocksize=blk,
                        channels=out_ch,
                        dtype="float32",
                        latency=lat_mode,
                        callback=out_cb,
                    )
                    self._in_stream.start()
                    self._out_stream.start()
                    self.running = True
                    self.last_used_in_idx = in_idx
                    self.last_used_out_idx = out_idx
                    sr_txt = f"{in_sr} Hz" if in_sr == out_sr else f"{in_sr}→{out_sr} Hz"
                    eff_blk = blk if blk > 0 else blocksize
                    prefix = f"Ativo (Ponte • {api_note}):" if api_note else "Ativo (Ponte):"
                    msg = f"{prefix} {sr_txt} | Bloco {eff_blk}"
                    if self.monitor_enabled and monitor_idx is not None and monitor_idx != out_idx:
                        mon_err = self._start_monitor(monitor_idx, out_sr, blk)
                        if mon_err:
                            self.monitor_enabled = False
                            self._mon_fifo.clear()
                            msg += f" | Monitor off: {mon_err}"
                    elif self.monitor_enabled and monitor_idx == out_idx:
                        self.monitor_enabled = False
                        self._mon_fifo.clear()
                    return True, msg
                except Exception as e:
                    last_err = str(e)
                    self._stop_unlocked()

        return False, last_err

    def start(
        self,
        in_idx: int,
        out_idx: int,
        blocksize: int = 512,
        monitor_enabled: bool = False,
        monitor_idx: int | None = None,
    ) -> tuple[bool, str]:
        with self._op_lock:
            self._abort_event.clear()
            self._stop_unlocked()
            self.last_used_in_idx = None
            self.last_used_out_idx = None
            self.monitor_enabled = monitor_enabled and (monitor_idx is not None) and (monitor_idx != out_idx)
            self._bridge_fifo.clear()
            self._mon_fifo.clear()

            # 1. Tenta o par exato selecionado pelo usuário
            ok, msg = self._start_pair(in_idx, out_idx, blocksize, monitor_idx)
            if ok or self._abort_event.is_set():
                return ok, msg

            first_err = msg
            # 2. Fallback automático para o mesmo dispositivo em APIs mais estáveis (WASAPI -> DirectSound -> MME)
            in_cands = self._equivalent_device_indices(in_idx, is_input=True)
            out_cands = self._equivalent_device_indices(out_idx, is_input=False)

            try:
                devs = sd.query_devices()
                hostapis = sd.query_hostapis()
            except Exception:
                devs, hostapis = [], []

            def _dev_api(d_idx: int) -> str:
                try:
                    return _short_hostapi(str(hostapis[devs[d_idx]["hostapi"]]["name"]))
                except Exception:
                    return ""

            # Ordena pares alternativos favorecendo mesma Host API (WASAPI+WASAPI etc.)
            alt_pairs: list[tuple[int, int, int, int, int, str]] = []
            for rank_i, ci in enumerate(in_cands):
                for rank_o, co in enumerate(out_cands):
                    if ci == in_idx and co == out_idx:
                        continue
                    api_i = _dev_api(ci)
                    api_o = _dev_api(co)
                    same_api_pen = 0 if (api_i and api_i == api_o) else 1
                    api_note = api_i if api_i == api_o else f"{api_i}/{api_o}".strip("/")
                    alt_pairs.append((same_api_pen, _hostapi_rank(api_i) + _hostapi_rank(api_o), rank_i + rank_o, ci, co, api_note))

            alt_pairs.sort()
            last_err = first_err
            for _, _, _, ci, co, api_note in alt_pairs[:8]:
                if self._abort_event.is_set():
                    return False, "Interrompido"
                self._stop_unlocked()
                ok, msg = self._start_pair(ci, co, blocksize, monitor_idx, api_note=api_note)
                if ok:
                    return True, msg
                if msg:
                    last_err = msg

            return False, f"Falha ao iniciar áudio: {first_err or last_err}"

    def _start_monitor(self, monitor_idx: int, preferred_sr: int, blocksize: int) -> str | None:
        cand_indices = self._equivalent_device_indices(monitor_idx, is_input=False)
        last_err = ""
        blk_opts = [(blocksize, "low"), (0, "low"), (0, "high")] if blocksize > 0 else [(0, "low"), (0, "high")]

        for m_idx in cand_indices[:4]:
            try:
                configs = self._find_supported_configs(
                    m_idx, is_input=False, preferred_srs=[preferred_sr, 48000, 44100], abort_event=self._abort_event
                )
            except Exception as exc:
                last_err = str(exc)
                continue
            for blk, lat_mode in blk_opts:
                for mon_sr, ch in configs:
                    if self._abort_event.is_set():
                        return "Interrompido"
                    try:
                        self.active_mon_sr = mon_sr
                        self._mon_fifo.clear()

                        def mon_cb(outdata, frames, time_info, status):
                            chunk = self._mon_fifo.pop(frames)
                            if outdata.shape[1] == 1:
                                outdata[:, 0] = chunk
                            else:
                                outdata[:] = chunk[:, None]

                        self._mon_stream = sd.OutputStream(
                            device=m_idx,
                            samplerate=mon_sr,
                            blocksize=blk,
                            channels=ch,
                            dtype="float32",
                            latency=lat_mode,
                            callback=mon_cb,
                        )
                        self._mon_stream.start()
                        return None
                    except Exception as e:
                        last_err = str(e)
                        if self._mon_stream is not None:
                            try:
                                self._mon_stream.close()
                            except Exception:
                                pass
                            self._mon_stream = None
        return last_err or "Erro no monitor"

    def _stop_unlocked(self):
        self.running = False
        streams = (self._stream, self._in_stream, self._out_stream, self._mon_stream)
        self._stream = None
        self._in_stream = None
        self._out_stream = None
        self._mon_stream = None
        for s in streams:
            if s is not None:
                try:
                    s.stop()
                except Exception:
                    pass
                try:
                    s.close()
                except Exception:
                    pass
        self._bridge_fifo.clear()
        self._mon_fifo.clear()

    def stop(self):
        self._abort_event.set()
        with self._op_lock:
            self._stop_unlocked()
