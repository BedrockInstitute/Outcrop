from pathlib import Path
import tempfile
import unittest
from outcrop.adapters.source_stage import sync_sources


class SourceStageTests(unittest.TestCase):
    def test_allows_parent_directory_alias(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / 'source'
            source.mkdir()
            (source / 'A.lagda.md').write_text('source')
            (root / 'alias').symlink_to(root, target_is_directory=True)
            sync_sources(source, root / 'alias/check')
            self.assertEqual((root / 'check/A.lagda.md').read_text(), 'source')

    def test_add_modify_delete_and_rename_without_touching_interfaces(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source, dest = root / 'source', root / 'check/src'
            source.mkdir()
            original = source / 'A.lagda.md'
            original.write_text('first')
            sync_sources(source, dest)
            staged = dest / original.name
            timestamp = staged.stat().st_mtime_ns
            sync_sources(source, dest)
            self.assertEqual(timestamp, staged.stat().st_mtime_ns)
            original.write_text('second')
            sync_sources(source, dest)
            self.assertEqual(staged.read_text(), 'second')
            interface = dest.parent / 'A.agdai'
            interface.write_text('keep interfaces isolated from source sync')
            original.rename(source / 'B.lagda.md')
            sync_sources(source, dest)
            self.assertFalse(staged.exists())
            self.assertTrue((dest / 'B.lagda.md').exists())
            self.assertTrue(interface.exists())

    def test_rejects_source_destination_overlap_and_symlink_before_deleting(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source, dest = root / 'source', root / 'check'
            source.mkdir(); dest.mkdir()
            (source / 'A.lagda.md').write_text('source')
            for bad in (source, root, source / 'nested'):
                with self.assertRaises(ValueError):
                    sync_sources(source, bad)
            (dest / 'A.lagda.md').symlink_to(source / 'A.lagda.md')
            (dest / 'stale.lagda.md').write_text('do not partially delete')
            with self.assertRaises(ValueError):
                sync_sources(source, dest)
            self.assertTrue((dest / 'stale.lagda.md').exists())
