"""Closed-vector evidence must not be inferred from cons spelling alone."""
import unittest

from outcrop.core import MarkdownDocument, CodeContext
from outcrop.core.vector_notation import vector_items, vector_attributes, cons_root
from outcrop.core.agda_semantics import (
    AgdaSemantics, _expression_opening, inline_notation_expression_index, decorate_type_nodes,
    qualified_name_pattern,
    annotate_inline_notation_expressions,
)


class VectorNotationTests(unittest.TestCase):
    def test_inline_candidates_need_no_invented_type_or_ast(self):
        for source in ('x ∷ y ∷ []', '(x ∷ y ∷ [])', 'f (x ∷ y ∷ [])'):
            body = annotate_inline_notation_expressions(source, [])
            self.assertIn('data-vector-inline="true"', body)
            self.assertIn('data-vector-items=', body)
            self.assertNotIn('data-vector-type=', body)
            self.assertNotIn('expr-node', body)
        body = annotate_inline_notation_expressions('γ = a ∷ []', [])
        self.assertTrue(body.startswith('γ = <span'))
        self.assertNotIn('data-vector-items=', annotate_inline_notation_expressions('"x ∷ []"', []))
        body = annotate_inline_notation_expressions('x ∷ y ∷ []', [self.node('x ∷ y ∷ []')])
        self.assertEqual(body.count('data-vector-candidate='), 1)
        self.assertIn('data-vector-checked=', body)

    def test_untyped_inline_and_display_publish_candidate(self):
        for source in ('`x ∷ y ∷ []`{.Agda}',
                       '<div class="single-line-code"><code>`(x ∷ y ∷ [])`{.Agda}</code></div>'):
            result = MarkdownDocument(source).render('en')
            self.assertIn('data-vector-items=', result.body)
            self.assertIn('data-vector-inline="true"', result.body)
            self.assertNotIn('data-vector-type=', result.body)

    def node(self, source='a ∷ b ∷ []', **extra):
        return dict(kind='application', source=source, start=0, end=len(source),
                    id=1, type='Vec A 2', **extra)

    def test_short_closed_entries(self):
        self.assertEqual(vector_items('a ∷ []'), ['a'])
        self.assertEqual(vector_items('a ∷ b ∷ c ∷ []'), ['a', 'b', 'c'])
        self.assertEqual(vector_items('𝒮 ∷ x̂ ∷ 2 ∷ []'), ['𝒮', 'x̂', '2'])
        self.assertEqual(vector_items('[] ∷ []'), ['[]'])
        for source in ('[]', 'a ∷ xs', 'a ∷', 'f a ∷ []',
                       'a ∷ (b ∷ [])', 'a ∷\n b ∷ []', 'a ∷ [] trailing',
                       'a' * 49 + ' ∷ []', 'a ∷ [ b ]', '_ ∷ []'):
            with self.subTest(source=source):
                self.assertIsNone(vector_items(source))

    def test_grouped_elements_and_nested_vectors(self):
        for item in ('(suc n)', '(p .fst)', '(p .fst .snd)', '(a ∷ b ∷ [])', '(f a)'):
            self.assertEqual(vector_items(item + ' ∷ []'), [item])
        self.assertEqual(vector_items('(a ∷ []) ∷ (b ∷ []) ∷ []'), ['(a ∷ [])', '(b ∷ [])'])
        for source in ('(a ∷ [] ∷ []', '(a) (b) ∷ []', '(a] ∷ []', '() ∷ []'):
            self.assertIsNone(vector_items(source))
        body = annotate_inline_notation_expressions('(a ∷ []) ∷ (b ∷ []) ∷ []', [])
        self.assertEqual(body.count('data-vector-items='), 3)
        self.assertNotIn('expr-node', body)

    def test_singleton_in_prose_syntax_components(self):
        for source in ('a ∷ []', 'γ = a ∷ []', 'a ∷ [] : Vec A 1',
                       'λ a → a ∷ []', '(γ = a ∷ [])', 'γ = (a ∷ [])'):
            body = annotate_inline_notation_expressions(source, [])
            self.assertEqual(body.count('data-vector-items='), 1, source)
            self.assertIn('data-vector-items="[&quot;a&quot;]"', body)
            self.assertNotIn('expr-node', body)
        for source in ('"γ = a ∷ []"', 'γ = f a ∷ []', 'a ∷ tail', 'γ = a ∷ xs'):
            self.assertNotIn('data-vector-items=', annotate_inline_notation_expressions(source, []))

    def test_only_outer_cons_suppresses_a_suffix(self):
        for source in ('a ∷ xs', '(f a) ∷ b ∷ []', 'a ∷'):
            self.assertTrue(cons_root(source))
        for source in ('f (a ∷ [])', 'f "a ∷ []"', 'a∷b', '(a ∷ [])'):
            self.assertFalse(cons_root(source))

    def test_pattern_and_partial_terms_have_no_renderable_metadata(self):
        for node in (self.node(context='pattern'), self.node('a ∷ xs')):
            self.assertEqual(vector_attributes(node), ' data-vector-candidate="true"')
        self.assertNotIn('data-vector-', _expression_opening(self.node('f (a ∷ [])'), 0))
        opening = _expression_opening(self.node(), 0)
        self.assertIn('data-vector-type="Vec A 2"', opening)
        self.assertIn('data-vector-items=', opening)

    def test_inline_evidence_requires_unanimous_types(self):
        node = self.node()
        self.assertIn(node['source'], inline_notation_expression_index([node]))
        other = {**node, 'type': 'List A', 'start': 20, 'end': 20 + len(node['source'])}
        self.assertNotIn(node['source'], inline_notation_expression_index([node, other]))

    def test_hover_surface_retains_same_metadata(self):
        body = decorate_type_nodes('a ∷ b ∷ []', [self.node()], 'Example')
        self.assertIn('data-vector-items=', body)
        self.assertIn('data-expression-type="Example#1"', body)

    def test_inline_ineligible_outer_root_remains_a_suffix_barrier(self):
        outer = self.node('f x ∷ a ∷ b ∷ []')
        inner = {**self.node(), 'id': 2, 'start': 6, 'end': 16}
        index = inline_notation_expression_index([outer, inner])
        self.assertEqual(len(index[outer['source']]), 2)
        self.assertNotIn('data-vector-items=', vector_attributes(index[outer['source']][0]))

    def test_authored_type_and_constructor_identity(self):
        code = CodeContext(names={'Example': {'Vec': '1', 'Vec.[]': '2', 'Vec._∷_': '3'},
                                  'Other': {'List': '11', 'List.[]': '12', 'List._∷_': '13'}})
        for family, expected in [('Vec A 2', 'Example.html#3'), ('List A', 'Other.html#13')]:
            source = '`a ∷ b ∷ []`{.Agda type="' + family + '"}'
            result = MarkdownDocument(source, code=code).render('en')
            self.assertIn('href="' + expected + '"', result.body)
            self.assertIn('data-constructor-family="' + ('Example.Vec' if family.startswith('Vec') else 'Other.List') + '"', result.body)
            self.assertIn('data-vector-items=', result.body)
            self.assertIn('`a ∷ b ∷ []`', result.mirror)
        result = MarkdownDocument('`a ∷ []`{.Agda type="Vec A 1"}').render('en')
        self.assertNotIn('href=', result.body)
        self.assertIn('data-vector-type=', result.body)  # author assertion, not a guessed link
        result = MarkdownDocument('`((a ∷ []))`{.Agda type="Vec A 1"}', code=code).render('en')
        self.assertIn('data-vector-items=', result.body)
        self.assertIn('((a ', result.body)

    def test_resolved_untyped_inline_survives_real_link_pipeline(self):
        code = CodeContext(rendered={'Example'}, canonical_names={'Example': {'3': 'Vec._∷_'}},
                           types={'Example': {'3': 'A → Vec A n → Vec A (suc n)'}})
        source = '<pre class="Agda"><a href="Example.html#3" class="InductiveConstructor">∷</a></pre>\n\n`(x ∷ y ∷ [])`{.Agda}'
        result = MarkdownDocument(source, code=code).render('en')
        self.assertIn('data-vector-inline="true"', result.body)
        self.assertEqual(result.body.count('data-constructor-family="Example.Vec"'), 3)

    def test_forwarded_constructor_retains_declaring_datatype(self):
        semantics = AgdaSemantics()
        source = '<a href="Example.html#2" class="InductiveConstructor">∷</a>'
        body = semantics.rewrite_links(source, {'Example', 'Intro'},
            {'Intro': {'9': 'A → Vec A n → Vec A (suc n)'}},
            {'Example': {'2': 'Vec._∷_'}}, current_module='Chapter',
            prelude_reexports={'by_href': {'Example.html#2': ('Intro', '9', 'InductiveConstructor', '_∷_')}})
        self.assertIn('data-constructor-family="Example.Vec"', body)
        self.assertIn('data-type="Intro#9"', body)

    def test_type_popup_constructor_retains_same_family(self):
        names = {'Example.Vec._∷_': ('Example', '2')}
        body = AgdaSemantics().render_type('Example.Vec._∷_', names, qualified_name_pattern(names),
            pos_aspect={'Example': {'2': 'InductiveConstructor'}})
        self.assertIn('data-constructor-family="Example.Vec"', body)
