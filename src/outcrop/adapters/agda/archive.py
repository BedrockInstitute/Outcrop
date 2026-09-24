"""Checksummed downloads and confined extraction shared by Agda installers."""
import hashlib
from pathlib import Path
import tarfile
import urllib.request


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, expected: str, archive: Path) -> None:
    if archive.is_file() and sha256(archive) == expected:
        return
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_suffix(archive.suffix + '.download')
    try:
        urllib.request.urlretrieve(url, temporary)
        actual = sha256(temporary)
        if actual != expected:
            raise RuntimeError(f'checksum mismatch for {url}: expected {expected}, got {actual}')
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)


def safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar.getmembers():
            target = (destination / member.name).resolve()
            if (not target.is_relative_to(destination) or member.name.startswith('/')
                    or not (member.isfile() or member.isdir())):
                raise RuntimeError(f'unsafe archive member: {member.name}')
        tar.extractall(destination)
