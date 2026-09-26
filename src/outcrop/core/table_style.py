"""Shared Markdown pipe-table and immediately following caption grammar."""

import re

CAPTION_RE = re.compile(r"^:[ \t]+(\S.*)$")
FINAL_PERIODS = ('.', '。', '．', '｡')


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


def _tables(text):
    """Yield table/caption positions outside fenced examples."""
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
        caption = caption_text(content[end]) if end < len(content) else None
        yield (offsets[index], offsets[end] if end < len(content) else None,
               caption, content[end] if end < len(content) else '')
        index = end + 1


def missing_table_captions(text):
    """Yield source offsets of uncaptained tables, ignoring fenced examples."""
    for table_at, _, caption, _ in _tables(text):
        if caption is None:
            yield table_at


def table_caption_periods(text):
    """Yield offsets of terminal periods in live pipe-table captions."""
    for _, caption_at, caption, line in _tables(text):
        if caption and caption.endswith(FINAL_PERIODS):
            yield caption_at + len(line.rstrip()) - 1
