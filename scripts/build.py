import argparse
import sys

from common import run_npm, run_script, run_tauri_build


def build() -> None:
    parser = argparse.ArgumentParser(description="Compila o VoxCraft Studio.")
    parser.add_argument(
        "--target",
        choices=("desktop", "linux", "windows", "frontend"),
        default="desktop",
        help=(
            "desktop usa o padrão do sistema atual; linux gera deb/rpm; "
            "windows gera NSIS; frontend compila apenas o Vite."
        ),
    )
    target = parser.parse_args().target

    if target == "frontend":
        run_npm(["run", "build"])
        return
    if target == "linux" and not sys.platform.startswith("linux"):
        raise RuntimeError("O alvo Linux precisa ser compilado em Linux.")
    if target == "windows" and sys.platform != "win32":
        raise RuntimeError("O alvo Windows precisa ser compilado no Windows.")

    if target == "desktop":
        target = "windows" if sys.platform == "win32" else "linux" if sys.platform.startswith("linux") else ""
    bundles = {"linux": ["deb", "rpm"], "windows": ["nsis"]}
    if target not in bundles:
        raise RuntimeError("O build desktop está configurado para Windows e Linux.")
    run_tauri_build(bundles[target])


if __name__ == "__main__":
    run_script(build)
