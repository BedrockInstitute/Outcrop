"""Configured inline-math review inventory; decisions remain human-owned."""
from dataclasses import asdict
from collections import Counter
import json
from outcrop.core.math_lint import approval_records, inline_math, paragraph_context, temporary_records
from outcrop.site.site_inputs import source_paths
from outcrop.site.reading_routes import load_catalog


def load_math_review(config):
    path = config.values.get('inline_math_approvals')
    data = json.loads(config.path(path).read_text(encoding='utf-8')) if path else {'version': 1, 'approved': []}
    approvals, chapters = approval_records(data), temporary_records(data)
    if not chapters:
        return approvals, {}
    _, catalog = load_catalog(config.path(config.catalog))
    root = config.path(config.sources)
    modules = {path.relative_to(root).as_posix(): module
               for module, path in source_paths(root, config.source_extension).items()}
    temporary = {}
    for chapter in chapters:
        module = modules.get(chapter)
        if module not in catalog:
            raise ValueError(f'inline_math_approvals: temporary chapter missing from sources or catalog: {chapter}')
        temporary[chapter] = catalog[module]['human_reviewed'] is False
    return approvals, temporary


def math_inventory(config):
    root = config.path(config.sources)
    approvals, temporary = load_math_review(config)
    rows = []
    for _, path in sorted(source_paths(root, config.source_extension).items()):
        chapter = path.relative_to(root).as_posix()
        remaining = set(approvals.get(chapter, ()))
        text = path.read_text(encoding='utf-8')
        deferred = temporary.get(chapter) is True
        expired = chapter in temporary and not deferred
        lines = text.splitlines(keepends=True)
        for item in inline_math(text):
            paragraph_line, paragraph = paragraph_context(
                lines, item.line, item.line + item.context.count('\n'))
            approved = item.fingerprint in remaining
            remaining.discard(item.fingerprint)
            rows.append(dict(asdict(item), chapter=chapter,
                             source=path.relative_to(config.root).as_posix(),
                             paragraph_line=paragraph_line, paragraph=paragraph,
                             approved=approved, temporarily_allowed=deferred,
                             temporary_expired=expired))
    return rows


def inventory_markdown(rows):
    """Portable working report; contains exact review keys, never approvals."""
    groups = {}
    for row in rows:
        key = (row['source'], row['language'], row['paragraph_line'])
        groups.setdefault(key, []).append(row)
    output = ['# Inline LaTeX review inventory', '',
              f'{len(groups)} paragraphs containing {len(rows)} inline LaTeX occurrences outside figures and standalone display math.',
              'One review item covers one source paragraph, including all its formulas. Language variants and separate list items remain separate.',
              'This is an inventory, not an approval. IDs are report-local paragraph IDs and replace the previous formula-level IDs; approval keys still bind exact source occurrences.',
              'Figure-reference paragraphs are mechanically allowed by the localized fixed wording; this is separate from human approval and never extends to neighboring paragraphs.',
              'Temporary chapter allowances are separate from permanent approvals: edits remain allowed while human_reviewed is false; setting it to true ends the allowance.',
              'Re-run the inventory after editing prose. Only an explicit human decision may update the approval registry.', '']
    output.extend(['| Source | Paragraphs |', '| --- | ---: |'])
    output.extend(f'| `{source}` | {count} |' for source, count in sorted(Counter(key[0] for key in groups).items()))
    output.append('')
    for number, ((source, language, line), items) in enumerate(groups.items(), 1):
        if all(item['approved'] for item in items):
            status = 'Approved'
        elif all(item['figure_reference'] or item['approved'] for item in items):
            status = 'Allowed by figure-reference convention'
        elif all(item['temporarily_allowed'] for item in items):
            status = 'Temporarily allowed until this chapter is human-reviewed'
        elif any(item['temporary_expired'] for item in items):
            status = 'Temporary allowance expired; pending human review'
        else:
            status = 'Pending human review'
        output.extend([f'## M{number:03d}: {source}:{line} ({language})', '',
                       f'{status}. {len(items)} inline LaTeX occurrence(s).', '',
                       'Context:', '', '```text', items[0]['paragraph'], '```', '',
                       'Formulas, in source order:', '', '```latex',
                       '\n'.join(item['expression'] for item in items), '```', '',
                       'Exact approval keys, in the same order:', ''])
        output.extend(f"- `{item['fingerprint']}` ({'approved' if item['approved'] else 'figure-reference convention' if item['figure_reference'] else 'temporarily allowed' if item['temporarily_allowed'] else 'pending'})" for item in items)
        output.append('')
    return '\n'.join(output)
