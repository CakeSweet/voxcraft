from pathlib import Path
import re
import sys

core_entrypoint = Path(SPECPATH).parent / "internal" / "core" / "app.py"
analysis = Analysis([str(core_entrypoint)])

# Use the audio libraries from the machine running VoxCraft. The copies pulled
# in on the build host can mask the user's PipeWire/JACK and ALSA plugins.
system_audio = re.compile(
    r"^lib(?:portaudio|asound(?:_module_[^.]+)?|jack(?:server|net)?|"
    r"pipewire-[\d.]+|pulse(?:-simple)?)\.so(?:\..*)?$"
)
analysis.binaries = [
    entry for entry in analysis.binaries
    if not any(system_audio.fullmatch(Path(path).name) for path in entry[:2])
]

exe = EXE(
    PYZ(analysis.pure),
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    name=sys.argv[1],
    console=True,
)
