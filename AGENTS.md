# Working on Outcrop

Outcrop Core and Outcrop Site are reusable software. Bedrock is one consumer,
not an implicit project, corpus or brand. Follow the current task and preserve
unrelated work. Do not commit or publish without authorization.
Commit-only authorization does not permit a push or deployment, including when
Outcrop is checked out as a consumer's submodule.

## Boundaries

- Core accepts explicit text and optional semantic context. It cannot depend on
  Site, discover a repository, load a project glossary or run a compiler.
- Site owns complete website composition, configuration, routes, search,
  publication, browser resources and lint orchestration. Every consuming project
  gets the same full feature set.
- Adapters receive explicit paths/options. Outcrop owns optional Agda compiler
  instrumentation, builds, library installation and parallel trace production.
  Consumers choose when to invoke them and supply dependencies, entry modules,
  safety flags, resource budgets, cache directories and deployment policy.
  Rendering/linting Markdown never implicitly installs or invokes Agda.
- Keep instance names, icons, source/canonical URLs, storage keys, vocabulary,
  source extensions and exceptions in configuration. Do not add Bedrock defaults.
- Read docs/RENDERER-MARKDOWN.md and docs/SITE-CONFIG.md before changing contracts.
  Prose labels and compiler-certified definition endings are independent.
- Site's default inline-math lint permits figures, standalone displays and
  figure-reference paragraphs using the localized fixed wording `图中的` /
  `in the figure` / `図中の`. This mechanical allowance never extends to other
  paragraphs and is distinct from human approval. Other inline math requires
  explicit human approval. Keep decisions in configured input data;
  inventory generation must never grant approvals or imply a successful lint.
  Explicit temporary chapter allowances end at `human_reviewed: true` in the
  configured catalog, not on content edits. Do not unset review status to bypass
  lint; there are no implicit chapter exemptions or source-digest exceptions.
- Prefer cohesive owners and real interface tests. Do not add old-API facades,
  duplicate implementations or broad catch-all contexts to make migration easier.

## Interaction invariants

Every code surface uses the same compiler-certified targets and AST nesting.
Offsets are Unicode code points, not JavaScript UTF-16 indices. Missing semantic
data must not create fake AST highlights. Retain infix/mixfix recognition,
vocabulary forwarding and precise universe/primitive stopping rules.

Desktop hover branches grow downward, keep ancestors alive through descendants,
and eventually close with per-branch delays. Touch first shows a persistent
hover, never a modal; its explicit action opens the modal. Node gestures return
to leaf names and clear the previous highlight. Loading requests are cancelable.

Definition and prose-link inspection use one full-body iframe modal with target-based history,
not stacked dialogs or history of incidental scroll positions. Keep dark/light
loading, native navigation for non-content links, same-target entry, code-block anchors,
sticky contents, scroll controls and explicit/outside close. Test Safari layout
when the browser is available; do not equate narrow Chrome with iPhone Safari.

Landscape code reading moves the original DOM. It shares hover, semantic lookup
and gesture selection, transforms coordinates once, preserves source IDs, and
restores the normal reading surface before opening a definition modal.
Keep standard and WebKit `text-size-adjust: 100%` scoped to code frames and
fullscreen reading without disabling user zoom. Check rendered glyph sizes,
not only computed font sizes, when testing mobile autosizing.

Agda code frames grow to their full content height and scroll only horizontally;
their page, modal or fullscreen reading plane may scroll vertically. Preserve
right-end scroll padding and independently indented submodules with compact
declaration headers. Code uses its full containing width, with no QED outdent or
external gutter. The exact rectangular `∎` is a noninteractive absolute overlay
at each compiler-certified definition's last line at fixed opacity `.25`, even when overlapping code. It
reserves no row, height or extra padding. Do not restore overlap measurement or
dynamic opacity. Markdown has no authored QED delimiter. Require a signature and
equation clauses; exclude where-local definitions, retain submodule definitions.
Keep proof prose close to its code without introducing a special frame wrapper.

Retain trilingual search independent of edition, IME and keyboard controls,
appearance persistence, diagram interactions, dependency graph gestures,
sidebar title/disclosure hit regions, reading progress and Ask AI copying.
Use theme tokens, accessible controls and reduced-motion handling.
Search results remain native navigation links, not modal targets. Dismiss on
outside click or outside `focusin`; input `focusout` with null `relatedTarget`
may precede Safari's result click and must not hide its target prematurely.
The shared footer credit is "Powered by Outcrop", linked to the Outcrop
repository, separate from instance copyright. Keep upstream acknowledgments in
the repository rather than adding them to every reader footer.

## Verification and licensing

Run reusable tests, strict example lint and an independent example build. Verify
the installable distribution includes templates, JS modules, workers and fonts.
Use actual browser interactions for changed behavior and record the tested
runtime generation; no stale copied assets. Keep tests of no-toolchain builds,
ordinary Markdown, optional semantics and multi-project isolation.
Attribute user-reported real-device acceptance to the user and tested revision;
it does not establish acceptance of later changes.

Source Markdown and compiler evidence are authoritative; a renderer refactor
must preserve code text and anchors. Raw authored HTML is trusted, not sanitized.
Do not change mathematics or claim proof verification without running it.

Respect REUSE.toml, NOTICE and font/upstream licenses. Do not silently relicense
files during moves. Generated sites, caches, screenshots and build logs belong
under ignored _build or temporary directories. The small committed semantic
fixture is the explicit exception. Dispatched agents write only assigned files
and must not change Git state, commit or push.
