import json
from pathlib import Path
import tempfile
import unittest

from outcrop.adapters.search_check import check
from outcrop.site.site_config import SiteConfig, BookCatalog
from outcrop.site.publication import Publication
from outcrop.site.page_renderer import PageRenderer

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples/renderer'


class PublicationConfigurationTests(unittest.TestCase):
    def config(self, **overrides):
        return SiteConfig.load(EXAMPLE / 'project.json', root=EXAMPLE).with_overrides(**overrides)

    def test_external_module_labels_match_namespace_not_project_assumptions(self):
        config = self.config(external_libraries=[
            {'prefix': 'Algebra', 'name': 'Algebra', 'url': 'https://example.org/algebra'},
            {'prefix': 'Algebra.Category', 'name': 'Categories', 'url': 'https://example.org/category'}])
        book = BookCatalog()
        publisher = Publication(config, book)
        pages = PageRenderer(config, book, publisher)
        for language in config.languages:
            self.assertIn('Categories', publisher.page_description('Algebra.Category.Core', language, False, True))
            self.assertIn('Categories', pages.ext_banner(language, 'Algebra.Category.Core'))
            self.assertNotIn('Cubical', publisher.page_description('Other', language, False, True))
        self.assertIsNone(config.external_library('Algebraic.Core'))

    def test_plain_site_has_no_implicit_programming_language(self):
        publisher = Publication(self.config(programming_language=None), BookCatalog())
        plain = publisher.json_ld('Sample.Seed', 'en', 'Sample.Seed.html', ['en'], False, False, True)
        self.assertNotIn('programmingLanguage', plain)
        formal = Publication(self.config(programming_language={'name': 'Agda', 'url': 'https://agda.readthedocs.io'}), BookCatalog())
        data = formal.json_ld('Sample.Seed', 'en', 'Sample.Seed.html', ['en'], False, False, True)
        self.assertIn('"name":"Agda"', data)
        self.assertNotIn('Cubical', data)

    def test_non_english_only_project_has_no_hidden_english_dependency(self):
        config = self.config(languages=['zh'], descriptions={'zh': '独立教材'})
        publisher = Publication(config, BookCatalog())
        data = publisher.json_ld('Start', 'zh', 'Start.html', ['zh'], True, False, True)
        self.assertIn('独立教材', data)

    def test_metadata_urls_and_names_are_validated(self):
        for overrides in [
            {'programming_language': {'name': 'Agda', 'url': 'javascript:x'}},
            {'external_libraries': [{'prefix': '../bad', 'name': 'Bad', 'url': 'https://example.org'}]},
            {'external_libraries': [{'prefix': 'Lib', 'name': 'Lib', 'url': 'https://u:p@example.org'}]},
        ]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.config(**overrides)

    def test_footer_uses_instance_name_and_links_framework_in_every_edition(self):
        for name in ('Bedrock', 'Category <Notes>'):
            config = self.config(name=name)
            publisher = Publication(config, BookCatalog())
            for language in config.languages:
                footer = publisher.footer_html(language, '', 'Start.md')
                self.assertIn(('Bedrock' if name == 'Bedrock' else 'Category &lt;Notes&gt;') + ', powered by ', footer)
                self.assertIn('href="https://github.com/BedrockInstitute/Outcrop">Outcrop</a>', footer)
                self.assertNotIn('1lab', footer)

    def test_search_check_discovers_actual_editions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'en').mkdir()
            (root / 'en/index.html').write_text('<h1 id="target">Title</h1>')
            entries = [{'lang': '*', 'href': 'index.html#target', 'kind': 'heading'}]
            (root / 'search-content.json').write_text(json.dumps(entries))
            self.assertFalse(check(root))
            entries[0]['href'] = 'index.html#missing'
            (root / 'search-content.json').write_text(json.dumps(entries))
            self.assertTrue(check(root))


if __name__ == '__main__':
    unittest.main()
