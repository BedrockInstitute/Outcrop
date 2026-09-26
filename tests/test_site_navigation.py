from site_test_support import site_config
import json
from html.parser import HTMLParser
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from outcrop import site as site_package
RESOURCES = Path(site_package.__file__).resolve().parent / "resources"




import sys

from outcrop.core.agda_semantics import inline_ref_link
from outcrop.core.markdown_core import (
    dedent_submodule_code, md_to_html, plain_code, render_code_scroll_content,
)
from outcrop.core.agda_semantics import AgdaSemantics
semantics = AgdaSemantics(prelude_module='Base.Prelude')
from outcrop.site.site_config import SiteConfig, BookCatalog
from outcrop.site.page_renderer import PageRenderer
from outcrop.site.publication import Publication
from outcrop.site.external_links import external_links_new_window
from outcrop.core.agda_help import help_html


class PublicationCase(unittest.TestCase):
    def setUp(self):
        self.config = site_config()
        self.book = BookCatalog()
        self.publication = Publication(self.config, self.book)
        self.pages = PageRenderer(self.config, self.book, self.publication)


class TocParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.details = []
        self.branches = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "details":
            self.details.append(attrs)
            if attrs.get("class") == "toc-branch":
                self.branches.append(attrs)
        elif tag == "a":
            self.links.append((attrs["href"], [d["data-heading"] for d in self.details
                                              if "data-heading" in d]))

    def handle_endtag(self, tag):
        if tag == "details":
            self.details.pop()


