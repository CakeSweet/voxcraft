from dataclasses import dataclass, asdict
import threading
import numpy as np
from scipy import signal
from .noise_suppressor import StreamingNoiseSuppressor


@dataclass
class DSPParams:
    # Controle geral
    bypass: bool = False
    input_gain_db: float = 0.0
    output_gain_db: float = 0.0

    # Supressão de ruído e compressor
    noise_suppression_level: int = 2  # Supressão espectral Python: 0–3
    gate_threshold_db: float = -44.0
    comp_enabled: bool = True
    comp_threshold_db: float = -18.0
    comp_ratio: float = 4.0

    # Alterar Tom (Pitch Shifter estilo Audacity)
    pitch_enabled: bool = False
    pitch_semitones: float = 0.0   # -12.0 a +12.0
    pitch_cents: float = 0.0       # -100.0 a +100.0
    pitch_mix: float = 1.0         # 0.0 a 1.0

    # Frequency Shifter (Deslocamento linear em Hz - Hilbert SSB)
    freq_shift_enabled: bool = False
    freq_shift_hz: float = 0.0     # -500.0 a +500.0 Hz
    freq_shift_mix: float = 1.0

    # Vocoder (estilo Audacity - Filtro de 12 Bandas)
    vocoder_enabled: bool = False
    vocoder_carrier: str = "Dente de Serra"  # "Dente de Serra", "Acorde", "Quadrada", "Sussurro (Ruído)"
    vocoder_freq_hz: float = 110.0           # 55 a 300 Hz
    vocoder_smooth: float = 0.45             # 0.1 a 0.95 (suavidade do envelope)
    vocoder_mix: float = 0.85

    # Equalizador (Filtro + 5 Bandas estilo Audacity)
    eq_enabled: bool = True
    eq_hpf_enabled: bool = True
    eq_hpf_hz: float = 80.0        # Corte de graves (Low-Cut)
    eq_lpf_enabled: bool = False
    eq_lpf_hz: float = 12000.0     # Corte de agudos (High-Cut)
    eq_band1_db: float = 0.0       # Grave (120 Hz)
    eq_band2_db: float = 0.0       # Médio-Grave (400 Hz)
    eq_band3_db: float = 0.0       # Médio / Presença (1200 Hz)
    eq_band4_db: float = 0.0       # Médio-Agudo (3500 Hz)
    eq_band5_db: float = 0.0       # Agudo / Brilho (7500 Hz)

    # Chorus / Flanger (Duplicador de Voz)
    chorus_enabled: bool = False
    chorus_rate_hz: float = 1.2    # 0.1 a 8.0 Hz
    chorus_delay_ms: float = 14.0  # 1.5 a 35.0 ms (<8 ms = Flanger, >=10 ms = Chorus)
    chorus_depth_ms: float = 4.5   # 0.5 a 15.0 ms
    chorus_feedback: float = 0.25  # 0.0 a 0.85
    chorus_mix: float = 0.5

    # Phaser (estilo Audacity)
    phaser_enabled: bool = False
    phaser_stages: int = 6         # 2, 4, 6, 8, 10, 12
    phaser_freq_hz: float = 0.8    # 0.1 a 6.0 Hz
    phaser_depth: float = 0.7      # 0.0 a 1.0
    phaser_feedback: float = 0.45  # -0.90 a +0.90
    phaser_mix: float = 0.6

    # Wahwah (estilo Audacity)
    wah_enabled: bool = False
    wah_freq_hz: float = 1.5       # 0.2 a 8.0 Hz
    wah_depth: float = 0.75        # 0.0 a 1.0
    wah_resonance: float = 2.8     # 0.5 a 8.0 Q
    wah_mix: float = 0.75

    # Tremolo (estilo Audacity)
    tremolo_enabled: bool = False
    tremolo_freq_hz: float = 6.0   # 0.5 a 25.0 Hz
    tremolo_waveform: str = "Senoide"  # "Senoide", "Triangular", "Quadrada", "Dente de Serra"
    tremolo_depth: float = 0.65    # 0.0 a 1.0

    # Modulador em Anel (Robô / Alien)
    ring_enabled: bool = False
    ring_freq_hz: float = 60.0     # 5 a 400 Hz
    ring_waveform: str = "Senoide" # "Senoide", "Quadrada", "Triangular"
    ring_mix: float = 0.7

    # Distorção & Lo-Fi / Rádio (Overdrive + Bitcrusher)
    dist_enabled: bool = False
    dist_drive: float = 3.0        # 1.0 a 25.0
    dist_bits: int = 16            # 4 a 16 bits
    dist_downsample: int = 1       # 1 a 16x
    dist_mix: float = 0.7

    # Eco / Delay (serve para capacete/tubo em ms curtos ou caverna em ms longos)
    echo_enabled: bool = False
    echo_delay_ms: float = 220.0   # 10 a 700 ms
    echo_feedback: float = 0.35    # 0.0 a 0.85
    echo_mix: float = 0.35

    # Reverb (Espaço / Sala)
    reverb_enabled: bool = False
    reverb_room: float = 0.6       # 0.0 a 1.0
    reverb_damp: float = 0.45      # 0.0 a 1.0
    reverb_mix: float = 0.3

    def __post_init__(self):
        if (
            type(self.noise_suppression_level) is not int
            or self.noise_suppression_level not in range(4)
        ):
            raise ValueError("O nível da supressão de ruído precisa estar entre 0 e 3.")

    def copy(self) -> "DSPParams":
        return DSPParams(**asdict(self))


