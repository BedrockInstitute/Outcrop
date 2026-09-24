"""Install an explicit library lock into a project-local Agda registry."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from urllib.parse import urlsplit

from .archive import download, safe_extract


def read_lock(path):
    lock = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(lock, dict) or lock.get('version') != 1 or not isinstance(lock.get('libraries'), list):
        raise ValueError('expected a version 1 library lock')
    names = set()
    for library in lock['libraries']:
        if not isinstance(library, dict):
            raise ValueError('library lock entries must be objects')
        for key in ('name', 'version'):
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*', library.get(key, '')):
                raise ValueError(f'invalid library {key}')
        if library['name'] in names:
            raise ValueError(f'duplicate library: {library["name"]}')
        names.add(library['name'])
        for key in ('archive_root', 'library'):
            value = library.get(key, '')
            part = PurePosixPath(value)
            if (not value or part.is_absolute() or '..' in part.parts or '\\' in value
                    or any(ord(c) < 32 for c in value)):
                raise ValueError(f'invalid library {key}')
        if not re.fullmatch(r'[a-f0-9]{64}', library.get('sha256', '')):
            raise ValueError('library sha256 must be a lowercase SHA-256 digest')
        url = urlsplit(library.get('url', ''))
        if url.scheme != 'https' or not url.netloc or url.username or url.password:
            raise ValueError('library url must be HTTPS without credentials')
    return lock['libraries']


def install(lock, build_dir, agda_dir):
    """No implicit Cubical dependency, global registry or environment mutation."""
    libraries = read_lock(lock)
    build_dir, agda_dir = Path(build_dir).resolve(), Path(agda_dir).resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    registered = []
    for library in libraries:
        identity = f'{library["name"]}-{library["version"]}'
        destination = build_dir / identity
        marker = destination / '.outcrop-source-sha256'
        archive = build_dir / 'downloads' / f'{identity}.tar.gz'
        expected = library['sha256']
        download(library['url'], expected, archive)
        descriptor = destination / library['library']
        if (not marker.is_file() or marker.read_text().strip() != expected or not descriptor.is_file()):
            with tempfile.TemporaryDirectory(prefix='.outcrop-library-', dir=build_dir) as temporary:
                safe_extract(archive, Path(temporary))
                extracted = Path(temporary) / library['archive_root']
                if not (extracted / library['library']).is_file():
                    raise RuntimeError(f'archive has no declared library: {library["library"]}')
                # Replace only this validated, named dependency, never the build root.
                if destination.exists():
                    shutil.rmtree(destination)
                extracted.replace(destination)
                marker.write_text(expected + '\n', encoding='utf-8')
        registered.append(str(descriptor))
    agda_dir.mkdir(parents=True, exist_ok=True)
    registry = agda_dir / 'libraries'
    # A lock owns this explicit registry. Replacing its entries removes stale
    # versions on upgrades; it never edits ~/.agda or an environment-chosen path.
    registry.write_text(''.join(path + '\n' for path in registered), encoding='utf-8')
    return registered


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--agda-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    for path in install(args.lock, args.build_dir, args.agda_dir):
        print(path)
    return 0