class SiteNavigationTests(PublicationCase):
    def test_only_off_site_links_open_new_window(self):
        source = ('<a href="/zh/Origin.html#intro">local</a>'
                  '<a href="https://example.test/zh/Origin.html">canonical</a>'
                  '<a href="https://example.test:443/zh/Origin.html">same port</a>'
                  '<a href="//docs.example.test/help?x=1&amp;y=2">docs</a>'
                  '<a href="https://other.test" rel="help" target="_self">outside</a>'
                  '<a href="mailto:hello@other.test">mail</a>')
        result = external_links_new_window(source, 'https://example.test')
        self.assertIn('<a href="/zh/Origin.html#intro">local</a>', result)
        self.assertIn('<a href="https://example.test/zh/Origin.html">canonical</a>', result)
        self.assertIn('<a href="https://example.test:443/zh/Origin.html">same port</a>', result)
        self.assertIn('href="//docs.example.test/help?x=1&amp;y=2" target="_blank" rel="noopener noreferrer"', result)
        self.assertIn('href="https://other.test" rel="help noopener noreferrer" target="_blank"', result)
        self.assertIn('<a href="mailto:hello@other.test">mail</a>', result)
        self.assertIn('target="_blank" rel="noopener noreferrer"', help_html('module', 'zh'))

    def test_mobile_header_layout_does_not_wait_for_reader_module(self):
        template = (RESOURCES / 'template.html').read_text()
        css = (RESOURCES / 'static/outcrop.css').read_text()
        controls = (RESOURCES / 'static/reader/header-controls.js').read_text()
        self.assertIn('id="search-toggle" class="header-disclosure"', template)
        self.assertIn('id="language-toggle" class="header-disclosure"', template)
        self.assertIn('id="header-search" class="search-form"', template)
        self.assertIn('#topbar :is(.search-form, #lang-switch)', css)
        self.assertNotIn('#topbar.header-controls-ready :is(.search-form, #lang-switch)', css)
        self.assertIn("document.getElementById(index ? 'language-toggle' : 'search-toggle')", controls)
        self.assertIn('media="print" onload="this.media=\'all\'"', template)

    def test_adaptive_sidebar_css_and_navigation_share_breakpoint(self):
        css = (RESOURCES / 'static/outcrop.css').read_text()
        navigation = (RESOURCES / 'static/reader/navigation.js').read_text()
        self.assertIn('matchMedia("(min-width: 80rem)")', navigation)
        self.assertEqual(css.count('@media (min-width: 80rem)'), 2)
        self.assertIn('@media (max-width: 79.999rem)', css)
        self.assertIn('minmax(10rem, 1fr) minmax(0, var(--reading-width)) minmax(10rem, 1fr)', css)

    def test_milestones_and_chapters_share_compact_top_bottom_navigation(self):
        modules = ['Origin', 'Base.Prelude', 'Base.Choice']
        for lang in ('en', 'zh', 'ja'):
            body = self.pages.chapter_navigation('<h1>Origin</h1><p>Proofs</p>', 'Origin', modules, lang)
            home = self.pages.learning_home(body, '<section id="reading-explorer"></section>', lang, [])
            panel = home.split('class="book-panel guide-landmark">', 1)[1].split('</section>', 1)[0]
            self.assertEqual(panel.count('class="chapnav-next"'), 2)
            self.assertEqual(panel.count('href="Base.Prelude.html"'), 2)
            self.assertNotIn('class="chapnav-prev"', home)
            self.assertIn('aria-hidden="true"', panel)
            chapter = self.pages.chapter_navigation('<h1>Prelude</h1>', 'Base.Prelude', modules, lang)
            self.assertEqual(chapter.count('class="chapnav-prev"'), 2)
            self.assertEqual(chapter.count('class="chapnav-next"'), 2)
            visible = plain_code(chapter)
            self.assertNotIn(self.pages.ui[lang]['prev'], visible)
            self.assertNotIn(self.pages.ui[lang]['next'], visible)

    def test_private_submodule_keeps_inline_modifier_and_body_alignment(self):
        body = ('<details open class="submodule-fold"><summary class="submodule-fold-heading">'
                '<pre class="Agda">private module BooleanCodes where\n</pre></summary>'
                '<div class="submodule-fold-content"><pre class="Agda">'
                '  <a id="50">encodeB</a> = value\n    continued\n</pre></div></details>')
        output = dedent_submodule_code(body)
        self.assertIn('private module BooleanCodes where', output)
        self.assertIn('<pre class="Agda"><a id="50">encodeB</a> = value\n  continued\n</pre>', output)

    def test_code_scroll_padding_wrap_preserves_tokens_and_anchors(self):
        inner = '<a id="123" href="A.html#123">x</a> = y\n  z\n'
        code = '<pre class="Agda">' + inner + '</pre>'
        body = '<details><summary class="submodule-fold-heading">' + code + '</summary><div>' + code + '</div></details>'
        rendered = render_code_scroll_content(body)
        self.assertEqual(rendered.count('<span class="agda-code-content">' + inner + '</span>'), 1)
        self.assertIn('<summary class="submodule-fold-heading">' + code + '</summary>', rendered)
        self.assertEqual(render_code_scroll_content(rendered), rendered)
        self.assertEqual(plain_code(code), plain_code(render_code_scroll_content(code)))
        legacy = body.replace(code, '<pre class="Agda"><span class="agda-code-content">' + inner + '</span></pre>')
        self.assertEqual(render_code_scroll_content(legacy), rendered)


    def test_formal_labels_have_shared_semantic_classes(self):
        body, _ = md_to_html('**定义** (`x`) Text.\n\n**证明** Reason.')
        self.assertIn('class="prose-statement"', body)
        self.assertIn('class="prose-proof"', body)

    def test_review_status_is_outside_heading_and_localized(self):
        previous = dict(self.book.meta)
        try:
            self.book.meta['A'] = {'human_reviewed': True}
            body = self.pages.render_review_status('<h1 id="sec-0">Title</h1>', 'A', 'zh')
            self.assertIn('is-reviewed', body)
            self.assertIn('已人工校阅', body)
            self.assertIn('<h1 id="sec-0">Title</h1>', body)
            self.assertGreater(body.index('chapter-review '), body.index('</h1>'))
            self.book.meta['A']['human_reviewed'] = False
            self.assertIn('未人工校阅', self.pages.render_review_status('<h1>Title</h1>', 'A', 'zh'))
            home = self.pages.learning_home(body, '<section id="reading-explorer"></section>', 'zh', [])
            self.assertEqual(home.count('class="chapter-review '), 1)
        finally:
            self.book.meta.clear()
            self.book.meta.update(previous)

    def test_nested_submodule_code_dedents_only_rendered_scope(self):
        body = '''<details open class="submodule-fold">
<summary class="submodule-fold-heading"><pre class="Agda">module Outer where\n</pre></summary>
<div class="submodule-fold-content">
<pre class="Agda">  <a id="1">outer</a> = value\n    continuation\n</pre>
<details open class="submodule-fold">
<summary class="submodule-fold-heading"><pre class="Agda">  module Inner\n    (x : A) where\n</pre></summary>
<div class="submodule-fold-content">
<pre class="Agda">    <a id="2">inner</a> = outer\n      continuation\n</pre>
</div></details>
<pre class="Agda">  after = Inner.inner\n</pre>
</div></details>
<pre class="Agda">  outside = value\n</pre>'''
        rendered = dedent_submodule_code(body)
        self.assertIn('<pre class="Agda"><a id="1">outer</a> = value\n'
                      '  continuation\n</pre>', rendered)
        self.assertIn('<pre class="Agda">module Inner\n  (x : A) where\n</pre>', rendered)
        self.assertIn('<pre class="Agda"><a id="2">inner</a> = outer\n'
                      '  continuation\n</pre>', rendered)
        self.assertIn('<pre class="Agda">after = Inner.inner\n</pre>', rendered)
        self.assertIn('<pre class="Agda">  outside = value\n</pre>', rendered)

    def test_home_starts_with_milestones(self):
        home = self.pages.learning_home('<h1 id="sec-0">Origin</h1><p>Proofs</p>',
                                      '<section id="reading-explorer"></section>', "en", [])
        self.assertLess(home.index('id="tab-milestones"'), home.index('id="tab-reading-explorer"'))
        self.assertLess(home.index('<section id="milestones"'),
                        home.index('<section id="reading-explorer"'))

    def test_milestones_preserves_chapter_heading_hover_anchors_and_review(self):
        previous = dict(self.book.meta)
        try:
            self.book.meta['Origin'] = {'human_reviewed': True}
            for lang, title in [('en', 'Origin'), ('zh', '里程碑'), ('ja', 'マイルストーン')]:
                body = ('<h1 id="sec-0"><span id="123" class="boilerplate-anchor"></span>'
                        '<button class="boilerplate-hover" data-hover-template="setup">'
                        + title + '</button></h1><p>Content</p>'
                        '<template id="setup">module Origin where</template>')
                reviewed = self.pages.render_review_status(body, 'Origin', lang)
                home = self.pages.learning_home(reviewed, '<section id="reading-explorer"></section>', lang, [])
                intro, panel = home.split('<section id="milestones"', 1)
                self.assertNotIn('chapter-review', intro)
                self.assertNotIn('data-hover-template', intro)
                self.assertIn('<h1 id="reading-guide-title">', intro)
                self.assertIn('<h2 id="sec-0"><span id="123"', panel)
                self.assertIn('data-hover-template="setup">' + title, panel)
                self.assertIn('chapter-review is-reviewed', panel)
                self.assertEqual(home.count('id="123"'), 1)
                self.assertEqual(home.count('id="setup"'), 1)
        finally:
            self.book.meta.clear()
            self.book.meta.update(previous)

    def test_sidebar_folds_guide_and_opens_current_route(self):
        data = {"routes": [{"id": "foundation", "title": {"en": "Foundations"},
                            "chapters": ["A.One", "A.Two"]}]}
        nav = self.pages.modules_nav("A.Two", ["A.One", "A.Two"], "en", data)
        self.assertIn('<details class="navsec reading-guide"><summary', nav)
        self.assertIn('<details class="navsec current-route" open', nav)
        self.assertIn('data-route="foundation"', nav)
        self.assertIn('data-chapter="A.Two" aria-current="page"', nav)
        self.assertNotIn('modnav', nav)
        self.assertNotIn('modgroup', nav)
        self.assertIn('Interactive contents', nav)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the JavaScript behavior test")
    def test_sticky_directory_nests_all_chapter_headings(self):
        javascript = (RESOURCES / "static/reader/navigation.js").read_text()
        helper = re.search(r"  function sectionOutline\(headings\) \{.*?\n  \}\n",
                           javascript, re.DOTALL)
        self.assertIsNotNone(helper)
        scenario = r'''
var headings = ["H2:a", "H3:b", "H4:c", "H2:d", "H3:e"].map(function (item) {
  var parts = item.split(":");
  return {tagName: parts[0], id: parts[1]};
});
function shape(nodes) {
  return nodes.map(function (node) { return [node.heading.id, shape(node.children)]; });
}
console.log(JSON.stringify(shape(sectionOutline(headings))));
'''
        completed = subprocess.run([shutil.which("node"), "-e", helper.group(0) + scenario],
                                   check=True, capture_output=True, text=True, timeout=5)
        self.assertEqual(json.loads(completed.stdout),
                         [["a", [["b", [["c", []]]]]], ["d", [["e", []]]]])

    def test_heading_tree_is_nested_and_initially_collapsed(self):
        toc = [(2, "logic", "Logic & operations"), (3, "truth", "Truth"),
               (5, "witness", "Witness"), (3, "false", "Falsity"), (2, "next", "Next")]
        html = self.pages.toc_html(toc, "en")
        parser = TocParser()
        parser.feed(html)
        self.assertEqual(parser.links, [
            ("#logic", ["logic"]), ("#truth", ["logic", "truth"]),
            ("#witness", ["logic", "truth"]), ("#false", ["logic"]), ("#next", []),
        ])
        self.assertEqual(len(parser.branches), 2)
        self.assertTrue(all("open" not in branch for branch in parser.branches))
        self.assertIn("Logic &amp; operations", html)
        self.assertEqual(self.pages.toc_html([], "en"), "")

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the JavaScript behavior test")
    def test_reading_position_opens_ancestors_and_closes_departed_sections(self):
        javascript = (RESOURCES / "static/reader/navigation.js").read_text()
        helper = re.search(r"    function syncTocBranches\(activeLink\) \{.*?\n    \}\n",
                           javascript, re.DOTALL)
        self.assertIsNotNone(helper)
        scenario = r'''
function branch(links) {
  return {open: false, contains: function (link) { return links.includes(link); }};
}
var tocBranches = [branch(["logic", "truth", "witness", "false"]),
                   branch(["truth", "witness"]), branch(["other", "child"])];
var states = [];
[null, "logic", "witness", "false", "child", "witness", "next", null].forEach(function (link) {
  syncTocBranches(link);
  states.push(tocBranches.map(function (branch) { return branch.open; }));
});
console.log(JSON.stringify(states));
'''
        completed = subprocess.run([shutil.which("node"), "-e", helper.group(0) + scenario],
                                   check=True, capture_output=True, text=True, timeout=5)
        self.assertEqual(json.loads(completed.stdout), [
            [False, False, False], [True, False, False], [True, True, False],
            [True, False, False], [False, False, True], [True, True, False],
            [False, False, False], [False, False, False],
        ])

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the JavaScript behavior test")
    def test_active_section_link_stays_inside_sidebar_viewport(self):
        javascript = (RESOURCES / "static/reader/navigation.js").read_text()
        helper = re.search(
            r"    function revealTocLink\(link\) \{.*?\n    \}\n",
            javascript,
            re.DOTALL,
        )
        self.assertIsNotNone(helper)
        scenario = r'''
var toc = {
  scrollTop: 100,
  getBoundingClientRect: function () { return {top: 10, bottom: 110}; }
};
var document = {getElementById: function () { return toc; }};
function show(top, bottom) {
  toc.scrollTop = 100;
  revealTocLink({getBoundingClientRect: function () { return {top: top, bottom: bottom}; }});
  return toc.scrollTop;
}
console.log(JSON.stringify({above: show(-5, 5), visible: show(30, 50), below: show(120, 140)}));
'''
        completed = subprocess.run(
            [shutil.which("node"), "-e", helper.group(0) + scenario],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(json.loads(completed.stdout), {
            "above": 77,
            "visible": 100,
            "below": 138,
        })


class PreludeReferenceTests(PublicationCase):
    PRELUDE = '''<pre class="Agda"><a id="1" class="Keyword">open</a>
<a id="2" class="Keyword">import</a>
<a id="3" href="Cubical.Relation.Nullary.html" class="Module">Cubical.Relation.Nullary</a>
<a id="4" class="Keyword">public</a>
<a id="5" class="Keyword">using</a> <a id="42" class="Symbol">(</a> <a id="43" href="Cubical.Relation.Nullary.Properties.html#2891" class="Function">mapDec</a>
<a id="50" class="Symbol">)</a></pre>'''

    def test_later_code_links_visit_prelude_before_library(self):
        bridge = semantics.prelude_reexport_index(self.PRELUDE)
        later = ('<a id="90" href="Cubical.Relation.Nullary.Properties.html#2891" '
                 'class="Function">mapDec</a>')
        rewritten = semantics.rewrite_links(
            later,
            {"Base.Prelude", "Cubical.Relation.Nullary.Properties"},
            {},
            current_module="Base.Choice",
            prelude_reexports=bridge,
        )
        self.assertIn('href="Base.Prelude.html#43"', rewritten)
        self.assertNotIn('href="Cubical.Relation.Nullary.Properties.html#2891"', rewritten)

    def test_prelude_hop_keeps_hover_payload_when_its_type_exists(self):
        bridge = semantics.prelude_reexport_index(self.PRELUDE)
        later = ('<a id="90" href="Cubical.Relation.Nullary.Properties.html#2891" '
                 'class="Function">mapDec</a>')
        rewritten = semantics.rewrite_links(
            later,
            {"Base.Prelude", "Cubical.Relation.Nullary.Properties"},
            {"Base.Prelude": {"43": "type"}},
            current_module="Base.Choice",
            prelude_reexports=bridge,
        )
        self.assertIn('href="Base.Prelude.html#43"', rewritten)
        self.assertIn('data-type="Base.Prelude#43"', rewritten)

    def test_prelude_keeps_the_original_library_link(self):
        bridge = semantics.prelude_reexport_index(self.PRELUDE)
        original = ('<a id="43" href="Cubical.Relation.Nullary.Properties.html#2891" '
                    'class="Function">mapDec</a>')
        rewritten = semantics.rewrite_links(
            original,
            {"Base.Prelude", "Cubical.Relation.Nullary.Properties"},
            {},
            current_module="Base.Prelude",
            prelude_reexports=bridge,
        )
        self.assertIn('href="Cubical.Relation.Nullary.Properties.html#2891"', rewritten)

    def test_later_inline_reference_uses_the_same_intermediate_hop(self):
        bridge = semantics.prelude_reexport_index(self.PRELUDE)
        rendered = semantics.inline_ref(
            "mapDec",
            {"Base.Prelude", "Base.Choice"},
            {},
            {"mapDec": ("Cubical.Relation.Nullary.Properties.html#2891", "Function")},
            "Base.Choice",
            bridge,
        )
        self.assertIn('href="Base.Prelude.html#43"', rendered)

    def test_aliased_inline_reference_uses_target_declaration_for_hover(self):
        rendered = inline_ref_link(
            "V", "V.Hierarchy", "𝒮ᵥ", {"V.Hierarchy": {"𝒮ᵥ": "97"}},
            {"V.Hierarchy": {"97": "Function"}})
        rewritten = semantics.rewrite_links(
            rendered, {"V.Hierarchy"}, {"V.Hierarchy": {"97": "type"}})
        self.assertIn('href="V.Hierarchy.html#97"', rewritten)
        self.assertIn('data-type="V.Hierarchy#97"', rewritten)
        self.assertIn('>V</a>', rewritten)
        self.assertIn('class="inline-ref Function"', rewritten)

    def test_bound_variable_is_unlinked_but_standalone_declaration_may_be_bare(self):
        bound = semantics.inline_ref(
            "x", {"Base.Prelude"}, {},
            {"x": ("Base.Prelude.html#10", "Bound")}, "Base.Prelude")
        declaration = semantics.inline_ref(
            "refl", {"Base.Prelude"}, {},
            {"refl": ("Cubical.Foundations.Prelude.html#20", "Function")},
            "Base.Prelude")
        self.assertEqual(bound, '<code class="Agda inline-ref">x</code>')
        self.assertNotIn('inline-code', declaration)

    def test_unqualified_name_cannot_link_to_unrelated_module(self):
        rendered = semantics.inline_ref(
            "A", {"Base.Prelude", "Elsewhere"},
            {"Elsewhere": {"A": "42"}}, {}, "Base.Prelude")
        self.assertEqual(rendered, '<code class="Agda inline-ref">A</code>')

    def test_expression_links_declaration_but_not_its_local_arguments(self):
        rendered = semantics.inline_ref(
            "cong f p", {"Base.Prelude"}, {},
            {"cong": ("Cubical.Foundations.Prelude.html#30", "Function"),
             "f": ("Base.Prelude.html#31", "Bound"),
             "p": ("Base.Prelude.html#32", "Bound")}, "Base.Prelude")
        self.assertIn('>cong</a> f p', rendered)
        self.assertNotIn('>f</a>', rendered)
        self.assertNotIn('>p</a>', rendered)

    def test_projection_expressions_keep_code_and_link_only_field_tokens(self):
        fields = {'fst': ('Base.Prelude.html#10', 'Field'),
                  'snd': ('Base.Prelude.html#20', 'Field')}
        vocabulary = {'inline': fields, 'by_name': {
            name: ('Base.Prelude', href.rsplit('#', 1)[1], aspect, name)
            for name, (href, aspect) in fields.items()}}
        for expression in ('g [ true ] .snd', 'g [ false ] .snd',
                           'λ x → g x .fst', '(g x).fst', '.fst',
                           'record { value = g x .fst }', '"text.snd"'):
            with self.subTest(expression=expression):
                rendered = semantics.inline_ref(expression, {'Base.Prelude'}, {}, {},
                                                'Chapter', vocabulary)
                self.assertTrue(rendered.startswith('<code class="Agda inline-ref">'))
                self.assertEqual(plain_code(rendered), expression)
                self.assertNotIn('class="inline-ref Field"', rendered)
                if '.fst' in expression:
                    self.assertIn('>fst</a>', rendered)
                elif not expression.startswith('"'):
                    self.assertIn('>snd</a>', rendered)
                if 'λ' in expression:
                    self.assertIn('>λ</a>', rendered)
                    self.assertIn('>→</a>', rendered)
        for name in ('fst', 'Base.Prelude.fst'):
            rendered = semantics.inline_ref(name, {'Base.Prelude'}, {}, {}, 'Chapter', vocabulary)
            self.assertTrue(rendered.startswith('<span class="Agda">'))
            self.assertIn('Base.Prelude.html#10', rendered)
        unknown = semantics.inline_ref('Other.fst', {'Base.Prelude'}, {}, {}, 'Chapter', vocabulary)
        self.assertEqual(unknown, '<code class="Agda inline-ref">Other.fst</code>')
        known = semantics.inline_ref('Other.fst', {'Other'}, {},
                                     {'Other.fst': ('Other.html#30', 'Field')}, 'Chapter', vocabulary)
        self.assertIn('Other.html#30', known)

    def test_valid_projection_markdown_stays_boxed_through_full_core_rendering(self):
        from outcrop.core import CodeContext, MarkdownDocument
        from outcrop.core.prose_lint import inline_agda_violations
        expressions = ('g [ true ] .snd', 'g [ false ] .snd', 'λ x → g x .fst')
        text = '\n'.join('<!--' + lang + '-->\n\n' +
                         '\n'.join('- `' + code + '`{.Agda}' for code in expressions)
                         for lang in ('en', 'zh', 'ja')) + '\n<!--/-->\n'
        vocabulary = {'inline': {'fst': ('Base.Prelude.html#10', 'Field'),
                                 'snd': ('Base.Prelude.html#20', 'Field')},
                      'by_name': {'fst': ('Base.Prelude', '10', 'Field', 'fst'),
                                  'snd': ('Base.Prelude', '20', 'Field', 'snd')}}
        self.assertEqual(inline_agda_violations(text), [])
        document = MarkdownDocument(text, module='Example',
                                    code=CodeContext(semantics=semantics, vocabulary=vocabulary))
        for lang in ('en', 'zh', 'ja'):
            with self.subTest(lang=lang):
                rendered = document.render(lang)
                code = re.findall(r'<code class="Agda inline-ref">(.*?)</code>', rendered.body)
                self.assertEqual([plain_code(item) for item in code], list(expressions))
                self.assertNotIn('class="inline-ref Field"', rendered.body)
                self.assertIn('>fst</a>', rendered.body)
                for expression in expressions:
                    self.assertIn(expression, rendered.mirror)


    def test_prelude_import_anchor_has_hover_type(self):
        types = {"Base.Prelude": {}}
        reexports = {"by_href": {
            "Cubical.HITs.PropositionalTruncation.Base.html#226":
                ("Base.Prelude", "102913", "Datatype Operator", "∥_∥₁")}}
        semantics.add_prelude_reexport_types(
            types, {"Base.Prelude": {"∥_∥₁": "Type → Type"}},
            reexports, {}, {})
        self.assertEqual(re.sub(r"<[^>]+>", "", types["Base.Prelude"]["102913"]),
                         "Type → Type")

    def test_prelude_overloaded_constructor_types_follow_compiler_targets(self):
        types = {
            "Base.Prelude": {},
            "Agda.Builtin.Nat": {"221": "ℕ", "234": "ℕ → ℕ"},
            "Cubical.Data.FinData.Base": {"376": "Fin (suc n)",
                                          "407": "Fin n → Fin (suc n)"},
        }
        reexports = {"by_href": {
            "Agda.Builtin.Nat.html#221": ("Base.Prelude", "10", "InductiveConstructor", "zero"),
            "Agda.Builtin.Nat.html#234": ("Base.Prelude", "20", "InductiveConstructor", "suc"),
            "Cubical.Data.FinData.Base.html#376": ("Base.Prelude", "30", "InductiveConstructor", "zero"),
            "Cubical.Data.FinData.Base.html#407": ("Base.Prelude", "40", "InductiveConstructor", "suc"),
        }}
        semantics.add_prelude_reexport_types(types, {"Base.Prelude": {
            "zero": "WRONG", "suc": "WRONG"}}, reexports, {}, {})
        self.assertEqual(types["Base.Prelude"], {
            "10": "ℕ", "20": "ℕ → ℕ", "30": "Fin (suc n)",
            "40": "Fin n → Fin (suc n)",
        })
        missing_target = {"Base.Prelude": {}, "Agda.Builtin.Nat": {"221": "ℕ"}}
        semantics.add_prelude_reexport_types(missing_target, {"Base.Prelude": {
            "zero": "WRONG", "suc": "WRONG"}}, reexports, {}, {})
        self.assertEqual(missing_target["Base.Prelude"], {"10": "ℕ"})

    def test_inline_successor_keeps_original_constructor_identity(self):
        reexports = {
            'inline': {'suc': ('Base.Prelude.html#20', 'InductiveConstructor')},
            'by_href': {
                'Agda.Builtin.Nat.html#234':
                    ('Base.Prelude', '20', 'InductiveConstructor', 'suc'),
                'Cubical.Data.FinData.Base.html#407':
                    ('Base.Prelude', '40', 'InductiveConstructor', 'suc'),
            },
        }
        rendered = semantics.inline_ref('suc (suc (suc n))', {'Base.Prelude'}, {}, {},
                                        'Base.Prelude', reexports)
        self.assertEqual(rendered.count('data-agda-origin="Agda.Builtin.Nat.html#234"'), 3)
        self.assertNotIn('data-agda-origin="Cubical.Data.FinData.Base.html#407"', rendered)

    def test_source_qualified_inline_constructor_uses_its_exact_compiler_anchor(self):
        reexports = {'inline': {'suc': ('Base.Prelude.html#20', 'InductiveConstructor')},
                     'by_href': {'Cubical.Data.FinData.Base.html#407':
                                 ('Base.Prelude', '40', 'InductiveConstructor', 'suc')}}
        rendered = semantics.inline_ref(
            'Fin.suc Fin.zero', {'Base.Prelude'},
            {'Cubical.Data.FinData.Base': {'Fin.suc': '407', 'Fin.zero': '376'}},
            {}, 'Base.Prelude', reexports)
        self.assertIn('data-agda-origin="Cubical.Data.FinData.Base.html#407"', rendered)
        self.assertNotIn('data-agda-origin="Agda.Builtin.Nat', rendered)

    def test_explicit_constructor_reference_keeps_correct_prelude_hop(self):
        rendered = inline_ref_link(
            'zero', 'Cubical.Data.FinData.Base', 'Fin.zero',
            {'Cubical.Data.FinData.Base': {'Fin.zero': '376'}},
            {'Cubical.Data.FinData.Base': {'376': 'InductiveConstructor'}},
            {'by_href': {'Cubical.Data.FinData.Base.html#376':
                         ('Base.Prelude', '133501', 'InductiveConstructor', 'zero')}})
        self.assertIn('href="Base.Prelude.html#133501"', rendered)
        self.assertIn('data-type="Base.Prelude#133501"', rendered)


if __name__ == "__main__":
    unittest.main()
