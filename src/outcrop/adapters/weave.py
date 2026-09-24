"""Weave explicit multilingual Markdown sources into language-specific trees.

No project, catalog, compiler dependency or Agda library is discovered implicitly.
An optional --library file is copied verbatim beside each language's sources.
"""
import argparse
from pathlib import Path
import sys

from outcrop.core.i18n_markers import LANGS, lint_markers, weave


def check(files):
    problems = 0
    for path in files:
        for line, message in lint_markers(Path(path).read_text(encoding='utf-8')):
            print(f'{path}:{line}: {message}')
            problems += 1
    if problems:
        print(f'{problems} marker problem(s).', file=sys.stderr)
    return bool(problems)


def generate(files, output, languages, *, root=None, library_for_language=None):
    """Weave a batch; an adapter may supply (filename, text) library metadata.

    Validate the entire batch before writing. Source-relative paths are preserved;
    explicitly supplied files outside root use their basename, with collisions
    diagnosed rather than silently overwriting another source.
    """
    files = [Path(path) for path in files]
    if any(language not in LANGS for language in languages):
        raise ValueError('unsupported language')
    root = Path(root).resolve() if root else None
    prepared, destinations = [], set()
    for path in files:
        source = path.read_text(encoding='utf-8')
        problems = lint_markers(source)
        if problems:
            raise ValueError('\n'.join(f'{path}:{line}: {message}' for line, message in problems))
        resolved = path.resolve()
        relative = resolved.relative_to(root) if root and resolved.is_relative_to(root) else Path(path.name)
        if relative in destinations:
            raise ValueError(f'duplicate woven destination: {relative}')
        destinations.add(relative)
        prepared.append((relative, source))
    libraries = {}
    if prepared and library_for_language:
        for language in languages:
            filename, text = library_for_language(language)
            if Path(filename).name != filename or not filename.endswith('.agda-lib'):
                raise ValueError('library filename must be a plain .agda-lib filename')
            libraries[language] = filename, text
    for language in languages:
        target = Path(output) / language
        for relative, source in prepared:
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(weave(source, language), encoding='utf-8')
        if language in libraries:
            filename, text = libraries[language]
            (target / filename).write_text(text, encoding='utf-8')
    print(f'woven {len(prepared) * len(languages)} file(s) into {output}/<lang>/', file=sys.stderr)
    return 0


def main(argv=None, *, default_root=None, default_extension='.md',
         default_languages=LANGS, library_for_language=None, excluded_roots=()):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check', action='store_true')
    modes.add_argument('--gen', action='store_true')
    modes.add_argument('--lang', choices=LANGS)
    parser.add_argument('--root', type=Path, default=default_root)
    parser.add_argument('--extension', choices=('.md', '.lagda.md'), default=default_extension)
    parser.add_argument('--out', type=Path, default=Path('_build/woven'))
    parser.add_argument('--langs', default=','.join(default_languages))
    parser.add_argument('--library', type=Path, help='copy this .agda-lib verbatim into each language tree')
    parser.add_argument('files', nargs='*', type=Path)
    args = parser.parse_args(argv)
    if args.lang and len(args.files) != 1:
        parser.error('--lang LANG needs exactly one FILE')
    if not args.files and args.root is None:
        parser.error('supply FILE or an explicit --root')
    languages = [language for language in args.langs.split(',') if language]
    if not languages or len(set(languages)) != len(languages) or any(language not in LANGS for language in languages):
        parser.error('--langs requires distinct supported languages')
    files = args.files or sorted(args.root.rglob('*' + args.extension))
    excluded = [Path(path).resolve() for path in excluded_roots]
    files = [path for path in files if not any(path.resolve().is_relative_to(root) for root in excluded)]
    try:
        if args.check:
            return int(check(files))
        if args.lang:
            if not files:
                parser.error('--lang FILE is excluded by the project source policy')
            sys.stdout.write(weave(files[0].read_text(encoding='utf-8'), args.lang))
            return 0
        if args.library:
            library_text = args.library.read_text(encoding='utf-8')
            library_for_language = lambda language: (args.library.name, library_text)
        return generate(files, args.out, languages, root=args.root,
                        library_for_language=library_for_language)
    except (OSError, ValueError) as error:
        print(f'weave: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
