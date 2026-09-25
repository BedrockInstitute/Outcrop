"""Synchronize an explicit source mirror for an isolated compiler cache."""
import argparse
from pathlib import Path
import shutil


def sync_sources(source: Path, destination: Path, *, extension='.lagda.md'):
    source, destination = source.resolve(), destination.absolute()
    resolved = destination.resolve()
    if (not source.is_dir() or resolved == source or resolved in source.parents
            or source in resolved.parents or destination.is_symlink()):
        raise ValueError('source and staging directories must be disjoint real directories')
    if not extension.startswith('.') or '/' in extension:
        raise ValueError('invalid source extension')
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
        if not target.is_file() or target.read_bytes() != path.read_bytes():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    for relative in staged.keys() - originals.keys():
        staged[relative].unlink()
    return len(originals)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--extension', default='.lagda.md')
    args = parser.parse_args(argv)
    count = sync_sources(args.source, args.destination, extension=args.extension)
    print(f'agda-stage: synchronized {count} sources')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
