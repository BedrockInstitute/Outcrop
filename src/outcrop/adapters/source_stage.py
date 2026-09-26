"""Synchronize an explicit source mirror for an isolated compiler cache."""
import argparse
import hashlib
from pathlib import Path
import shutil

from outcrop.core.source_syntax import AGDA_FENCE


def code_only_source(raw: bytes) -> bytes:
    """Canonical literate source: retain Agda fences, omit all prose.

    The pure-check interface hashes its entire input file, so timestamps alone
    cannot prevent a prose edit from invalidating it. The traced website build
    continues to use the original source, not this isolated mirror.
    """
    text = raw.decode('utf-8')
    blocks = AGDA_FENCE.findall(text)
    return ''.join(f'```agda\n{block}```\n' for block in blocks).encode('utf-8')


def code_fingerprint(source: Path, *, extension='.lagda.md') -> str:
    """Fingerprint exactly the paths and bytes written by code-only staging."""
    if not source.is_dir():
        raise ValueError(f'not a source directory: {source}')
    if not extension.startswith('.') or '/' in extension:
        raise ValueError('invalid source extension')
    digest = hashlib.sha256()
    for path in sorted(source.rglob('*' + extension)):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'not a regular source file: {path}')
        relative = path.relative_to(source).as_posix().encode('utf-8')
        data = code_only_source(path.read_bytes()) if extension == '.lagda.md' else path.read_bytes()
        digest.update(len(relative).to_bytes(8, 'big'))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, 'big'))
        digest.update(data)
    return digest.hexdigest()


def sync_sources(source: Path, destination: Path, *, extension='.lagda.md', code_only=False):
    source, destination = source.resolve(), destination.absolute()
    resolved = destination.resolve()
    if (not source.is_dir() or resolved == source or resolved in source.parents
            or source in resolved.parents or destination.is_symlink()):
        raise ValueError('source and staging directories must be disjoint real directories')
    if not extension.startswith('.') or '/' in extension:
        raise ValueError('invalid source extension')
    if code_only and extension != '.lagda.md':
        raise ValueError('code-only staging requires .lagda.md sources')
    # Permit platform aliases above the staging root (e.g. macOS /tmp),
    # but never follow a symlink within the mirror itself.
    destination = resolved
    originals = {path.relative_to(source): path for path in source.rglob('*' + extension)}
    staged = {path.relative_to(destination): path for path in destination.rglob('*' + extension)}
    # Validate the complete write set before copying or deleting. Never follow
    # a staged symlink into a different workspace or a third-party dependency.
    for relative, path in {**staged, **originals}.items():
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'not a regular source file: {path}')
        target = destination / relative
        if any(parent.is_symlink() for parent in [target, *target.parents]):
            raise ValueError(f'symlink in staging path: {target}')
    for relative, path in originals.items():
        target = destination / relative
        data = code_only_source(path.read_bytes()) if code_only else path.read_bytes()
        if not target.is_file() or target.read_bytes() != data:
            target.parent.mkdir(parents=True, exist_ok=True)
            if code_only:
                target.write_bytes(data)
            else:
                shutil.copy2(path, target)
    for relative in staged.keys() - originals.keys():
        staged[relative].unlink()
    return len(originals)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--extension', default='.lagda.md')
    parser.add_argument('--code-only', action='store_true',
                        help='stage only Agda fences for an isolated pure typecheck')
    parser.add_argument('--fingerprint', action='store_true',
                        help='print the code-only source identity without staging')
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args(argv)
    if args.fingerprint:
        if args.destination:
            parser.error('--fingerprint does not accept --destination')
        print(code_fingerprint(args.source, extension=args.extension))
        return 0
    if args.destination is None:
        parser.error('--destination is required unless --fingerprint is used')
    count = sync_sources(args.source, args.destination, extension=args.extension,
                         code_only=args.code_only)
    print(f'agda-stage: synchronized {count} sources')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
