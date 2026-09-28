"""Rebase compiler-highlighted Agda onto prose or fence-only source edits.

The compiler's decimal anchors and trace ranges are one-based Unicode source
offsets. A code-preserving edit may move those offsets even when no Agda needs
to be checked again. This module only relocates certified evidence; it never
guesses a new AST node or a type.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import html
import json
from pathlib import PurePosixPath
import re


PRE = re.compile(r'<pre class="Agda">(.*?)</pre>', re.S)
TAG = re.compile(r'<[^>]*>')
NUMERIC_ID = re.compile(r'\bid="(\d+)"')
HREF = re.compile(r'href="([^"#]+)\.html#(\d+)"')
MARKUP_TOKEN = re.compile(r'<[^>]*>|&(?:#[0-9]+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);|.', re.S)


@dataclass(frozen=True)
class CodeRelocation:
    """Map source positions through an unchanged concatenated Agda code stream."""

    old_spans: tuple[tuple[int, int], ...]
    new_spans: tuple[tuple[int, int], ...]

    def __post_init__(self):
        old = sum(end - start for start, end in self.old_spans)
        new = sum(end - start for start, end in self.new_spans)
        if old != new or any(start >= end for spans in (self.old_spans, self.new_spans)
                             for start, end in spans):
            raise ValueError('incompatible Agda code spans')

    @staticmethod
    def _index(spans: tuple[tuple[int, int], ...], position: int) -> int:
        prefix = 0
        for start, end in spans:
            if start <= position < end:
                return prefix + position - start
            prefix += end - start
        raise ValueError(f'position {position} is outside Agda code')

    @staticmethod
    def _position(spans: tuple[tuple[int, int], ...], index: int) -> int:
        for start, end in spans:
            length = end - start
            if index < length:
                return start + index
            index -= length
        raise ValueError('Agda code index exceeds source spans')

    def point(self, position: int) -> int:
        return self._position(self.new_spans, self._index(self.old_spans, position))

    def end(self, position: int) -> int:
        """Map a half-open end using its last actual code character."""
        return self.point(position - 1) + 1


def plain_code(fragment: str) -> str:
    return html.unescape(TAG.sub('', fragment))


def split_highlighted(fragment: str, blocks: list[str]) -> list[str]:
    """Split only between complete HTML tags, at certified code boundaries."""
    lengths = [len(block) for block in blocks]
    if not lengths or any(length == 0 for length in lengths):
        raise ValueError('empty Agda fence cannot be safely repartitioned')
    boundaries = []
    cumulative = 0
    for length in lengths[:-1]:
        cumulative += length
        boundaries.append(cumulative)
    parts = ['']
    visible = depth = boundary = 0

    def advance():
        nonlocal boundary
        if boundary < len(boundaries) and visible == boundaries[boundary] and depth == 0:
            parts.append('')
            boundary += 1

    for token in MARKUP_TOKEN.findall(fragment):
        if token.startswith('<') and token.endswith('>'):
            if token.startswith('</'):
                parts[-1] += token
                depth -= 1
                if depth < 0:
                    raise ValueError('unbalanced Agda highlight markup')
                advance()
            else:
                advance()
                parts[-1] += token
                if not token.endswith('/>') and not token.startswith('<!'):
                    depth += 1
            continue
        advance()
        width = len(html.unescape(token))
        if boundary < len(boundaries) and visible < boundaries[boundary] < visible + width:
            raise ValueError('Agda fence boundary bisects an HTML entity')
        parts[-1] += token
        visible += width
        advance()
    if depth or len(parts) != len(blocks) or [plain_code(part) for part in parts] != blocks:
        raise ValueError('Agda highlight markup cannot be safely repartitioned')
    return ['<pre class="Agda">' + part + '</pre>' for part in parts]


def rebase_pres(highlighted: str, old_spans: tuple[tuple[int, int], ...],
                old_hashes: list[str], blocks: list[str],
                relocation: CodeRelocation) -> list[str]:
    """Verify old compiler code, then return newly partitioned and rebased PREs."""
    pres = list(PRE.finditer(highlighted))
    old = [plain_code(pre.group(1)) for pre in pres]
    if (len(old) != len(old_spans) or len(old) != len(old_hashes)
            or any(len(code) != end - start or hashlib.sha256(code.encode()).hexdigest() != digest
                   for code, (start, end), digest in zip(old, old_spans, old_hashes))
            or ''.join(old) != ''.join(blocks)):
        raise ValueError('highlighted Agda code does not match certified source')
    parts = split_highlighted(''.join(pre.group(1) for pre in pres), blocks)
    return [NUMERIC_ID.sub(lambda match: f'id="{relocation.point(int(match[1]))}"', part)
            for part in parts]


def rebase_hrefs(document: str, relocations: dict[str, CodeRelocation]) -> str:
    """Retarget inbound compiler links while leaving external URLs untouched."""
    def replace(match: re.Match) -> str:
        path = match[1]
        if '://' in path or path.startswith('//'):
            return match[0]
        module = PurePosixPath(path).name
        relocation = relocations.get(module)
        if relocation is None:
            return match[0]
        return f'href="{path}.html#{relocation.point(int(match[2]))}"'
    return HREF.sub(replace, document)


def rebase_trace(trace: str, paths: dict[str, tuple[CodeRelocation, str, str]]) -> str:
    """Move only records certified against the old source hash.

    Unrelated and older trace runs stay byte-for-byte intact. The extractor's
    ordinary source-hash and code-range validation remains the final gate.
    """
    lines = []
    for line in trace.splitlines(keepends=True):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            lines.append(line)
            continue
        entry = paths.get(record.get('path'))
        if entry is None or record.get('sourceHash') != entry[1]:
            lines.append(line)
            continue
        relocation, _, new_hash = entry
        record['start'] = relocation.point(record['start'])
        record['end'] = relocation.end(record['end'])
        record['sourceHash'] = new_hash
        lines.append(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
    return ''.join(lines)
