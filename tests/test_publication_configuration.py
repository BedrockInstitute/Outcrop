import json
from pathlib import Path
import tempfile
import unittest
import re
import xml.etree.ElementTree as ET

from outcrop.adapters.search_check import check
from outcrop.site.site_config import SiteConfig, BookCatalog
from outcrop.site.publication import Publication
from outcrop.site.page_renderer import PageRenderer
from outcrop.site.site_localization import hreflang_links

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
            {'taglines': {'en': 'Missing translations'}},
            {'taglines': []},
        ]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.config(**overrides)

    def test_home_brand_and_tagline_are_static_text_not_code_or_markup(self):
        config = self.config(name='Lantern & Notes', taglines={lang: 'A <new> 𝑉.' for lang in ('en', 'zh', 'ja')})
        publication = Publication(config, BookCatalog())
        pages = PageRenderer(config, BookCatalog(), publication)
        for lang in config.languages:
            home = pages.learning_home('<h1 id="sec-0">Start</h1>', '', lang, [])
            self.assertIn('<h1 id="reading-guide-title">Lantern &amp; Notes</h1>', home)
            self.assertIn('<p class="book-tagline">A &lt;new&gt; 𝑉.</p>', home)
            self.assertIn('data-guide-intro hidden', home)
            self.assertIn('id="origin"', home)
        self.assertEqual(publication.document_title(config.name), config.name)
        self.assertEqual(publication.document_title('Chapter'), 'Chapter · Lantern & Notes')

    def test_homepage_metadata_agrees_and_alternates_are_absolute(self):
        config = self.config()
        publisher = Publication(config, BookCatalog())
        data = publisher.json_ld('Welcome', 'zh', 'index.html', config.languages, True, False, True)
        graph = json.loads(re.search(r'>(.*)</script>', data)[1])['@graph']
        page = graph[0]
        self.assertEqual(page['@type'], 'WebPage')
        self.assertEqual(page['headline'], config.name)
        self.assertEqual(page['encoding']['contentUrl'], config.canonical + '/zh/index.md')
        website = next(item for item in graph if item['@type'] == 'WebSite')
        self.assertEqual(website['url'], config.canonical + '/')
        social = publisher.social_metadata('Welcome', 'zh', 'index.html', True, False)
        self.assertIn('property="og:title" content="Lantern Notes"', social)
        self.assertIn('https://lantern.example/academy/zh/index.html', social)
        alternates = hreflang_links('index.html', config.languages, config.canonical)
        self.assertIn('hreflang="x-default" href="https://lantern.example/academy/"', alternates)
        self.assertEqual(alternates.count('href="https://'), 4)

    def test_root_sitemap_and_missing_page_do_not_confuse_crawlers(self):
        config = self.config()
        publisher = Publication(config, BookCatalog())
        with tempfile.TemporaryDirectory() as folder:
            publisher.write_root(folder, config.languages, config.base_url)
            publisher.write_agent_files(folder, config.languages, config.base_url, [])
            root = Path(folder)
            home = (root / 'index.html').read_text()
            self.assertIn('"@type":"WebSite"', home)
            self.assertIn('location.search + location.hash', home)
            missing = (root / '404.html').read_text()
            self.assertIn('content="noindex"', missing)
            self.assertNotIn('location.replace', missing)
            self.assertNotIn('canonical', missing)
            sitemap = ET.fromstring((root / 'sitemap.xml').read_text())
            self.assertEqual(len(sitemap), 4)
            for entry in sitemap:
                self.assertEqual(len(entry.findall('{http://www.w3.org/1999/xhtml}link')), 4)

    def test_agent_endpoints_share_one_inventory_and_deployment_prefix(self):
        config = self.config()
        publisher = Publication(config, BookCatalog())
        for lang in config.languages:
            transport = json.loads(publisher.page_config('Welcome', lang, 'index.html', 'index.md',
                                   config.base_url, config.name, True, False))
            self.assertEqual(transport['agentResources'], publisher.agent_resources(lang, 'Welcome'))
            self.assertIn(f'{lang}/types/Welcome.json', [item['path'] for item in transport['agentResources']])
            self.assertIn('search-content.json', [item['path'] for item in transport['agentResources']])
        guide = publisher.agent_guide(['ja'], [])
        self.assertIn(config.canonical + '/search-content.json', guide)
        self.assertIn('Published language segments: ja.', guide)
        self.assertNotIn('Replace `/en/`', guide)
        self.assertIn('Positional anchors can change', guide)
        self.assertIn('`$names`', guide)
        plain = Publication(self.config(types=''), BookCatalog()).agent_guide(['en'], [])
        self.assertNotIn('types/<Module>', plain)
        plain_resources = Publication(self.config(types=''), BookCatalog()).agent_resources('en', 'Welcome')
        self.assertFalse(any('/types/' in item['path'] for item in plain_resources))

    def test_markdown_home_preserves_chapter_identity_and_promoted_tagline(self):
        config = self.config(taglines={lang: 'A quiet tagline.' for lang in ('en', 'zh', 'ja')})
        publisher = Publication(config, BookCatalog())
        mirror = publisher.publish_markdown('# Welcome\n\nChapter body.', 'Welcome', 'en', 'index.html', ['en'])
        self.assertIn('homepage_title: "Lantern Notes"', mirror)
        self.assertIn('tagline: "A quiet tagline."', mirror)
        self.assertIn('module: Welcome', mirror)
        self.assertIn('agent_guide: https://lantern.example/academy/llms.txt', mirror)
        self.assertTrue(mirror.endswith('# Welcome\n\nChapter body.\n'))

    def test_footer_links_framework_without_repeating_site_name_in_every_edition(self):
        for name in ('Bedrock', 'Category <Notes>'):
            config = self.config(name=name)
            publisher = Publication(config, BookCatalog())
            for language in config.languages:
                footer = publisher.footer_html(language, '', 'Start.md')
                credit = footer.split('</div>', 1)[0]
                self.assertTrue(credit.startswith('<div class="footer-credit">Powered by '))
                self.assertNotIn('Bedrock,', credit)
                self.assertNotIn('Category', credit)
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
