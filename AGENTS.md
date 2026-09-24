# Working on Outcrop

Outcrop Core and Outcrop Site are reusable software. Bedrock is one consumer,
not an implicit project, corpus or brand. Follow the current task and preserve
unrelated work. Do not commit or publish without authorization.

## Boundaries

- Core accepts explicit text and optional semantic context. It cannot depend on
  Site, discover a repository, load a project glossary or run a compiler.
- Site owns complete website composition, configuration, routes, search,
  publication, browser resources and lint orchestration. Every consuming project
  gets the same full feature set.
- Adapters receive explicit paths/options. Mathematical policies and compiler
  installation belong to the consuming project.
- Keep instance names, icons, source/canonical URLs, storage keys, vocabulary,
  source extensions and exceptions in configuration. Do not add Bedrock defaults.
- Read docs/RENDERER-MARKDOWN.md and docs/SITE-CONFIG.md before changing contracts.
  The Markdown statement/QED grammar is distinct from its visual rendering.
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

Definition inspection uses one full-body iframe modal with target-based history,
not stacked dialogs or history of incidental scroll positions. Keep dark/light
loading, ordinary link navigation, same-definition entry, code-block anchors,
sticky contents, scroll controls and explicit/outside close. Test Safari layout
when the browser is available; do not equate narrow Chrome with iPhone Safari.

Landscape code reading moves the original DOM. It shares hover, semantic lookup
and gesture selection, transforms coordinates once, preserves source IDs, and
restores the normal reading surface before opening a definition modal.

Retain trilingual search independent of edition, IME and keyboard controls,
appearance persistence, diagram interactions, dependency graph gestures,
sidebar title/disclosure hit regions, reading progress and Ask AI copying.
Use theme tokens, accessible controls and reduced-motion handling.

## Verification and licensing

Run reusable tests, strict example lint and an independent example build. Verify
the installable distribution includes templates, JS modules, workers and fonts.
Use actual browser interactions for changed behavior and record the tested
runtime generation; no stale copied assets. Keep tests of no-toolchain builds,
ordinary Markdown, optional semantics and multi-project isolation.

Source Markdown and compiler evidence are authoritative; a renderer refactor
must preserve code text and anchors. Raw authored HTML is trusted, not sanitized.
Do not change mathematics or claim proof verification without running it.

Respect REUSE.toml, NOTICE and font/upstream licenses. Do not silently relicense
files during moves. Generated sites, caches, screenshots and build logs belong
under ignored _build or temporary directories. The small committed semantic
fixture is the explicit exception. Dispatched agents write only assigned files
and must not change Git state, commit or push.
