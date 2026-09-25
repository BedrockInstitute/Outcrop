"""Focused tests for prose conventions enforced by lint-prose.py."""

import unittest
from outcrop.core import prose_lint as prose_rules


class InlineAgdaTests(unittest.TestCase):
    def test_standalone_link_and_complete_expression(self):
        text = ('[refl](Cubical.Foundations.Prelude.html#123){.Agda} '
                'and `f x ≡ g x`{.Agda}\n')
        self.assertEqual(prose_rules.inline_agda_violations(text), [])

    def test_split_expressions_and_unboxed_table_notation(self):
        text = ('[refl x](Cubical.Foundations.Prelude.html#123){.Agda}\n'
                '`f x`{.Agda} ≡ `g x`{.Agda}\n'
                '| ∥ B x ∥₁ | explanation |\n')
        self.assertGreaterEqual(len(prose_rules.inline_agda_violations(text)), 3)

    def test_milestones_has_no_exemption(self):
        text = '[LEM x](Base.Classical.html#123){.Agda}\n'
        self.assertTrue(prose_rules.analyze(text, policy=prose_rules.ProsePolicy(chapter='Preview.md'))[2])

    def test_plain_variables_are_caught_in_refined_chapters(self):
        text = ('If f x ≡ g x, then f ≡ g.\n'
                '对 A 中的元素。\n'
                'A type is given.\n'
                'For `x`{.Agda}, [V](V.Hierarchy.html#𝒮ᵥ){.Agda} is named.\n'
                '```agda\nf x = x\n```\n')
        hits = prose_rules.bare_variable_violations(text)
        self.assertEqual({text[hit.index] for hit in hits}, {'f', 'x', 'g', 'A'})

    def test_later_chapter_new_prose_is_checked_too(self):
        text = '对 x 中的元素。\n'
        hits = prose_rules.analyze(text, policy=prose_rules.ProsePolicy(chapter='Later.md'))[2]
        self.assertTrue(any('bare Agda variable' in hit.message for hit in hits))



class TheoremLabelTests(unittest.TestCase):
    def violations(self, text):
        return prose_rules.theorem_label_violations(text)

    def test_named_statements_and_proofs_accept_canonical_format(self):
        valid = "\n".join([
            "**Lemma** (`helper`{.Agda}) Text.",
            "**引理** (`helper`{.Agda}) 正文。",
            "**補題** (`helper`{.Agda}) 本文。",
            "**Fact** (`property`{.Agda}) Text.",
            "**事实** (`property`{.Agda}) 正文。",
            "**事実** (`property`{.Agda}) 本文。",
            "**Theorem** (`result`{.Agda}) Text.",
            "**定理** (`result`{.Agda}) 正文。",
            "**Corollary** (`consequence`{.Agda}) Text.",
            "**推论** (`consequence`{.Agda}) 正文。",
            "**系** (`consequence`{.Agda}) 本文。",
            "**Proof** Text.",
            "**证明** 正文。",
            "**証明** 本文。",
        ])
        self.assertEqual(self.violations(valid), [])

    def test_period_and_missing_statement_name_are_rejected(self):
        invalid = "\n".join([
            "**Lemma.** Text.",
            "**定理。**正文。",
            "**Theorem** Text.",
            "**证明。**正文。",
        ])
        self.assertEqual(len(self.violations(invalid)), 4)

    def test_numbered_statement_cannot_bypass_the_rule(self):
        self.assertTrue(self.violations("**Theorem 1.** Text."))
        self.assertTrue(prose_rules.statement_violations("**Theorem 1.** Text."))

    def test_numbered_registry_labels_are_scoped_and_still_require_code(self):
        text = '**Theorem 0** Text.\n\n```agda\nopen import Base.Choice public using ( SetChoice→LEM )\n```\n\n'
        self.assertEqual(prose_rules.theorem_label_violations(text, numbered_theorems=range(5)), [])
        self.assertTrue(prose_rules.theorem_label_violations(text))
        self.assertEqual(prose_rules.statement_violations(text), [])
        self.assertTrue(prose_rules.statement_violations(text.replace('```agda', '```text')))
        self.assertTrue(prose_rules.theorem_label_violations(text.replace('Theorem', 'Lemma'), numbered_theorems=range(5)))

    def test_labels_inside_agda_fences_are_ignored(self):
        self.assertEqual(self.violations("```agda\n**Lemma.**\n```"), [])


