#!/usr/bin/env python3
"""Glossary rule engines over supplied text and explicit language scopes."""

import importlib.util
import os
import tempfile
import unittest

from pathlib import Path

from outcrop.core import glossary_lint as glossary_rules
# Golden glossary rows (term, zh, ja, avoid-list, presence), exercising tagged and untagged avoids.
ROWS = [
    ("charter", "纲领", "綱領", ["zh:宪章", "ja:憲章"], True),
    ("prose", "文稿", "文章", ["散文"], False),
]
CHECKS = glossary_rules.build_checks(ROWS)


def write(tmp, rel, content):
    path = os.path.join(tmp, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def msgs(violations):
    return [m for _ln, _idx, m in violations]


class GlossaryTableTests(unittest.TestCase):
    def test_build_checks_expands_tagged_and_untagged(self):
        forb = {(f, lang) for f, lang, _t, _c in CHECKS}
        self.assertIn(("宪章", "zh"), forb)
        self.assertIn(("憲章", "ja"), forb)
        self.assertNotIn(("宪章", "ja"), forb)   # zh-tagged is not checked in ja
        self.assertIn(("散文", "zh"), forb)       # untagged applies to both
        self.assertIn(("散文", "ja"), forb)

    def test_load_glossary_reads_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "glossary.toml",
                      '[[term]]\ncategory = "Other"\nen = "charter"\nzh = "纲领"\nja = "綱領"\n'
                      'avoid = ["zh:宪章"]\npresence = true\n\n'
                      '[[term]]\nen = "prose"\nzh = "文稿"\nja = "文章"\navoid = ["散文"]\n')
            rows = glossary_rules.load_glossary(p)
            self.assertEqual(rows[0], ("charter", "纲领", "綱領", ["zh:宪章"], True))
            self.assertEqual(rows[1], ("prose", "文稿", "文章", ["散文"], False))

    def test_load_glossary_preserves_order_and_optional_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "glossary.toml",
                      '[[term]]\nen = "forcing"\nzh = "力迫"\nja = "強制"\npresence = true\n\n'
                      '[[term]]\nen = "charter"\nzh = "纲领"\nja = "綱領"\navoid = ["zh:宪章"]\n')
            rows = glossary_rules.load_glossary(p)
            self.assertEqual([r[0] for r in rows], ["forcing", "charter"])  # array order preserved
            self.assertEqual(rows[0][3], [])    # missing avoid -> empty list
            self.assertFalse(rows[1][4])        # missing presence -> False

    def test_build_presence_selects_opted_in_rows(self):
        rows = [("charter", "纲领", "綱領", [], True), ("prose", "文稿", "文章", ["散文"], False)]
        self.assertEqual(glossary_rules.build_presence(rows), [("charter", "纲领", "綱領")])




class MasterScopeTests(unittest.TestCase):
    def test_route_metadata_checks_only_language_values(self):
        text = '<!-- outcrop-routes {"id":"宪章", "title":{"zh":"宪章", "en":"宪章"}} -->'
        hits = glossary_rules.route_metadata_violations(text, CHECKS)
        self.assertEqual(len(hits), 1)
        self.assertIn("纲领", hits[0])

    MASTER = ("# T\n\n<!--zh-->\n这是 宪章 块。\n<!--ja-->\n憲章 ブロック。\n<!--/-->\n\n"
              "<!--en-->\nThe 宪章 here is shared-ish English.\n<!--/-->\n")

    def test_zh_group_flagged_ja_group_flagged_en_group_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "src/M.lagda.md", self.MASTER)
            v = glossary_rules.check_text(Path(p).read_text(), CHECKS)
            self.assertEqual(len(v), 2)  # the zh 宪章 and the ja 憲章; the en-group 宪章 is ignored
            joined = " ".join(msgs(v))
            self.assertIn("use 纲领 (zh)", joined)
            self.assertIn("use 綱領 (ja)", joined)

    def test_english_aliases_are_word_bounded_and_language_scoped(self):
        checks = glossary_rules.build_checks([("constant mapping", "常量映射", "定数写像",
                                   ["en:constant remap"], False)])
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, "src/M.lagda.md", "<!--en-->\nA constant remap.\n"
                      "A constant remapping.\n`constant remap`\n<!--zh-->\nconstant remap\n<!--/-->")
            self.assertEqual(len(glossary_rules.check_text(Path(p).read_text(), checks)), 1)

    def test_master_presence_checks_only_present_translations(self):
        text = "<!--en-->\nA charter.\n<!--zh-->\n纲领。\n<!--/-->"
        self.assertEqual(glossary_rules.master_presence_violations("M.lagda.md", text,
                         [("charter", "纲领", "綱領")]), [])
        text += "\n<!--en-->\nThe charter.\n<!--ja-->\n別の言葉。\n<!--/-->"
        hits = glossary_rules.master_presence_violations("M.lagda.md", text,
                                           [("charter", "纲领", "綱領")])
        self.assertEqual(len(hits), 1)
        self.assertIn("綱領", hits[0][1])


PRESENCE = [("charter", "纲领", "綱領")]


class PresenceTests(unittest.TestCase):
    EN = "# Example Charter\n\nThe full treatment is in the Charter.\n"

    def test_warns_when_canonical_rendering_absent(self):
        v = glossary_rules.presence_violations("docs/zh/CHARTER.md", "zh", self.EN, "# 文档\n标题。\n", PRESENCE)
        self.assertEqual(len(v), 1)
        self.assertIn("纲领", v[0][1])

    def test_clean_when_canonical_present(self):
        v = glossary_rules.presence_violations("docs/zh/CHARTER.md", "zh", self.EN, "# Example 纲领\n", PRESENCE)
        self.assertEqual(v, [])

    def test_no_warning_when_term_absent_in_english(self):
        v = glossary_rules.presence_violations("docs/zh/X.md", "zh", "# Intro\nNothing here.\n", "标题。\n", PRESENCE)
        self.assertEqual(v, [])

    def test_english_term_only_in_protected_region_does_not_count(self):
        en = "See `charter` and [x](charter.md)\n"  # inline code + link dest, both protected
        v = glossary_rules.presence_violations("docs/zh/X.md", "zh", en, "标题。\n", PRESENCE)
        self.assertEqual(v, [])

    def test_japanese_uses_ja_rendering(self):
        v = glossary_rules.presence_violations("docs/ja/CHARTER.md", "ja", self.EN, "# Example タイトル\n", PRESENCE)
        self.assertIn("綱領", v[0][1])

    def test_scoped_ignore_in_target_suppresses(self):
        tgt = "# 文档\n<!-- glossary-ignore: charter -->\n"
        v = glossary_rules.presence_violations("docs/zh/X.md", "zh", self.EN, tgt, PRESENCE)
        self.assertEqual(v, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
