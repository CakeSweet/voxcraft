import unittest

import numpy as np

from internal.core.src import dsp_engine


class StreamingNoiseSuppressorTests(unittest.TestCase):
    def test_suppressor_handles_variable_callback_sizes(self):
        engine = dsp_engine.RealTimeDSPEngine(48_000)
        source = np.ones(2048, dtype=np.float32) * 0.05

        output = np.concatenate([
            engine.process(source[:256]),
            engine.process(source[256:768]),
            engine.process(source[768:]),
        ])

        self.assertEqual(output.shape, source.shape)
        self.assertTrue(np.isfinite(output).all())

    def test_preserves_frame_count_and_has_twenty_ms_lookahead(self):
        suppressor = dsp_engine.StreamingNoiseSuppressor(48_000, level=0)
        first = suppressor.process(np.ones(480, dtype=np.float32))
        second = suppressor.process(np.ones(480, dtype=np.float32))
        third = suppressor.process(np.ones(480, dtype=np.float32))

        self.assertEqual(len(first), 480)
        self.assertEqual(len(second), 480)
        self.assertEqual(len(third), 480)
        np.testing.assert_allclose(first, 0.0, atol=1e-6)
        np.testing.assert_allclose(second, 0.0, atol=1e-6)
        self.assertGreater(float(np.sqrt(np.mean(third[32:] ** 2))), 0.8)

    def test_reset_discards_queued_audio_and_resets_processor(self):
        suppressor = dsp_engine.StreamingNoiseSuppressor(48_000)
        suppressor.process(np.ones(480, dtype=np.float32))
        suppressor.reset()
        output = suppressor.process(np.ones(480, dtype=np.float32))

        np.testing.assert_array_equal(output, np.zeros(480, dtype=np.float32))
        self.assertEqual(len(output), 480)

    def test_reduces_stationary_noise_after_profile_warmup(self):
        suppressor = dsp_engine.StreamingNoiseSuppressor(48_000, level=3)
        rng = np.random.default_rng(1234)
        source = rng.normal(0.0, 0.003, 48_000 * 2).astype(np.float32)
        output = np.concatenate([
            suppressor.process(source[index:index + 480])
            for index in range(0, len(source), 480)
        ])

        input_rms = float(np.sqrt(np.mean(source[48_000:] ** 2)))
        output_rms = float(np.sqrt(np.mean(output[48_000:] ** 2)))
        self.assertLess(output_rms, input_rms * 0.9)

    def test_does_not_learn_sustained_voice_as_noise(self):
        suppressor = dsp_engine.StreamingNoiseSuppressor(48_000, level=3)
        source = (0.1 * np.sin(
            2 * np.pi * 440 * np.arange(48_000, dtype=np.float32) / 48_000
        )).astype(np.float32)
        output = np.concatenate([
            suppressor.process(source[index:index + 512])
            for index in range(0, len(source), 512)
        ])

        self.assertEqual(suppressor._history_count, 0)
        self.assertGreater(float(np.sqrt(np.mean(output[2_000:] ** 2))), 0.06)

    def test_preserves_voice_after_learning_background_noise(self):
        sample_rate = 48_000
        rng = np.random.default_rng(21)
        quiet = rng.normal(0.0, 0.003, sample_rate // 2).astype(np.float32)
        noise = rng.normal(0.0, 0.003, sample_rate * 2).astype(np.float32)
        time = np.arange(sample_rate, dtype=np.float32) / sample_rate
        voice = (0.1 * np.sin(2 * np.pi * 440 * time)).astype(np.float32)
        source = np.concatenate((quiet, voice + noise[:sample_rate], noise[sample_rate:]))
        suppressor = dsp_engine.StreamingNoiseSuppressor(sample_rate, level=3)
        output = np.concatenate([
            suppressor.process(source[index:index + 512])
            for index in range(0, len(source), 512)
        ])

        voice_start = len(quiet) + suppressor.frame_samples
        filtered_voice = output[voice_start:voice_start + sample_rate]
        voice_gain = float(np.dot(filtered_voice, voice) / np.dot(voice, voice))
        residual = filtered_voice - voice_gain * voice
        self.assertGreater(voice_gain, 0.85)
        self.assertLess(
            float(np.sqrt(np.mean(residual ** 2))),
            float(np.sqrt(np.mean(noise[:sample_rate] ** 2))),
        )


class NoiseSuppressionParameterTests(unittest.TestCase):
    def test_changing_level_selects_python_suppressor_strength(self):
        engine = dsp_engine.RealTimeDSPEngine(48_000)
        suppressor = engine._noise_suppressor
        rng = np.random.default_rng(7)
        quiet = rng.normal(0.0, 0.002, 48_000 // 2).astype(np.float32)
        engine.process(quiet)
        history_before = engine._noise_suppressor._history_count
        self.assertGreater(history_before, 0)

        params = engine.params.copy()
        params.noise_suppression_level = 3
        engine.update_params(params)

        self.assertIs(engine._noise_suppressor, suppressor)
        self.assertEqual(engine._noise_suppressor.level, 3)
        self.assertEqual(engine._noise_suppressor._history_count, history_before)

    def test_rejects_unsupported_suppression_level(self):
        with self.assertRaises(ValueError):
            dsp_engine.DSPParams(noise_suppression_level=4)
        suppressor = dsp_engine.StreamingNoiseSuppressor(48_000, level=1)
        for bad_level in (-1, 4, 1.5, True):
            with self.assertRaises(ValueError):
                suppressor.set_level(bad_level)
        self.assertEqual(suppressor.level, 1)

    def test_parameter_is_global_and_not_saved_in_presets(self):
        from internal.core.src.presets import preset_effect_params

        params = dsp_engine.DSPParams()
        params.noise_suppression_level = 3
        preset = preset_effect_params(params)

        self.assertNotIn("noise_suppression_level", preset)
        self.assertFalse(hasattr(params, "noise_suppression_enabled"))


class NoiseGateTests(unittest.TestCase):
    def test_gate_opens_for_voice_and_closes_after_hold_period(self):
        engine = dsp_engine.RealTimeDSPEngine(48_000)
        voice = np.full(512, 0.1, dtype=np.float32)
        silence = np.zeros(512, dtype=np.float32)
        hold_blocks = max(1, int(0.14 * engine.sr / len(silence)))

        engine._apply_noise_gate_unlocked(voice, -44.0)
        self.assertTrue(engine.gate_is_open)
        self.assertEqual(engine._gate_hold_counter, hold_blocks)

        for _ in range(hold_blocks):
            engine._apply_noise_gate_unlocked(silence, -44.0)
            self.assertTrue(engine.gate_is_open)

        engine._apply_noise_gate_unlocked(silence, -44.0)
        self.assertFalse(engine.gate_is_open)
        for _ in range(20):
            engine._apply_noise_gate_unlocked(silence, -44.0)
        self.assertLess(engine._gate_gain, 0.01)

    def test_gate_threshold_is_global_and_not_saved_in_presets(self):
        from internal.core.src.presets import preset_effect_params

        params = dsp_engine.DSPParams(gate_threshold_db=-52.0)

        self.assertNotIn("gate_threshold_db", preset_effect_params(params))


class EchoBufferResetTests(unittest.TestCase):
    def test_re_enabling_echo_clears_stale_ring_buffer(self):
        engine = dsp_engine.RealTimeDSPEngine(48_000)
        p = engine.params.copy()
        p.echo_enabled = True
        p.echo_delay_ms = 50.0
        p.echo_mix = 0.8
        engine.update_params(p)
        engine.process(np.full(512, 0.25, dtype=np.float32))

        p.echo_enabled = False
        engine.update_params(p)
        engine.process(np.zeros(512, dtype=np.float32))

        p.echo_enabled = True
        engine.update_params(p)
        out = engine.process(np.zeros(512, dtype=np.float32))
        self.assertLess(float(np.max(np.abs(out))), 1e-5)
