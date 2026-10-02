"""One discoverable, packaged owner for compact mathematical presentation."""
from pathlib import Path
import unittest
import subprocess
import json

from outcrop.site.assets import AssetBundle
from outcrop import site

RESOURCES = Path(site.__file__).parent / 'resources'
STATIC = RESOURCES / 'static'


class DeepNotationTests(unittest.TestCase):
    def test_shared_natural_exponent_algebra(self):
        module = (STATIC / 'deep-notation/numeric.js').as_uri()
        script = f"""
globalThis.window = {{}};
const {{naturalNotation, successorNotation}} = await import({json.dumps(module)});
const inputs = ['zero', 'suc zero', 'suc n', 'suc (suc n)',
 'suc (suc (suc n))', 'suc 9007199254740993', '2', 'n',
 'suc length', 'suc (f n)', 'suc n m', 'n′'];
console.log(JSON.stringify(inputs.map(s => naturalNotation(s)?.label ?? null)));
if (successorNotation('n', 12).label !== 'n⁺¹²') process.exit(1);
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script],
                                check=True, text=True, capture_output=True)
        self.assertEqual(json.loads(result.stdout),
                         ['0', '1', 'n⁺', 'n⁺⁺', 'n⁺³', '9007199254740994',
                          '2', 'n', 'length⁺', None, None, 'n′'])

    def test_outer_rules_do_not_implement_numeric_children(self):
        vector = (STATIC / 'deep-notation/vectors.js').read_text()
        self.assertIn('presentation(container,', vector)
        self.assertNotIn("from './numeric.js'", vector)
        self.assertNotIn('Agda.Builtin.Nat', vector)
        self.assertNotIn('exponentNotation', vector)

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
        for name in ('index', 'source', 'composition', 'presentation', 'colors', 'universe', 'numeric', 'projections', 'vectors'):
            self.assertIn(f'deep-notation/{name}.js', bundle.files)
        css = bundle.files['deep-notation/styles.css'].decode()
        self.assertIn('../fonts/BedrockUniverseLevels-Regular.woff2', css)
        self.assertNotIn('.source-notation', bundle.files['appearance.css'].decode())
        rendered = bundle.template((RESOURCES / 'template.html').read_text())
        self.assertRegex(rendered, r'/deep-notation/styles\.css\?v=[0-9a-f]{16}')
        self.assertNotIn('%%NOTATIONCSSVER%%', rendered)

    def test_structured_layout_retains_nested_scripts_and_source_free_paint(self):
        module = (STATIC / 'deep-notation/presentation.js').as_uri()
        script = f"""
import {{text, sequence, superscript, subscript, group, successor, styled, toned, plain, paint, mapText}} from {json.dumps(module)};
const model = superscript(text('A'), successor(text('n'), 3));
if (model.index.form !== 'script' || plain(model) !== 'A^n⁺³') process.exit(1);
const sub = subscript(text('S'), group(sequence([text('𝒮 '),text('↾ M')])));
const compact = mapText(sub, s => s.replace(/\\s/g, ''));
if (plain(compact) !== 'S_(𝒮↾M)') process.exit(2);
const document = {{createElement: () => ({{dataset: {{}}, children: [], classList: {{add(){{}}}},
 append(...nodes){{this.children.push(...nodes);}}}})}};
const dom = paint(styled('vector', model), document);
function verify(node) {{
 if (node.textContent || node.innerHTML) process.exit(3);
 node.children.forEach(verify);
}}
verify(dom);
if (JSON.stringify(dom).indexOf('notation-super') < 0) process.exit(4);
const colored = toned(['Field'], subscript(text('S'), toned(['Bound'], text('𝒮 '))));
const mapped = mapText(colored, s => s.trim());
if (plain(mapped) !== 'S_𝒮' || mapped.classes[0] !== 'Field' || mapped.body.index.classes[0] !== 'Bound') process.exit(5);
verify(paint(mapped, document));
"""
        subprocess.run(['node', '--input-type=module', '-e', script], check=True)
