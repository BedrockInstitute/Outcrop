import unittest

from outcrop.core.agda_lint import AgdaPolicy, fixity_order_findings, lint_text


def book(code):
    return '```agda\nmodule Test where\n' + code + '\n```\n'


class FixityOrderTests(unittest.TestCase):
    def test_late_signature_and_group(self):
        findings = fixity_order_findings(book('_+_ _*_ : A\ninfixl 6 _+_ _*_'))
        self.assertEqual(len(findings), 2)
        self.assertTrue(all(f[1] == 'fixity-order' for f in findings))

    def test_separated_fences_are_one_stream(self):
        self.assertFalse(fixity_order_findings(book('infixr 6 _+_\n```\nProse\n```agda\n_+_ : A')))
        self.assertTrue(fixity_order_findings(book('_+_ : A\n```\nProse\n```agda\ninfix 6 _+_')))

    def test_namespaces_and_multiline_record(self):
        self.assertFalse(fixity_order_findings(book('module A where\n  _+_ : T\nmodule B where\n  infix 6 _+_\n  _+_ : T')))
        self.assertFalse(fixity_order_findings(book('_+_ : T\nrecord R\n  : Set where\n  infix 6 _+_\n  field\n    _+_ : T')))
        self.assertTrue(fixity_order_findings(book('record R\n  : Set where\n  field\n    _+_ : T\n  infix 6 _+_')))

    def test_data_mutual_private_and_local(self):
        self.assertTrue(fixity_order_findings(book('mutual\n  data D : Set where\n    _+_ : D\ninfix 6 _+_')))
        self.assertTrue(fixity_order_findings(book('private\n  _+_ : T\ninfix 6 _+_')))
        self.assertFalse(fixity_order_findings(book('f = x\n  where\n  _+_ : T\ninfix 6 _+_\n_+_ : T')))

    def test_comments_strings_and_signatureless_equations(self):
        self.assertFalse(fixity_order_findings(book('-- _+_ : T\nx = "_+_ : T"\ninfix 6 _+_\n_+_ : T')))
        self.assertTrue(fixity_order_findings(book('x + y = x\ninfix 6 _+_')))

    def test_opt_in(self):
        text = book('_+_ : T\ninfix 6 _+_')
        self.assertFalse(any(f[1] == 'fixity-order' for f in lint_text(text)))
        self.assertTrue(any(f[1] == 'fixity-order' for f in lint_text(
            text, AgdaPolicy(fixity_before_definition=True))))


if __name__ == '__main__':
    unittest.main()
