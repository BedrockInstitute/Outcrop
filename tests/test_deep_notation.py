"""One discoverable, packaged owner for compact mathematical presentation."""
from pathlib import Path
import unittest

from outcrop.site.assets import AssetBundle
from outcrop import site

RESOURCES = Path(site.__file__).parent / 'resources'
STATIC = RESOURCES / 'static'


class DeepNotationTests(unittest.TestCase):
    def test_single_lifecycle_and_no_legacy_scanners(self):
        directory = STATIC / 'deep-notation'
        files = list(directory.glob('*.js'))
        self.assertEqual(sum(p.read_text().count('new MutationObserver(') for p in files), 1)
        self.assertIn('if (observer) return;', (directory / 'index.js').read_text())
        for old in ('universe-levels.js', 'mathematical-notation.js'):
            self.assertFalse((STATIC / old).exists())
            self.assertNotIn(old, (RESOURCES / 'template.html').read_text())
        self.assertIn("'./deep-notation/index.js'", (STATIC / 'outcrop.js').read_text())
        hover = (STATIC / 'reader/hover.js').read_text()
        self.assertIn("'../deep-notation/index.js'", hover)
        self.assertNotIn('var sourceLabels', hover)

    def test_styles_and_nested_runtime_are_published_together(self):
        bundle = AssetBundle(STATIC)
        for name in ('index', 'source', 'universe', 'numeric', 'projections', 'powers'):
            self.assertIn(f'deep-notation/{name}.js', bundle.files)
        css = bundle.files['deep-notation/styles.css'].decode()
        self.assertIn('../fonts/BedrockUniverseLevels-Regular.woff2', css)
        self.assertNotIn('.source-notation', bundle.files['appearance.css'].decode())
        rendered = bundle.template((RESOURCES / 'template.html').read_text())
        self.assertRegex(rendered, r'/deep-notation/styles\.css\?v=[0-9a-f]{16}')
        self.assertNotIn('%%NOTATIONCSSVER%%', rendered)
