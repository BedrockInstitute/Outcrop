"""Real Git comparisons for conservative CI documentation shortcuts."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from outcrop.adapters.ci_scope import classify, documentation, main, read_policy

ROOT = Path(__file__).resolve().parents[1]
POLICY = {'files': ['README.md'], 'markdown_trees': ['docs'], 'submodules': {}}


class ChangeScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        self.policy = self.root / 'policy.json'
        self.write('policy.json', json.dumps(POLICY))
        self.write('README.md', 'Initial\n')
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args],
                                       text=True, stderr=subprocess.PIPE).strip()

    def write(self, path, text):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD')

    def full(self, head=None, base=None, event='push'):
        base = base or self.base
        payload = ({'before': base} if event == 'push' else
                   {'pull_request': {'base': {'sha': base}}})
        return classify(self.root, self.policy, event, payload,
                        head or self.git('rev-parse', 'HEAD'))[0]

    def test_entire_push_not_just_last_commit(self):
        self.write('source.py', 'changed\n')
        self.commit()
        self.write('README.md', 'docs\n')
        self.commit()
        self.assertTrue(self.full())

    def test_docs_add_edit_delete_and_unusual_filenames(self):
        self.write('README.md', 'edited\n')
        self.write('docs/a space\nand newline.md', 'docs\n')
        self.assertFalse(self.full(self.commit()))
        (self.root / 'README.md').unlink()
        self.assertFalse(self.full(self.commit()))

    def test_literate_source_and_unknown_paths_are_full(self):
        for path in ('docs/Example.lagda.md', 'examples/chapter.md',
                     'docs/data.json', '.github/workflows/check.yml', 'new-file'):
            with self.subTest(path=path):
                self.assertFalse(documentation(path, POLICY))

    def test_large_changeset_does_not_truncate_late_source_change(self):
        for index in range(350):
            self.write(f'docs/{index}.md', 'doc\n')
        self.write('z-source.py', 'must trigger full CI\n')
        self.assertTrue(self.full(self.commit()))

    def test_rename_out_of_code_cannot_hide_removal(self):
        self.write('policy.json', json.dumps({**POLICY, 'files': ['README.md', 'docs.md']}))
        self.write('source.py', 'code\n')
        base = self.commit()
        self.git('mv', 'source.py', 'docs.md')
        self.assertTrue(self.full(self.commit(), base))

    def test_pr_uses_merge_base_not_unrelated_base_branch_changes(self):
        self.git('checkout', '-qb', 'target')
        self.write('unrelated.py', 'target-only\n')
        target = self.commit()
        self.git('checkout', '-qb', 'topic', self.base)
        self.write('README.md', 'topic docs\n')
        self.assertFalse(self.full(self.commit(), target, 'pull_request'))

    def test_missing_history_new_branch_manual_and_bad_policy_fall_back(self):
        for base in ('0' * 40, 'a' * 40, '--help'):
            self.assertTrue(self.full(base=base))
        self.assertTrue(self.full(event='workflow_dispatch'))
        self.policy.write_text('{}')
        self.assertTrue(self.full())

    def test_submodule_docs_only_and_missing_old_object(self):
        child = self.root / 'engine'
        child.mkdir()
        def run(*args):
            return subprocess.check_output(['git', '-C', str(child), *args],
                                           text=True, stderr=subprocess.PIPE).strip()
        run('init', '-q')
        run('config', 'user.email', 'test@example.invalid')
        run('config', 'user.name', 'Test')
        (child / 'README.md').write_text('old\n')
        (child / 'policy.json').write_text(json.dumps(POLICY))
        run('add', '.')
        run('commit', '-qm', 'initial child')
        self.policy.write_text(json.dumps({**POLICY, 'submodules': {'engine': 'policy.json'}}))
        base = self.commit()
        (child / 'README.md').write_text('new\n')
        run('commit', '-qam', 'child docs')
        self.assertFalse(self.full(self.commit(), base))
        (child / 'source.py').write_text('code\n')
        run('add', '.')
        run('commit', '-qm', 'child code')
        self.assertTrue(self.full(self.commit(), base))
        self.git('update-index', '--cacheinfo', '160000,' + 'a' * 40 + ',engine')
        self.git('commit', '-qm', 'unavailable child')
        missing = self.git('rev-parse', 'HEAD')
        self.assertTrue(self.full(head=missing, base=base))

    def test_action_output_and_summary(self):
        self.write('README.md', 'edited\n')
        head = self.commit()
        event = self.root / 'event.json'
        event.write_text(json.dumps({'before': self.base}))
        output, summary = self.root / 'output', self.root / 'summary'
        with patch.dict(os.environ, {
            'GITHUB_EVENT_NAME': 'push', 'GITHUB_EVENT_PATH': str(event),
            'GITHUB_SHA': head, 'GITHUB_OUTPUT': str(output),
            'GITHUB_STEP_SUMMARY': str(summary),
        }):
            self.assertEqual(main(['--project-root', str(self.root),
                                   '--policy', str(self.policy)]), 0)
        self.assertEqual(output.read_text(), 'full=false\n')
        self.assertIn('documentation-only', summary.read_text())


class FrameworkCIPolicyTests(unittest.TestCase):
    def test_only_reference_docs_not_example_inputs_are_exempt(self):
        policy = read_policy(ROOT / '.github/docs-only.json')
        for path in ('README.md', 'AGENTS.md', 'docs/AGDA.md'):
            self.assertTrue(documentation(path, policy))
        for path in ('examples/renderer/plain.md', 'tests/test_ci_scope.py',
                     '.github/docs-only.json', 'pyproject.toml',
                     'src/outcrop/site/resources/static/outcrop.css'):
            self.assertFalse(documentation(path, policy))

    def test_package_gate_always_runs_and_compiler_is_scoped(self):
        workflow = (ROOT / '.github/workflows/check.yml').read_text()
        package, compiler = workflow.split('  agda-integration:\n')
        self.assertIn('fetch-depth: 0', package)
        self.assertIn('run: make check PY=python', package)
        self.assertIn('run: reuse lint', package)
        self.assertNotIn('    if:', package)
        self.assertIn("if: needs.independent-package.outputs.full == 'true'", compiler)