class StatementCodeTests(unittest.TestCase):
    def test_labels_keep_code_requirement_without_authored_end_mark(self):
        for label in ('Definition', '定义', '定義', 'Proof', '证明', '証明', 'Fact', 'Corollary'):
            prefix = f'**{label}** (`x`{{.Agda}}) Text.\n'
            self.assertTrue(prose_rules.statement_violations(prefix))
            self.assertTrue(prose_rules.statement_violations(prefix + '```agda\n\n```\n'))
            self.assertEqual(prose_rules.statement_violations(prefix + '```agda\nx = y\n```\n'), [])

    def test_nested_and_adjacent_statements_close_structurally(self):
        text = '**Theorem** (`result`{.Agda}) Text.\n```agda\nresult = helper\n```\n'
        nested = '<details>\n**Lemma** (`helper`{.Agda}) Text.\n```agda\nhelper = proof\n```\n</details>\n'
        following = '**Fact** (`next`{.Agda}) Text.\n```agda\nnext = result\n```\n'
        self.assertEqual(prose_rules.statement_violations(text + nested + following), [])
        self.assertTrue(prose_rules.statement_violations(text + nested.replace('```agda\nhelper = proof\n```\n', '') + following))

    def test_proof_requires_its_own_code_and_may_have_following_exposition(self):
        text = '**Lemma** (`x`{.Agda}) Text.\n```agda\nx : Set\n```\n**Proof** Explanation.\n'
        self.assertTrue(prose_rules.statement_violations(text))
        self.assertEqual(prose_rules.statement_violations(text + '```agda\nx = y\n```\nMore explanation.\n'), [])

    def test_empty_parallel_statements_and_non_agda_code_remain_errors(self):
        text = '**Construction** (`x`{.Agda}) First.\n**Construction** (`y`{.Agda}) Second.\n```agda\nx = y\n```\n'
        self.assertTrue(prose_rules.statement_violations(text))
        self.assertTrue(prose_rules.statement_violations('**Proof** Text.\n```text\nx = y\n```\n'))

    def test_all_language_routes_and_heading_boundaries_are_checked(self):
        text = '<!--en-->\n**Definition** (`x`{.Agda}) Text.\n<!--zh-->\n**定义** (`x`{.Agda}) 正文。\n**定义** (`y`{.Agda}) 多余。\n<!--ja-->\n**定義** (`x`{.Agda}) 本文。\n<!--/-->\n```agda\nx = y\n```\n'
        self.assertTrue(prose_rules.statement_violations(text))
        self.assertTrue(prose_rules.statement_violations('**Proof** Text.\n## Next\n```agda\nx = y\n```\n'))

    def test_grouped_construction_has_named_bullets(self):
        prefix = '**Construction** (`x`{.Agda} `y`{.Agda})\n\n'
        bullets = '- `x`{.Agda} First.\n- `y`{.Agda} Second.\n'
        self.assertEqual(prose_rules.theorem_label_violations(prefix + bullets), [])
        self.assertTrue(prose_rules.theorem_label_violations(prefix))
        self.assertTrue(prose_rules.theorem_label_violations((prefix + bullets).replace('Construction', 'Lemma')))
        self.assertTrue(prose_rules.theorem_label_violations(prefix + bullets.replace('- `y`', '- `z`')))



