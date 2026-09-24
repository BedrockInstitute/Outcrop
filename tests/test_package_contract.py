"""The installed API, dependency direction and evidence-preserving boundaries."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from outcrop.core import CodeContext, MarkdownDocument
from outcrop.core.reading_order import prerequisite_order_errors
from outcrop.site.site_inputs import source_paths


class PackageContractTests(unittest.TestCase):
    def test_subcommand_help_is_owned_by_the_subcommand(self):
        for command, option in [('build', '--out'), ('lint', '--literary'),
                                ('extract-types', '--entry'), ('extract-expressions', '--trace'),
                                ('check-links', 'published site directory')]:
            with self.subTest(command=command):
                result = subprocess.run([sys.executable, '-m', 'outcrop', command, '--help'],
                                        capture_output=True, text=True, check=True)
                self.assertIn(option, result.stdout)

    def test_core_import_does_not_initialize_the_website(self):
        script = 'import sys; from outcrop.core import MarkdownDocument; print(any(n.startswith("outcrop.site") for n in sys.modules))'
        result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), 'False')

    def test_explicit_alias_keeps_compiler_target_and_aspect(self):
        code = CodeContext(names={'Model': {'structure': '17'}}, rendered={'Model'},
                           canonical_names={'Model': {'17': 'structure'}},
                           aspects={'Model': {'17': 'Function'}})
        result = MarkdownDocument('[V](Model.html#structure){.Agda}', code=code).render('en')
        self.assertIn('class="inline-ref Function"', result.body)
        self.assertIn('href="Model.html#17"', result.body)
        self.assertIn('data-name="structure"', result.body)
        self.assertIn('>V</a>', result.body)

    def test_source_inventory_uses_exact_configured_suffix(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'A.md').write_text('# A')
            (root / 'B.lagda.md').write_text('# B')
            (root / 'C.txt').write_text('# C')
            self.assertEqual(set(source_paths(root, '.md')), {'A', 'B.lagda'})
            self.assertEqual(set(source_paths(root, '.lagda.md')), {'B'})

    def test_preview_policy_is_explicit_and_order_is_shared(self):
        graph = {'Origin': ['A'], 'A': []}
        self.assertTrue(prerequisite_order_errors(['Origin', 'A'], graph))
        self.assertEqual(prerequisite_order_errors(['Origin', 'A'], graph, previews={'Origin'}), [])


if __name__ == '__main__':
    unittest.main()
