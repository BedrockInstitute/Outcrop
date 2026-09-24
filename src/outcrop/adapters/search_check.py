#!/usr/bin/env python3
"""Audit every full-text search destination in an explicitly published site."""
from collections import Counter
import argparse
from html import unescape
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


def check(root, languages=None):
    root = Path(root)
    languages = languages or [language for language in ('en', 'zh', 'ja') if (root / language / 'index.html').is_file()]
    if not languages:
        raise ValueError('no published language editions found')
    entries = json.loads((root / "search-content.json").read_text())
    targets = set()
    for entry in entries:
        for language in languages if entry["lang"] == "*" else (entry["lang"],):
            link = urlsplit(entry["href"])
            targets.add((language, unquote(link.path), unquote(link.fragment)))
    cache, errors = {}, []
    for language, name, anchor in sorted(targets):
        path = root / language / name
        if path not in cache:
            cache[path] = (set(unescape(x) for x in re.findall(r'\bid="([^"]+)"', path.read_text()))
                           if path.is_file() else None)
        if cache[path] is None or (anchor and anchor not in cache[path]):
            errors.append(f"{language}/{name}#{anchor}")
    print(f"Search: {len(entries)} entries; {len(targets)} destinations; {len(errors)} broken")
    print(dict(Counter(entry["kind"] for entry in entries)))
    for error in errors[:30]:
        print(error)
    return bool(errors)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', type=Path)
    parser.add_argument('--languages', help='comma-separated edition directories; default: discover published editions')
    args = parser.parse_args(argv)
    return int(check(args.site, args.languages.split(',') if args.languages else None))


if __name__ == "__main__":
    sys.exit(main())
