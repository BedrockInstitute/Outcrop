# Outcrop Markdown, version 1

This is the reusable renderer's input contract, not the Bedrock mathematical
style guide. A document is UTF-8 text. Its filename need not end in `.lagda.md`.
The core accepts a string and never discovers a repository, catalog or glossary:

```python
from outcrop.core import MarkdownDocument, CodeContext
result = MarkdownDocument(text).render('en')
html, outline, markdown = result.body, result.toc, result.mirror
```

Install Outcrop with `python -m pip install -e .` from its checkout. Python 3.11 or newer is required;
the core and static site builder do not invoke Agda. The current language set is
English (`en`), Chinese (`zh`) and Japanese (`ja`), not an arbitrary locale plugin
system. `examples/renderer/plain.md` is the minimal project-free example.

## Ordinary content

Supported blocks are ATX headings, paragraphs, bullet and numbered lists, fenced
code, pipe tables and authored HTML. Supported inline forms include emphasis,
strong emphasis, backtick code, links, images and math delimiters. This is a
deliberately small textbook Markdown dialect, not a claim of full CommonMark or
GFM conformance. Keep blank lines between blocks. A heading receives a stable
document-order `sec-N` anchor. Explicit HTML IDs are retained. Prose blocks receive
`p-N` anchors for selection and machine-readable citations. Changing block order
can change generated anchors; use explicit IDs for long-lived authored links.

Site lint permits LaTeX in figures and standalone `$$...$$` display blocks.
An explanatory paragraph containing the fixed prose phrase `图中的` (Chinese),
`in the figure` (English, case-insensitive with whitespace/soft-wrap tolerance),
or `図中の` (Japanese) also permits inline math in that paragraph only. Language
groups use their corresponding phrase; shared/monolingual prose may use any of
the three. List items and language variants are separate paragraphs. Code,
comments, HTML attributes, link destinations and math cannot supply the phrase.
This is a mechanical convention for actual figure explanations, not semantic
verification that a formula belongs to a figure, and not a human approval.
Other inline math outside figures requires explicit human approval of the exact source
occurrence, unless the chapter has an explicit temporary allowance and its
catalog flag is `human_reviewed: false`. Editing the text does not expire that
allowance; marking the chapter human-reviewed does.
Use complete `{.Agda}` code spans for Agda expressions. Core can still
render approved inline math; this is an editorial lint policy, not removal of
the rendering syntax. See `policies.inline_math_review` and
`inline_math_approvals` in [SITE-CONFIG.md](SITE-CONFIG.md).

Raw HTML and SVG are **trusted author input**, not sanitized user-generated
content. Do not render untrusted uploads into the site's origin. Configuration
strings, generated labels and normal code text are escaped separately. Script
execution is never a prerequisite for interpreting source Markdown.

