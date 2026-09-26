"""Public renderer boundaries, isolated distribution, and project-state isolation."""
from pathlib import Path
from outcrop import site as site_package
RESOURCES = Path(site_package.__file__).resolve().parent / "resources"
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

from outcrop.site.assets import AssetBundle
from outcrop.core.document_renderer import CodeContext, MarkdownDocument
from outcrop.site.site_config import SiteConfig
from outcrop.site.site_lint import lint_site
from outcrop.site.website import build_site

EXAMPLE = ROOT / 'examples/renderer'


class RendererLibraryTests(unittest.TestCase):
    def test_inline_source_notation_opt_out_is_rendered_not_literal_html(self):
        source = 'Original `suc n`{.Agda .raw-notation}; later `suc n`{.Agda}.'
        result = MarkdownDocument(source).render('en')
        self.assertEqual(result.body.count('data-outcrop-notation="source"'), 1)
        self.assertNotIn('&lt;span data-outcrop-notation', result.body)
        self.assertIn('Original `suc n`; later `suc n`.', result.mirror)

    def test_explicit_inline_agda_type_disambiguates_without_guessing_links(self):
        source = ('`suc zero`{.Agda type="Fin 3"} and '
                  '`suc zero`{.Agda .raw-notation type="Fin 3"}')
        result = MarkdownDocument(source).render('en')
        self.assertEqual(result.body.count('data-agda-inline-type="Fin 3"'), 2)
        self.assertIn('data-hover-html="&lt;code class=&quot;Agda inline-ref&quot;&gt;Fin 3&lt;/code&gt;"', result.body)
        self.assertNotIn('data-agda-origin="Agda.Builtin.Nat', result.body)
        self.assertEqual(result.body.count('data-outcrop-notation="source"'), 1)
        self.assertIn('`suc zero` and `suc zero`', result.mirror)

    def test_typed_overloaded_constructors_use_compiler_identity_and_unmarked_fallback(self):
        code = CodeContext(
            names={'Agda.Builtin.Nat': {'Nat.zero': '12', 'Nat.suc': '15'},
                   'Cubical.Data.FinData.Base': {'Fin.zero': '20', 'Fin.suc': '25'}},
            vocabulary={'by_href': {
                'Agda.Builtin.Nat.html#12': ('Base.Prelude', '40', 'InductiveConstructor', 'zero'),
                'Cubical.Data.FinData.Base.html#20': ('Base.Prelude', '50', 'InductiveConstructor', 'zero'),
                'Cubical.Data.FinData.Base.html#25': ('Base.Prelude', '55', 'InductiveConstructor', 'suc'),
            }, 'inline': {'zero': ('Base.Prelude.html#40', 'InductiveConstructor')}})
        source = ('`zero`{.Agda type="Fin 3"} '
                  '`suc zero`{.Agda type="Fin 3"} '
                  '`zero`{.Agda type="ℕ"} `zero`{.Agda}')
        body = MarkdownDocument(source, code=code).render('en').body
        self.assertEqual(body.count('data-agda-origin="Cubical.Data.FinData.Base.html#20"'), 2)
        self.assertIn('data-agda-origin="Cubical.Data.FinData.Base.html#25"', body)
        self.assertIn('data-agda-origin="Agda.Builtin.Nat.html#12"', body)
        self.assertIn('href="Base.Prelude.html#40"', body)  # unmarked legacy fallback

    def test_agda_preview_preserves_one_full_code_surface(self):
        source = '<!-- outcrop:agda-preview-lines=1 -->\n\n```agda\nx = 1\ny = 2\n```'
        result = MarkdownDocument(source).render('en')
        self.assertIn('data-preview-lines="1"', result.body)
        self.assertEqual(result.body.count('<pre class="Agda">'), 1)
        self.assertIn('x = 1\ny = 2', re.sub('<[^>]+>', '', result.body))
        self.assertIn('```agda\nx = 1\ny = 2\n```', result.mirror)

    def test_plain_markdown_needs_no_project_or_semantics(self):
        result = MarkdownDocument((EXAMPLE / 'plain.md').read_text()).render('en')
        self.assertIn('A renderer without a project', result.body)
        self.assertIn('href="chapter.html#detail"', result.body)
        self.assertIn('unknown value', result.body)
        self.assertNotIn('data-type=', result.body)
        self.assertNotIn('expr-node', result.body)
        self.assertNotIn('Bedrock', result.body)
        self.assertNotIn('\x00', result.mirror)
        self.assertIn('```agda\nunknown value = value\n```', result.mirror)

    def test_asset_snapshot_is_a_single_generation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source'; source.mkdir()
            (source / 'entry.js').write_text('import "./leaf.js";')
            (source / 'leaf.js').write_text('export const value = 1;')
            first = AssetBundle(source)
            (source / 'leaf.js').write_text('export const value = 2;')
            second = AssetBundle(source)
            self.assertNotEqual(first.runtime, second.runtime)
            first.publish(root / 'output')
            self.assertEqual((root / 'output' / first.runtime / 'leaf.js').read_text(),
                             'export const value = 1;')
            self.assertIn(first.runtime, first.template('%%RUNTIME%%'))

    def test_config_rejects_unsafe_paths_types_and_references(self):
        values = json.loads((EXAMPLE / 'project.json').read_text())
        for update in ({'sources': '../secret'}, {'sources': 'https:chapter'},
                       {'base_url': '/bad path'}, {'base_url': '/bad\npath'},
                       {'favicon': []}, {'favicon': ''}, {'languages': [{}]}, {'base_url': '//outside'},
                       {'stylesheets': 'custom.css'}, {'stylesheets': ['../outside.css']},
                       {'stylesheets': ['custom.js']}, {'stylesheets': ['custom.css', 'custom.css']},
                       {'canonical': 'javascript:alert(1)'}, {'agent': {'translations': {'en': {'fetch': 'code'}}}},
                       {'legacy_pages': {'../old.html': 'index.html'}}, {'agda_policy': {'options': 'not-list'}},
                       {'policies': {'level_name_convention': 'true'}}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                SiteConfig({**values, **update}, root=EXAMPLE)
        config = SiteConfig(values, root=EXAMPLE)
        with self.assertRaises(ValueError):
            config.validate_references({'Unrelated'})

    def test_strict_lint_of_independent_project(self):
        config = SiteConfig.load(EXAMPLE / 'project.json', root=EXAMPLE)
        self.assertEqual(lint_site(config), [])

    def test_partial_prerequisites_override_only_named_chapters(self):
        from outcrop.site.reading_routes import build_reading_data
        reading = build_reading_data(EXAMPLE / 'chapters', EXAMPLE / 'catalog.json',
            previews={'Welcome'}, prerequisites={'Sample.Seed': []})
        nodes = {node['id']: node for node in reading['nodes']}
        self.assertEqual(nodes['Sample.Seed']['prerequisites'], [])
        self.assertEqual(nodes['Sample.Use']['prerequisites'], ['Sample.Seed'])

    def test_configuration_is_an_owned_snapshot(self):
        values = json.loads((EXAMPLE / 'project.json').read_text())
        config = SiteConfig(values, root=EXAMPLE)
        values['languages'].clear()
        values['descriptions']['en'] = 'mutated'
        self.assertEqual(config.languages, ['en', 'zh', 'ja'])
        self.assertNotEqual(config.descriptions['en'], 'mutated')

    def test_two_instances_in_one_process(self):
        first = SiteConfig.load(EXAMPLE / 'project.json', root=EXAMPLE)
        second = first.with_overrides(name='Prism Lessons', publisher='Prism Group',
            storage_namespace='prism', canonical='https://prism.example/course', base_url='/course')
        with tempfile.TemporaryDirectory() as folder:
            for index, config in enumerate((first, second, first)):
                output = Path(folder) / str(index)
                self.assertEqual(build_site(config, ['--out', str(output)]), 0)
                page = (output / 'en/Sample.Use.html').read_text()
                self.assertIn(config.name, page)
                self.assertIn('"storageNamespace":"' + config.storage_namespace + '"', page)
                self.assertIn('"preludeModule":""', page)
                self.assertIn('"levelNameConvention":false', page)
                self.assertIn(config.canonical + '/en/Sample.Use.html', page)
                for forbidden in ('Bedrock Institute', 'bedrock.institute', 'Base.Prelude', 'L⊨ZFC', 'src/'):
                    self.assertNotIn(forbidden, page)
                self.assertIn(config.name, (output / 'llms.txt').read_text())
                self.assertIn(f'agent_guide: {config.canonical}/llms.txt\n',
                              (output / 'en/Sample.Use.md').read_text())
                self.assertIn('CC0-1.0', page)
                self.assertEqual((output / 'static/assets/logo.svg').read_bytes(), (EXAMPLE / 'lantern.svg').read_bytes())

    def test_instance_stylesheet_is_versioned_and_not_inherited(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project = root / 'project'
            shutil.copytree(EXAMPLE, project)
            custom = project / 'figures.css'
            custom.write_text('.example-figure { gap: 1rem; }')
            configured = SiteConfig.load(project / 'project.json', root=project).with_overrides(
                stylesheets=['figures.css'])
            output = root / 'styled'
            self.assertEqual(build_site(configured, ['--out', str(output), '--langs', 'en']), 0)
            page = (output / 'en/Sample.Use.html').read_text()
            self.assertIn('/static/project/style-0.css?v=', page)
            self.assertEqual((output / 'static/project/style-0.css').read_text(), custom.read_text())
            plain = root / 'plain'
            self.assertEqual(build_site(configured.with_overrides(stylesheets=[]),
                                        ['--out', str(plain), '--langs', 'en']), 0)
            self.assertNotIn('/static/project/style-0.css', (plain / 'en/Sample.Use.html').read_text())

    def test_incremental_page_updates_global_search_without_rewriting_other_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            book = root / 'book'
            shutil.copytree(EXAMPLE, book)
            config = SiteConfig.load(book / 'project.json', root=book)
            output = root / 'site'
            cache = root / 'code-context.json.gz'
            cache_args = ['--code-cache', str(cache), '--code-cache-key', 'fixture-v1']
            self.assertEqual(build_site(config, ['--out', str(output), *cache_args]), 0)
            cache_mtime = cache.stat().st_mtime_ns
            other_page = output / 'en/Sample.Use.html'
            other_mtime = other_page.stat().st_mtime_ns
            other_search = [item for item in json.loads((output / 'search-content.json').read_text())
                            if item['module'] == 'Sample.Use']

            highlighted = book / 'semantic/html/Sample.Seed.md'
            old = highlighted.read_text()
            highlighted.write_text(old.replace('The declaration below specifies its only constructor.',
                                               'The cached declaration still has one constructor.'))
            self.assertEqual(build_site(config, ['--out', str(output), '--incremental',
                                                 '--module', 'Sample.Seed', *cache_args]), 0)
            self.assertEqual(cache.stat().st_mtime_ns, cache_mtime)
            self.assertEqual(other_page.stat().st_mtime_ns, other_mtime)
            self.assertIn('The cached declaration still has one constructor.',
                          (output / 'en/Sample.Seed.html').read_text())
            search = json.loads((output / 'search-content.json').read_text())
            self.assertEqual([item for item in search if item['module'] == 'Sample.Use'],
                             other_search)
            self.assertTrue(any('The cached declaration still has one constructor.' in item.get('text', '')
                                for item in search))
            self.assertFalse(any('The declaration below specifies its only constructor.' in item.get('text', '')
                                 for item in search))
            reference = root / 'reference'
            self.assertEqual(build_site(config, ['--out', str(reference), *cache_args]), 0)
            for relative in ('search-content.json', 'en/Sample.Seed.html',
                             'zh/Sample.Seed.html', 'ja/Sample.Seed.html'):
                self.assertEqual((output / relative).read_bytes(),
                                 (reference / relative).read_bytes(), relative)

    def test_isolated_distribution_has_no_instance_or_toolchain(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(Path(site_package.__file__).resolve().parent.parent, root / 'distribution/outcrop',
                            ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(EXAMPLE, root / 'book')
            self.assertFalse((root / 'site/project.json').exists())
            self.assertFalse((root / 'src').exists())
            self.assertFalse((root / 'dev').exists())
            environment = {**os.environ, 'PATH': '/no-toolchain', 'PYTHONPATH': str(root / 'distribution')}
            result = subprocess.run([sys.executable, '-m', 'outcrop', 'build',
                '--config', str(root / 'book/project.json'), '--project-root', str(root / 'book'),
                '--out', str(root / 'output')], cwd=root, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((root / 'output/en/index.html').exists())
            result = subprocess.run([sys.executable, '-m', 'outcrop', 'lint',
                '--config', str(root / 'book/project.json'), '--project-root', str(root / 'book')],
                cwd=root, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
