from dataclasses import dataclass, asdict
import threading
import numpy as np
from scipy import signal


@dataclass
class DSPParams:
    # Controle geral
    bypass: bool = False
    input_gain_db: float = 0.0
    output_gain_db: float = 0.0

    # Noise Gate & Compressor (Limpeza para Discord)
    gate_enabled: bool = True
    gate_threshold_db: float = -42.0
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

    # Modulador (Robô / Alien / Tremolo)
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
    """Buffer circular vetorizado para Eco e Filtros Comb/All-pass."""

    def __init__(self, max_samples: int):
        self.size = int(max_samples)
        self.buf = np.zeros(self.size, dtype=np.float32)
        self.write_idx = 0

    def read_chunk(self, delay_samples: int, length: int) -> np.ndarray:
        delay = max(1, min(delay_samples, self.size - 1))
        start = (self.write_idx - delay) % self.size
        indices = (start + np.arange(length)) % self.size
        return self.buf[indices]

    def write_chunk(self, data: np.ndarray):
        length = len(data)
        indices = (self.write_idx + np.arange(length)) % self.size
        self.buf[indices] = data
        self.write_idx = (self.write_idx + length) % self.size


class RealTimeDSPEngine:
    def __init__(self, sample_rate: float = 48000.0):
        self._lock = threading.Lock()
        self.params = DSPParams()
        self.sr = float(sample_rate)

        # Métricas para a UI
        self.input_peak_db = -60.0
        self.output_peak_db = -60.0
        self.gate_is_open = True
        self.last_waveform = np.zeros(256, dtype=np.float32)

        self._init_states()

    def set_sample_rate(self, sample_rate: float):
        with self._lock:
            if abs(self.sr - float(sample_rate)) > 1.0:
                self.sr = float(sample_rate)
                self._init_states()

    def update_params(self, new_params: DSPParams):
        with self._lock:
            self.params = new_params.copy()
            self._eq_dirty = True

    def _init_states(self):
        sr = self.sr

        # Noise Gate & Compressor
        self._gate_gain = 1.0
        self._gate_hold_counter = 0
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

        # Equalizador SOS (7 estágios biquad)
        self._eq_sos = build_eq_sos(self.params, sr)
        self._eq_zi = np.zeros((7, 2), dtype=np.float64)
        self._eq_dirty = False

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
        self._comb_lp_state = [0.0 for _ in self._comb_delays]
        self._ap_rings = [RingDelay(d + 2048) for d in self._ap_delays]

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
            p = self.params.copy()
            if self._eq_dirty:
                self._eq_sos = build_eq_sos(p, self.sr)
                self._eq_dirty = False

        # Medidor de entrada (pré-efeitos)
        in_db = self._peak_db(x)
        self.input_peak_db = 0.65 * self.input_peak_db + 0.35 * in_db

        if p.bypass:
            self.output_peak_db = self.input_peak_db
            self.gate_is_open = True
            self._update_waveform(x)
            return x

        # 1. Ganho de Entrada
        if abs(p.input_gain_db) > 0.05:
            x *= 10.0 ** (p.input_gain_db / 20.0)

        # 2. Noise Gate (antes de distorção/reverb para cauda natural)
        if p.gate_enabled:
            rms = float(np.sqrt(np.mean(x * x) + 1e-12))
            rms_db = 20.0 * np.log10(rms)
            hold_blocks = max(1, int(0.14 * self.sr / n))
            if rms_db >= p.gate_threshold_db:
                self._gate_hold_counter = hold_blocks
                target_g = 1.0
                self.gate_is_open = True
            elif self._gate_hold_counter > 0:
                self._gate_hold_counter -= 1
                target_g = 1.0
                self.gate_is_open = True
            else:
                target_g = 0.0005  # -66 dB
                self.gate_is_open = False

            coeff = 0.45 if target_g > self._gate_gain else 0.22
            next_g = self._gate_gain + coeff * (target_g - self._gate_gain)
            ramp = np.linspace(self._gate_gain, next_g, n, dtype=np.float32)
            x *= ramp
            self._gate_gain = float(next_g)
        else:
            self.gate_is_open = True

        # 3. Compressor
        if p.comp_enabled:
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

        # 6. Equalizador (HPF + 5 Bandas + LPF)
        if p.eq_enabled:
            y_eq, self._eq_zi = signal.sosfilt(self._eq_sos, x, zi=self._eq_zi)
            x = y_eq.astype(np.float32)

        # 7. Modulador em Anel (Robô / Alien)
        if p.ring_enabled and p.ring_mix > 0.01:
            wet = self._process_ring_mod(x, p.ring_freq_hz, p.ring_waveform)
            x = x * (1.0 - p.ring_mix) + wet * p.ring_mix

        # 8. Distorção & Bitcrusher (Rádio / Mega-fone)
        if p.dist_enabled and p.dist_mix > 0.01:
            wet = self._process_distortion(x, p.dist_drive, p.dist_bits, p.dist_downsample)
            x = x * (1.0 - p.dist_mix) + wet * p.dist_mix

        # 9. Eco / Delay
        if p.echo_enabled and p.echo_mix > 0.01:
            x = self._process_echo(x, p.echo_delay_ms, p.echo_feedback, p.echo_mix)

        # 10. Reverb
        if p.reverb_enabled and p.reverb_mix > 0.01:
            x = self._process_reverb(x, p.reverb_room, p.reverb_damp, p.reverb_mix)

        # 11. Ganho de Saída + Soft Limiter (evita clipping no Discord)
        if abs(p.output_gain_db) > 0.05:
            x *= 10.0 ** (p.output_gain_db / 20.0)
        x = np.tanh(x * 0.92).astype(np.float32) * 0.98

        out_db = self._peak_db(x)
        self.output_peak_db = 0.65 * self.output_peak_db + 0.35 * out_db
        self._update_waveform(x)
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

        phi1 = (self._pitch_phase + np.arange(n, dtype=np.float64) * dphi) % 1.0
        phi2 = (phi1 + 0.5) % 1.0
        self._pitch_phase = float((self._pitch_phase + n * dphi) % 1.0)

        d1 = (1.0 - phi1) * w + 2.0
        d2 = (1.0 - phi2) * w + 2.0

        idx = np.arange(n, dtype=np.float64) + m
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
        phases = self._fshift_phase + np.arange(n, dtype=np.float64) * dphi
        self._fshift_phase = float((self._fshift_phase + n * dphi) % (2.0 * np.pi))

        out = x_del * np.cos(phases) - x_hilb * np.sin(phases)
        return out.astype(np.float32)

    def _process_ring_mod(self, x: np.ndarray, freq_hz: float, waveform: str) -> np.ndarray:
        n = len(x)
        dphi = freq_hz / self.sr
        phases = (self._ring_phase + np.arange(n, dtype=np.float64) * dphi) % 1.0
        self._ring_phase = float((self._ring_phase + n * dphi) % 1.0)

        if waveform == "Quadrada":
            mod = np.where(phases < 0.5, 1.0, -1.0)
        elif waveform == "Triangular":
            mod = 4.0 * np.abs(phases - 0.5) - 1.0
        else:
            mod = np.sin(2.0 * np.pi * phases)

        return (x * mod.astype(np.float32))

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
            filt_del = filt_del.astype(np.float32)
            self._echo_ring.write_chunk(xc + fb * filt_del)
            out[pos:pos + chunk_len] = xc + mix * delayed
            pos += chunk_len

        return out

    def _process_reverb(self, x: np.ndarray, room: float, damp: float, mix: float) -> np.ndarray:
        fb = 0.68 + 0.27 * float(np.clip(room, 0.0, 1.0))
        d = float(np.clip(damp, 0.05, 0.92))
        n = len(x)
        max_chunk = min(self._ap_delays)
        wet_out = np.empty(n, dtype=np.float32)

        pos = 0
        while pos < n:
            clen = min(n - pos, max_chunk)
            xc = x[pos:pos + clen] * 0.25

            comb_sum = np.zeros(clen, dtype=np.float32)
            for idx, (ring, delay) in enumerate(zip(self._comb_rings, self._comb_delays)):
                del_sig = ring.read_chunk(delay, clen)
                # Suavização simples por bloco + passa-baixa leve
                lp_b = np.array([1.0 - d], dtype=np.float64)
                lp_a = np.array([1.0, -d], dtype=np.float64)
                zi = np.array([self._comb_lp_state[idx]], dtype=np.float64)
                damped, zf = signal.lfilter(lp_b, lp_a, del_sig, zi=zi)
                self._comb_lp_state[idx] = float(zf[0])
                ring.write_chunk(xc + fb * damped.astype(np.float32))
                comb_sum += del_sig

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