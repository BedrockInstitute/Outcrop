"""Place compiler-certified declaration ends without interpreting Markdown prose."""
from html import escape, unescape
from html.parser import HTMLParser
import json
import re


def definition_lines(block, definitions):
    """Map Unicode source endpoints through Agda's highlighted token anchors.

    Newline counts are local to this code surface, not the source file; signatures
    and bodies may live in different fences. Missing evidence creates no mark.
    """
    wanted = {int(item['end']) - 1: item.get('name', '') for item in definitions}
    found = {}

    class Positions(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.position = None
            self.line = 0

        def handle_starttag(self, tag, attrs):
            identifier = dict(attrs).get('id', '')
            if tag == 'a' and identifier.isdecimal():
                self.position = int(identifier)

        def handle_data(self, text):
            if self.position is not None:
                for end, name in wanted.items():
                    if self.position <= end < self.position + len(text):
                        found[self.line + text[:end - self.position].count('\n')] = name
                self.position += len(text)
            self.line += text.count('\n')

    Positions().feed(block)
    return sorted(found.items())


def annotate_definition_endings(block, definitions):
    lines = definition_lines(block, definitions)
    if not lines:
        return block
    # Metadata only: decoration is outside the source scroll content. It never
    # changes compiler offsets, source copying, AST children or anchor identity.
    encoded = json.dumps(lines, ensure_ascii=False, separators=(',', ':'))
    return block.replace('<pre class="Agda">', '<pre class="Agda" data-definition-ends="'
                         + escape(encoded, quote=True) + '">', 1)


def render_definition_endings(body, language):
    labels = {'en': 'End of definition', 'zh': '定义结束', 'ja': '定義の終わり'}
    def render(match):
        opening, metadata, content = match.groups()
        marks = []
        for line, name in json.loads(unescape(metadata)):
            label = labels.get(language, labels['en']) + (': ' + name if name else '')
            marks.append('<span class="agda-definition-end" style="--definition-line:' + str(line)
                         + '" role="img" aria-label="' + escape(label, quote=True) + '"></span>')
        return opening + content + ''.join(marks) + '</pre>'
    return re.sub(r'(<pre class="Agda" data-definition-ends="([^"]*)">)(.*?)</pre>',
                  render, body, flags=re.S)


def render_code_frames(body, definitions, language):
    """One finishing path for literate chapters and standalone Agda pages."""
    from outcrop.core.html_contract import PRE_RE
    from outcrop.core.markdown_core import render_code_scroll_content
    body = render_code_scroll_content(body)
    body = PRE_RE.sub(lambda match: annotate_definition_endings(match[0], definitions), body)
    return render_definition_endings(body, language)
