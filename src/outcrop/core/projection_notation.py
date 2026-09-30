"""Conservative presentation policy for compiler-certified record projections.

Certification and typography are separate: a field aspect, a record-looking
variable or balanced parentheses can never supply missing semantic evidence.
"""
import html
import re
import unicodedata


def single_letter(value):
    return bool(value and unicodedata.category(value[0]).startswith('L')
                and all(unicodedata.category(char).startswith('M') for char in value[1:]))


def pair_projection_attribute(module, name):
    """Only the compiler-resolved builtin Sigma fields authorize this lens."""
    field = name.rsplit('.', 1)[-1]
    if module == 'Agda.Builtin.Sigma' and field in {'fst', 'snd'}:
        return ' data-pair-projection="' + ('1' if field == 'fst' else '2') + '"'
    return ''


def projection_notation(node):
    evidence = node.get('projection')
    if node.get('kind') != 'application' or node.get('context') == 'pattern' or not evidence:
        return None
    record = evidence.get('record', '')
    # These projections already have established ordinary mathematical syntax.
    if record in {'Agda.Builtin.Sigma.Σ', 'Agda.Primitive.Lift',
                  'Cubical.Foundations.Prelude.Lift', 'Cubical.Core.Primitives.Lift'}:
        return None
    head, argument = evidence.get('head', ''), evidence.get('argument', '')
    # Long/qualified names, operators, multiline arguments, binders, records,
    # nested groups and nested scripts are less readable as subscripts.
    if not single_letter(head):
        return None
    if head in {'fst', 'snd', 'lower'} or not record or not evidence.get('name'):
        return None
    if '\n' in argument or '\r' in argument:
        return None
    argument = argument.strip()
    if not argument or len(argument) > 12 or len(argument.split()) > 3:
        return None
    if re.search(r'[(){}\[\],;:=→λ∀∃\n₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]', argument):
        return None
    # Underscores signify holes/mixfix notation, not a legible instance label.
    if '_' in argument or not re.search(r'\w', argument):
        return None
    return head, argument


def projection_attributes(node):
    notation = projection_notation(node)
    if not notation:
        return ''
    head, argument = notation
    return (' data-projection-head="' + html.escape(head, quote=True)
            + '" data-projection-argument="' + html.escape(argument, quote=True) + '"')


def checked_projection(record, source, end):
    """Validate all independent trace intervals before publishing metadata."""
    start = record['start']
    head_end, arg_start, arg_end = (record.get(key) for key in
                                   ('headEnd', 'argumentStart', 'argumentEnd'))
    if not all(isinstance(value, int) for value in (head_end, arg_start, arg_end)):
        return None
    if not (1 <= start < head_end <= arg_start < arg_end <= end <= len(source) + 1):
        return None
    head = source[start - 1:head_end - 1]
    argument = source[arg_start - 1:arg_end - 1]
    # Abstract ranges may omit the argument's enclosing parentheses. Retain its
    # certified interior; punctuation outside it must be only grouping/space.
    if source[head_end - 1:arg_start - 1].strip(' \t\r\n('):
        return None
    if source[arg_end - 1:end - 1].strip(' \t\r\n)'):
        return None
    while argument.startswith('(') and argument.endswith(')'):
        depth = 0
        for index, char in enumerate(argument):
            depth += (char == '(') - (char == ')')
            if depth == 0 and index != len(argument) - 1:
                break
        else:
            argument = argument[1:-1].strip()
            continue
        break
    return {'name': record.get('projection'), 'record': record.get('record'),
            'head': head, 'argument': argument}
