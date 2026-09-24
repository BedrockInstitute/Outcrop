"""Agda's resource guard must not reach ghcup, which rejects RTS options."""
from pathlib import Path
import unittest


class CompilerCIResourceTests(unittest.TestCase):
    def test_rts_options_are_scoped_to_compiler_invocations(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/check.yml').read_text()
        job = workflow.split('  agda-integration:\n', 1)[1]
        self.assertNotIn('GHCRTS', job.split('    steps:\n', 1)[0])
        setup = job.split('      - uses: haskell-actions/setup@', 1)[1].split('      - ', 1)[0]
        self.assertNotIn('GHCRTS', setup)
        invocations = [step for step in job.split('      - run: ')[1:]
                       if 'agda-build --build-dir' in step.splitlines()[0]
                       or 'scripts/smoke-agda.py' in step.splitlines()[0]
                       or 'refresh_semantics.py' in step.splitlines()[0]]
        self.assertEqual(len(invocations), 3)
        for step in invocations:
            self.assertIn("          GHCRTS: '-A64m -I0 -M8g'", step)


if __name__ == '__main__':
    unittest.main()
