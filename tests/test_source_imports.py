"""All import consumers retain complete Agda module-name tokens."""
from pathlib import Path
import tempfile
import unittest

from outcrop.core.source_syntax import imports
from outcrop.core.reading_order import reading_order_errors
from outcrop.adapters.agda.parallel import local_graph, external_dependencies


class SourceImportTests(unittest.TestCase):
    def test_hyphens_ascii_and_unicode_primes_are_not_prefixes(self):
        text = "```agda\nimport A-B\nopen import Theory'.Lemma′ using ( result )\nimport Δ.Cat₀\n```\n"
        self.assertEqual(imports(text), ['A-B', "Theory'.Lemma′", 'Δ.Cat₀'])

    def test_module_token_stops_at_agda_delimiters(self):
        for delimiter in (' ', '\t', '\n', '(', ')', '{', '}', ';'):
            with self.subTest(delimiter=delimiter):
                self.assertEqual(imports('```agda\nimport A-B' + delimiter + 'argument\n```\n'), ['A-B'])

    def test_prose_other_fences_and_import_prefixes_do_not_count(self):
        text = ('import Prose\n```text\nimport Example\n```\n'
                '```agda\nimportant = value\nopen import A-B\n```\n')
        self.assertEqual(imports(text), ['A-B'])

    def test_scheduler_and_order_gate_use_the_same_complete_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'A-B.agda').write_text('module A-B where\n')
            (root / "Prime'.lagda.md").write_text("```agda\nmodule Prime' where\nimport A-B\n```\n")
            (root / 'Start.agda').write_text("module Start where\nimport Prime'\nimport External.Lib′\n")
            paths, graph = local_graph(root)
            self.assertEqual(graph, {'A-B': set(), "Prime'": {'A-B'}, 'Start': {"Prime'"}})
            self.assertEqual(external_dependencies(paths, set(paths)), {'External.Lib′'})
        sources = {'A-B': '```agda\nmodule A-B where\n```\n',
                   'Start': '```agda\nimport A-B\n```\n'}
        catalog = {'chapters': [{'id': 'Start'}, {'id': 'A-B'}]}
        self.assertEqual(reading_order_errors(sources, catalog), ['Start precedes prerequisite A-B'])


if __name__ == '__main__':
    unittest.main()