class SubmoduleFoldTests(unittest.TestCase):
    VALID = '''<details open class="submodule-fold">
<summary class="submodule-fold-heading">
```agda
module Helper where
```
</summary>
<div class="submodule-fold-content">
<!--en-->
The helper supplies a value.
<!--zh-->
辅助模块给出一个值。
<!--ja-->
補助モジュールが値を与える。
<!--/-->
```agda
  value = result
```
</div>
</details>
```agda
result = Helper.value
```
'''

    def test_valid_fold_and_scope(self):
        self.assertEqual(prose_rules.submodule_fold_violations(self.VALID), [])

    def test_private_module_modifier_stays_with_its_declaration(self):
        text = ('```agda\nmodule Example where\n```\n\n' + self.VALID
                .replace('module Helper where', 'private module Helper where'))
        self.assertEqual(prose_rules.submodule_fold_violations(text, check_all=True), [])
        self.assertTrue(prose_rules.submodule_fold_violations(
            text.replace('  value = result', 'value = result'), check_all=True))
        self.assertTrue(prose_rules.submodule_fold_violations(
            text.replace('private module', 'private\n  module'), check_all=True))

    def test_multiline_declaration_is_allowed_but_body_code_is_not(self):
        text = self.VALID.replace('module Helper where\n', 'module Helper\n  where\n')
        self.assertEqual(prose_rules.submodule_fold_violations(text), [])
        text = self.VALID.replace('module Helper where\n', 'module Helper where\n  value = result\n')
        self.assertTrue(prose_rules.submodule_fold_violations(text))
        text = self.VALID.replace('module Helper where\n',
                                  'module Helper where\n  module Extra where\n')
        self.assertTrue(prose_rules.submodule_fold_violations(text, check_all=True))

    def test_default_open_and_complete_body_are_required(self):
        self.assertTrue(prose_rules.submodule_fold_violations(
            self.VALID.replace('<details open class=', '<details class=')))
        self.assertTrue(prose_rules.submodule_fold_violations(
            self.VALID.replace('</div>\n</details>', 'More prose.\n</div>\n</details>')))
        self.assertTrue(prose_rules.submodule_fold_violations(
            self.VALID.replace('result = Helper.value', '  more = value')))

    def test_old_optional_style_is_rejected(self):
        self.assertTrue(prose_rules.submodule_fold_violations(
            '<details open class="optional-reading">'))

    def test_fold_after_code_needs_a_blank_line_for_markdown(self):
        text = '```agda\nprior = value\n```\n' + self.VALID
        self.assertTrue(any('blank line' in hit.message
                            for hit in prose_rules.submodule_fold_violations(text)))

    def test_one_nested_submodule_with_figure_div_is_valid(self):
        nested = '''<details open class="submodule-fold">
<summary class="submodule-fold-heading">
```agda
module Outer where
```
</summary>
<div class="submodule-fold-content">
```agda
  outer = value
```
<figure><div class="diagram-framed"><div>picture</div></div></figure>
<details open class="submodule-fold">
<summary class="submodule-fold-heading">
```agda
  module Inner where
```
</summary>
<div class="submodule-fold-content">
```agda
    inner = outer
```
</div>
</details>
```agda
  after = Inner.inner
```
</div>
</details>
```agda
result = Outer.after
```
'''
        self.assertEqual(prose_rules.submodule_fold_violations(nested), [])

    def test_third_submodule_fold_level_is_rejected(self):
        third = '''<details open class="submodule-fold">
<summary class="submodule-fold-heading">
```agda
    module Deep where
```
</summary>
<div class="submodule-fold-content">
```agda
      value = result
```
</div>
</details>
'''
        nested = self.VALID.replace('```agda\n  value = result\n```',
            '''<details open class="submodule-fold">
<summary class="submodule-fold-heading">
```agda
  module Inner where
```
</summary>
<div class="submodule-fold-content">
''' + third + '''
</div>
</details>''')
        hits = prose_rules.submodule_fold_violations(nested)
        self.assertTrue(any('maximum depth 2' in hit.message for hit in hits))


class JapanesePlainStyleTests(unittest.TestCase):
    def violations(self, text):
        return prose_rules.japanese_polite_violations(text)

    def test_polite_forms_in_japanese_prose_are_rejected(self):
        text = """<!--ja-->
これは命題です。写像を返しますが、まだ終わりません。
<!--/-->
"""
        self.assertEqual(len(self.violations(text)), 3)

    def test_plain_style_and_lexical_masumasu_are_accepted(self):
        text = """<!--ja-->
これは命題である。包んですぐ戻る。段階ですでに成立する。これですべてである。これはますます重要である。
<!--/-->
"""
        self.assertEqual(self.violations(text), [])

    def test_polite_forms_before_connectives_are_rejected(self):
        text = """<!--ja-->
これは命題ですが、証明は後である。値を返しますので、場合分けできる。
<!--/-->
"""
        self.assertEqual(len(self.violations(text)), 2)

    def test_other_languages_and_protected_regions_are_ignored(self):
        text = """<!--en-->
です ます
<!--ja-->
`です` [参照](https://example.test/ます) <span title="です">常体である。</span>
```text
これは例です。
```
<!--/-->
"""
        self.assertEqual(self.violations(text), [])


if __name__ == "__main__":
    unittest.main()
