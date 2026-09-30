"""Source notation checks must distinguish applications from operator values."""
import unittest

from outcrop.core.agda_lint import AgdaPolicy, infix_application_findings, lint_text


class InfixApplicationTests(unittest.TestCase):
    def check(self, code):
        return infix_application_findings('```agda\n' + code + '\n```')

    def test_reported_record_projection_regression(self):
        self.assertEqual(len(self.check('f = λ a b → _≈ˢ_ 𝒮 (a .fst) (b .fst)')), 1)
        text = '`_≈ˢ_ 𝒮 (a .fst) (b .fst)`{.Agda} and `_∈ˢ_ 𝒮 (a .fst) (b .fst)`{.Agda}'
        self.assertEqual(len(infix_application_findings(text)), 2)

    def test_nested_qualified_and_parenthesized_heads(self):
        for value in ('_+_ x y', 'M._+_ x y', '(_+_) x y',
                      'f (_+_ x y)', 'p ≡ M._+_ x y', '⟨ M._∈_ x y ⟩',
                      '_≡_ {A = T} x y'):
            self.assertTrue(self.check('f = ' + value), value)

    def test_values_sections_declarations_and_infix_remain_legal(self):
        code = '''open import M using ( _+_; _∈_ )
infix 20 _+_ _∈_
_+_ : A → A → A
_+_ x y = combine x y
f = cong₂ _+_ p q
g = cong₂ (_+_) p q
h = WellFounded _∈_
i = Acc (_≺_ {k} {k}) r
j = (x ∈_)
k = x + y
l = bqCase ∀̇∈ _⇒̇_ t
m = apply ⟪ A ⟫ _∈_ wf
n = _+_
next = x
-- _+_ x y
text = "_+_ x y"
{- _+_ x y -}'''
        self.assertFalse(self.check(code))

    def test_continuation_and_split_fences(self):
        text = '```agda\nf =\n```\nText\n```agda\n  _+_ x\n    y\n```'
        self.assertEqual(infix_application_findings(text)[0][:2], (6, 'infix-application'))
        self.assertFalse(self.check('f = apply\n  _+_ x y'))

    def test_inline_name_is_not_an_application(self):
        self.assertFalse(infix_application_findings('`_+_`{.Agda} and `cong₂ _+_ p q`{.Agda}'))
        self.assertEqual(len(infix_application_findings('<code>`_+_ x y`{.Agda}</code>')), 1)

    def test_policy_is_opt_in(self):
        source = '```agda\nf = _+_ x y\n```'
        self.assertNotIn('infix-application', [rule for _, rule, _ in lint_text(source)])
        self.assertIn('infix-application', [rule for _, rule, _ in lint_text(
            source, AgdaPolicy(infix_applications=True))])
