"""Build the Linux VoxCraft core sidecar with PyInstaller.

PyInstaller needs a spec file for custom analysis, so this script generates one
temporarily instead of keeping a platform-specific .spec file in the project.
"""

import argparse
from pathlib import Path
import tempfile

from common import CORE_DIR, SYSTEM_PYTHON, run, run_script


# Keep audio libraries provided by the target Linux system out of the bundle.
_SYSTEM_AUDIO_PATTERN = (
    r"^lib(?:portaudio|asound(?:_module_[^.]+)?|jack(?:server|net)?|"
    r"pipewire-[\d.]+|pulse(?:-simple)?)\.so(?:\..*)?$"
)


def _spec_source(name: str) -> str:
    entrypoint = str(CORE_DIR / "app.py")
    return f'''from pathlib import Path
import re

analysis = Analysis([{entrypoint!r}])

# Host audio libraries and plugins must come from the user's Linux system.
system_audio = re.compile({_SYSTEM_AUDIO_PATTERN!r})
analysis.binaries = [
    entry for entry in analysis.binaries
    if not any(system_audio.fullmatch(Path(path).name) for path in entry[:2])
]

exe = EXE(
    PYZ(analysis.pure),
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    name={name!r},
    console=True,
)
'''


def build() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distpath", type=Path, required=True)
    parser.add_argument("--workpath", type=Path, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="voxcraft-pyinstaller-") as directory:
        spec_file = Path(directory) / "voxcraft-core-linux.spec"
        spec_file.write_text(_spec_source(args.name), encoding="utf-8")
        run([
            *SYSTEM_PYTHON,
            "-m", "PyInstaller", "--noconfirm",
            "--distpath", args.distpath,
            "--workpath", args.workpath,
            spec_file,
        ])


if __name__ == "__main__":
    run_script(build)
