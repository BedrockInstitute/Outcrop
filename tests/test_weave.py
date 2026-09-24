"""Batch weaving and CLI contracts without any consuming-project files."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from outcrop.adapters.weave import generate, main

TEXT = '<!--en-->\nWords.\n<!--zh-->\n文字。\n<!--/-->\n\n```agda\nf = value\n```\n'


class WeaveTests(unittest.TestCase):
    def test_plain_markdown_nested_paths_and_language_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'lessons'
            (root / 'unit').mkdir(parents=True)
            (root / 'unit/A.md').write_text(TEXT)
            output = Path(directory) / 'editions'
            self.assertEqual(main(['--gen', '--root', str(root), '--out', str(output)]), 0)
            self.assertEqual((output / 'en/unit/A.md').read_text(), 'Words.\n\n```agda\nf = value\n```\n')
            self.assertIn('文字。', (output / 'zh/unit/A.md').read_text())
            self.assertEqual((output / 'ja/unit/A.md').read_text(), (output / 'en/unit/A.md').read_text())
            self.assertEqual(list(output.rglob('*.agda-lib')), [])

    def test_explicit_library_is_copied_without_invented_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'A.md'; source.write_text(TEXT)
            library = root / 'unrelated.agda-lib'
            library.write_text('name: unrelated\ninclude: .\ndepend: independent-library\n')
            output = root / 'output'
            self.assertEqual(main(['--gen', '--langs', 'ja', '--library', str(library),
                                   '--out', str(output), str(source)]), 0)
            self.assertEqual((output / 'ja/unrelated.agda-lib').read_bytes(), library.read_bytes())
            self.assertEqual(sorted(path.name for path in output.iterdir()), ['ja'])

    def test_single_language_stdout_and_bad_marker_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'A.md'; source.write_text(TEXT)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['--lang', 'zh', str(source)]), 0)
            self.assertIn('文字。', output.getvalue())
            self.assertIn('f = value', output.getvalue())
            source.write_text('<!--en-->\nMissing end.\n')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['--check', str(source)]), 1)

    def test_invalid_batch_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good, bad = root / 'Good.md', root / 'Bad.md'
            good.write_text(TEXT); bad.write_text('<!--/-->')
            with self.assertRaises(ValueError):
                generate([good, bad], root / 'output', ['en'])
            self.assertFalse((root / 'output').exists())

    def test_no_implicit_root_or_project(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-m', 'outcrop.adapters.weave', '--check'],
                                    cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('explicit --root', result.stderr)


if __name__ == '__main__':
    unittest.main()
