# Outcrop architecture

Outcrop is a reusable renderer and a complete interactive textbook website.
Bedrock is one configured consumer. It is not a hidden default project, source
tree, glossary, mathematical policy or brand.

## Two layers

| Layer | Public entry | Responsibility |
| --- | --- | --- |
| Outcrop Core | `from outcrop.core import MarkdownDocument, CodeContext` | Explicit Markdown and optional compiler evidence become HTML, an outline and a usable Markdown mirror |
| Outcrop Site | `from outcrop.site import SiteConfig, build_site` | Complete static textbook composition, configuration, metadata, publication, packaged resources and reusable lint |
| Optional adapters | `outcrop.adapters` | Agda toolchain/build/trace production, semantic extraction, weaving and published-link/search validation with explicit paths/options |

Site depends on Core. Core does not import Site, discover a repository, load a
catalog or glossary by default, or run Agda. A document without compiler evidence
still renders correctly; unknown code does not acquire invented types or AST
nodes. The adapters are optional integration tools, not a third product layer.

The package uses a standard `src/outcrop/` layout. Browser resources live under
`src/outcrop/site/resources/`: `template.html`, `depmap-template.html`, `static/`
and `vendor/`. Installed distributions include these resources. Consumers do not
copy or patch a website shell to adopt another name or teaching subject.

## Python owners and lifetimes

| Owner | Contract |
| --- | --- |
| `MarkdownDocument` / `RenderedDocument` | One explicit source document; `.render(lang)` returns `body`, `toc`, `mirror` and `code_blocks` |
| `CodeContext` / `AgdaSemantics` | Shared compiler-certified names, aspects, signatures, ranges, scope and optional vocabulary forwarding; no inference from popup text |
| `source_syntax` | Common fenced-import grammar and coordinate-preserving route-annotation stripping |
| `SourceCorpus` / `compiler_index` | Explicit project source inventory, highlighted documents, reachable document closure and one semantic join per build |
| `SiteConfig` / `BookCatalog` | Validated instance configuration and owned chapter metadata; centralized chapter addresses |
| `PageRenderer` | Document composition, headings, navigation and page-level markup |
| `Publication` | Markdown front matter, browser configuration, agent guide, structured metadata, search/term files and redirects |
| `reading_routes` / `dependency_graph` | Configured reading order, prerequisite overrides, route membership and shared graph layouts |
| `AssetBundle` | Captured asset bytes, immutable runtime generation and publication from that same snapshot |
| Core lint engines / `site_lint` | Pure language, code, statement, fold, term, outline and figure rules; configured whole-book orchestration |

`build_site` creates new instance state for every invocation. Building two projects
in one process must not leak titles, source URLs, route data, preferences or
branding. CLI overrides are resolved before these owners are constructed.

There is no monolithic Python compatibility facade. Tests import the responsible
owner or public package API. A consuming project's old command may remain a thin
adapter when its build genuinely uses it; private functions are not re-exported
merely to preserve old test imports.

## Browser owners

`static/outcrop.js` composes features. It is not a shared mutable context.
`appearance.js` runs synchronously before paint and owns theme/palette preferences.
`window.outcrop` carries validated page data; `window.outcropAppearance` exposes
the appearance service. Preference keys use the configured storage namespace,
not the framework's name. A project may retain its historical namespace.

The `static/reader/` modules own separate lifecycles:

- `code-targets` owns semantic identities and leaf/ancestor selection;
  `type-store` owns coalesced payload loading, retries and resolution.
- `HoverBranch` owns ancestor delays and disposal. `hover-view` shares downward
  positioning and selection cleanup across source and signature views.
- `DefinitionSession` owns target-based history, forward truncation and loading
  generations. `definition-layout` owns the iframe reading viewport, redirect
  identity and code-block alignment. The modal view owns neither a second history
  nor arbitrary user-scroll restoration.
- `code-surface` owns the coordinate transform for the current code surface;
  `code-fullscreen` moves the existing code DOM into a landscape reading surface.
