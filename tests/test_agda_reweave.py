"""Compiler evidence may move with prose, but must never be invented."""
import hashlib
import unittest

from outcrop.adapters.agda.reweave import (
    CodeRelocation, rebase_hrefs, rebase_pres, rebase_trace, split_highlighted,
)


class AgdaReweaveTests(unittest.TestCase):
    def test_unicode_offsets_and_endpoints_survive_fence_split(self):
        # The old stream starts at 11 and the new second line starts at 35.
        moved = CodeRelocation(((11, 17),), ((21, 24), (35, 38)))
        self.assertEqual(moved.point(11), 21)
        self.assertEqual(moved.point(15), 36)
        self.assertEqual(moved.end(17), 38)
        with self.assertRaises(ValueError):
            moved.point(18)

    def test_repartition_preserves_token_markup_and_rebases_inbound_links(self):
        old = '<pre class="Agda"><a id="11" href="Sample.html#14">x</a> = 1\n' \
              '<a id="17">y</a> = 2\n</pre>'
        first, second = 'x = 1\n', 'y = 2\n'
        moved = CodeRelocation(((11, 23),), ((21, 27), (41, 47)))
        parts = rebase_pres(old, ((11, 23),),
                           [hashlib.sha256((first + second).encode()).hexdigest()],
                           [first, second], moved)
        self.assertEqual(len(parts), 2)
        self.assertIn('id="21"', parts[0])
        self.assertIn('id="41"', parts[1])
        self.assertEqual(rebase_hrefs('<a href="Sample.html#17">y</a> '
                                           '<a href="https://example.com/Sample.html#17">remote</a>',
                                           {'Sample': moved}),
                         '<a href="Sample.html#41">y</a> '
                         '<a href="https://example.com/Sample.html#17">remote</a>')

    def test_rejects_changed_code_or_a_boundary_inside_a_token(self):
        moved = CodeRelocation(((11, 17),), ((21, 24), (35, 38)))
        old = '<pre class="Agda"><a id="11">abcdef</a></pre>'
        with self.assertRaises(ValueError):
            rebase_pres(old, ((11, 17),), ['wrong'], ['abc', 'def'], moved)
        with self.assertRaises(ValueError):
            split_highlighted('<a id="11">abcdef</a>', ['abc', 'def'])

    def test_cannot_map_a_prose_position(self):
        moved = CodeRelocation(((11, 17),), ((21, 27),))
        with self.assertRaises(ValueError):
            rebase_hrefs('<a href="Sample.html#9">unknown</a>', {'Sample': moved})

    def test_trace_rebases_only_matching_source_runs(self):
        moved = CodeRelocation(((11, 17),), ((21, 27),))
        old = ('{"path":"/src/Sample.lagda.md","start":11,"end":17,'
               '"sourceHash":"old","kind":"definition-end"}\n'
               '{"path":"/src/Sample.lagda.md","start":11,"end":17,'
               '"sourceHash":"older","kind":"definition-end"}\n')
        actual = rebase_trace(old, {'/src/Sample.lagda.md': (moved, 'old', 'new')})
        self.assertIn('"start":21,"end":27,"sourceHash":"new"', actual)
        self.assertIn('"start":11,"end":17,"sourceHash":"older"', actual)


if __name__ == '__main__':
    unittest.main()
