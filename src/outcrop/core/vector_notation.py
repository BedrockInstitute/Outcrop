"""Source shape/evidence for closed vector notation; no Site policy or styling.

The browser must still validate the resolved type and constructor identities.
Syntax alone is deliberately not a certificate that a term is a vector.
"""
import html
import json
import unicodedata


def cons_root(source):
    """Recognize only a top-level infix cons, not f (a ∷ []) or quoted text."""
    depth = 0
    quoted = escaped = False
    for index, character in enumerate(source):
        if quoted:
            if escaped:
                escaped = False
            elif character == '\\':
                escaped = True
            elif character == '"':
                quoted = False
            continue
        if character == '"':
            quoted = True
        elif character in '({[':
            depth += 1
        elif character in ')}]':
            depth -= 1
        elif (character == '∷' and depth == 0 and index > 0
              and source[index - 1].isspace()
              and (index + 1 == len(source) or source[index + 1].isspace())):
            return True
        if depth < 0:
            return False
    return False


def vector_items(source):
    """Only short, single-line chains of atomic entries; never evaluate a term."""
    if '\n' in source or '\r' in source:
        return None
    parts = [part.strip() for part in source.strip().split('∷')]
    if len(parts) < 2 or parts[-1] != '[]':
        return None
    items = parts[:-1]
    # Compound entries retain their grouping and ordinary AST rendering.
    def atom(item):
        if item.isascii() and item.isdigit():
            return True
        return bool(item and item[0].isalpha() and all(
            char.isalnum() or unicodedata.category(char).startswith('M')
            or char in "_′″‴⁗'’" for char in item[1:]))
    if not all(atom(item) for item in items):
        return None
    if len(', '.join(items)) > 48:
        return None
    return items


def vector_attributes(node):
    """Publish application type, not a guessed Vec judgement, on all cons roots.

    Even an ineligible outer cons is marked: its inner suffix must not acquire
    a partial bracket display. Pattern roots likewise suppress all descendants.
    """
    if node.get('kind') != 'application' or not cons_root(node.get('source', '')):
        return ''
    attributes = ' data-vector-candidate="true"'
    if node.get('context') == 'pattern':
        return attributes
    items = vector_items(node['source'])
    if items and node.get('type'):
        if node.get('id') is not None:
            attributes += ' data-vector-checked="true"'
        attributes += (' data-vector-items="' + html.escape(json.dumps(items, ensure_ascii=False), quote=True)
                       + '" data-vector-type="' + html.escape(node['type'], quote=True) + '"')
    return attributes
