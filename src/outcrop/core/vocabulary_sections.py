"""Attach introductory sections to compiler-certified vocabulary targets.

Keep declaration identity for types and navigation history; the reading view
starts at the section that introduces an imported name or a local notation.
Section positions belong to the rendered edition, not the cached code index.
"""
import html
import re


def mark_vocabulary_sections(body, module, semantics, vocabulary):
    if not semantics.prelude_module or module != semantics.prelude_module:
        return body
    positions = {entry[1] for entry in vocabulary.get('by_href', {}).values()
                 if entry[0] == module}
    for name, _parts in vocabulary.get('syntax', ()):
        target = vocabulary.get('inline', {}).get(name)
        if target and target[0].startswith(module + '.html#'):
            positions.add(target[0].rsplit('#', 1)[1])
    section = None

    def annotate(match):
        nonlocal section
        tag = match[0]
        if tag.startswith('<h'):
            identifier = re.search(r'\bid="([^"]+)"', tag)
            if identifier:
                section = identifier[1]
            return tag
        if not section:
            return tag
        # Import blocks also contain renamed aliases and module imports that
        # need not appear in the public-using index. Preserve their section hop.
        imported = bool(re.search(r'<a\b[^>]*class="Keyword">import</a>', tag))

        def anchor(match):
            identifier = re.search(r'\bid="([^"]+)"', match[0])
            if identifier and (imported or html.unescape(identifier[1]) in positions):
                return match[0][:-1] + f' data-introduction-section="{section}">'
            return match[0]

        return re.sub(r'<a\b[^>]*>', anchor, tag)

    return re.sub(r'<h[2-6]\b[^>]*>|<pre class="Agda">.*?</pre>', annotate, body, flags=re.S)
