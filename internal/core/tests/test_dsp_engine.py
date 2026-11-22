import unittest
from unittest.mock import patch

import numpy as np

from internal.core.src import dsp_engine


class StreamingNoiseSuppressorTests(unittest.TestCase):
    def test_native_processor_handles_variable_callback_sizes(self):
        engine = dsp_engine.RealTimeDSPEngine(48_000)
        source = np.ones(2048, dtype=np.float32) * 0.05

        output = np.concatenate([
            engine.process(source[:256]),
            engine.process(source[256:768]),
            engine.process(source[768:]),
        ])

        self.assertEqual(output.shape, source.shape)
        self.assertTrue(np.isfinite(output).all())

    def test_buffers_variable_callbacks_into_contiguous_ten_ms_frames(self):
        class FakeProcessor:
            def __init__(self, **kwargs):
                self.frames = []

            def process(self, frame):
                self.frames.append(frame.copy())
                return frame * 0.5

            def reset(self):
                self.frames.clear()

        with patch.object(dsp_engine, "AudioProcessor", FakeProcessor):
            suppressor = dsp_engine.StreamingNoiseSuppressor(48_000)
            first = suppressor.process(np.ones(256, dtype=np.float32))
            second = suppressor.process(np.full(256, 2.0, dtype=np.float32))

        self.assertEqual(len(first), 256)
        np.testing.assert_array_equal(first, np.zeros(256, dtype=np.float32))
        self.assertEqual(len(second), 256)
        np.testing.assert_array_equal(second[:224], np.zeros(224, dtype=np.float32))
        np.testing.assert_array_equal(second[224:], np.full(32, 0.5, dtype=np.float32))
        self.assertEqual(len(suppressor.processor.frames), 1)
        frame = suppressor.processor.frames[0]
        np.testing.assert_array_equal(frame[:256], np.ones(256, dtype=np.float32))
        np.testing.assert_array_equal(frame[256:], np.full(224, 2.0, dtype=np.float32))

    def test_reset_discards_queued_audio_and_resets_processor(self):
        class FakeProcessor:
            def __init__(self, **kwargs):
                self.reset_count = 0

            def process(self, frame):
                return frame

            def reset(self):
                self.reset_count += 1

        with patch.object(dsp_engine, "AudioProcessor", FakeProcessor):
            suppressor = dsp_engine.StreamingNoiseSuppressor(48_000)
            suppressor.process(np.ones(480, dtype=np.float32))
            suppressor.reset()
            output = suppressor.process(np.ones(256, dtype=np.float32))

        self.assertEqual(suppressor.processor.reset_count, 1)
        np.testing.assert_array_equal(output, np.zeros(256, dtype=np.float32))


class NoiseSuppressionParameterTests(unittest.TestCase):
    def test_parameter_is_global_and_not_saved_in_presets(self):
        from internal.core.src.presets import preset_effect_params

        params = dsp_engine.DSPParams(noise_suppression_enabled=False)

        self.assertNotIn("noise_suppression_enabled", preset_effect_params(params))
