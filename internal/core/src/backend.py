from __future__ import annotations

from dataclasses import asdict
import json
import sys
from typing import Any

from . import APP_VERSION
from .audio_router import AudioRouter
from .dsp_engine import DSPParams, RealTimeDSPEngine
from .presets import (
    get_builtin_presets,
    load_user_presets,
    preset_effect_params,
    save_user_presets,
)


class VoxCraftCore:
    """Serviço headless de áudio controlado pela interface Tauri via JSON Lines."""

    def __init__(self) -> None:
        self.engine = RealTimeDSPEngine(48000.0)
        self.router = AudioRouter(self.engine)
        self.builtin_presets = get_builtin_presets()
        self.user_presets = load_user_presets()
        self.params = self.builtin_presets["Normal"].copy()
        self.engine.update_params(self.params)

    @staticmethod
    def _device_data(device: Any) -> dict[str, Any]:
        return {**asdict(device), "label": device.label}

    def _devices(self, refresh: bool = False) -> dict[str, list[dict[str, Any]]]:
        if refresh:
            if self.router.running:
                self.router.stop()
            inputs, outputs = AudioRouter.refresh_backend()
        else:
            inputs, outputs = AudioRouter.list_devices()
        return {
            "inputs": [self._device_data(device) for device in inputs],
            "outputs": [self._device_data(device) for device in outputs],
        }

    def _set_params(self, raw_params: Any) -> dict[str, Any]:
        if not isinstance(raw_params, dict):
            raise ValueError("'params' precisa ser um objeto.")

        current = asdict(self.params)
        unknown = set(raw_params) - set(current)
        if unknown:
            raise ValueError(f"Parâmetros desconhecidos: {', '.join(sorted(unknown))}")

        current.update(raw_params)
        self.params = DSPParams(**current)
        self.engine.update_params(self.params)
        return asdict(self.params)

    def _apply_preset(self, name: Any, custom: bool | None = None) -> dict[str, Any]:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("'name' precisa ser um nome de preset.")

        preset_name = name.strip()
        if preset_name.startswith("★ "):
            preset_name = preset_name[2:].strip()
            custom = True

        if custom is None:
            custom = preset_name in self.user_presets
        preset = (self.user_presets if custom else self.builtin_presets).get(preset_name)
        if preset is None:
            raise ValueError(f"Preset não encontrado: {preset_name}")

        return self._set_params(preset_effect_params(preset))

    def dispatch(self, method: str, params: dict[str, Any]) -> Any:
        if method == "ping":
            return {
                "connected": True,
                "version": APP_VERSION,
                "message": "Core Python conectado; motor DSP pronto (áudio parado).",
            }
        if method == "list_devices":
            return self._devices()
        if method == "refresh_devices":
            return self._devices(refresh=True)
        if method == "get_params":
            return asdict(self.params)
        if method == "set_params":
            return self._set_params(params.get("params"))
        if method == "list_presets":
            return {
                "builtIn": list(self.builtin_presets),
                "custom": list(self.user_presets),
            }
        if method == "apply_preset":
            return self._apply_preset(params.get("name"), params.get("custom"))
        if method == "save_preset":
            name = params.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("'name' precisa ser um nome de preset.")
            name = name.strip()
            self.user_presets[name] = DSPParams(**preset_effect_params(self.params))
            save_user_presets(self.user_presets)
            return {"name": name}
        if method == "delete_preset":
            name = params.get("name")
            if not isinstance(name, str) or name not in self.user_presets:
                raise ValueError("Somente presets personalizados podem ser excluídos.")
            del self.user_presets[name]
            save_user_presets(self.user_presets)
            return {"deleted": name}
        if method == "start_audio":
            try:
                input_index = int(params["input_index"])
                output_index = int(params["output_index"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("'input_index' e 'output_index' são obrigatórios.") from exc

            blocksize = int(params.get("blocksize", 512))
            if blocksize not in (256, 512, 1024):
                raise ValueError("'blocksize' precisa ser 256, 512 ou 1024.")
            monitor_index = params.get("monitor_index")
            if monitor_index is not None:
                monitor_index = int(monitor_index)
            monitor_enabled = bool(params.get("monitor_enabled", False))
            started, message = self.router.start(
                in_idx=input_index,
                out_idx=output_index,
                blocksize=blocksize,
                monitor_enabled=monitor_enabled and monitor_index is not None,
                monitor_idx=monitor_index,
            )
            monitor_error = None
            if started and monitor_enabled and monitor_index is None:
                try:
                    self.router.set_default_monitor(True)
                except (ValueError, OSError) as exc:
                    monitor_error = str(exc)
            return {
                "started": started,
                "message": message,
                "inputIndex": self.router.last_used_in_idx,
                "outputIndex": self.router.last_used_out_idx,
                "monitorError": monitor_error,
            }
        if method == "set_monitor":
            self.router.set_default_monitor(bool(params.get("enabled", False)))
            return {}
        if method == "stop_audio":
            self.router.stop()
            return {"stopped": True}
        if method == "meters":
            return {
                "running": self.router.running,
                "inputPeakDb": self.engine.input_peak_db,
                "outputPeakDb": self.engine.output_peak_db,
                "gateOpen": self.engine.gate_is_open,
                "waveform": self.engine.last_waveform.tolist(),
            }
        if method == "shutdown":
            self.close()
            return {"stopping": True}
        raise ValueError(f"Comando desconhecido: {method}")

    def close(self) -> None:
        self.router.stop()


def run_stdio_server() -> None:
    core = VoxCraftCore()
    for line in sys.stdin:
        request: Any = None
        method: str | None = None
        try:
            request = json.loads(line)
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})
            if not isinstance(method, str) or not isinstance(params, dict):
                raise ValueError("Requisição inválida.")
            result = core.dispatch(method, params)
            response = {"id": request_id, "ok": True, "result": result}
        except Exception as exc:
            response = {
                "id": request.get("id") if isinstance(request, dict) else None,
                "ok": False,
                "error": str(exc),
            }
            method = request.get("method") if isinstance(request, dict) else None

        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()
        if method == "shutdown" and response["ok"]:
            break

    core.close()


def main() -> None:
    try:
        run_stdio_server()
    except Exception as exc:
        print(f"VoxCraft Python core failed to start: {exc}", file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    main()
