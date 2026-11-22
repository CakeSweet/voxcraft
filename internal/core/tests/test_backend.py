import io
import json
import unittest
from unittest.mock import Mock, patch

from internal.core.src import backend


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
