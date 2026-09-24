"""The optional producer is installable and has no consuming-project defaults."""
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from outcrop.adapters.agda import build, libraries, parallel
from outcrop.adapters.agda.archive import safe_extract, sha256
from outcrop.adapters.extract_types import write_loader


class AgdaToolchainTests(unittest.TestCase):
    def test_identity_is_location_independent_and_covers_resources(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            moved = Path(folder) / 'package'
            shutil.copytree(build.RESOURCES, moved)
            self.assertEqual(build.identity(), build.identity(moved))
            overlay = moved / 'src/Outcrop/Agda/TypeTrace.hs'
            overlay.write_text(overlay.read_text() + '\n-- Changed instrumentation\n')
            self.assertNotEqual(build.identity(), build.identity(moved))

    def test_verified_install_does_not_need_cabal_or_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'bin').mkdir()
            (root / 'bin/outcrop-agda').touch()
            (root / 'install/bin').mkdir(parents=True)
            (root / 'install/bin/agda').touch()
            (root / 'install/data').mkdir()
            (root / 'install/outcrop-agda.json').write_text(json.dumps(build.identity()))
            with patch.object(build, 'download', side_effect=AssertionError('network')):
                self.assertEqual(build.build(root), root.resolve() / 'bin/outcrop-agda')

    def test_archive_rejects_traversal_links_and_devices(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('/escape', tarfile.REGTYPE),
                           ('link', tarfile.SYMTYPE), ('hard', tarfile.LNKTYPE), ('dev', tarfile.CHRTYPE)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                archive = root / 'bad.tar.gz'
                with tarfile.open(archive, 'w:gz') as tar:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = '../../outside'
                    tar.addfile(member)
                with self.assertRaisesRegex(RuntimeError, 'unsafe archive'):
                    safe_extract(archive, root / 'extract')

    def test_library_installer_is_project_neutral_and_registry_is_exact(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            downloads = root / 'deps/downloads'
            downloads.mkdir(parents=True)
            archive = downloads / 'category-1.0.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                content = b'name: category\ninclude: .\n'
                member = tarfile.TarInfo('upstream-1/category.agda-lib')
                member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
            lock = root / 'lock.json'
            lock.write_text(json.dumps({'version': 1, 'libraries': [{
                'name': 'category', 'version': '1.0', 'url': 'https://example.org/library.tar.gz',
                'sha256': sha256(archive), 'archive_root': 'upstream-1', 'library': 'category.agda-lib'}]}))
            registry = root / 'agda/libraries'
            registry.parent.mkdir()
            registry.write_text('/stale/category.agda-lib\n')
            with patch('urllib.request.urlretrieve', side_effect=AssertionError('network')):
                first = libraries.install(lock, root / 'deps', registry.parent)
                second = libraries.install(lock, root / 'deps', registry.parent)
            self.assertEqual(first, second)
            self.assertEqual(registry.read_text(), first[0] + '\n')
            self.assertNotIn('cubical', registry.read_text())

    def test_loader_does_not_invent_cubical_options_or_dependencies(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(write_loader(folder, '/explicit/sources', ['Start'], options=['--safe']))
            self.assertIn('{-# OPTIONS --safe #-}', path.read_text())
            self.assertNotIn('cubical', path.read_text())
            self.assertNotIn('cubical', (Path(folder) / 'typeext.agda-lib').read_text())

    def test_plain_agda_modules_and_duplicate_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'A.agda').write_text('module A where\n')
            (root / 'Start.lagda.md').write_text('```agda\nmodule Start where\nimport A\n```')
            paths, graph = parallel.local_graph(root)
            self.assertEqual(set(paths), {'A', 'Start'})
            self.assertEqual(graph['Start'], {'A'})
            (root / 'A.lagda.md').write_text('```agda\nmodule A where\n```')
            with self.assertRaisesRegex(ValueError, 'duplicate source module'):
                parallel.local_graph(root)

    def test_external_seed_uses_only_explicit_flags_and_disables_trace(self):
        def check(command, **kwargs):
            seed = Path(command[-1]).read_text()
            self.assertIn('module OutcropExternalDependencies where', seed)
            self.assertNotIn('cubical', seed)
            self.assertIn('{-# OPTIONS --safe #-}', seed)
            self.assertNotIn('--safe', command)
            self.assertNotIn('OUTCROP_AGDA_TYPES', kwargs['env'])
        with patch.dict(os.environ, {'OUTCROP_AGDA_TYPES': '/not-used'}), patch.object(parallel.subprocess, 'run', side_effect=check):
            parallel.precompile_external_dependencies(project_root=Path.cwd(), agda=Path('/agda'),
                dependencies={'Category.Core'}, options=('--safe',))


if __name__ == '__main__':
    unittest.main()