def _biquad_lowpass(fc: float, q: float, fs: float) -> list[float]:
    fc = np.clip(fc, 20.0, fs * 0.48)
    w0 = 2.0 * np.pi * fc / fs
    alpha = np.sin(w0) / (2.0 * q)
    cos_w0 = np.cos(w0)
    b0 = (1.0 - cos_w0) / 2.0
    b1 = 1.0 - cos_w0
    b2 = (1.0 - cos_w0) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha
    return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]


def _biquad_highpass(fc: float, q: float, fs: float) -> list[float]:
    fc = np.clip(fc, 20.0, fs * 0.48)
    w0 = 2.0 * np.pi * fc / fs
    alpha = np.sin(w0) / (2.0 * q)
    cos_w0 = np.cos(w0)
    b0 = (1.0 + cos_w0) / 2.0
    b1 = -(1.0 + cos_w0)
    b2 = (1.0 + cos_w0) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha
    return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]


def _biquad_peaking(fc: float, gain_db: float, q: float, fs: float) -> list[float]:
    fc = np.clip(fc, 20.0, fs * 0.48)
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * fc / fs
    alpha = np.sin(w0) / (2.0 * q)
    cos_w0 = np.cos(w0)
    b0 = 1.0 + alpha * A
    b1 = -2.0 * cos_w0
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha / A
    return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]


def _biquad_low_shelf(fc: float, gain_db: float, fs: float, slope: float = 0.85) -> list[float]:
    fc = np.clip(fc, 20.0, fs * 0.48)
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * fc / fs
    cos_w0 = np.cos(w0)
    sin_w0 = np.sin(w0)
    alpha = sin_w0 / 2.0 * np.sqrt((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0)
    sqrt_A2 = 2.0 * np.sqrt(A) * alpha
    b0 = A * ((A + 1.0) - (A - 1.0) * cos_w0 + sqrt_A2)
    b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w0)
    b2 = A * ((A + 1.0) - (A - 1.0) * cos_w0 - sqrt_A2)
    a0 = (A + 1.0) + (A - 1.0) * cos_w0 + sqrt_A2
    a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w0)
    a2 = (A + 1.0) + (A - 1.0) * cos_w0 - sqrt_A2
    return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]


def _biquad_high_shelf(fc: float, gain_db: float, fs: float, slope: float = 0.85) -> list[float]:
    fc = np.clip(fc, 20.0, fs * 0.48)
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * fc / fs
    cos_w0 = np.cos(w0)
    sin_w0 = np.sin(w0)
    alpha = sin_w0 / 2.0 * np.sqrt((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0)
    sqrt_A2 = 2.0 * np.sqrt(A) * alpha
    b0 = A * ((A + 1.0) + (A - 1.0) * cos_w0 + sqrt_A2)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)
    b2 = A * ((A + 1.0) + (A - 1.0) * cos_w0 - sqrt_A2)
    a0 = (A + 1.0) - (A - 1.0) * cos_w0 + sqrt_A2
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)
    a2 = (A + 1.0) - (A - 1.0) * cos_w0 - sqrt_A2
    return [b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]


def build_eq_sos(p: DSPParams, fs: float) -> np.ndarray:
    rows = []
    if p.eq_hpf_enabled:
        rows.append(_biquad_highpass(p.eq_hpf_hz, 0.707, fs))
    else:
        rows.append([1.0, 0.0, 0.0, 1.0, 0.0, 0.0])

    rows.append(_biquad_low_shelf(120.0, p.eq_band1_db, fs))
    rows.append(_biquad_peaking(400.0, p.eq_band2_db, 1.0, fs))
    rows.append(_biquad_peaking(1200.0, p.eq_band3_db, 1.0, fs))
    rows.append(_biquad_peaking(3500.0, p.eq_band4_db, 1.0, fs))
    rows.append(_biquad_high_shelf(7500.0, p.eq_band5_db, fs))

    if p.eq_lpf_enabled:
        rows.append(_biquad_lowpass(p.eq_lpf_hz, 0.707, fs))
    else:
        rows.append([1.0, 0.0, 0.0, 1.0, 0.0, 0.0])

    return np.asarray(rows, dtype=np.float64)


