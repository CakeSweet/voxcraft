from common import CLIENT_DIR, CORE_DIR, SYSTEM_PYTHON, VENV_PYTHON, run, run_script


def check() -> None:
    python = [str(VENV_PYTHON)] if VENV_PYTHON.is_file() else SYSTEM_PYTHON
    manifest = CLIENT_DIR / "src-back" / "Cargo.toml"
    run([*python, "-m", "compileall", "-q", str(CORE_DIR)])
    run(["node", "--check", str(CLIENT_DIR / "src-front" / "main.js")])
    run(["node", "--check", str(CLIENT_DIR / "src-front" / "updates.js")])
    run(["cargo", "check", "--manifest-path", str(manifest)])
    run(["cargo", "fmt", "--manifest-path", str(manifest), "--", "--check"])


if __name__ == "__main__":
    run_script(check)
