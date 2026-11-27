"""Validate, bump, and stage signed installers for GitHub Releases."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import quote

from common import CLIENT_DIR, CORE_DIR, ROOT, run_script


# Keep the manifest keys in sync with updater_target in the Tauri host.
INSTALLERS = {
    "windows-x86_64": ("*-setup.exe", "VoxCraftStudio_Setup_v{version}.exe"),
    "linux-x86_64-deb": ("*.deb", "voxcraft-studio_{version}_amd64.deb"),
    "linux-x86_64-rpm": ("*.rpm", "voxcraft-studio-{version}-1.x86_64.rpm"),
}

SEMVER_PATTERN = r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
SEMVER_RE = re.compile(SEMVER_PATTERN)
TAG_SEMVER_RE = re.compile(rf"^v({SEMVER_PATTERN})$")


def parse_semver(version: str) -> tuple[int, int, int]:
    if not SEMVER_RE.fullmatch(version):
        raise RuntimeError(f"Versão inválida (use MAJOR.MINOR.PATCH): {version!r}")
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def format_semver(parts: tuple[int, int, int]) -> str:
    return f"{parts[0]}.{parts[1]}.{parts[2]}"


def configured_version() -> str:
    tauri_config = CLIENT_DIR / "src-back" / "tauri.conf.json"
    config_version = json.loads(tauri_config.read_text(encoding="utf-8"))["version"]
    core_file = CORE_DIR / "src" / "__init__.py"
    core_version = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', core_file.read_text(encoding="utf-8"), re.M)
    if not SEMVER_RE.fullmatch(config_version):
        raise RuntimeError(f"Versão inválida em tauri.conf.json (use MAJOR.MINOR.PATCH): {config_version!r}")
    if core_version is None or core_version.group(1) != config_version:
        raise RuntimeError("A versão de tauri.conf.json deve coincidir com APP_VERSION do core.")
    return config_version


def resolve_release(tag: str | None = None) -> tuple[str, str]:
    version = configured_version()
    expected_tag = f"v{version}"
    if tag is not None:
        if not TAG_SEMVER_RE.fullmatch(tag):
            raise RuntimeError(f"Use uma tag no formato vMAJOR.MINOR.PATCH: {tag!r}")
        if tag != expected_tag:
            raise RuntimeError("A versão da tag deve coincidir com tauri.conf.json e APP_VERSION do core.")
    return expected_tag, version


def release_exists(tag: str) -> bool:
    result = subprocess.run(
        ["gh", "release", "view", tag],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def existing_github_versions() -> set[tuple[int, int, int]]:
    versions: set[tuple[int, int, int]] = set()

    gh_result = subprocess.run(
        ["gh", "release", "list", "--limit", "1000", "--json", "tagName"],
        capture_output=True,
        text=True,
    )
    if gh_result.returncode != 0:
        raise RuntimeError(f"Não foi possível consultar as releases no GitHub: {gh_result.stderr.strip()}")
    for item in json.loads(gh_result.stdout or "[]"):
        match = TAG_SEMVER_RE.fullmatch(str(item.get("tagName", "")).strip())
        if match:
            versions.add(parse_semver(match.group(1)))

    git_result = subprocess.run(
        ["git", "ls-remote", "--tags", "origin"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if git_result.returncode == 0:
        for line in git_result.stdout.splitlines():
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            ref = parts[1].strip()
            if ref.endswith("^{}") or not ref.startswith("refs/tags/"):
                continue
            match = TAG_SEMVER_RE.fullmatch(ref.removeprefix("refs/tags/"))
            if match:
                versions.add(parse_semver(match.group(1)))

    return versions


def next_available_version(base_version: str) -> str:
    existing = existing_github_versions()
    candidate = max([parse_semver(base_version), *existing])
    while candidate in existing or release_exists(f"v{format_semver(candidate)}"):
        candidate = (candidate[0], candidate[1], candidate[2] + 1)
    return format_semver(candidate)


def _replace_once(path: Path, pattern: str, replacement: str, *, flags: int = 0) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Não foi possível atualizar a versão em {path.relative_to(ROOT)}.")
    path.write_text(updated, encoding="utf-8")


def apply_version(version: str, *, only_if_newer: bool = False) -> bool:
    target = parse_semver(version)
    if only_if_newer and target <= parse_semver(configured_version()):
        return False

    _replace_once(
        CORE_DIR / "src" / "__init__.py",
        r'^(APP_VERSION\s*=\s*")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        flags=re.M,
    )
    _replace_once(
        CLIENT_DIR / "src-back" / "Cargo.toml",
        r'(\[package\][\s\S]*?^version\s*=\s*")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        flags=re.M,
    )

    cargo_lock = CLIENT_DIR / "src-back" / "Cargo.lock"
    if cargo_lock.is_file():
        _replace_once(
            cargo_lock,
            r'(\[\[package\]\]\s+name\s*=\s*"voxcraft-app"\s+version\s*=\s*")[^"]+(")',
            rf"\g<1>{version}\g<2>",
        )

    for json_path in (CLIENT_DIR / "package.json", CLIENT_DIR / "src-back" / "tauri.conf.json"):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        data["version"] = version
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    package_lock = CLIENT_DIR / "package-lock.json"
    if package_lock.is_file():
        lock_data = json.loads(package_lock.read_text(encoding="utf-8"))
        lock_data["version"] = version
        packages = lock_data.get("packages")
        if isinstance(packages, dict) and isinstance(packages.get(""), dict):
            packages[""]["version"] = version
        package_lock.write_text(json.dumps(lock_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    docs_app = ROOT / "docs" / "app.js"
    if docs_app.is_file():
        _replace_once(
            docs_app,
            r'(const\s+DEFAULT_VERSION\s*=\s*")[^"]+(";)',
            rf"\g<1>{version}\g<2>",
        )

    docs_index = ROOT / "docs" / "index.html"
    if docs_index.is_file():
        _replace_once(
            docs_index,
            r'(<span id="releaseVersionText">)v[^<]+(</span>)',
            rf"\g<1>v{version}\g<2>",
        )
        _replace_once(
            docs_index,
            r'(id="dlMetaLine">Versão )v[^\s<]+',
            rf"\g<1>v{version}",
        )
    return True


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
    next_cmd = commands.add_parser("next")
    next_cmd.add_argument("--keep-configured", action="store_true")
    apply_cmd = commands.add_parser("apply")
    apply_cmd.add_argument("version")
    apply_cmd.add_argument("--only-if-newer", action="store_true")
    stage = commands.add_parser("stage")
    stage.add_argument("source", type=Path)
    stage.add_argument("destination", type=Path)
    args = parser.parse_args()
    ref_is_tag = os.environ.get("GITHUB_REF_TYPE") == "tag" or os.environ.get("GITHUB_EVENT_NAME") == "push"
    explicit_tag = os.environ.get("GITHUB_REF_NAME", "") if ref_is_tag else None

    if args.command == "apply":
        if apply_version(args.version, only_if_newer=args.only_if_newer):
            configured_version()
        return

    tag, version = resolve_release(explicit_tag)
    if args.command == "check":
        if args.ensure_new and release_exists(tag):
            raise RuntimeError(f"A release {tag} já existe. Atualize a versão antes de publicar.")
        return
    if args.command == "tag":
        print(tag)
        return
    if args.command == "next":
        resolved_version = version if (ref_is_tag or args.keep_configured) else next_available_version(version)
        resolved_tag = f"v{resolved_version}"
        write_github_output("version", resolved_version)
        write_github_output("tag", resolved_tag)
        print(resolved_tag)
        return
    if args.command == "stage":
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not repo:
            raise RuntimeError("GITHUB_REPOSITORY não definido.")
        stage_installers(args.source, args.destination, repo=repo, tag=tag, version=version)
        write_github_output("tag", tag)


if __name__ == "__main__":
    run_script(main)
