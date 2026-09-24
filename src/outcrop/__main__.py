"""Command-line entry point with no implicit project or repository."""
import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "lint", "extract-types", "extract-expressions", "check-links"))
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(argv[:1])
    options = argv[1:]
    if args.command == "build":
        from .site.website import main as run
    elif args.command == "lint":
        from .site.site_lint import main as run
    elif args.command == "extract-types":
        from .adapters.extract_types import main as run
    elif args.command == "extract-expressions":
        from .adapters.extract_expression_types import main as run
    else:
        from .adapters.link_check import main as run
    return run(options)


if __name__ == "__main__":
    raise SystemExit(main())
