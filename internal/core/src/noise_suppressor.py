"""Supressão espectral adaptativa em Python para áudio de microfone ao vivo."""

import numpy as np


class StreamingNoiseSuppressor:
    """Reduz ruído por subtração espectral em janelas sobrepostas de 20 ms."""

    _STRENGTH = (
        (0.55, 0.50),
        (0.85, 0.36),
        (1.20, 0.24),
        (1.55, 0.14),
    )

    def __init__(self, sample_rate: float, level: int = 2):
        self.sample_rate = int(round(sample_rate))
        self.level = 2
        self.set_level(level)
        self.hop_samples = max(1, int(round(self.sample_rate / 100.0)))
        self.frame_samples = self.hop_samples * 2
        self.fft_size = 1 << (self.frame_samples - 1).bit_length()
        self.window = np.sqrt(
            np.hanning(self.frame_samples + 1)[:-1]
        ).astype(np.float32)

        self._input = np.empty(0, dtype=np.float32)
        self._previous_input = np.zeros(self.hop_samples, dtype=np.float32)
        self._frame_buf = np.zeros(self.frame_samples, dtype=np.float32)
        self._windowed_frame = np.zeros(self.frame_samples, dtype=np.float32)
        self._overlap = np.zeros(self.hop_samples, dtype=np.float32)
        # Buffer de saída para manter callbacks contínuos durante o look-ahead.
        self._output = np.zeros(self.frame_samples, dtype=np.float32)
        self._first_frame = True

        bins = self.fft_size // 2 + 1
        self._history = np.zeros((48, bins), dtype=np.float32)
        self._history_count = 0
        self._history_index = 0
        self._noise_power = np.zeros(bins, dtype=np.float32)
        self._gain = np.ones(bins, dtype=np.float32)
        self._padded_gain = np.ones(bins + 2, dtype=np.float32)
        self._frames_since_profile = 0

    def set_level(self, level: int) -> None:
        if type(level) is not int or level not in range(len(self._STRENGTH)):
            raise ValueError("O nível da supressão de ruído precisa estar entre 0 e 3.")
        self.level = level

    def reset(self) -> None:
        self._input = np.empty(0, dtype=np.float32)
        self._previous_input.fill(0)
        self._frame_buf.fill(0)
        self._windowed_frame.fill(0)
        self._overlap.fill(0)
        self._output = np.zeros(self.frame_samples, dtype=np.float32)
        self._first_frame = True
        self._history.fill(0)
        self._history_count = 0
        self._history_index = 0
        self._noise_power.fill(0)
        self._gain.fill(1)
        self._padded_gain.fill(1)
        self._frames_since_profile = 0

    def _update_noise_profile(self, power: np.ndarray, frame_rms: float) -> bool:
        # Não transforme voz sustentada em "ruído": atualize o perfil apenas
        # em pausas, abaixo de aproximadamente -42 dBFS.
        if frame_rms >= 10.0 ** (-42.0 / 20.0):
            return self._history_count >= 20

        self._history[self._history_index] = power
        self._history_index = (self._history_index + 1) % len(self._history)
        self._history_count = min(self._history_count + 1, len(self._history))
        self._frames_since_profile += 1

        # A mediana temporal reduz a influência de fonemas e transientes isolados.
        if self._history_count >= 20 and self._frames_since_profile >= 4:
            profile = self._history[:self._history_count]
            self._noise_power = np.median(profile, axis=0) * 1.44
            self._frames_since_profile = 0

        return self._history_count >= 20

    def _process_frame(self, block: np.ndarray) -> np.ndarray:
        self._frame_buf[:self.hop_samples] = self._previous_input
        self._frame_buf[self.hop_samples:] = block
        self._previous_input[:] = block

        np.multiply(self._frame_buf, self.window, out=self._windowed_frame)
        spectrum = np.fft.rfft(self._windowed_frame, n=self.fft_size)
        power = (spectrum.real * spectrum.real + spectrum.imag * spectrum.imag).astype(np.float32)
        frame_rms = float(np.sqrt(np.mean(self._frame_buf * self._frame_buf) + 1e-12))
        profile_ready = self._update_noise_profile(power, frame_rms)

        if profile_ready:
            oversubtraction, minimum_gain = self._STRENGTH[self.level]
            min_gain_sq = minimum_gain * minimum_gain
            gain_squared = np.maximum(
                power - oversubtraction * self._noise_power,
                min_gain_sq * power,
            ) / (power + 1e-12)
            target_gain = np.sqrt(np.clip(gain_squared, min_gain_sq, 1.0))

            self._padded_gain[1:-1] = target_gain
            self._padded_gain[0] = target_gain[0]
            self._padded_gain[-1] = target_gain[-1]
            target_gain = (
                self._padded_gain[:-2] * 0.2
                + self._padded_gain[1:-1] * 0.6
                + self._padded_gain[2:] * 0.2
            )
            smoothing = np.where(target_gain > self._gain, 0.72, 0.32)
            self._gain += smoothing * (target_gain - self._gain)
        else:
            self._gain += 0.72 * (1.0 - self._gain)

        filtered = np.fft.irfft(spectrum * self._gain, n=self.fft_size)[:self.frame_samples]
        filtered = (filtered * self.window).astype(np.float32)

        output = self._overlap + filtered[:self.hop_samples]
        self._overlap[:] = filtered[self.hop_samples:]
        return output

    def process(self, samples: np.ndarray) -> np.ndarray:
        source = np.asarray(samples, dtype=np.float32).reshape(-1)
        count = len(source)
        if not count:
            return source.copy()

        buf = np.concatenate((self._input, source)) if len(self._input) else source
        pos = 0
        end = len(buf)
        produced = []
        while end - pos >= self.hop_samples:
            block = buf[pos:pos + self.hop_samples]
            pos += self.hop_samples
            frame_output = self._process_frame(block)
            if self._first_frame:
                # Esse quadro só contém o pré-roll silencioso anterior à entrada.
                self._first_frame = False
            else:
                produced.append(frame_output)
        self._input = buf[pos:].copy() if pos < end else np.empty(0, dtype=np.float32)

        if produced:
            self._output = np.concatenate((self._output, *produced))

        if len(self._output) < count:
            self._output = np.pad(self._output, (0, count - len(self._output)))
        output = self._output[:count].copy()
        self._output = self._output[count:].copy() if len(self._output) > count else np.empty(0, dtype=np.float32)
        return output
