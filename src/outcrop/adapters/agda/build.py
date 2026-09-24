#!/usr/bin/env python3
"""Build the optional Outcrop Agda toolchain into an explicit local directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from .archive import download, safe_extract

RESOURCES = Path(__file__).resolve().parent / 'resources'


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command), file=sys.stderr)
    subprocess.run(command, cwd=cwd, check=True)


def ensure_happy(build_root: Path, version: str) -> Path:
    """Install the pinned parser generator outside Cabal's opaque store path."""
    directory = build_root / "build-tools" / f"happy-{version}"
    executable = directory / "happy"
    wrapper = directory / "outcrop-happy"
    happy_environment = os.environ.copy()
    happy_environment.pop("GHCRTS", None)
    if executable.is_file():
        actual = subprocess.check_output(
            [str(executable), "--numeric-version"], text=True,
            env=happy_environment,
        ).strip()
        if actual != version:
            executable.unlink()

    if not executable.is_file():
        directory.mkdir(parents=True, exist_ok=True)
        run([
            "cabal", "install", f"happy-{version}",
            f"--installdir={directory}", "--install-method=copy",
            "--overwrite-policy=always", "-j2",
        ], cwd=build_root)
        actual = subprocess.check_output(
            [str(executable), "--numeric-version"], text=True,
            env=happy_environment,
        ).strip()
        if actual != version:
            raise RuntimeError(
                f"Happy version mismatch: expected {version}, got {actual}"
            )

    # The Makefile's GHCRTS heap guard is intended for Agda. Happy is not
    # linked with -rtsopts, so isolate it without weakening Agda's limit.
    wrapper.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        "tool_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
        "unset GHCRTS\n"
        "exec \"$tool_dir/happy\" \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    actual = subprocess.check_output(
        [str(wrapper), "--numeric-version"], text=True,
    ).strip()
    if actual != version:
        raise RuntimeError(
            f"Happy wrapper version mismatch: expected {version}, got {actual}"
        )
    return wrapper


def macos_ghc_options() -> list[str]:
    """Use an older installed SDK when GHC 9.4 cannot parse a newer .tbd."""
    if platform.system() != "Darwin":
        return []
    sdk_root = Path("/Library/Developer/CommandLineTools/SDKs")
    for name in ("MacOSX14.4.sdk", "MacOSX14.sdk", "MacOSX13.3.sdk", "MacOSX13.sdk"):
        sdk = sdk_root / name
        if sdk.is_dir():
            return [
                f"--ghc-option=-L{sdk / 'usr/lib'}",
                f"--ghc-option=-optl-isysroot{sdk}",
            ]
    return []


def identity(tool_root=RESOURCES):
    """Content identity, independent of the checkout/install/cache location."""
    manifest_path = tool_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    overlay_hash = tree_hash(tool_root / 'src')
    fingerprint = hashlib.sha256(
        manifest_path.read_bytes() + (tool_root / manifest['adapter']).read_bytes()
        + overlay_hash.encode() + Path(__file__).read_bytes()
        + Path(__file__).with_name('archive.py').read_bytes()
    ).hexdigest()
    return {'schema': 1, 'agda_version': manifest['agda_version'],
            'source_sha256': manifest['source_sha256'], 'adapter': manifest['adapter'],
            'overlay_sha256': overlay_hash, 'fingerprint': fingerprint}


def build(build_root: Path, *, tool_root=RESOURCES) -> Path:
    build_root = build_root.resolve()
    manifest = json.loads((tool_root / 'manifest.json').read_text(encoding='utf-8'))
    compiler_identity = identity(tool_root)
    version = manifest["agda_version"]
    happy_version = manifest["happy_version"]
    source_url = manifest["source_url"]
    source_sha256 = manifest["source_sha256"]
    adapter = tool_root / manifest["adapter"]
    overlay = tool_root / "src"

    downloads = build_root / "downloads"
    archive = downloads / f"Agda-{version}.tar.gz"
    source = build_root / "source" / f"Agda-{version}"
    marker = source / ".outcrop-overlay"
    fingerprint = compiler_identity['fingerprint']
    expected_marker = f"{source_sha256}\n{fingerprint}\n"
    wrapper = build_root / 'bin/outcrop-agda'
    installed_identity = build_root / 'install/outcrop-agda.json'
    if (wrapper.is_file() and installed_identity.is_file()
            and json.loads(installed_identity.read_text()) == compiler_identity
            and (build_root / 'install/bin/agda').is_file()
            and (build_root / 'install/data').is_dir()):
        # This is a verified content hit, not a timestamp-only cache assumption.
        wrapper.touch()
        return wrapper

    downloads.mkdir(parents=True, exist_ok=True)
    download(source_url, source_sha256, archive)

    if not marker.exists() or marker.read_text(encoding="utf-8") != expected_marker:
        shutil.rmtree(source.parent, ignore_errors=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        safe_extract(archive, source.parent)
        shutil.copytree(overlay, source / "src/full", dirs_exist_ok=True)
        run(["patch", "-p1", "--forward", "--batch", "-i", str(adapter)], cwd=source)
        marker.write_text(expected_marker, encoding="utf-8")

    allow_newer = ",".join(manifest.get("cabal_allow_newer", []))
    happy = ensure_happy(build_root, happy_version)
    # Cabal 3.12 resolves Agda's packaged build tools incorrectly when this
    # local build directory is expressed as an absolute path.
    command = [
        "cabal", "build", "exe:agda", "--builddir=dist-outcrop", "-j2",
    ]
    # Cabal 3.12 cannot reliably determine the version of a Happy executable
    # stored under its hashed package path. Use the pinned project-local copy.
    command.append(f"--with-happy={happy}")
    if allow_newer:
        command.append(f"--allow-newer={allow_newer}")
    command.extend(macos_ghc_options())
    run(command, cwd=source)
    executable = subprocess.check_output(
        ["cabal", "list-bin", "exe:agda", "--builddir=dist-outcrop"],
        cwd=source, text=True,
    ).strip()

    install = build_root / "install"
    binary = install / "bin/agda"
    data = install / "data"
    binary.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(executable, binary)
    shutil.rmtree(data, ignore_errors=True)
    shutil.copytree(source / "src/data", data)
    installed_identity.write_text(
        json.dumps(compiler_identity, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        "outcrop_build=$(CDPATH= cd -- \"$(dirname -- \"$0\")/..\" && pwd)\n"
        "if [ \"${1-}\" = --outcrop-version ]; then\n"
        "  cat \"$outcrop_build/install/outcrop-agda.json\"\n"
        "  exit 0\n"
        "fi\n"
        "Agda_datadir=\"$outcrop_build/install/data\"; export Agda_datadir\n"
        "exec \"$outcrop_build/install/bin/agda\" \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    print(f"built {wrapper}", file=sys.stderr)
    return wrapper


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path)
    parser.add_argument('--identity', action='store_true', help='print expected compiler identity without building')
    args = parser.parse_args(argv)
    if args.identity:
        print(json.dumps(identity(), indent=2, sort_keys=True))
    elif args.build_dir is None:
        parser.error('--build-dir is required unless --identity is used')
    else:
        build(args.build_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
