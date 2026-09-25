from pathlib import Path
import tempfile
import unittest

from outcrop.adapters.python_inputs import dependency_files


class PythonInputsTests(unittest.TestCase):
    def test_transitive_relative_package_and_deferred_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'sample'
            files = {
                '__init__.py': 'from . import common',
                'common.py': 'VALUE = 1',
                'site/__init__.py': '',
                'site/main.py': 'from .leaf import value\ndef run():\n    from .. import extra\n',
                'site/leaf.py': 'from ..common import VALUE\nvalue = VALUE',
                'extra.py': 'import json',
                'unused_lint.py': '',
            }
            for name, text in files.items():
                path = package / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            entry = root / 'build.py'
            entry.write_text('from sample.site.main import run')
            result = dependency_files(package, [entry])
            self.assertEqual(set(result), {entry.resolve()} | {
                (package / name).resolve() for name in files if name != 'unused_lint.py'})
            (package / 'site/leaf.py').write_text('from sample.missing import value')
            with self.assertRaisesRegex(ValueError, 'unresolved'):
                dependency_files(package, [entry])

    def test_dynamic_import_falls_back_to_whole_package(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / 'sample'
            package.mkdir()
            (package / '__init__.py').write_text('')
            (package / 'plugin.py').write_text('')
            entry = package / 'main.py'
            entry.write_text('import importlib\nimportlib.import_module(name)')
            self.assertEqual(set(dependency_files(package, [entry])),
                             {path.resolve() for path in package.glob('*.py')})
