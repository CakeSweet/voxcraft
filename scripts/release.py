"""Validate a release tag and stage the signed installers for GitHub Releases."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import quote

from common import CLIENT_DIR, CORE_DIR, run_script


# Keep the manifest keys in sync with updater_target in the Tauri host.
INSTALLERS = {
    "windows-x86_64": ("*-setup.exe", "VoxCraftStudio_Setup_v{version}.exe"),
    "linux-x86_64-deb": ("*.deb", "voxcraft-studio_{version}_amd64.deb"),
    "linux-x86_64-rpm": ("*.rpm", "voxcraft-studio-{version}-1.x86_64.rpm"),
}


def configured_version() -> str:
    tauri_config = CLIENT_DIR / "src-back" / "tauri.conf.json"
    config_version = json.loads(tauri_config.read_text(encoding="utf-8"))["version"]
    core_file = CORE_DIR / "src" / "__init__.py"
    core_version = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', core_file.read_text(encoding="utf-8"), re.M)
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", config_version):
        raise RuntimeError(f"Versão inválida em tauri.conf.json (use MAJOR.MINOR.PATCH): {config_version!r}")
    if core_version is None or core_version.group(1) != config_version:
        raise RuntimeError("A versão de tauri.conf.json deve coincidir com APP_VERSION do core.")
    return config_version


def resolve_release(tag: str | None = None) -> tuple[str, str]:
    version = configured_version()
    expected_tag = f"v{version}"
    if tag is not None:
        if not re.fullmatch(r"v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", tag):
            raise RuntimeError(f"Use uma tag no formato vMAJOR.MINOR.PATCH: {tag!r}")
        if tag != expected_tag:
            raise RuntimeError("A versão da tag deve coincidir com tauri.conf.json e APP_VERSION do core.")
    return expected_tag, version


def stage_installers(source: Path, destination: Path, *, repo: str, tag: str, version: str) -> None:
    platforms = {}
    copies = []
    for target, (pattern, template) in INSTALLERS.items():
        matches = [path for path in source.rglob(pattern) if path.is_file()]
        if len(matches) != 1:
            raise RuntimeError(f"Esperava um instalador para {target}; encontrei {len(matches)}.")
        artifact, = matches
        signature_file = artifact.with_name(f"{artifact.name}.sig")
        if not signature_file.is_file():
            raise RuntimeError(f"Assinatura ausente: {signature_file.name}")
        signature = signature_file.read_text(encoding="utf-8").strip()
        if not signature:
            raise RuntimeError(f"Assinatura vazia: {signature_file.name}")
        name = template.format(version=version)
        platforms[target] = {
            "signature": signature,
            "url": f"https://github.com/{repo}/releases/download/{quote(tag)}/{quote(name)}",
        }
        copies.append((artifact, name))

    destination.mkdir(parents=True, exist_ok=False)
    for path, name in copies:
        shutil.copyfile(path, destination / name)
    manifest = {
        "version": version,
        "pub_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platforms": platforms,
    }
    (destination / "latest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def write_github_output(name: str, value: str) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with Path(output_file).open("a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("--ensure-new", action="store_true")
    commands.add_parser("tag")
    stage = commands.add_parser("stage")
    stage.add_argument("source", type=Path)
    stage.add_argument("destination", type=Path)
    args = parser.parse_args()
    ref_is_tag = os.environ.get("GITHUB_REF_TYPE") == "tag" or os.environ.get("GITHUB_EVENT_NAME") == "push"
    explicit_tag = os.environ.get("GITHUB_REF_NAME", "") if ref_is_tag else None
    tag, version = resolve_release(explicit_tag)
    if args.command == "check":
        if args.ensure_new:
            result = subprocess.run(
                ["gh", "release", "view", tag],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                raise RuntimeError(f"A release {tag} já existe. Atualize a versão antes de publicar.")
        return
    if args.command == "tag":
        print(tag)
        return
    if args.command == "stage":
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not repo:
            raise RuntimeError("GITHUB_REPOSITORY não definido.")
        stage_installers(args.source, args.destination, repo=repo, tag=tag, version=version)
        write_github_output("tag", tag)


if __name__ == "__main__":
    run_script(main)
