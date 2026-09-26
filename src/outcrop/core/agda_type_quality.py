"""Reject Agda interaction types containing unsolved, internal metavariable names."""

import re


IMPRECISE_TYPE_RE = re.compile(r"_[\w.']+_\d+|(?<![\w'])_\d+\b|\?\d+")


def imprecise_type(value: str) -> bool:
    return bool(IMPRECISE_TYPE_RE.search(value))
