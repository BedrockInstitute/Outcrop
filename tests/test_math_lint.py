"""Editorial math review is exact, shared and never self-approving."""
import json
from dataclasses import replace
from pathlib import Path
import shutil
import tempfile
import unittest

from outcrop.core.math_lint import inline_math, approval_records, unapproved_math, temporary_records, paragraph_context
from outcrop.core.prose_lint import ProsePolicy, analyze
from outcrop.site.math_review import math_inventory, inventory_markdown
from outcrop.site.site_config import SiteConfig
from outcrop.site.site_lint import lint_site
from site_test_support import EXAMPLE


class MathReviewTests(unittest.TestCase):
    def test_inline_and_embedded_display_require_review(self):
        text = 'Before $x$ after.\n$$y$$\n\n$$\na + b\n$$\nBefore $$z$$ after.\n'
        self.assertEqual([item.expression for item in inline_math(text)], ['$x$', '$$z$$'])
        self.assertEqual(inline_math(''), [])

    def test_opaque_regions_are_not_prose(self):
        text = ('```agda\nx = "$code$"\n```\n~~~text\n$code$\n~~~\n'
                '`$code$` `` `$code$` ``\n<!-- $comment$ -->\n'
                '<pre>$raw$</pre><code>$raw$</code><script>"$js$"</script>\n'
                '<figure><div>$figure$</div><figcaption>$caption$</figcaption></figure>\n'
                '<span title="$attr$">$visible$</span>\n'
                '[label](https://example.org/$path$) https://example.org/$path$\n'
                'Price \\$5 and \\$6.\n')
        self.assertEqual([item.expression for item in inline_math(text)], ['$visible$'])

    def test_language_context_and_movement(self):
        text = '<!--en-->\nBefore $x$ after.\n<!--zh-->\n这里 $x$。\n<!--/-->\n'
        items = inline_math(text)
        self.assertEqual([item.language for item in items], ['en', 'zh'])
        self.assertEqual([item.line for item in items], [2, 4])
        moved = inline_math('\n\n' + text)
        self.assertEqual([item.fingerprint for item in items], [item.fingerprint for item in moved])
        self.assertNotEqual(items[0].fingerprint, inline_math(text.replace('Before', 'After'))[0].fingerprint)

    def test_approval_is_single_use_and_context_bound(self):
        text = 'Before $x$ after.\n'
        key = inline_math(text)[0].fingerprint
        self.assertEqual(unapproved_math(text, [key]), [])
        self.assertEqual(len(unapproved_math(text * 2, [key])), 1)
        self.assertEqual(len(unapproved_math(text.replace('after', 'again'), [key])), 1)
        record = dict(chapter='Example.md', fingerprint=key, reviewer='Human', reason='Explicit review')
        self.assertEqual(approval_records(dict(version=1, approved=[record])), {'Example.md': {key}})
        for data in [None, {}, dict(version=True, approved=[]),
                     dict(version=1, approved=[record, record]),
                     dict(version=1, approved=[{**record, 'reviewer': ''}]),
                     dict(version=1, approved=[{**record, 'fingerprint': 'M001'}])]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                approval_records(data)

    def test_localized_figure_reference_allows_only_its_paragraph(self):
        for language, phrase in [('en', 'In the figure'), ('zh', '图中的'), ('ja', '図中の')]:
            with self.subTest(language=language):
                text = f'<!--{language}-->\n{phrase} $x$ and $y$,\ncontinued $z$.\n\nOther $a$.\n<!--/-->\n'
                self.assertEqual([item.figure_reference for item in inline_math(text)], [True, True, True, False])
                self.assertEqual([item.expression for item in unapproved_math(text)], ['$a$'])
                policy = ProsePolicy(inline_math_review=True)
                hits = [hit for hit in analyze(text, policy=policy)[2] if 'inline LaTeX' in hit.message]
                self.assertEqual(len(hits), 1)

    def test_figure_reference_wording_is_deliberately_mechanical(self):
        for language, phrase in [('en', 'in the diagram'), ('en', 'in the figures'),
                                 ('en', 'within the figure'), ('zh', '图中'),
                                 ('zh', '如下图'), ('ja', '図の'), ('ja', '図では'),
                                 ('zh', 'in the figure')]:
            with self.subTest(language=language, phrase=phrase):
                self.assertTrue(unapproved_math(f'<!--{language}-->\n{phrase} $x$.\n<!--/-->\n'))
        # Case and source soft wraps do not change the English phrase.
        self.assertEqual(unapproved_math('<!--en-->\nIN THE\nFIGURE $x$.\n<!--/-->\n'), [])
        # Ordinary monolingual Markdown need not add language markers.
        self.assertEqual(unapproved_math('In the figure $x$.\n'), [])

    def test_figure_reference_cannot_leak_across_blocks(self):
        cases = [
            '- In the figure $x$.\n- Other $y$.\n',
            'In the figure $x$.\n\nOther $y$.\n',
            '# In the figure\nOther $y$.\n',
            '<!--en-->\nIn the figure $x$.\n<!--zh-->\n比较 $y$。\n<!--/-->\n',
            'In the figure $x$.\n```agda\nx = y\n```\nOther $y$.\n',
            'In the figure $x$.\n$$z$$\nOther $y$.\n',
            '<figure>In the figure $x$.</figure>\nOther $y$.\n',
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual([item.expression for item in unapproved_math(text)], ['$y$'])

    def test_opaque_text_and_math_cannot_supply_a_figure_reference(self):
        for hidden in ['`in the figure`', '<!--in the figure-->',
                       '<span title="in the figure"></span>',
                       '<code>in the figure</code>',
                       '[link](in the figure)', '$\\text{in the figure}$',
                       'in `ignored` the figure', 'in <!--ignored--> the figure']:
            with self.subTest(hidden=hidden):
                items = inline_math(f'<!--en-->\n{hidden} and $x$.\n<!--/-->\n')
                self.assertTrue(items)
                self.assertFalse(any(item.figure_reference for item in items))

    def test_figure_reference_inventory_is_not_human_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            shutil.copytree(EXAMPLE, root)
            source = root / 'chapters/Sample/Seed.md'
            source.write_text(source.read_text() + '\n<!--en-->\nIn the figure $x$.\n<!--/-->\n')
            config = SiteConfig.load(root / 'project.json', root=root)
            rows = math_inventory(config)
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]['figure_reference'])
            self.assertFalse(rows[0]['approved'])
            self.assertFalse(rows[0]['temporarily_allowed'])
            self.assertIn('Allowed by figure-reference convention', inventory_markdown(rows))
            self.assertFalse(any('inline LaTeX' in hit.message for hit in lint_site(config)))
            source.write_text(source.read_text().replace('In the figure', 'In the diagram'))
            self.assertTrue(any('inline LaTeX' in hit.message for hit in lint_site(config)))

    def test_shared_prose_engine(self):
        text = 'Compare $x$.\n'
        policy = ProsePolicy(chapter='Example.md', inline_math_review=True)
        self.assertTrue(any('inline LaTeX' in item.message for item in analyze(text, policy=policy)[2]))
        policy = replace(policy, math_approvals={'Example.md': {inline_math(text)[0].fingerprint}})
        self.assertFalse(any('inline LaTeX' in item.message for item in analyze(text, policy=policy)[2]))

    def test_temporary_allowance_survives_edits_but_ends_at_human_review(self):
        original = 'Before.\n\nCompare $x$.\n\n```agda\nvalue = zero\n```\n'
        policy = ProsePolicy(chapter='Example.md', inline_math_review=True,
                             math_temporary={'Example.md': True})
        reviewed = replace(policy, math_temporary={'Example.md': False})
        self.assertEqual(unapproved_math(original, temporary_allowed=True), [])
        self.assertFalse(any('inline LaTeX' in hit.message for hit in analyze(original, policy=policy)[2]))
        # Edits, including whole-document replacements, do not end a deferral.
        for edited in (original + '\n', original.replace('Before.', 'After.'),
                       original.replace('zero', 'one'), original.replace('x', 'y'),
                       'Entirely rewritten with $z$.\n'):
            with self.subTest(edited=edited):
                hits = analyze(edited, policy=policy)[2]
                self.assertFalse(any('inline LaTeX' in hit.message for hit in hits))
                hits = analyze(edited, policy=reviewed)[2]
                self.assertTrue(any('human-reviewed; temporary inline-LaTeX allowance expired' in hit.message for hit in hits))
        self.assertTrue(unapproved_math(original, temporary_allowed=False))
        self.assertTrue(unapproved_math(original, temporary_allowed='false'))
        renamed = replace(policy, chapter='Other.md')
        self.assertTrue(any('inline LaTeX' in hit.message for hit in analyze(original, policy=renamed)[2]))
        fixed = original.replace('$x$', '`x`{.Agda}')
        self.assertFalse(any('inline LaTeX' in hit.message for hit in analyze(fixed, policy=reviewed)[2]))

    def test_temporary_registry_is_explicit_and_validated(self):
        record = dict(chapter='Example.md', until='human_reviewed',
                      reviewer='Human', reason='Explicit deferral')
        data = dict(version=1, approved=[], temporary=[record])
        self.assertEqual(temporary_records(data), {'Example.md'})
        self.assertEqual(approval_records(data), {})
        for records in (None, {}, [record, record], [{**record, 'source_sha256': 'a' * 64}],
                        [{**record, 'until': 'edited'}],
                        [{**record, 'reviewer': ''}], [dict(chapter='Example.md')]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                temporary_records({**data, 'temporary': records})

    def test_site_temporary_allowance_and_inventory_are_not_permanent_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            shutil.copytree(EXAMPLE, root)
            source = root / 'chapters/Sample/Seed.md'
            original = source.read_text() + '\n<!--en-->\nCompare $x$.\n<!--/-->\n'
            source.write_text(original)
            (root / 'review.json').write_text(json.dumps(dict(version=1, approved=[], temporary=[dict(
                chapter='Sample/Seed.md', until='human_reviewed',
                reviewer='Human', reason='Explicit deferral')])))
            config = SiteConfig.load(root / 'project.json', root=root).with_overrides(inline_math_approvals='review.json')
            catalog_path = config.path(config.catalog)
            catalog = json.loads(catalog_path.read_text())
            entry = next(item for item in catalog['chapters'] if item['id'] == 'Sample.Seed')
            entry['human_reviewed'] = False
            catalog_path.write_text(json.dumps(catalog))
            self.assertFalse(any('inline LaTeX' in hit.message for hit in lint_site(config)))
            rows = math_inventory(config)
            self.assertFalse(rows[0]['approved'])
            self.assertTrue(rows[0]['temporarily_allowed'])
            self.assertIn('Temporarily allowed until this chapter is human-reviewed', inventory_markdown(rows))
            source.write_text(original.replace('$x$', '$y$') + '\n')
            self.assertFalse(any('inline LaTeX' in hit.message for hit in lint_site(config)))
            self.assertTrue(math_inventory(config)[0]['temporarily_allowed'])
            entry['human_reviewed'] = True
            catalog_path.write_text(json.dumps(catalog))
            self.assertTrue(any('allowance expired' in hit.message for hit in lint_site(config)))
            rows = math_inventory(config)
            self.assertFalse(rows[0]['temporarily_allowed'])
            self.assertTrue(rows[0]['temporary_expired'])
            self.assertIn('Temporary allowance expired', inventory_markdown(rows))
            source.write_text(original.replace('$x$', '`x`{.Agda}'))
            self.assertFalse(any('inline LaTeX' in hit.message for hit in lint_site(config)))
            # The absence of a review state must not silently grant an exception.
            del entry['human_reviewed']
            catalog_path.write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError, 'human_reviewed'):
                math_inventory(config)

    def test_site_inventory_and_gate_share_explicit_decisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            shutil.copytree(EXAMPLE, root)
            source = root / 'chapters/Sample/Seed.md'
            source.write_text(source.read_text() + '\n<!--en-->\nCompare $x$.\n<!--/-->\n')
            config = SiteConfig.load(root / 'project.json', root=root)
            rows = math_inventory(config)
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0]['approved'])
            self.assertIn('Pending human review', inventory_markdown(rows))
            self.assertTrue(any('inline LaTeX' in item.message for item in lint_site(config)))
            registry = root / 'math-approvals.json'
            registry.write_text(json.dumps(dict(version=1, approved=[dict(
                chapter=rows[0]['chapter'], fingerprint=rows[0]['fingerprint'],
                reviewer='Human', reason='Explicit fixture approval')])))
            config = config.with_overrides(inline_math_approvals='math-approvals.json')
            self.assertTrue(math_inventory(config)[0]['approved'])
            self.assertFalse(any('inline LaTeX' in item.message for item in lint_site(config)))
            source.write_text(source.read_text().replace('Compare $x$', 'Compare $y$'))
            self.assertFalse(math_inventory(config)[0]['approved'])
            self.assertTrue(any('inline LaTeX' in item.message for item in lint_site(config)))

    def test_configuration_rejects_invalid_policy_and_paths(self):
        config = SiteConfig.load(EXAMPLE / 'project.json', root=EXAMPLE)
        for overrides in [dict(inline_math_approvals='../approvals.json'),
                          dict(policies={'inline_math_review': 'yes'})]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                config.with_overrides(**overrides)

    def test_review_groups_formulas_by_paragraph_without_granting_approval(self):
        text = ('<!--en-->\nBefore $x$ and $y$,\ncontinued with $z$.\n\n'
                '- First $a$\n  and $b$.\n- Second $c$.\n'
                '<!--zh-->\n比较 $x$ 和 $y$。\n<!--/-->\n')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            shutil.copytree(EXAMPLE, root)
            source = root / 'chapters/Sample/Seed.md'
            source.write_text(text)
            config = SiteConfig.load(root / 'project.json', root=root)
            rows = math_inventory(config)
            self.assertEqual(len(rows), 8)
            self.assertEqual([row['paragraph_line'] for row in rows], [2, 2, 2, 5, 5, 7, 9, 9])
            report = inventory_markdown(rows)
            self.assertIn('4 paragraphs containing 8 inline LaTeX occurrences', report)
            self.assertEqual(report.count('## M'), 4)
            self.assertEqual(report.count('Pending human review.'), 4)
            self.assertEqual(report.count('Before $x$ and $y$,'), 1)
            self.assertIn('$x$\n$y$\n$z$', report)
            for row in rows:
                self.assertIn(row['fingerprint'], report)
            rows[0]['approved'] = True
            self.assertEqual(inventory_markdown(rows).count('Pending human review.'), 4)

    def test_paragraph_context_stops_at_heading_and_language_markers(self):
        lines = '# Heading\nBefore $x$\nand $y$.\n<!--zh-->\n中文 $z$。\n'.splitlines(keepends=True)
        self.assertEqual(paragraph_context(lines, 3, 3), (2, 'Before $x$\nand $y$.'))
        self.assertEqual(paragraph_context(lines, 5, 5), (5, '中文 $z$。'))


if __name__ == '__main__':
    unittest.main()
