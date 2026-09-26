"""Shared Markdown pipe-table and immediately following caption grammar."""

import re

CAPTION_RE = re.compile(r"^:[ \t]+(\S.*)$")


def caption_text(line):
    match = CAPTION_RE.match(line)
    return match.group(1).strip() if match else None


def is_table_separator(line):
    stripped = line.strip()
    return bool(stripped) and set(stripped) <= set("|:- ") and "-" in stripped


def table_end(lines, index):
    """Return the first line after a pipe table starting at index, or None."""
    if (index + 1 >= len(lines) or not lines[index].lstrip().startswith("|")
            or not is_table_separator(lines[index + 1])):
        return None
    end = index + 2
    while (end < len(lines) and lines[end].lstrip().startswith("|")
           and not is_table_separator(lines[end])):
        end += 1
    return end


def missing_table_captions(text):
    """Yield source offsets of uncaptained tables, ignoring fenced examples."""
    lines = text.splitlines(keepends=True)
    content = [line.rstrip("\r\n") for line in lines]
    offsets = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)
    index = 0
    fence = None
    while index < len(content):
        line = content[index]
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            index += 1
            continue
        if fence is not None:
            index += 1
            continue
        end = table_end(content, index)
        if end is None:
            index += 1
            continue
        if end == len(content) or caption_text(content[end]) is None:
            yield offsets[index]
        index = end + 1