Inline Agda uses `` `term`{.Agda} ``. A single linked name can be rendered unboxed;
composite expressions retain a code surface. Field projections such as `g x .fst`
and lambdas remain complete
inline code; only their individual compiler-resolved tokens link to definitions.
A matching final dotted component never turns a whole expression or an unknown
qualified name into a standalone declaration link. ` ```agda ` fences retain the
entire code stream. Without compiler input they receive lexical syntax help, but no
invented definition links, expression ranges or types. Other fences are ordinary
escaped code. Math is retained for the shared KaTeX client.

## Language groups and fallback

Markers occupy their own lines, outside code fences:

```markdown
<!--en-->
## A heading
<!--zh-->
## 一个标题
<!--ja-->
## 見出し
<!--/-->
```

Content outside a group is shared. Within each group choose the requested
language, then English, then the first available supported language. The website
also labels English narrative fallback. A missing closing marker, stray closing
marker, unknown language marker, marker inside a fence, or Agda fence inside a
language group is a diagnostic. The pure renderer supports fallback; the default
strict textbook lint additionally requires parallel chapter outlines. A project
can explicitly set `policies.trilingual` to false for a monolingual ordinary
Markdown corpus. That does not disable marker integrity checks.

## Teaching structures

Statement labels use the established localized bold labels (Definition, Lemma,
Theorem, Construction, Corollary and their Chinese/Japanese counterparts). A
statement contains Agda code, and a proof contains code after its label. There is
no Markdown QED delimiter and no special statement-ending frame. Prose labels
retain their typography and tight proof/code spacing independently of decoration.
With compiler evidence, the renderer automatically places the exact rectangular
`∎` just below each eligible definition's last line, inside the code frame at the
right, even when another definition follows in that same block. Its opacity is
0.25; it reserves no row or padding and never enters copied code. Definitions
have an explicit type signature and equation clauses. Submodule definitions are
included, where-local definitions are excluded; the enclosing definition ends
after its complete body including where declarations. Signature-only imports,
postulates, records and data declarations are not equation definitions.
Missing semantic evidence produces no guessed mark. Ordinary and final
code blocks use the full width of their containing column, with no external QED
gutter or left outdent; each submodule retains its own indented width.
Proof labels are explanatory prose, not additional statement wrappers.
See `outcrop.core.statement_structure` for the authoritative label vocabulary and
`outcrop.core.prose_lint` for diagnostics. Numbered theorem allowances are explicit project
data, not an exception inferred from a chapter's name.

Use semantic `details.submodule-fold`, `summary.submodule-fold-heading` and
`div.submodule-fold-content` for a nested formal module. The declaration remains
its compact code surface; inner code retains its own indentation and horizontal
scroll area. Default-open and nested folds are supported. A private module's
`private module` must be on one code line even across fence boundaries. General
HTML details are supported too. The removed `prose.disclosure` convention is not
part of this dialect.

Annotations use the recipe's `span.prose-annotation-target` followed by
`aside.prose-annotation-note`, or the generated template form. They work in prose
and code without modifying the underlying Agda text. Tables scroll independently.
Single-line code, type popups, source popups and definition mirrors use the same
syntax-help and semantic code contract.

Figures are authored HTML/SVG with a stable `figure` ID, accessible labeling and
localized captions. A frame is a direct `div.diagram-framed` containing only the
diagram, followed by a direct, unframed sibling `figcaption`. Mathematical relation
arrows use semantic diagram colors, not link tokens. Put explanatory prose, not
an Agda fence, immediately after a figure in every language and fold. Shared
diagram classes, animation controls and static-print behavior are documented in
[RENDERER-RECIPES.md](RENDERER-RECIPES.md). These structural/accessibility rules are
reusable lint rules; the figure's mathematical meaning belongs to its author.

## Terms

The optional glossary supplies stable IDs, preferred `en`/`zh`/`ja` forms,
introduction locations, automatic matching and official-document links. Explicit
markers use the same `term-intro`/`term-ref` classes and `data-term` IDs as the
recipes. An introduction is unique and parallel across the configured textbook.
An explicit reference can look forward, in the same chapter or another chapter.
Bare automatic terminology remains subject to prerequisite/introduction order;
one explicit lookup does not exempt other bare occurrences. No glossary is read
unless supplied by the caller. Bedrock's particular translations are not built
into the renderer.
An automatic glossary entry may list language-local `auto_exclude_en`,
`auto_exclude_zh` or `auto_exclude_ja` phrases. A term form wholly inside an
excluded phrase stays plain text in both rendering and prerequisite lint;
unrelated occurrences in the same text remain automatic. This is for audited
lexical collisions, not a general replacement for explicit term references.

## Optional formal chapter convention

The complete site defaults to strict formal chapter setup. Set
`policies.formal_setup=false` for ordinary Markdown that has no formal module.
When enabled, a parameter-free chapter has OPTIONS/module, a title-only language
group, local prerequisite imports, then prose and external-library imports. The
title reveals the original OPTIONS and module through a source popup. Imports
become real prerequisite source popups. A parameterized module is different:
required early imports and parameter exposition may precede the declaration;
the declaration stays visible and only OPTIONS goes into the title popup.
Visible theorem imports at an overview chapter require an explicit
`visible_import_chapters` entry. There is no implicit `Origin` exception.

## Optional compiler evidence

`CodeContext` from `outcrop.core` is the explicit enhanced-rendering input: semantic operations,
internal/rendered module sets, name and canonical-name indices, type records,
expression records, vocabulary/reexport index, token aspects and definition-end
records (`CodeContext.definition_ends`, keyed by module).
`outcrop.site.site_inputs.SourceCorpus` and
`outcrop.site.compiler_index.build_code_context` adapt a supplied compiler package for the website. The
core does not run a compiler or infer a type from displayed text.

The current Agda adapter accepts `--html --html-highlight=code` output: literate
module `.md` documents with `<pre class="Agda">` token HTML and external module
`.html` documents. Definition anchors are Agda's decimal source positions;
symbolic/Unicode anchors are retained. Source positions are **one-based Unicode
code-point offsets**, not UTF-8 byte or JavaScript UTF-16 offsets. Expression
intervals are half-open `[start,end)` and must refer to the exact source that
produced the highlighted document. Browser popup-local ranges are explicitly
rebased to code-point offsets; cloning removes source IDs, not semantic identity.

Raw type JSON maps modules and declaration names to compiler-produced type text;
the site joins it with definition positions and aspects from highlighted output.
Raw expression JSON maps modules to compiler records containing `id`, `start`,
`end`, `source`, `type` and `kind`. The supplied extraction adapters validate source
hashes and filter compiler Dummy records before publication. The browser sidecars
contain position-to-HTML signatures plus `$names`, `$expressions` and `$syntax`
metadata. The extraction package also carries `kind: "definition-end"` records
with `start`, exclusive `end` and `name`. These may cross literate fences and are
kept separate from expression/hover nodes. Both endpoints come from Agda AST
ranges, joined to explicit signature records and validated against source hashes.
They are generated outputs, not an alternative handwritten AST format.
Use the example's `refresh_semantics.py` to reproduce a small genuine package.

Missing signatures leave code visible and links usable without a fake structural
node. Lexical syntax help remains available. Terminal universe-former signatures
and primitive sorts use precise semantic stop rules; this is not a general hover
depth limit. Modules are navigation targets, not ordinary result-typed terms.
Do not manufacture an application type for a module import.

## Links, assets and diagnostics

Ordinary prose links navigate normally, including inside a definition mirror.
Only code-definition actions enter the single-history modal. Internal module
addresses come from `BookCatalog`; external compiler modules retain flat module
filenames. Language, canonical URL and deployment prefix belong to `SiteConfig`.
Raw core documents without a rendered-module set retain ordinary links unchanged.

The website emits HTML, Markdown mirrors, type/search/route metadata, dependency
graphs, agent guides, sitemap, redirects and static assets. JavaScript modules are
published as one immutable content-hashed graph. CSS has content versions. Static
deployment needs no application server. `python -m outcrop lint` reports source, line, rule
and message; invalid metadata/configuration raises an explicit error. It does not
silently repair mathematical content. See [SITE-CONFIG.md](SITE-CONFIG.md) for a
complete independent build and [ARCHITECTURE.md](ARCHITECTURE.md) for ownership,
lint boundaries and verification requirements.
