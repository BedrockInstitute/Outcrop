"""Expression extraction accepts the same local source formats as agda-check."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from outcrop.adapters import extract_expression_types as extractor


class ExpressionSourceTests(unittest.TestCase):
    def test_definition_end_requires_signature_and_allows_separate_fences(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src, highlighted = root / 'src', root / 'html'
            src.mkdir(); highlighted.mkdir()
            source = '```agda\nf : Set\n```\nProse.\n```agda\nf = Set\n```\n'
            path = src / 'A.lagda.md'
            path.write_text(source)
            start, end = source.index('f :') + 1, source.index('f = Set') + len('f = Set') + 1
            (highlighted / 'A.md').write_text(f'<a id="{start}" href="A.html#{start}" class="Function">f</a>')
            records = [dict(version=1, run='one', path=str(path), sourceHash=extractor.source_hash(path),
                            start=start, end=stop, kind=kind, type='')
                       for kind, stop in [('signature', start + 7), ('definition-end', end)]]
            trace = root / 'trace.jsonl'
            trace.write_text(''.join(json.dumps(record) + '\n' for record in records))
            data, compact = extractor.normalize(src, highlighted, trace)
            self.assertEqual([(n['start'], n['end'], n['kind'], n['name']) for n in data['A']],
                             [(start, end, 'definition-end', 'f')])
            self.assertEqual(len(compact), 2)
            for invalid in (dict(records[1], sourceHash='stale'),
                            dict(records[1], end=source.index('Prose.') + 2)):
                trace.write_text(json.dumps(records[0]) + '\n' + json.dumps(invalid) + '\n')
                self.assertEqual(extractor.normalize(src, highlighted, trace)[0]['A'], [])
            trace.write_text(json.dumps(records[1]) + '\n')
            self.assertEqual(extractor.normalize(src, highlighted, trace)[0]['A'], [])

    def test_plain_and_mixed_sources_keep_unicode_nodes_and_compacted_trace(self):
        for mixed in (False, True):
            with self.subTest(mixed=mixed), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                src, html_dir = root / 'sources', root / 'html'
                (src / 'Theory').mkdir(parents=True)
                html_dir.mkdir()
                records = []
                expected = {}
                files = [('Theory.Plain′', '.agda')]
                if mixed:
                    files.append(('Literate', '.lagda.md'))
                for module, suffix in files:
                    code = f'module {module} where\nf 𝒜 = g 𝒜\n'
                    source = ('Prose 𝒜 outside code.\n```agda\n' + code + '```\n'
                              if suffix == '.lagda.md' else code)
                    path = src / (module.replace('.', '/') + suffix)
                    path.write_text(source, encoding='utf-8')
                    binder = source.index('𝒜 =') + 1
                    use = source.rindex('𝒜') + 1
                    application = source.index('g 𝒜') + 1
                    expected[module] = (binder, use, application)
                    (html_dir / (module + ('.md' if suffix == '.lagda.md' else '.html'))).write_text(
                        f'<a id="{binder}" class="Bound">𝒜</a>'
                        f'<a id="{use}" href="{module}.html#{binder}" class="Bound">𝒜</a>',
                        encoding='utf-8',
                    )
                    for kind, start, length in [('binding', binder, 1),
                                                ('application', application, 3)]:
                        records.append({
                            'version': 1, 'run': 'one', 'kind': kind,
                            'path': str(path.resolve()), 'sourceHash': extractor.source_hash(path),
                            'start': start, 'end': start + length, 'type': 'Set',
                        })
                trace, output = root / 'trace.jsonl', root / 'expressions.json'
                trace.write_text(''.join(json.dumps(record) + '\n' for record in records),
                                 encoding='utf-8')
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(extractor.main([
                        '--src', str(src), '--html-dir', str(html_dir),
                        '--trace', str(trace), '--out', str(output),
                    ]), 0)
                data = json.loads(output.read_text(encoding='utf-8'))
                self.assertEqual(set(data), set(expected))
                for module, (binder, use, application) in expected.items():
                    nodes = {node['kind']: node for node in data[module]}
                    self.assertEqual(set(nodes), {'binding', 'variable', 'application'})
                    for kind, start, fragment in [('binding', binder, '𝒜'),
                                                  ('variable', use, '𝒜'),
                                                  ('application', application, 'g 𝒜')]:
                        self.assertEqual(nodes[kind]['start'], start)
                        self.assertEqual(nodes[kind]['end'], start + len(fragment))
                        self.assertEqual(nodes[kind]['source'], fragment)
                    self.assertEqual(nodes['variable']['targetModule'], module)
                    self.assertEqual(nodes['variable']['target'], binder)
                compacted = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]
                self.assertCountEqual(compacted, records)

    def test_duplicate_module_rejected_before_output_or_trace_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Same.agda').write_text('module Same where\n', encoding='utf-8')
            (root / 'Same.lagda.md').write_text('```agda\nmodule Same where\n```\n', encoding='utf-8')
            trace, output = root / 'trace.jsonl', root / 'expressions.json'
            trace.write_text('original trace\n', encoding='utf-8')
            output.write_text('original output\n', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, r'duplicate module Same:.*Same\.agda.*Same\.lagda\.md'):
                extractor.main(['--src', str(root), '--html-dir', str(root),
                                '--trace', str(trace), '--out', str(output)])
            self.assertEqual(trace.read_text(encoding='utf-8'), 'original trace\n')
            self.assertEqual(output.read_text(encoding='utf-8'), 'original output\n')

    def test_source_intervals_distinguish_plain_code_from_markdown_prose(self):
        source = '𝒜 prose\n```agda\nf 𝒜\n```\n'
        start = source.index('f 𝒜') + 1
        self.assertEqual(extractor.code_intervals(source), [(start, start + len('f 𝒜\n'))])
        self.assertEqual(extractor.code_intervals(source, literate=False), [(1, len(source) + 1)])
        self.assertFalse(extractor.inside_code(1, 2, extractor.code_intervals(source)))


if __name__ == '__main__':
    unittest.main()
