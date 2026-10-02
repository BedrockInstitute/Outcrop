"""Postfix authoring is explicit policy; rendering needs resolved Sigma fields."""
import unittest
from outcrop.core.agda_lint import AgdaPolicy, lint_text, postfix_projection_findings
from outcrop.core.projection_notation import pair_projection_attribute
from outcrop.core.agda_semantics import AgdaSemantics, ref_link, inline_notation_expression_index


class PostfixTests(unittest.TestCase):
    def lint(self, code):
        return postfix_projection_findings('```agda\n' + code + '\n```', ('fst', 'snd'))

    def test_prefix_and_higher_order_are_rejected(self):
        self.assertEqual(len(self.lint('a = fst p\nb = snd (f x)\nc = cong fst q\nd = Σ.snd p')), 4)

    def test_postfix_names_imports_comments_and_declarations(self):
        self.assertFalse(self.lint('''open import A using ( fst; snd )
open B renaming ( fst to first ) hiding ( snd )
x = p .snd .fst
y = cong (λ p → p .fst) q
fst : A
fst = value
z = record { snd = other }
name = "fst p"
-- fst p
{- snd p -}
fst-related = thing'''))

    def test_module_arguments_not_hidden_with_import_bindings(self):
        self.assertEqual(len(self.lint('open M fst using ( snd )')), 1)

    def test_inline_and_display_share_rule_but_names_remain(self):
        text = '`fst`{.Agda}, `p .snd`{.Agda}, `snd p`{.Agda}\n<div><code>`fst p`{.Agda}</code></div>'
        self.assertEqual(len(postfix_projection_findings(text, ('fst','snd'))), 2)

    def test_policy_is_opt_in_and_postfix_counts_as_import_usage(self):
        text = '```agda\n{-# OPTIONS --cubical --safe --guardedness #-}\nopen import A using ( fst )\nx = p .fst\n```'
        self.assertFalse(lint_text(text, AgdaPolicy(postfix_projections=('fst','snd'))))
        self.assertNotIn('postfix-projection', [r for _,r,_ in lint_text(text.replace('p .fst','fst p'))])

    def test_only_canonical_builtin_fields(self):
        self.assertIn('="1"', pair_projection_attribute('Agda.Builtin.Sigma', 'Σ.fst'))
        self.assertIn('="2"', pair_projection_attribute('Agda.Builtin.Sigma', 'snd'))
        self.assertEqual(pair_projection_attribute('User.Pair', 'fst'), '')
        self.assertEqual(pair_projection_attribute('Agda.Builtin.Sigma', 'Σ'), '')

    def test_origin_survives_introductory_forwarding(self):
        bridge = {'by_href': {'Agda.Builtin.Sigma.html#251': ('Intro', '40', 'Field', 'fst')},
                  'inline': {'fst': ('Intro.html#40', 'Field')}}
        semantics = AgdaSemantics(prelude_module='Intro')
        resolve = semantics.inline_reference_resolver({}, 'Later', bridge)
        self.assertIn('data-pair-projection="1"', resolve('.fst', ['.fst'], 0))
        body = '<a href="Agda.Builtin.Sigma.html#251" class="Field">fst</a>'
        result = semantics.rewrite_links(body, {'Intro','Agda.Builtin.Sigma'}, {},
            {'Agda.Builtin.Sigma': {'251': 'Σ.fst'}}, 'Later', bridge)
        self.assertIn('data-pair-projection="1"', result)
        self.assertIn('Intro.html#40', result)

    def test_unknown_inline_field_not_marked(self):
        self.assertNotIn('data-pair-projection', ref_link('Other.html#5','Field','fst'))

    def test_checked_chain_retains_exact_inline_boundary(self):
        source = 'p .fst .snd'
        node = dict(id=1, kind='application', source=source, start=0, end=len(source), type='A')
        self.assertIn(source, inline_notation_expression_index([node]))
        long = {**node, 'source': 'pair .fst .snd', 'end': 14}
        self.assertNotIn(long['source'], inline_notation_expression_index([long]))


if __name__ == '__main__':
    unittest.main()
