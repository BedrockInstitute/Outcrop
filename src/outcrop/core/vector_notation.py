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
        elif (character in '=:→' and depth == 0 and index > 0
              and source[index - 1].isspace()
              and index + 1 < len(source) and source[index + 1].isspace()):
            return False
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


def inline_vector_candidates(source):
    """Lexical cons ranges, not inferred AST nodes or inferred types.

    Parenthesized components may occur inside a larger inline expression.
    Constructor identity is checked later, after ordinary reference resolution.
    """
    ranges = [(0, len(source))]
    stack = []
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
        elif character == '(':
            stack.append(index + 1)
        elif character == ')' and stack:
            ranges.append((stack.pop(), index))
    # Prose may present a term as an equation, a type judgement, or a lambda
    # body. These lexical syntax boundaries are not part of a cons operand.
    # Do not split on arbitrary user-defined infix operators.
    components = []
    for start, end in ranges:
        left = start
        depth = 0
        quoted = escaped = False
        for index in range(start, end):
            character = source[index]
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
            elif (depth == 0 and character in '=:→' and index > start
                  and source[index - 1].isspace()
                  and index + 1 < end and source[index + 1].isspace()):
                components.append((left, index))
                left = index + 1
        components.append((left, end))
    candidates = []
    for start, end in components:
        # Whitespace belongs to the surrounding prose expression, not the badge.
        start += len(source[start:end]) - len(source[start:end].lstrip())
        end = start + len(source[start:end].rstrip())
        if cons_root(source[start:end]):
            candidates.append(dict(start=start, end=end, source=source[start:end],
                                   kind='application', vector_inline=True))
    return candidates


def vector_attributes(node):
    """Publish application type, not a guessed Vec judgement, on all cons roots.

    Even an ineligible outer cons is marked: its inner suffix must not acquire
    a partial bracket display. Pattern roots likewise suppress all descendants.
    """
    if node.get('kind') != 'application' or not cons_root(node.get('source', '')):
        return ''
    attributes = ' data-vector-candidate="true"'
    if node.get('vector_inline'):
        attributes += ' data-vector-inline="true"'
    if node.get('context') == 'pattern':
        return attributes
    items = vector_items(node['source'])
    if items and (node.get('type') or node.get('vector_inline')):
        if node.get('id') is not None:
            attributes += ' data-vector-checked="true"'
        attributes += (' data-vector-items="' + html.escape(json.dumps(items, ensure_ascii=False), quote=True)
                       + '"')
        if node.get('type'):
            attributes += ' data-vector-type="' + html.escape(node['type'], quote=True) + '"'
    return attributes
