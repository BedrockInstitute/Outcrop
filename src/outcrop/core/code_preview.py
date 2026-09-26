"""Optional source-preserving previews of long Agda fences."""
from html import escape
import re


_PREVIEW_RE = re.compile(
    r'<!--\s*outcrop:agda-preview-lines=([1-9][0-9]*)\s*-->\s*'
    r'(<pre class="Agda"[^>]*>.*?</pre>)', re.DOTALL,
)


def render_code_previews(body):
    """Wrap a marked code surface without splitting or cloning its Agda DOM."""
    def wrap(match):
        count, block = match.groups()
        return ('<div class="agda-code-preview" data-preview-lines="' +
                escape(count, quote=True) + '">'
                '<div class="agda-code-preview-clip">' + block + '</div>'
                '<button class="agda-code-preview-toggle" type="button" hidden '
                'aria-expanded="true"></button></div>')
    return _PREVIEW_RE.sub(wrap, body)


def preview_directive_issues(text):
    """Return source-line diagnostics for malformed or orphaned preview markers."""
    lines = text.splitlines()
    issues = []
    fence = None
    for index, line in enumerate(lines):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        if not line.lstrip().startswith('<!--') or 'outcrop:agda-preview-lines' not in line:
            continue
        if not re.fullmatch(r'\s*<!--\s*outcrop:agda-preview-lines=[1-9][0-9]*\s*-->\s*', line):
            issues.append((index + 1, 'invalid Agda preview directive; use a positive line count'))
            continue
        following = index + 1
        while following < len(lines) and not lines[following].strip():
            following += 1
        if following >= len(lines) or not re.fullmatch(r'```agda[ \t]*', lines[following]):
            issues.append((index + 1, 'Agda preview directive must immediately precede an Agda fence'))
    return issues