- `route-store` shares catalog loading and route selection; `preferences` supplies
  failure-tolerant namespaced storage. Navigation, search, notes and diagrams own
  their respective listeners and local state.

All JavaScript, imported modules and workers are published under one
`runtime/<digest>/` generation. CSS uses content versions. Modal documents load
the same entry and features as ordinary pages, not a reduced reader.

## Interaction contracts

Formal, inline and single-line code, signature/source popups, dynamically added
content and modal mirrors share semantic behavior. Unicode offsets refer to code
points. Compiler-backed AST nesting, infix/mixfix names and definition links stay
intact. No semantic evidence means no fake range highlight or result type.

Desktop hover grows downward. Each branch has a disappearance delay, entering a
descendant retains ancestors, and leaving the complete chain eventually clears
every source highlight. Touch first opens persistent hover; its explicit window
action opens the definition modal. Hold-and-slide selection can return from a
parent expression to its leaf and clears the previous selection. Precise universe
and primitive stop rules prevent meaningless recursion without a depth cap.

The definition modal lazily fetches the complete original page, including a
same-page definition, using `outcrop-modal=1`. It removes outer header/footer but
retains sticky contents, code interactions, diagrams and scroll controls. Its one
history records target definitions and their whole code-block tops, not later
manual scroll positions. The enter-page action uses that target. Ordinary prose
links navigate normally, and revisiting the current definition from inside the
modal enters its page. Loading is theme-aware, inert until ready, cancellable and
cannot revive a closed modal.

On compact portrait devices, activating code exposes landscape reading. This is
a CSS-oriented surface, not a request to lock the device's physical orientation.
It moves the original code or statement-ending DOM, preserving IDs and AST
identity. Hover and gestures use the shared transformed coordinates. Close, Escape
and definition navigation restore the normal surface; a modal opens only after
that restoration. A separate non-scrolling control layer preserves the close
button and maps physical safe-area insets into landscape coordinates. For code
inside a definition mirror, the parent first restores the normal iframe size,
then acknowledges that layout before the saved reading position is restored.
Pointer, focus, scroll and real-device behavior require browser
acceptance, not just geometry-unit tests.

Ordinary code uses the full width of its containing column, without an outdent or
reserved external QED gutter. Each folded submodule keeps its own independently
indented column. Its compact declaration header is not a body-code block. The
literal rectangular `∎` appears semi-transparently inside the final code frame at
the lower right; extra bottom padding keeps it clear of source text. It is not
part of copied code. The Markdown and lint contract remains a standalone `∎`
immediately after each statement's last Agda fence, including inside folds.

The sidebar's localized Current route label includes its colon; the route name
follows it, while the disclosure arrow remains on the right. Section titles link
only over their text; remaining branch-row space toggles children. Preserve one
row highlight, keyboard disclosure, drawer focus and Escape behavior.

The top-right appearance menu owns system/light/dark mode and independently
remembered light/dark code palettes: default, GitHub, Solarized, Catppuccin and
Gruvbox. All code surfaces use the same semantic `--code-*` tokens; changing that
palette does not recolor ordinary UI or mathematical diagram roles. Ordinary
links, Agda modules/definitions/constructors and mathematical relations remain
visually distinct. Handle unavailable storage, invalid preferences, system theme
changes and cross-tab updates without overriding a parent modal's preferences.

Boilerplate source popups have a floating code-frame shell distinct from type
hints and glossary terms. Their highlighted contents reuse ordinary recursive
syntax help and definition navigation. Syntax words, symbolic tokens and neutral
punctuation retain their separate palettes; terminal built-ins are neutral only
inside the stopped hover, never globally in ordinary source code.

Search covers all configured editions, terms, headings, prose and every rendered
project/external Agda block. Its worker owns index loading/ranking. Preserve IME,
keyboard selection, explicit empty/error states and retry. Mobile scroll-driven
visibility must not fight focused input or cause repeated layout jumps. Search
and appearance changes require narrow-screen and keyboard checks.