class RingDelay:
    """Buffer circular vetorizado de baixa alocação para Eco, Chorus/Flanger e Reverb."""

    def __init__(self, max_samples: int):
        self.size = int(max_samples)
        self.buf = np.zeros(self.size, dtype=np.float32)
        self.write_idx = 0
        self._scratch = np.zeros(512, dtype=np.float32)
        self._ramp = np.arange(512, dtype=np.float64)

    def clear(self):
        self.buf.fill(0.0)
        self.write_idx = 0

    def _get_ramp(self, length: int) -> np.ndarray:
        if length > len(self._ramp):
            self._ramp = np.arange(length, dtype=np.float64)
        return self._ramp[:length]

    def read_chunk(self, delay_samples: int, length: int) -> np.ndarray:
        delay = max(1, min(delay_samples, self.size - 1))
        start = (self.write_idx - delay) % self.size
        end = start + length
        if end <= self.size:
            return self.buf[start:end]
        if length > len(self._scratch):
            self._scratch = np.empty(length, dtype=np.float32)
        first = self.size - start
        self._scratch[:first] = self.buf[start:]
        self._scratch[first:length] = self.buf[:length - first]
        return self._scratch[:length]

    def read_frac_chunk(self, delays: np.ndarray) -> np.ndarray:
        """Lê um chunk com atrasos fracionários por amostra (interpolação linear)."""
        length = len(delays)
        d = np.clip(delays, 1.0, float(self.size - 2))
        read_pos = (self.write_idx + self._get_ramp(length) - d) % self.size
        i0 = np.floor(read_pos).astype(np.int32) % self.size
        i1 = i0 + 1
        i1[i1 >= self.size] = 0
        frac = (read_pos - i0).astype(np.float32)
        return self.buf[i0] * (1.0 - frac) + self.buf[i1] * frac

    def write_chunk(self, data: np.ndarray):
        length = len(data)
        if length >= self.size:
            self.buf[:] = data[-self.size:]
            self.write_idx = 0
            return
        end = self.write_idx + length
        if end <= self.size:
            self.buf[self.write_idx:end] = data
            self.write_idx = 0 if end == self.size else end
        else:
            first = self.size - self.write_idx
            self.buf[self.write_idx:] = data[:first]
            rest = length - first
            self.buf[:rest] = data[first:]
            self.write_idx = rest


