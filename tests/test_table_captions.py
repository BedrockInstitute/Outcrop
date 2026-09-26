"""Pipe-table captions are rendered and required by the shared prose gate."""

import unittest

from outcrop.core.i18n_markers import weave_for_site
from outcrop.core.markdown_core import anchor_prose_blocks, md_to_html
from outcrop.core.prose_lint import analyze
from outcrop.core.table_style import missing_table_captions


class TableCaptionTests(unittest.TestCase):
    TABLE = "| Name | Meaning |\n| --- | --- |\n| `x` | one |\n"

    def test_caption_is_below_scroll_region_and_renders_inline_markdown(self):
        body, _ = md_to_html(self.TABLE + ": Describes `x` and <y>.\n\nAfter.")
        self.assertIn('<figure class="prose-table"><div class="prose-table-scroll"><table>', body)
        self.assertIn('</table></div><figcaption>Describes <code>x</code> and &lt;y&gt;.</figcaption></figure>', body)
        self.assertLess(body.index('</table>'), body.index('<figcaption>'))
        self.assertIn('<p>After.</p>', body)
        anchored = anchor_prose_blocks(body)
        self.assertEqual(anchored.count('id="p-'), 2)  # table, then paragraph

    def test_lint_rejects_missing_blank_and_displaced_captions(self):
        self.assertEqual(list(missing_table_captions(self.TABLE + ": A caption.\n")), [])
        for suffix in ("", "\n: Too far away.\n", ":    \n"):
            with self.subTest(suffix=suffix):
                self.assertEqual(list(missing_table_captions(self.TABLE + suffix)), [0])
                _, _, manual = analyze(self.TABLE + suffix)
                self.assertTrue(any("table needs" in item.message for item in manual))

    def test_fenced_example_is_not_a_live_table(self):
        example = "```markdown\n" + self.TABLE + "```\n"
        self.assertEqual(list(missing_table_captions(example)), [])

    def test_caption_remains_with_english_fallback_table(self):
        master = "<!--en-->\n" + self.TABLE + ": The English caption.\n<!--/-->\n"
        woven = weave_for_site(master, "ja")
        self.assertEqual(woven.count('<details class="localized-fallback"'), 1)
        self.assertLess(woven.index(self.TABLE.strip()), woven.index(": The English caption."))
        self.assertLess(woven.index(": The English caption."), woven.index("</details>"))


if __name__ == "__main__":
    unittest.main()
