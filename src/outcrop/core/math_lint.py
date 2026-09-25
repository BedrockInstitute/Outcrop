"""Locate inline LaTeX for explicit editorial review, without rendering it."""
from bisect import bisect_right
from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
import json
import re


@dataclass(frozen=True)
class InlineMath:
    index: int
    end: int
    line: int
    language: str
    expression: str
    context: str
    fingerprint: str
    figure_reference: bool = False


FIGURE_REFERENCES = {
    'en': re.compile(r'\bin\s+the\s+figure\b', re.I),
    'zh': re.compile('图中的'),
    'ja': re.compile('図中の'),
}


def paragraph_context(lines, first, last):
    """One prose paragraph, retaining soft wraps but separating list items."""
    def separator(line):
        return not line.strip() or re.match(r'\s*(?:<!--|</?(?:div|p|figure|details|summary|pre)\b|`{3,}|~{3,}|\$\$|#{1,6}\s)', line)
    def starts_block(line):
        return separator(line) or re.match(r'\s*(?:[-+*]\s|\d+[.)]\s|\|)', line)
    start, end = first - 1, last
    while start > 0 and not starts_block(lines[start]) and not separator(lines[start - 1]):
        start -= 1
    while end < len(lines) and not starts_block(lines[end]):
        end += 1
    return start + 1, ''.join(lines[start:end]).rstrip('\n')


def inline_math(text):
    """Code/comments/figures are opaque; standalone display math is allowed.

    Fingerprints bind an occurrence to its language, exact source line and
    position within that line, not a moving document line number. Duplicating an
    approved occurrence does not grant a second approval.
    """
    masked = list(text)
    def mask(start, end):
        for index in range(start, end):
            if masked[index] != '\n':
                masked[index] = ' '
    fence, offset = None, 0
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if fence:
            mask(offset, offset + len(line))
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
        elif marker:
            fence = marker[1]
            mask(offset, offset + len(line))
        offset += len(line)
    for match in re.finditer(r'(`+)(?!`)(.*?)\1(?!`)', ''.join(masked), re.S):
        mask(*match.span())
    for pattern in (r'(?<=\])\([^\n)]*\)', r'[A-Za-z][A-Za-z0-9+.\-]*://[^\s)<>]+'):
        for match in re.finditer(pattern, ''.join(masked)):
            mask(*match.span())
    lines = text.splitlines(keepends=True)
    starts, languages, offset, language = [], [], 0, 'shared'
    for line in lines:
        marker = re.fullmatch(r'\s*<!--(en|zh|ja|/)-->\s*', line)
        if marker:
            language = 'shared' if marker[1] == '/' else marker[1]
        starts.append(offset)
        languages.append(language)
        offset += len(line)

    class Regions(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.opaque = []

        def position(self):
            line, column = self.getpos()
            return starts[line - 1] + column

        def handle_starttag(self, tag, attrs):
            start = self.position()
            if tag in {'figure', 'pre', 'code', 'script', 'style'}:
                self.opaque.append((tag, start))
            mask(start, start + len(self.get_starttag_text()))

        def handle_startendtag(self, tag, attrs):
            start = self.position()
            mask(start, start + len(self.get_starttag_text()))

        def handle_endtag(self, tag):
            start = self.position()
            end = text.find('>', start) + 1
            for index in range(len(self.opaque) - 1, -1, -1):
                if self.opaque[index][0] == tag:
                    mask(self.opaque[index][1], end)
                    del self.opaque[index:]
                    break
            mask(start, end)

        def handle_comment(self, data):
            start = self.position()
            mask(start, start + len(data) + 7)

    regions = Regions()
    regions.feed(''.join(masked))
    for _, start in regions.opaque:
        mask(start, len(text))
    visible = ''.join(masked)
    matches = list(re.finditer(r'(?<!\\)(\$\$|\$)(.+?)(?<!\\)\1', visible, re.S))
    # Opaque regions cannot supply or bridge a prose reference phrase. Math
    # itself cannot self-authorize via, for example, $\text{in the figure}$.
    references = [char if char == text[index] else '\0'
                  for index, char in enumerate(visible)]
    for match in matches:
        for index in range(*match.span()):
            if references[index] != '\n':
                references[index] = '\0'
    references = ''.join(references)
    out = []
    for match in matches:
        start, end = match.span()
        row = bisect_right(starts, start) - 1
        last_row = bisect_right(starts, end - 1) - 1
        before = visible[starts[row]:start]
        after = visible[end:starts[last_row] + len(lines[last_row])]
        if match[1] == '$$' and not before.strip() and not after.strip():
            continue
        context = ''.join(lines[row:last_row + 1]).rstrip('\n')
        expression = text[start:end]
        key = json.dumps([languages[row], context, start - starts[row], expression], ensure_ascii=False)
        paragraph_line, paragraph = paragraph_context(lines, row + 1, last_row + 1)
        paragraph_start = starts[paragraph_line - 1]
        reference_prose = references[paragraph_start:paragraph_start + len(paragraph)]
        patterns = ([FIGURE_REFERENCES[languages[row]]] if languages[row] in FIGURE_REFERENCES
                    else FIGURE_REFERENCES.values())
        figure_reference = any(pattern.search(reference_prose) for pattern in patterns)
        out.append(InlineMath(start, end, row + 1, languages[row], expression,
                              context, sha256(key.encode()).hexdigest(), figure_reference))
    return out


def approval_records(data):
    """Validate explicit human decisions; there is no legacy auto-allow list."""
    if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1 or not isinstance(data.get('approved'), list):
        raise ValueError('inline_math_approvals: expected version 1 and approved list')
    result = {}
    for record in data['approved']:
        if not isinstance(record, dict) or any(not isinstance(record.get(key), str) or not record[key].strip()
                                              for key in ('chapter', 'fingerprint', 'reviewer', 'reason')):
            raise ValueError('inline_math_approvals: each approval needs chapter, fingerprint, reviewer and reason')
        if not re.fullmatch(r'[0-9a-f]{64}', record['fingerprint']):
            raise ValueError('inline_math_approvals: invalid fingerprint')
        keys = result.setdefault(record['chapter'], set())
        if record['fingerprint'] in keys:
            raise ValueError('inline_math_approvals: duplicate approval')
        keys.add(record['fingerprint'])
    return result


def temporary_records(data):
    """Explicit deferrals until human review, not permanent formula approvals."""
    approval_records(data)  # Validate the shared registry version and shape.
    records = data.get('temporary', [])
    if not isinstance(records, list):
        raise ValueError('inline_math_approvals: temporary must be a list')
    result = set()
    for record in records:
        if not isinstance(record, dict) or any(not isinstance(record.get(key), str) or not record[key].strip()
                                              for key in ('chapter', 'reviewer', 'reason')):
            raise ValueError('inline_math_approvals: temporary record needs chapter, reviewer and reason')
        if record.get('until') != 'human_reviewed' or 'source_sha256' in record:
            raise ValueError('inline_math_approvals: temporary records require until=human_reviewed, not a source digest')
        if record['chapter'] in result:
            raise ValueError('inline_math_approvals: duplicate temporary chapter')
        result.add(record['chapter'])
    return result


def unapproved_math(text, approved=(), *, temporary_allowed=False):
    if temporary_allowed is True:
        return []
    remaining = set(approved)
    out = []
    for item in inline_math(text):
        if item.fingerprint in remaining:
            remaining.remove(item.fingerprint)
        elif not item.figure_reference:
            out.append(item)
    return out
