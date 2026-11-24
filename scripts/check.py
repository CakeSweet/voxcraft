from common import CLIENT_DIR, CORE_DIR, ROOT, SYSTEM_PYTHON, VENV_PYTHON, run, run_script


def check() -> None:
    python = [str(VENV_PYTHON)] if VENV_PYTHON.is_file() else SYSTEM_PYTHON
    manifest = CLIENT_DIR / "src-back" / "Cargo.toml"
    run([*python, "-m", "compileall", "-q", str(CORE_DIR)])
    js_files = [
        *sorted((CLIENT_DIR / "src-front").glob("*.js")),
        ROOT / "docs" / "app.js",
    ]
    for js_file in js_files:
        run(["node", "--check", str(js_file)])
    run(["cargo", "check", "--manifest-path", str(manifest)])
    run(["cargo", "fmt", "--manifest-path", str(manifest), "--", "--check"])


if __name__ == "__main__":
    run_script(check)
