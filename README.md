# Outcrop

Outcrop publishes an interactive mathematics textbook from Markdown, with optional
compiler-backed Agda semantics. It is the reusable software behind
[Bedrock](https://github.com/BedrockInstitute/Bedrock), not a copy of its set-theory
content or brand.

Two layers share one document and interaction contract:

- **Outcrop Core** renders Markdown into HTML, an outline and a Markdown mirror.
  It owns multilingual prose, statements, figures, glossary markup, syntax help
  and optional compiler-certified definition/type/AST data. No repository,
  glossary, compiler or project is discovered implicitly.
- **Outcrop Site** builds the complete static textbook: interactive contents,
  reading routes and progress, dependency graph, sidebar, multilingual search,
  appearance, recursive hover, definition inspection, mobile code reading,
  reusable lint and machine-readable publication. Site depends on Core, not the
  other way around.

## Quick start

Python 3.11+ is required. Rendering the bundled example does not require Agda.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m outcrop lint --config examples/renderer/project.json --project-root examples/renderer
.venv/bin/python -m outcrop build --config examples/renderer/project.json --project-root examples/renderer --out _build/example/academy
.venv/bin/python -m http.server 8000 --directory _build/example
```

Open <http://localhost:8000/academy/en/index.html>. Change the explicit project
configuration, catalog, glossary, source documents and brand assets to publish
another textbook with the same features. The three language editions are English,
Chinese and Japanese; searches cover all three regardless of the selected edition.

Use Core without the website:

```python
from outcrop.core import MarkdownDocument

document = MarkdownDocument('# A chapter\n\nAn ordinary Markdown paragraph.').render('en')
print(document.body)
```

The Markdown dialect and compiler input contract are documented in
[Markdown](docs/RENDERER-MARKDOWN.md), reusable markup in
[Recipes](docs/RENDERER-RECIPES.md), and instance settings in
[Configuration](docs/SITE-CONFIG.md). Authored HTML/SVG is trusted content, not
sanitized user uploads. Without compiler evidence, Outcrop never invents types,
AST ranges or definition links.

## Repository boundaries

`src/outcrop/core` is the document engine. `src/outcrop/site` contains the site
builder and packaged browser resources. `src/outcrop/adapters` contains explicit
compiler build/trace, library installation, weaving and validation tools.
The optional `outcrop-agda` producer ships here too, including its source adapter
and checksummed build manifest; see [Agda integration](docs/AGDA.md).
`examples/renderer` is a small independent
textbook with a genuine checked semantic fixture; it is not Bedrock content.
`tests` exercises those reusable contracts.

The consuming project owns its mathematics, filenames and reading catalog,
terminology, domain proof gates, library lock, compiler invocation policy, build cache and
deployment credentials. Configuration provides the site's name, publisher,
icons, URLs, storage namespace and narrow policy exceptions. It is data, not an
arbitrary command-execution interface.

Bedrock consumes this repository as a pinned Git submodule. Changes to shared
behavior belong here and receive independent tests; changes to the textbook's
mathematical policies remain in Bedrock. See [AGENTS.md](AGENTS.md) for contributor
rules and [NOTICE](NOTICE) for inherited attribution.

The reader footer credit is exactly `Powered by Outcrop`, linked to this
repository and separate from the instance's copyright notice. Upstream acknowledgements remain here: Outcrop adapts
code and assets from [1lab](https://1lab.dev), by Amelia Liao and contributors;
see [NOTICE](NOTICE) and the retained upstream license files.

## Development and verification

The [architecture guide](docs/ARCHITECTURE.md) maps implementation owners and
interaction invariants. `docs/` holds the public contracts; `scripts/` holds
fixture/font builders and the optional compiler smoke test, not project-specific
proof gates. Build products and acceptance logs belong under ignored `_build/`.

From this repository root, after the editable install above:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python -m outcrop lint --config examples/renderer/project.json --project-root examples/renderer
.venv/bin/python -m outcrop build --config examples/renderer/project.json --project-root examples/renderer --out _build/example/academy
.venv/bin/python -m outcrop check-links _build/example/academy
.venv/bin/python -m outcrop check-search _build/example/academy
```

When working inside a consumer's submodule, use that consumer's installed Python
environment instead of assuming an Outcrop-local `.venv`. Reader changes also
require actual browser testing against freshly published runtime assets; unit
tests alone do not establish mobile Safari acceptance. Compiler changes require
the additional producer checks in [AGDA](docs/AGDA.md), but ordinary Markdown
rendering and lint must remain usable without the toolchain.

CI always runs the independent package checks, example build and REUSE audit.
Only the Agda integration job is skipped for changes confined to the reference
documents in `.github/docs-only.json`. Example Markdown is executable renderer
input and is not exempt. Mixed/unknown changes, missing comparison history and
manual dispatch run fully. `outcrop.adapters.ci_scope` provides the shared,
explicit-policy Git comparison helper; a consuming project supplies its own
allowlist rather than inheriting Outcrop's directory assumptions. The Actions
job summary records the decision. Local `make check` is unchanged.

## License

Software is AGPL-3.0-only. Documentation retains CC BY-NC-SA 4.0 where inherited
or declared, and bundled fonts retain OFL-1.1. The adapted/vendored 1lab material
keeps its upstream authorship and license. `REUSE.toml` is the per-file authority;
extraction from Bedrock does not relicense existing work.
