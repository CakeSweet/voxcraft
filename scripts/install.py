from common import (
    CLIENT_DIR,
    CORE_DIR,
    NPM,
    SYSTEM_PYTHON,
    VENV_DIR,
    VENV_PYTHON,
    run,
    run_script,
)


def install() -> None:
    run([NPM, "ci"], cwd=CLIENT_DIR)
    run([*SYSTEM_PYTHON, "-m", "venv", str(VENV_DIR)])
    run(
        [
            str(VENV_PYTHON),
            "-m",
            "pip",
            "install",
            "-r",
            str(CORE_DIR / "requirements.txt"),
        ]
    )


if __name__ == "__main__":
    run_script(install)
