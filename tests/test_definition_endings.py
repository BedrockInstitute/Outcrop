"""QED is a compiler-backed code-line decoration, never a prose delimiter."""
import unittest
from outcrop.core import MarkdownDocument, CodeContext
from outcrop.core.definition_endings import definition_lines, render_code_frames


class DefinitionEndingsTests(unittest.TestCase):
    def test_unicode_multiple_ends_and_cross_fence_definition(self):
        block = '<pre class="Agda"><a id="100">f</a> = 𝒜\n<a id="110">g</a> = f\n</pre>'
        ends = [{'start': 1, 'end': 105, 'name': 'f'},
                {'start': 20, 'end': 115, 'name': 'g'}]
        self.assertEqual(definition_lines(block, ends), [(0, 'f'), (1, 'g')])
        code = CodeContext(definition_ends={'A': ends})
        body = MarkdownDocument(block, module='A', code=code).render('zh').body
        self.assertEqual(body.count('class="agda-definition-end"'), 2)
        self.assertIn('--definition-line:0', body)
        self.assertIn('--definition-line:1', body)
        self.assertIn('aria-label="定义结束: f"', body)
        self.assertIn('class="agda-code-content"', body)
        self.assertNotIn('statement-ending', body)
        self.assertNotIn('∎', body)  # CSS generated content, absent from copying.
        self.assertIn('id="100"', body)

    def test_no_guessing_from_equals_or_prose(self):
        source = '**Theorem** (`f`{.Agda}) Text.\n\n```agda\nf : Set\nf = Set\n```\n'
        body = MarkdownDocument(source).render('en').body
        self.assertNotIn('agda-definition-end', body)
        self.assertNotIn('statement-ending', body)
        self.assertIn('prose-statement', body)

    def test_fold_dedent_keeps_line_positions_and_proof_role(self):
        source = ('**Proof** Reason.\n\n<details><div>\n'
                  '<pre class="Agda">  <a id="10">x</a> = y\n  <a id="20">z</a> = x\n</pre>'
                  '\n</div></details>')
        code = CodeContext(definition_ends={'A': [{'start': 1, 'end': 15, 'name': 'x'}]})
        body = MarkdownDocument(source, module='A', code=code).render('en').body
        self.assertIn('prose-proof', body)
        self.assertLess(body.index('class="agda-definition-end"'), body.index('</details>'))
        self.assertIn('--definition-line:0', body)

    def test_entities_and_absent_endpoints(self):
        block = '<pre class="Agda"><a id="7">x</a> = &lt;&amp;\n</pre>'
        self.assertEqual(definition_lines(block, [{'end': 13}]), [(0, '')])
        self.assertEqual(definition_lines(block, [{'end': 1000}]), [])

    def test_plain_agda_page_uses_the_same_frame_finisher(self):
        block = '<pre class="Agda"><a id="1">x</a> = y\n</pre>'
        definitions = [{'start': 1, 'end': 6, 'name': 'x'}]
        plain = render_code_frames(block, definitions, 'ja')
        self.assertIn('aria-label="定義の終わり: x"', plain)
        self.assertIn('class="agda-code-content"', plain)
        self.assertEqual(plain.count('class="agda-definition-end"'), 1)


if __name__ == '__main__':
    unittest.main()