class RealTimeDSPEngine:
    def __init__(self, sample_rate: float = 48000.0):
        self._lock = threading.Lock()
        self.params = DSPParams()
        self.sr = float(sample_rate)

        # Métricas para a UI
        self.input_peak_db = -60.0
        self.output_peak_db = -60.0
        self.last_waveform = np.zeros(256, dtype=np.float32)
        self._ramp_f64 = np.arange(2048, dtype=np.float64)

        self._pending_clear = False
        self._init_states()

    def _get_ramp_f64(self, n: int) -> np.ndarray:
        if n > len(self._ramp_f64):
            self._ramp_f64 = np.arange(n, dtype=np.float64)
        return self._ramp_f64[:n]

    def set_sample_rate(self, sample_rate: float):
        with self._lock:
            if abs(self.sr - float(sample_rate)) > 1.0:
                self.sr = float(sample_rate)
                self._init_states()

    def update_params(self, new_params: DSPParams):
        with self._lock:
            prev_bypass = bool(self.params.bypass)
            prev_noise_suppression_level = self.params.noise_suppression_level
            self.params = new_params.copy()
            self._eq_dirty = True
            if bool(self.params.bypass) != prev_bypass:
                self._pending_clear = True
            if self.params.noise_suppression_level != prev_noise_suppression_level:
                self._noise_suppressor = StreamingNoiseSuppressor(
                    self.sr, level=self.params.noise_suppression_level
                )

    def clear_effect_buffers(self):
        with self._lock:
            self._pending_clear = True

    def _init_states(self):
        sr = self.sr
        self._noise_suppressor = StreamingNoiseSuppressor(
            sr, level=self.params.noise_suppression_level
        )

        # Noise Gate
        self._gate_gain = 1.0
        self._gate_hold_counter = 0
        self.gate_is_open = True

        # Compressor
        self._comp_gain = 1.0

        # Pitch Shifter (Dual-Tap Delay Line, janela ~45ms)
        self._pitch_w = int(0.045 * sr)
        self._pitch_hist = np.zeros(self._pitch_w + 16, dtype=np.float32)
        self._pitch_phase = 0.0

        # Frequency Shifter (Hilbert FIR de 65 taps)
        n_tap = 65
        m = (n_tap - 1) // 2
        k = np.arange(n_tap) - m
        h = np.zeros(n_tap, dtype=np.float64)
        odd = (k % 2) != 0
        h[odd] = 2.0 / (np.pi * k[odd])
        h *= np.blackman(n_tap)
        self._hilb_b = h
        self._hilb_zi = np.zeros(n_tap - 1, dtype=np.float64)
        self._hilb_delay_buf = np.zeros(m, dtype=np.float32)
        self._hilb_delay_len = m
        self._fshift_phase = 0.0

        # Vocoder (12 bandas logarítmicas de 150 Hz a 5500 Hz)
        edges = np.geomspace(150.0, min(5500.0, sr * 0.44), 13)
        self._voc_sos = []
        self._voc_mod_zi = []
        self._voc_car_zi = []
        self._voc_env_zi = []
        for i in range(12):
            sos = signal.butter(2, [edges[i], edges[i + 1]], btype="bandpass", fs=sr, output="sos")
            self._voc_sos.append(sos)
            self._voc_mod_zi.append(np.zeros((sos.shape[0], 2), dtype=np.float64))
            self._voc_car_zi.append(np.zeros((sos.shape[0], 2), dtype=np.float64))
            self._voc_env_zi.append(np.zeros(1, dtype=np.float64))
        self._voc_phase1 = 0.0
        self._voc_phase2 = 0.0
        self._voc_phase3 = 0.0
        self._voc_last_smooth = -1.0
        self._voc_env_ba = None

        # Equalizador SOS (7 estágios biquad)
        self._eq_sos = build_eq_sos(self.params, sr)
        self._eq_zi = np.zeros((7, 2), dtype=np.float64)
        self._eq_dirty = False

        # Chorus / Flanger
        self._chorus_ring = RingDelay(int(0.12 * sr))
        self._chorus_phase = 0.0

        # Phaser (até 12 estágios all-pass em matriz SOS para 1 chamada C por chunk)
        self._phaser_phase = 0.0
        self._phaser_sos = np.zeros((12, 6), dtype=np.float64)
        self._phaser_sos[:, 1] = 1.0
        self._phaser_sos[:, 3] = 1.0
        self._phaser_zi = np.zeros((12, 2), dtype=np.float64)
        self._phaser_fb_sample = 0.0

        # Wahwah (biquad bandpass ressonante)
        self._wah_phase = 0.0
        self._wah_zi = np.zeros(2, dtype=np.float64)
        self._wah_b = np.zeros(3, dtype=np.float64)
        self._wah_a = np.array([1.0, 0.0, 0.0], dtype=np.float64)

        # Tremolo
        self._trem_phase = 0.0

        # Ring Modulator
        self._ring_phase = 0.0

        # Bitcrusher Downsample state
        self._bc_counter = 0
        self._bc_hold = 0.0

        # Echo
        self._echo_ring = RingDelay(int(1.2 * sr))
        self._echo_lp_zi = np.zeros(1, dtype=np.float64)
        self._echo_lp_b, self._echo_lp_a = self._onepole_lp(4800.0, sr)

        # Reverb (4 Comb paralelos + 2 All-pass em série)
        comb_base = [1116, 1188, 1277, 1356]
        ap_base = [556, 441]
        self._comb_delays = [max(64, int(d * sr / 44100.0)) for d in comb_base]
        self._ap_delays = [max(64, int(d * sr / 44100.0)) for d in ap_base]
        self._comb_rings = [RingDelay(d + 2048) for d in self._comb_delays]
        self._comb_lp_state = [np.zeros(1, dtype=np.float64) for _ in self._comb_delays]
        self._ap_rings = [RingDelay(d + 2048) for d in self._ap_delays]
        self._rev_lp_b = np.array([0.55], dtype=np.float64)
        self._rev_lp_a = np.array([1.0, -0.45], dtype=np.float64)
        self._rev_comb_sum = np.zeros(512, dtype=np.float32)
        self._was_bypass = bool(self.params.bypass)

    def _clear_effect_buffers_unlocked(self):
        self._noise_suppressor.reset()
        self._gate_gain = 1.0
        self._gate_hold_counter = 0
        self.gate_is_open = True
        self._pitch_hist.fill(0.0)
        self._pitch_phase = 0.0
        self._hilb_zi.fill(0.0)
        self._hilb_delay_buf.fill(0.0)
        self._fshift_phase = 0.0
        for arr in self._voc_mod_zi:
            arr.fill(0.0)
        for arr in self._voc_car_zi:
            arr.fill(0.0)
        for arr in self._voc_env_zi:
            arr.fill(0.0)
        self._voc_phase1 = 0.0
        self._voc_phase2 = 0.0
        self._voc_phase3 = 0.0
        self._eq_zi.fill(0.0)
        self._chorus_ring.clear()
        self._chorus_phase = 0.0
        self._phaser_phase = 0.0
        self._phaser_zi.fill(0.0)
        self._phaser_fb_sample = 0.0
        self._wah_phase = 0.0
        self._wah_zi.fill(0.0)
        self._trem_phase = 0.0
        self._ring_phase = 0.0
        self._bc_counter = 0
        self._bc_hold = 0.0
        self._echo_ring.clear()
        self._echo_lp_zi.fill(0.0)
        for ring in self._comb_rings:
            ring.clear()
        for st in self._comb_lp_state:
            st.fill(0.0)
        for ring in self._ap_rings:
            ring.clear()

    @staticmethod
    def _onepole_lp(fc: float, fs: float):
        x = np.exp(-2.0 * np.pi * fc / fs)
        return np.array([1.0 - x], dtype=np.float64), np.array([1.0, -x], dtype=np.float64)

    @staticmethod
    def _peak_db(x: np.ndarray) -> float:
        pk = float(np.max(np.abs(x))) if len(x) > 0 else 0.0
        return max(-60.0, 20.0 * np.log10(pk + 1e-7))

    def process(self, mono_in: np.ndarray) -> np.ndarray:
        x = mono_in.astype(np.float32, copy=True)
        n = len(x)
        if n == 0:
            return x

        with self._lock:
            p = self.params
            if self._eq_dirty:
                self._eq_sos = build_eq_sos(p, self.sr)
                self._eq_dirty = False
            if self._pending_clear:
                self._clear_effect_buffers_unlocked()
                self._pending_clear = False
                self._was_bypass = bool(p.bypass)

            # Medidor de entrada (pré-efeitos)
            in_db = self._peak_db(x)
            self.input_peak_db = 0.65 * self.input_peak_db + 0.35 * in_db

            if abs(p.input_gain_db) > 0.05:
                x *= 10.0 ** (p.input_gain_db / 20.0)

            if p.bypass:
                if not self._was_bypass:
                    self._clear_effect_buffers_unlocked()
                    self._was_bypass = True
                self.gate_is_open = True
            else:
                if self._was_bypass:
                    self._clear_effect_buffers_unlocked()
                    self._was_bypass = False
                x = self._process_chain_unlocked(x, p)

            if abs(p.output_gain_db) > 0.05:
                x *= 10.0 ** (p.output_gain_db / 20.0)

            if p.bypass:
                # Mantém a voz original linear, limitando apenas amostras fora da faixa.
                np.clip(x, -1.0, 1.0, out=x)
            else:
                x = np.tanh(x * 0.92).astype(np.float32) * 0.98

            out_db = self._peak_db(x)
            self.output_peak_db = 0.65 * self.output_peak_db + 0.35 * out_db
            self._update_waveform(x)
            return x

    def _process_chain_unlocked(self, x: np.ndarray, p: DSPParams) -> np.ndarray:
        n = len(x)

        # 1. Supressão espectral adaptativa em Python; preserva quadros entre callbacks.
        x = self._noise_suppressor.process(x)

        # 2. Noise Gate depois da supressão, antes do compressor.
        x = self._apply_noise_gate_unlocked(x, p.gate_threshold_db)

        # 3. Compressor
        rms = float(np.sqrt(np.mean(x * x) + 1e-12))
        lvl_db = 20.0 * np.log10(rms)
        if lvl_db > p.comp_threshold_db:
            over = lvl_db - p.comp_threshold_db
            reduced_db = over * (1.0 - 1.0 / max(1.1, p.comp_ratio))
            target_cg = 10.0 ** (-reduced_db / 20.0)
        else:
            target_cg = 1.0
        # Auto makeup leve
        makeup = 10.0 ** (min(8.0, max(0.0, (-p.comp_threshold_db - 10.0) * 0.22)) / 20.0)
        target_cg *= makeup
        c_coeff = 0.35 if target_cg < self._comp_gain else 0.12
        next_cg = self._comp_gain + c_coeff * (target_cg - self._comp_gain)
        x *= np.linspace(self._comp_gain, next_cg, n, dtype=np.float32)
        self._comp_gain = float(next_cg)

        # 4. Pitch Shifter (Alterar Tom estilo Audacity)
        total_st = p.pitch_semitones + p.pitch_cents / 100.0
        if p.pitch_enabled and abs(total_st) > 0.02 and p.pitch_mix > 0.01:
            wet = self._process_pitch_shift(x, total_st)
            x = x * (1.0 - p.pitch_mix) + wet * p.pitch_mix

        # 5. Frequency Shifter (Deslocamento Linear em Hz via Hilbert SSB)
        if p.freq_shift_enabled and abs(p.freq_shift_hz) > 0.5 and p.freq_shift_mix > 0.01:
            wet = self._process_freq_shift(x, p.freq_shift_hz)
            x = x * (1.0 - p.freq_shift_mix) + wet * p.freq_shift_mix

        # 6. Vocoder (estilo Audacity)
        if p.vocoder_enabled and p.vocoder_mix > 0.01:
            wet = self._process_vocoder(x, p.vocoder_carrier, p.vocoder_freq_hz, p.vocoder_smooth)
            x = x * (1.0 - p.vocoder_mix) + wet * p.vocoder_mix

        # 7. Equalizador (HPF + 5 Bandas + LPF)
        if p.eq_enabled:
            y_eq, self._eq_zi = signal.sosfilt(self._eq_sos, x, zi=self._eq_zi)
            x = y_eq.astype(np.float32)

        # 8. Wahwah (estilo Audacity)
        if p.wah_enabled and p.wah_mix > 0.01:
            wet = self._process_wah(x, p.wah_freq_hz, p.wah_depth, p.wah_resonance)
            x = x * (1.0 - p.wah_mix) + wet * p.wah_mix

        # 9. Phaser (estilo Audacity)
        if p.phaser_enabled and p.phaser_mix > 0.01:
            wet = self._process_phaser(x, p.phaser_stages, p.phaser_freq_hz, p.phaser_depth, p.phaser_feedback)
            x = x * (1.0 - p.phaser_mix) + wet * p.phaser_mix

        # 10. Chorus / Flanger
        if p.chorus_enabled and p.chorus_mix > 0.01:
            wet = self._process_chorus(x, p.chorus_rate_hz, p.chorus_delay_ms, p.chorus_depth_ms, p.chorus_feedback)
            x = x * (1.0 - p.chorus_mix) + wet * p.chorus_mix

        # 11. Modulador em Anel (Robô / Alien)
        if p.ring_enabled and p.ring_mix > 0.01:
            wet = self._process_ring_mod(x, p.ring_freq_hz, p.ring_waveform)
            x = x * (1.0 - p.ring_mix) + wet * p.ring_mix

        # 12. Tremolo (estilo Audacity)
        if p.tremolo_enabled and p.tremolo_depth > 0.01:
            x = self._process_tremolo(x, p.tremolo_freq_hz, p.tremolo_waveform, p.tremolo_depth)

        # 13. Distorção & Bitcrusher (Rádio / Mega-fone)
        if p.dist_enabled and p.dist_mix > 0.01:
            wet = self._process_distortion(x, p.dist_drive, p.dist_bits, p.dist_downsample)
            x = x * (1.0 - p.dist_mix) + wet * p.dist_mix

        # 14. Eco / Delay
        if p.echo_enabled and p.echo_mix > 0.01:
            x = self._process_echo(x, p.echo_delay_ms, p.echo_feedback, p.echo_mix)

        # 15. Reverb
        if p.reverb_enabled and p.reverb_mix > 0.01:
            x = self._process_reverb(x, p.reverb_room, p.reverb_damp, p.reverb_mix)

        return x

    def _apply_noise_gate_unlocked(self, x: np.ndarray, threshold_db: float) -> np.ndarray:
        n = len(x)
        rms = float(np.sqrt(np.mean(x * x) + 1e-12))
        rms_db = 20.0 * np.log10(rms)
        hold_blocks = max(1, int(0.14 * self.sr / n))

        if rms_db >= threshold_db:
            self._gate_hold_counter = hold_blocks
            target_gain = 1.0
            self.gate_is_open = True
        elif self._gate_hold_counter > 0:
            self._gate_hold_counter -= 1
            target_gain = 1.0
            self.gate_is_open = True
        else:
            target_gain = 0.0005  # atenua até aproximadamente -66 dB
            self.gate_is_open = False

        coefficient = 0.45 if target_gain > self._gate_gain else 0.22
        next_gain = self._gate_gain + coefficient * (target_gain - self._gate_gain)
        x *= np.linspace(self._gate_gain, next_gain, n, dtype=np.float32)
        self._gate_gain = float(next_gain)
        return x

    def _update_waveform(self, x: np.ndarray):
        if len(x) >= 256:
            step = max(1, len(x) // 256)
            self.last_waveform = x[::step][:256].copy()
        else:
            pad = np.zeros(256, dtype=np.float32)
            pad[:len(x)] = x
            self.last_waveform = pad

    def _process_pitch_shift(self, x: np.ndarray, semitones: float) -> np.ndarray:
        n = len(x)
        w = self._pitch_w
        alpha = 2.0 ** (semitones / 12.0)
        dphi = (alpha - 1.0) / float(w)

        buf = np.concatenate([self._pitch_hist, x])
        m = len(self._pitch_hist)

        ramp = self._get_ramp_f64(n)
        phi1 = (self._pitch_phase + ramp * dphi) % 1.0
        phi2 = (phi1 + 0.5) % 1.0
        self._pitch_phase = float((self._pitch_phase + n * dphi) % 1.0)

        d1 = (1.0 - phi1) * w + 2.0
        d2 = (1.0 - phi2) * w + 2.0

        idx = ramp + m
        pos1 = idx - d1
        pos2 = idx - d2

        i1 = pos1.astype(np.int32)
        f1 = (pos1 - i1).astype(np.float32)
        i2 = pos2.astype(np.int32)
        f2 = (pos2 - i2).astype(np.float32)

        y1 = buf[i1] * (1.0 - f1) + buf[i1 + 1] * f1
        y2 = buf[i2] * (1.0 - f2) + buf[i2 + 1] * f2

        w1 = (np.sin(np.pi * phi1) ** 2).astype(np.float32)
        w2 = (1.0 - w1)

        self._pitch_hist = buf[-m:].copy()
        return y1 * w1 + y2 * w2

    def _process_freq_shift(self, x: np.ndarray, shift_hz: float) -> np.ndarray:
        n = len(x)
        # Ramo real atrasado exatamente M amostras
        buf = np.concatenate([self._hilb_delay_buf, x])
        x_del = buf[:-self._hilb_delay_len]
        self._hilb_delay_buf = buf[-self._hilb_delay_len:].copy()

        # Ramo imaginário (Transformada de Hilbert FIR)
        x_hilb, self._hilb_zi = signal.lfilter(self._hilb_b, [1.0], x, zi=self._hilb_zi)

        # Oscilador complexo contínuo entre blocos
        dphi = 2.0 * np.pi * shift_hz / self.sr
        phases = self._fshift_phase + self._get_ramp_f64(n) * dphi
        self._fshift_phase = float((self._fshift_phase + n * dphi) % (2.0 * np.pi))

        out = x_del * np.cos(phases) - x_hilb * np.sin(phases)
        return out.astype(np.float32)

    def _process_vocoder(self, x: np.ndarray, carrier_type: str, freq_hz: float, smooth: float) -> np.ndarray:
        n = len(x)
        f1 = max(40.0, float(freq_hz))
        d1 = f1 / self.sr
        ramp = self._get_ramp_f64(n)
        p1 = (self._voc_phase1 + ramp * d1) % 1.0
        self._voc_phase1 = float((self._voc_phase1 + n * d1) % 1.0)

        if carrier_type == "Quadrada":
            car = np.where(p1 < 0.5, 0.7, -0.7).astype(np.float32)
        elif carrier_type == "Acorde":
            d2 = (f1 * 1.25) / self.sr
            d3 = (f1 * 1.50) / self.sr
            p2 = (self._voc_phase2 + ramp * d2) % 1.0
            p3 = (self._voc_phase3 + ramp * d3) % 1.0
            self._voc_phase2 = float((self._voc_phase2 + n * d2) % 1.0)
            self._voc_phase3 = float((self._voc_phase3 + n * d3) % 1.0)
            car = (0.35 * ((2.0 * p1 - 1.0) + (2.0 * p2 - 1.0) + (2.0 * p3 - 1.0))).astype(np.float32)
        elif carrier_type == "Sussurro (Ruído)":
            car = np.random.uniform(-0.85, 0.85, n).astype(np.float32)
        else:
            # Dente de Serra
            car = (2.0 * p1 - 1.0).astype(np.float32)

        # Filtro passa-baixa de envelope (suavidade) em cache
        sm = float(np.clip(smooth, 0.05, 0.95))
        if abs(sm - self._voc_last_smooth) > 1e-4 or self._voc_env_ba is None:
            env_fc = 8.0 + (1.0 - sm) * 55.0
            self._voc_env_ba = self._onepole_lp(env_fc, self.sr)
            self._voc_last_smooth = sm
        env_b, env_a = self._voc_env_ba

        out = np.zeros(n, dtype=np.float64)
        for i in range(12):
            sos = self._voc_sos[i]
            v_band, self._voc_mod_zi[i] = signal.sosfilt(sos, x, zi=self._voc_mod_zi[i])
            env, self._voc_env_zi[i] = signal.lfilter(env_b, env_a, np.abs(v_band), zi=self._voc_env_zi[i])
            c_band, self._voc_car_zi[i] = signal.sosfilt(sos, car, zi=self._voc_car_zi[i])
            out += c_band * env

        return np.tanh(out * 3.8).astype(np.float32)

    def _process_chorus(
        self, x: np.ndarray, rate_hz: float, delay_ms: float, depth_ms: float, feedback: float
    ) -> np.ndarray:
        n = len(x)
        base_s = max(48.0, float(delay_ms) * 0.001 * self.sr)
        depth_s = max(1.0, float(depth_ms) * 0.001 * self.sr)
        fb = float(np.clip(feedback, 0.0, 0.85))
        min_safe = max(16, int(max(1.0, base_s - depth_s * 0.5)))

        out = np.empty(n, dtype=np.float32)
        dphi = float(rate_hz) / self.sr
        pos = 0
        while pos < n:
            clen = min(n - pos, min_safe)
            xc = x[pos:pos + clen]
            phases = (self._chorus_phase + self._get_ramp_f64(clen) * dphi) % 1.0
            self._chorus_phase = float((self._chorus_phase + clen * dphi) % 1.0)

            lfo = 0.5 * (1.0 + np.sin(2.0 * np.pi * phases))
            delays = base_s + depth_s * lfo
            delayed = self._chorus_ring.read_frac_chunk(delays)
            self._chorus_ring.write_chunk(xc + fb * delayed)
            out[pos:pos + clen] = delayed
            pos += clen

        return out

    def _process_phaser(
        self, x: np.ndarray, stages: int, freq_hz: float, depth: float, feedback: float
    ) -> np.ndarray:
        n = len(x)
        n_stages = int(np.clip(stages, 2, 12))
        if n_stages % 2 != 0:
            n_stages += 1
        fb = float(np.clip(feedback, -0.90, 0.90))
        d = float(np.clip(depth, 0.0, 1.0))

        chunk_sz = 64
        out = np.empty(n, dtype=np.float32)
        dphi = float(freq_hz) / self.sr
        sos = self._phaser_sos[:n_stages]

        pos = 0
        while pos < n:
            clen = min(n - pos, chunk_sz)
            xc = x[pos:pos + clen].astype(np.float64)
            lfo = 0.5 * (1.0 + np.sin(2.0 * np.pi * self._phaser_phase))
            self._phaser_phase = float((self._phaser_phase + clen * dphi) % 1.0)

            fc = min(140.0 * (22.0 ** (lfo * d)), self.sr * 0.42)
            t = np.tan(np.pi * fc / self.sr)
            a = (1.0 - t) / (1.0 + t)
            sos[:, 0] = a
            sos[:, 4] = a

            y = xc + fb * self._phaser_fb_sample
            y, zi_out = signal.sosfilt(sos, y, zi=self._phaser_zi[:n_stages])
            self._phaser_zi[:n_stages] = zi_out

            self._phaser_fb_sample = float(np.tanh(y[-1]))
            out[pos:pos + clen] = (0.5 * xc + 0.5 * y).astype(np.float32)
            pos += clen

        return out

    def _process_wah(self, x: np.ndarray, freq_hz: float, depth: float, resonance: float) -> np.ndarray:
        n = len(x)
        d = float(np.clip(depth, 0.0, 1.0))
        q = float(np.clip(resonance, 0.5, 8.0))
        chunk_sz = 64
        out = np.empty(n, dtype=np.float32)
        dphi = float(freq_hz) / self.sr
        b_wah = self._wah_b
        a_wah = self._wah_a
        a_wah[0] = 1.0

        pos = 0
        while pos < n:
            clen = min(n - pos, chunk_sz)
            xc = x[pos:pos + clen].astype(np.float64)
            lfo = 0.5 * (1.0 + np.sin(2.0 * np.pi * self._wah_phase))
            self._wah_phase = float((self._wah_phase + clen * dphi) % 1.0)

            fc = min(320.0 * (8.5 ** (lfo * d)), self.sr * 0.44)
            w0 = 2.0 * np.pi * fc / self.sr
            alpha = np.sin(w0) / (2.0 * q)
            cos_w0 = np.cos(w0)
            inv_a0 = 1.0 / (1.0 + alpha)
            b_val = alpha * inv_a0 * 2.2
            b_wah[0] = b_val
            b_wah[2] = -b_val
            a_wah[1] = (-2.0 * cos_w0) * inv_a0
            a_wah[2] = (1.0 - alpha) * inv_a0

            yw, self._wah_zi = signal.lfilter(b_wah, a_wah, xc, zi=self._wah_zi)
            out[pos:pos + clen] = yw.astype(np.float32)
            pos += clen

        return out

    def _process_tremolo(self, x: np.ndarray, freq_hz: float, waveform: str, depth: float) -> np.ndarray:
        n = len(x)
        dphi = float(freq_hz) / self.sr
        phases = (self._trem_phase + self._get_ramp_f64(n) * dphi) % 1.0
        self._trem_phase = float((self._trem_phase + n * dphi) % 1.0)

        if waveform == "Quadrada":
            lfo = np.where(phases < 0.5, 1.0, 0.0)
        elif waveform == "Triangular":
            lfo = 1.0 - 2.0 * np.abs(phases - 0.5)
        elif waveform == "Dente de Serra":
            lfo = phases
        else:
            lfo = 0.5 * (1.0 + np.sin(2.0 * np.pi * phases))

        d = float(np.clip(depth, 0.0, 1.0))
        env = (1.0 - d * (1.0 - lfo)).astype(np.float32)
        return x * env

    def _process_ring_mod(self, x: np.ndarray, freq_hz: float, waveform: str) -> np.ndarray:
        n = len(x)
        dphi = freq_hz / self.sr
        phases = (self._ring_phase + self._get_ramp_f64(n) * dphi) % 1.0
        self._ring_phase = float((self._ring_phase + n * dphi) % 1.0)

        if waveform == "Quadrada":
            mod = np.where(phases < 0.5, 1.0, -1.0)
        elif waveform == "Triangular":
            mod = 4.0 * np.abs(phases - 0.5) - 1.0
        else:
            mod = np.sin(2.0 * np.pi * phases)

        return x * mod.astype(np.float32)

    def _process_distortion(self, x: np.ndarray, drive: float, bits: int, downsample: int) -> np.ndarray:
        drive = max(1.0, float(drive))
        comp = 1.0 / (1.0 + 0.16 * (drive - 1.0))
        y = np.tanh(x * drive) * comp

        if bits < 16:
            levels = float(2 ** (max(2, bits) - 1))
            y = np.round(y * levels) / levels

        k = int(max(1, downsample))
        if k > 1:
            n = len(y)
            idx = np.arange(n, dtype=np.int32) + self._bc_counter
            sample_idx = (idx // k) * k - self._bc_counter
            clipped_idx = np.clip(sample_idx, 0, n - 1)
            y = np.where(sample_idx < 0, self._bc_hold, y[clipped_idx]).astype(np.float32)
            self._bc_counter = int((self._bc_counter + n) % k)
            self._bc_hold = float(y[-1])

        return y.astype(np.float32)

    def _process_echo(self, x: np.ndarray, delay_ms: float, feedback: float, mix: float) -> np.ndarray:
        delay_samples = max(48, int(delay_ms * 0.001 * self.sr))
        fb = float(np.clip(feedback, 0.0, 0.88))
        n = len(x)
        out = np.empty(n, dtype=np.float32)

        pos = 0
        while pos < n:
            chunk_len = min(n - pos, delay_samples)
            xc = x[pos:pos + chunk_len]
            delayed = self._echo_ring.read_chunk(delay_samples, chunk_len)
            filt_del, self._echo_lp_zi = signal.lfilter(
                self._echo_lp_b, self._echo_lp_a, delayed, zi=self._echo_lp_zi
            )
            self._echo_ring.write_chunk(xc + fb * filt_del.astype(np.float32))
            out[pos:pos + chunk_len] = xc + mix * delayed
            pos += chunk_len

        return out

    def _process_reverb(self, x: np.ndarray, room: float, damp: float, mix: float) -> np.ndarray:
        fb = 0.68 + 0.27 * float(np.clip(room, 0.0, 1.0))
        d = float(np.clip(damp, 0.05, 0.92))
        n = len(x)
        max_chunk = min(self._ap_delays)
        wet_out = np.empty(n, dtype=np.float32)

        self._rev_lp_b[0] = 1.0 - d
        self._rev_lp_a[1] = -d
        lp_b = self._rev_lp_b
        lp_a = self._rev_lp_a
        if max_chunk > len(self._rev_comb_sum):
            self._rev_comb_sum = np.zeros(max_chunk, dtype=np.float32)

        pos = 0
        while pos < n:
            clen = min(n - pos, max_chunk)
            xc = x[pos:pos + clen] * 0.25

            comb_sum = self._rev_comb_sum[:clen]
            comb_sum.fill(0.0)
            for idx, (ring, delay) in enumerate(zip(self._comb_rings, self._comb_delays)):
                del_sig = ring.read_chunk(delay, clen)
                comb_sum += del_sig
                damped, self._comb_lp_state[idx] = signal.lfilter(
                    lp_b, lp_a, del_sig, zi=self._comb_lp_state[idx]
                )
                ring.write_chunk(xc + fb * damped.astype(np.float32))

            y_ap = comb_sum
            ap_g = 0.5
            for ring, delay in zip(self._ap_rings, self._ap_delays):
                v_del = ring.read_chunk(delay, clen)
                v = y_ap + ap_g * v_del
                ring.write_chunk(v)
                y_ap = -ap_g * v + v_del

            wet_out[pos:pos + clen] = y_ap
            pos += clen

        return x * (1.0 - 0.5 * mix) + wet_out * mix
