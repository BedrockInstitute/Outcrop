"""The complete shared gate must not depend on a consumer's extra linters."""
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

from site_test_support import EXAMPLE
from outcrop.core.agda_lint import AgdaPolicy, lint_text
from outcrop.core.chapter_structure import OPTIONS, opening_errors
from outcrop.core.document_renderer import MarkdownDocument
from outcrop.core.i18n_markers import shared_cjk_errors
from outcrop.core.markdown_core import plain_code
from outcrop.core.term_registry import load_entries
from outcrop.site.site_config import SiteConfig
from outcrop.site.site_lint import lint_site, diagram_errors
from outcrop.site.website import build_site


class SiteLintContractTests(unittest.TestCase):
    def test_prerequisite_override_does_not_hide_forward_source_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            shutil.copytree(EXAMPLE, root)
            source = root / 'chapters/Sample/Seed.md'
            source.write_text(source.read_text() + '\n```agda\nopen import Sample.Use\n```\n')
            config = SiteConfig.load(root / 'project.json', root=root).with_overrides(
                prerequisites={'Sample.Seed': [], 'Sample.Use': []})
            messages = [item.message for item in lint_site(config) if item.rule == 'reading-order']
            self.assertEqual(messages, ['Sample.Seed precedes prerequisite Sample.Use'])

    def test_site_gate_checks_framework_stylesheets_by_default(self):
        config = SiteConfig.load(EXAMPLE / 'project.json', root=EXAMPLE)
        with patch('outcrop.site.site_lint.diagram_errors', wraps=diagram_errors) as check:
            self.assertEqual(lint_site(config), [])
        self.assertTrue(check.call_args.kwargs['stylesheets'])
        self.assertTrue(any(path.name == 'outcrop.css'
                            for path in check.call_args.kwargs['stylesheets']))

    def test_css_relation_colour_failure_reaches_shared_site_gate(self):
        config = SiteConfig.load(EXAMPLE / 'project.json', root=EXAMPLE)
        with tempfile.TemporaryDirectory() as directory:
            css = Path(directory) / 'diagram.css'
            css.write_text('.diagram-relation { color: var(--link-color); }')
            errors = lint_site(config, stylesheets=[css])
            self.assertTrue(any(item.rule == 'diagram' and 'non-link diagram content' in item.message
                                for item in errors))
            css.write_text('.diagram-relation { color: var(--diagram-relation-color); }')
            self.assertEqual(lint_site(config, stylesheets=[css]), [])

    def test_configured_instance_stylesheet_reaches_diagram_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            shutil.copytree(EXAMPLE, root)
            css = root / 'figures.css'
            css.write_text('.diagram-relation { color: var(--link-color); }')
            config = SiteConfig.load(root / 'project.json', root=root).with_overrides(
                stylesheets=['figures.css'])
            self.assertTrue(any(item.rule == 'diagram' for item in lint_site(config)))
            css.write_text('.diagram-relation { color: var(--diagram-relation-color); }')
            self.assertEqual(lint_site(config), [])

    def test_shared_cjk_uses_marker_grammar_and_retains_source_lines(self):
        text = ('<!-- outcrop-routes {"title":"元数据"} -->\n'
                'Shared.\n中文。\n  ~~~text\n中文代码。\n  ~~~\n'
                '<!--zh-->\n中文译文。\n<!--/-->\n中文。\n')
        self.assertEqual([line for line, _ in shared_cjk_errors(text)], [3, 10])

    def test_custom_options_agree_across_lint_boilerplate_and_site(self):
        policy = AgdaPolicy(options=('--safe',))
        text = (EXAMPLE / 'chapters/Sample/Seed.md').read_text().replace(OPTIONS, policy.options_pragma)
        self.assertEqual(lint_text(text, policy), [])
        self.assertEqual(opening_errors(text, 'Sample.Seed', {'Sample.Seed'}, options=policy.options_pragma), [])
        self.assertTrue(opening_errors(text, 'Sample.Seed', {'Sample.Seed'}))
        rendered = MarkdownDocument(text, module='Sample.Seed', formal_setup=True,
                                    terms=load_entries(EXAMPLE / 'glossary.toml'),
                                    options=policy.options_pragma).render('en')
        self.assertIn('boilerplate-header-Sample.Seed', rendered.body)
        self.assertIn(policy.options_pragma, rendered.mirror)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            shutil.copytree(EXAMPLE, root)
            for source in (root / 'chapters').rglob('*.md'):
                source.write_text(source.read_text().replace(OPTIONS, policy.options_pragma))
            config = SiteConfig.load(root / 'project.json', root=root).with_overrides(
                agda_policy={'options': ['--safe']}, highlighted='', types='', expression_types='')
            self.assertEqual(lint_site(config), [])
            output = Path(directory) / 'output'
            self.assertEqual(build_site(config, ['--out', str(output), '--langs', 'en']), 0)
            page = (output / 'en/Sample.Seed.html').read_text()
            self.assertIn('boilerplate-header-Sample.Seed', page)
            article = re.search(r'<article\b[^>]*>(.*?)</article>', page, re.S)[1]
            visible = re.sub(r'<template\b[^>]*>.*?</template>', '', article, flags=re.S)
            self.assertNotIn('OPTIONS', plain_code(visible))


if __name__ == '__main__':
    unittest.main()
