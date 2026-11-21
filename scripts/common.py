from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CLIENT_DIR = ROOT / "internal" / "client"
CORE_DIR = ROOT / "internal" / "core"
VENV_DIR = ROOT / ".venv"
VENV_PYTHON = (
    VENV_DIR / "Scripts" / "python.exe"
    if os.name == "nt"
    else VENV_DIR / "bin" / "python"
)
CORE_BUILD_DIR = ROOT / "build" / "core"
SYSTEM_PYTHON = shlex.split(os.environ.get("PYTHON", sys.executable))
NPM = "npm.cmd" if os.name == "nt" else "npm"
SIGNING_ENV = {"SIGNING_PRIVATE_KEY", "TAURI_SIGNING_PRIVATE_KEY", "TAURI_SIGNING_PRIVATE_KEY_PASSWORD"}


def run(
    args: Sequence[str | os.PathLike[str]],
    *,
    cwd: Path = ROOT,
    env: Mapping[str, str] | None = None,
) -> None:
    command = [str(arg) for arg in args]
    options: dict[str, object] = {
        "cwd": cwd,
        "env": dict(env) if env is not None else None,
        "check": True,
    }

    if os.name == "nt" and command[0].lower().endswith((".cmd", ".bat")):
        subprocess.run(subprocess.list2cmdline(command), shell=True, **options)
    else:
        subprocess.run(command, **options)


def run_npm(args: Sequence[str]) -> None:
    run([NPM, *args], cwd=CLIENT_DIR)


def require_python_venv() -> None:
    if not VENV_PYTHON.is_file():
        raise RuntimeError("Core Python não instalado. Execute: python scripts/install.py")


def run_tauri_dev(*, env: Mapping[str, str] | None = None) -> None:
    require_python_venv()
    child_env = dict(env) if env is not None else os.environ.copy()
    # Preserve the venv path: resolving its symlink can select the system Python.
    child_env.setdefault("VOXCRAFT_PYTHON", str(VENV_PYTHON))
    run([NPM, "run", "tauri", "--", "dev"], cwd=CLIENT_DIR, env=child_env)


def run_tauri_build(bundles: Sequence[str] = ()) -> None:
    public_key = os.environ.get("UPDATER_PUBLIC_KEY")
    private_key = os.environ.get("SIGNING_PRIVATE_KEY")
    if not public_key:
        raise RuntimeError("Defina UPDATER_PUBLIC_KEY para gerar um build com updater.")
    if not private_key:
        raise RuntimeError("Defina SIGNING_PRIVATE_KEY para assinar o updater.")

    child_env = os.environ.copy()
    child_env.pop("SIGNING_PRIVATE_KEY", None)
    child_env["UPDATER_PUBLIC_KEY"] = public_key
    child_env["TAURI_SIGNING_PRIVATE_KEY"] = private_key
    child_env.setdefault("TAURI_SIGNING_PRIVATE_KEY_PASSWORD", "")

    compiler_info = subprocess.check_output(["rustc", "-vV"], text=True)
    target = next(line.removeprefix("host: ") for line in compiler_info.splitlines() if line.startswith("host: "))
    package_core(target)
    config = {
        "bundle": {"externalBin": ["binaries/voxcraft-core"]},
        "plugins": {"updater": {"pubkey": public_key}},
    }
    config_path = CORE_BUILD_DIR / f"tauri-{target}.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    args = ["run", "tauri", "--", "build", "--ci", "--target", target, "--config", str(config_path)]
    if bundles:
        args.extend(["--bundles", ",".join(bundles)])
    run([NPM, *args], cwd=CLIENT_DIR, env=child_env)


def package_core(target: str) -> None:
    python = [str(VENV_PYTHON)] if "PYTHON" not in os.environ and VENV_PYTHON.is_file() else SYSTEM_PYTHON
    binaries = CLIENT_DIR / "src-back" / "binaries"
    CORE_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    core_env = {key: value for key, value in os.environ.items() if key not in SIGNING_ENV}
    run([
        *python, "-m", "PyInstaller", "--noconfirm", "--onefile",
        "--name", f"voxcraft-core-{target}",
        "--distpath", binaries, "--workpath", CORE_BUILD_DIR, "--specpath", CORE_BUILD_DIR,
        CORE_DIR / "app.py",
    ], env=core_env)
    suffix = ".exe" if os.name == "nt" else ""
    smoke_test_core(binaries / f"voxcraft-core-{target}{suffix}", core_env)


def smoke_test_core(executable: Path, env: Mapping[str, str]) -> None:
    requests = [
        json.dumps({"id": 1, "method": "ping"}),
        json.dumps({"id": 2, "method": "shutdown"}),
    ]
    with TemporaryDirectory() as directory:
        try:
            result = subprocess.run(
                [executable],
                cwd=directory,
                env={**env, "APPDATA": directory, "XDG_CONFIG_HOME": directory},
                input="\n".join(requests) + "\n",
                capture_output=True,
                encoding="utf-8",
                timeout=30,
            )
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            if result.returncode != 0 or [
                (response.get("id"), response.get("ok")) for response in replies
            ] != [(1, True), (2, True)]:
                raise RuntimeError(f"O core empacotado falhou no teste de inicialização:\n{result.stderr}")
        except (ValueError, subprocess.TimeoutExpired) as error:
            raise RuntimeError(f"O core empacotado não respondeu corretamente: {error}") from error


def run_script(action) -> None:
    try:
        action()
    except subprocess.CalledProcessError as error:
        print(f"Comando falhou com código {error.returncode}: {error.cmd}", file=sys.stderr)
        raise SystemExit(error.returncode or 1)
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
