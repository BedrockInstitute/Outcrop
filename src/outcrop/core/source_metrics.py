"""Count source lines in literate Agda masters, independently of their prose."""

import argparse
import json
from pathlib import Path
from outcrop.core.agda_lint import agda_lines


def count(text):
    """Count supplied Markdown without discovering a project or reading files."""
    code = [line for _, line in agda_lines(text)]
    return {
        "nonblank_code": sum(bool(line.strip()) for line in code),
        "code": len(code),
        "physical": len(text.splitlines()),
    }


def main(argv=None, *, default_source=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path,
                        default=default_source, required=default_source is None)
    parser.add_argument("--extension", choices=('.md', '.lagda.md'), default='.lagda.md')
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    files = {str(path.relative_to(args.src)): count(path.read_text(encoding='utf-8'))
             for path in sorted(args.src.rglob('*' + args.extension))}
    if not files:
        parser.error(f"no literate Agda masters found in {args.src}")
    totals = {key: sum(row[key] for row in files.values())
              for key in ("nonblank_code", "code", "physical")}
    if args.json:
        print(json.dumps({"totals": totals, "files": files}, indent=2))
    else:
        print(f"{len(files)} modules; " + "; ".join(
            f"{value:,} {key}" for key, value in totals.items()))


if __name__ == "__main__":
    main()