Dependency graph layouts share the same graph, with explicit hub/preview policy.
Keep edge modes, legend, search, details, keyboard controls, canvas-scoped touch/
trackpad gestures and full-screen state restoration. A hidden tab need not render
the graph until activated. Routes retain choice, comparison, readiness and
completion. Completion does not toggle its containing disclosure.

Ask AI creates a local, copyable handover from page metadata and selected prose;
it does not submit the selection to an external assistant. The same metadata feeds
Markdown mirrors, `llms.txt`, sitemap, source links and JSON-LD.

Universe notation is a presentation lens: original source, Unicode ranges,
anchors and copy text survive. Linked primitives and compiler evidence authorize
shortening; local same-spelled names, incomplete/multiline forms and imports are
not guessed. `policies.level_name_convention` explicitly opts into treating `ℓ`
and its supported suffixes as level parameters; it defaults to false. Other names
need semantic evidence. The two dotted-operator clusters and universe-level font
subsets retain their own licensed family identifiers.

## Lint and consuming-project policy

`python -m outcrop lint` runs the shared structural rules under explicit project
configuration. Formal chapter setup and trilingual outlines are strict by default;
ordinary Markdown projects can explicitly disable those two policies without
disabling language-marker integrity or other applicable checks. Exact glossary,
numbered-theorem, vocabulary and legacy-line allowances are data, not exceptions
inferred from project names. `lint_site(config, project_checks=...)` can receive
additional diagnostic-producing callables; JSON configuration cannot execute
commands.

The shared gate checks both figure source structure and the framework stylesheets:
non-link diagram relations cannot inherit navigation-link colours. Shared CJK
prose diagnostics use the same marker/fence grammar in Core and consumer adapters.
`AgdaPolicy.options_pragma` supplies the exact setup contract to chapter lint and
rendering; `MarkdownDocument(..., options=...)` accepts that explicit pragma, so
a project using only `--safe` does not inherit Cubical boilerplate assumptions.

Framework tests own synthetic hover/modal/navigation, publication, terminology,
chapter, source-rule and route scenarios. They use explicit policy or the
independent example, never a consumer's catalog or project configuration. Consumer
tests retain actual-corpus conformance, editorial metadata and domain exceptions.
`outcrop.core.source_metrics.count(text)` shares Agda fence extraction with lint.
`python -m outcrop.adapters.weave` provides batch weaving and marker validation;
it needs explicit files or a root and never invents a compiler-library dependency.
Its optional library file is copied verbatim. A consumer adapter can instead supply
per-language library metadata while keeping its source paths and archive policy.

A consumer owns its mathematical correctness gates, dependency lock, entry
modules, invocation/resource/cache policy and deployment credentials. Outcrop
owns the reusable mechanisms, including optional compiler installation and trace
production in `outcrop.adapters.agda`. An optional dependency is not a reason to
leave its generic implementation in one consumer. These adapters belong to Core's
Agda integration, not a third product layer. Outcrop does not typecheck merely
because it renders or lints. Bedrock's host-LEM inventory and Origin closure are
examples of project policy, not generic Markdown rules. See [AGDA.md](AGDA.md).

## Verification

From the Outcrop checkout after installation:

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m outcrop lint --config examples/renderer/project.json --project-root examples/renderer
.venv/bin/python -m outcrop build --config examples/renderer/project.json --project-root examples/renderer --out _build/example/academy
.venv/bin/python -m outcrop check-links _build/example/academy
```

`scripts/build-renderer-fixtures.py --out ...` builds two differently configured
instances plus the project-free core page and browser fixture. No Agda toolchain
is needed because the small checked semantic package is committed. Its refresh
script is an explicit maintainer operation, not a hidden build step.

Test ordinary Markdown, optional semantics, isolated installed distributions,
same-process multi-project builds, configuration validation and resource packaging.
Browser tests must use the newly built production hash and matching modal pages.
Record browser, width, language, theme, actions and limitations; distinguish real
pointer actions from synthesized events. Desktop narrow widths are not iPhone
Safari evidence. This document specifies contracts, not a claim that every new
UI change has already passed browser acceptance.
