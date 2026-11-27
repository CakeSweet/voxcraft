import io
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from internal.core.src import backend, presets


class StdioServerTests(unittest.TestCase):
    def run_server(self, core, requests):
        output = io.StringIO()
        with (
            patch.object(backend, "VoxCraftCore", return_value=core),
            patch.object(backend.sys, "stdin", io.StringIO(requests)),
            patch.object(backend.sys, "stdout", output),
        ):
            backend.run_stdio_server()
        return [json.loads(line) for line in output.getvalue().splitlines()]

    def test_accepts_another_request_after_invalid_json_shape(self):
        core = Mock()
        core.dispatch.return_value = {"connected": True}

        responses = self.run_server(core, '[]\n{"id":7,"method":"ping"}\n')

        self.assertEqual(responses, [
            {"id": None, "ok": False, "error": "Requisição inválida."},
            {"id": 7, "ok": True, "result": {"connected": True}},
        ])
        core.dispatch.assert_called_once_with("ping", {})
        core.close.assert_called_once_with()

    def test_non_finite_response_is_reported_without_closing_the_session(self):
        core = Mock()
        core.dispatch.side_effect = [{"value": float("nan")}, {"connected": True}]

        bad, good = self.run_server(
            core, '{"id":1,"method":"meters"}\n{"id":2,"method":"ping"}\n'
        )

        self.assertEqual(bad["id"], 1)
        self.assertFalse(bad["ok"])
        self.assertEqual(good, {"id": 2, "ok": True, "result": {"connected": True}})
        core.close.assert_called_once_with()

    def test_shutdown_acknowledges_and_does_not_close_twice(self):
        core = Mock(spec=backend.VoxCraftCore)

        def dispatch(method, params):
            return backend.VoxCraftCore.dispatch(core, method, params)

        core.dispatch.side_effect = dispatch
        responses = self.run_server(
            core, '{"id":1,"method":"shutdown"}\n{"id":2,"method":"ping"}\n'
        )

        self.assertEqual(responses, [{"id": 1, "ok": True, "result": {"stopping": True}}])
        core.dispatch.assert_called_once_with("shutdown", {})
        core.close.assert_called_once_with()

    def test_broken_stdout_still_closes_core(self):
        core = Mock()
        core.dispatch.return_value = {"connected": True}
        output = Mock()
        output.flush.side_effect = BrokenPipeError
        with (
            patch.object(backend, "VoxCraftCore", return_value=core),
            patch.object(backend.sys, "stdin", io.StringIO('{"id":1,"method":"ping"}\n')),
            patch.object(backend.sys, "stdout", output),
            self.assertRaises(BrokenPipeError),
        ):
            backend.run_stdio_server()
        core.close.assert_called_once_with()


class ParameterValidationTests(unittest.TestCase):
    def test_set_params_rejects_non_finite_and_invalid_types(self):
        core = backend.VoxCraftCore()
        for bad_payload in (
            {"input_gain_db": float("nan")},
            {"output_gain_db": float("inf")},
            {"input_gain_db": True},
            {"noise_suppression_level": True},
            {"noise_suppression_level": 2.0},
            {"bypass": 1},
            {"vocoder_carrier": 123},
            {"echo_linger_ms": -50},
            {"echo_linger_ms": 5050},
            {"echo_linger_ms": float("nan")},
            {"echo_linger_ms": True},
        ):
            with self.assertRaises(ValueError):
                core._set_params(bad_payload)
        result = core._set_params({"input_gain_db": 3, "bypass": True, "echo_linger_ms": 1500})
        self.assertEqual(result["input_gain_db"], 3.0)
        self.assertIs(result["bypass"], True)
        self.assertEqual(result["echo_linger_ms"], 1500.0)


class PresetEchoLingerTests(unittest.TestCase):
    def test_echo_linger_ms_is_saved_and_restored_per_preset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            presets_file = os.path.join(tmpdir, "user_presets.json")
            with patch.object(presets, "USER_PRESETS_FILE", presets_file):
                core = backend.VoxCraftCore()
                core._set_params({"echo_enabled": True, "echo_linger_ms": 1500})
                core._save_preset("Eco Longo")

                core._set_params({"echo_enabled": True, "echo_linger_ms": 250})
                core._save_preset("Eco Curto")

                reloaded = backend.VoxCraftCore()
                first = reloaded._apply_preset("Eco Longo", custom=True)
                self.assertEqual(first["echo_linger_ms"], 1500.0)

                second = reloaded._apply_preset("Eco Curto", custom=True)
                self.assertEqual(second["echo_linger_ms"], 250.0)

                normal = reloaded._apply_preset("Normal", custom=False)
                self.assertEqual(normal["echo_linger_ms"], 0.0)

