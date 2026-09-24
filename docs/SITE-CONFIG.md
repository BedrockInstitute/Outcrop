# Outcrop Site configuration, version 1

There are two reusable layers: Outcrop Core renders an in-memory document;
Outcrop Site builds the entire interactive textbook.
Bedrock is an instance described by `site/project.json`. Another Agda textbook
uses the same templates, modules, styles, graph, lint and publication code. It
does not copy a Bedrock-specific shell.

## Independent build

From the Outcrop checkout:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m outcrop build \
  --config examples/renderer/project.json --project-root examples/renderer \
  --out _build/renderer-fixture/academy
.venv/bin/python -m outcrop lint \
  --config examples/renderer/project.json --project-root examples/renderer
```

Serve `_build/renderer-fixture` and open `/academy/en/index.html`. This example is
Lantern Notes, three ordinary `.md` chapters with a different icon, source path,
module vocabulary, license, canonical origin and storage namespace. Its checked
Agda semantic package is committed as fixture data, so these commands need no
Agda installation. The tiny code demonstrates only a marker datatype and identity
applications, not unverified category-theoretic claims. To refresh its compiler
package use `examples/renderer/refresh_semantics.py --help`; refreshing is a
separate optional adapter step, not a hidden build dependency.

The installed Python API is:

```python
from outcrop.core import MarkdownDocument, CodeContext
from outcrop.site import SiteConfig, build_site

config = SiteConfig.load('examples/renderer/project.json', root='examples/renderer')
build_site(config, ['--out', '_build/renderer-fixture/academy'])
```

`python -m outcrop build --help` and `lint --help` describe their own arguments.
The optional `agda-build`, `agda-libraries`, `agda-check`, `extract-types`,
`extract-expressions`, `weave`, `check-links` and `check-search` subcommands accept
explicit compiler/source/output paths. [AGDA.md](AGDA.md) documents the optional
producer; it needs no consumer repository. There is no legacy Python facade.
Bedrock's retained CLI is an instance adapter, not the generic entry point.
Tests copy the installed package without a Bedrock `src`, `dev` or
`site/project.json`, set `PATH=/no-toolchain`, and build/lint the example there.
When running from Bedrock rather than the Outcrop checkout, prefix example paths
with `outcrop/`; first initialize that pinned submodule and install it locally.

## Data and validation

All input paths are relative POSIX paths confined to the explicit project root,
including resolved symlinks. `..`, absolute paths, URL-like input paths and NUL
are rejected. Configuration cannot request Python imports or arbitrary executable
providers. URLs are HTTP(S), without embedded credentials. Brand labels are text,
not HTML. Trusted authored Markdown/SVG remain trusted content; configuration is
not a sandbox for executing untrusted authors' documents.

| Field | Meaning |
| --- | --- |
| `version` | Required integer `1` |
| `name`, `publisher` | Visible site and copyright identity |
| `copyright_year` | Optional positive year; omitted means a copyright notice without a year, not an inherited project date |
| `storage_namespace` | Preference isolation; Bedrock explicitly retains `bedrock` |
| `languages` | Nonempty unique subset of `en`, `zh`, `ja` |
| `canonical` | Public origin plus optional deployment path, no trailing slash |
| `base_url` | Local absolute path prefix, e.g. `/academy`, or empty |
| `repository`, `source_tree` | Optional source repository and chapter source-root URLs |
| `sources`, `source_extension` | Source root and `.md` (default) or `.lagda.md` |
| `catalog` | Complete chapter, stage and reading-route JSON |
| `glossary` | Optional glossary TOML; absent means no project terminology |
| `highlighted`, `types`, `expression_types` | Optional compiler package paths |
| `favicon`, `logo` | Required project SVG favicon; optional logo defaults to that explicit asset |
| `landing_module` | Overview chapter embedded in the interactive contents |
| `prelude_module` | Optional teaching-vocabulary reexport point; empty disables forwarding |
| `hubs` | Graph hub modules, explicitly validated against the corpus |
| `visible_import_chapters` | Explicit formal-setup exceptions for visible theorem imports |
| `prerequisites` | Optional per-chapter overrides; omitted chapters keep their inferred imports |
| `descriptions` | Text for each enabled language |
| `topics` | Site-level metadata keywords |
| `programming_language` | Optional metadata object with `name` and HTTP(S) `url`; absent means no language claim |
| `external_libraries` | Optional list of `{prefix, name, url}`; the longest module-prefix match supplies the external-library label; unknown libraries receive a neutral label, never an assumed Cubical identity |
| `license` | Required `name` and HTTP(S) `url` |
| `legacy_pages` | Flat old `.html` filenames mapped to local target pages/anchors |
| `source_links` | Extra agent-guide references: `url`, `description` |
| `agent.guide` | Project-specific AI reading guidance |
| `agent.translations` | Optional localized `docTitle`, `intro`, `hProject`, `fLibrary`, `project`, `want` copy |
| `policies.formal_setup`, `policies.trilingual` | Explicit booleans, both strict by default |
| `policies.level_name_convention` | Boolean, default false: opt into the book-wide convention that `ℓ` and supported suffixes are level parameters |
| `agda_policy` | Required options, bare-open hubs, prelude public-name data, empty-family and projection conventions |
| `variable_legacy` | Optional versioned exact legacy inline-variable allowances |
| `numbered_theorems` | Explicit chapter-to-number-list allowances |

Catalog entries retain stable module IDs separately from localized titles. They
include order, stage, titles/descriptions, routes and human-review status. Routes
may overlap, but cannot repeat a chapter within one route. All ordinary chapters
must be covered. Prerequisites come from fenced imports unless explicitly
supplied. A configured overview has no readiness prerequisites; no chapter name
receives that exception implicitly. `reading_routes.validate_metadata` and
`SiteConfig.validate_references` are callable without initializing a project.

`--site`, `--langs` and `--base-url` overrides produce a single effective config
before any renderer, graph or publisher is constructed. `--base-url` changes local
deployment paths, not the independently declared public `canonical` origin.
Supply a matching canonical when moving a published site. `--module` is a scoped
preview build, not a complete publish; it includes compiler dependencies and
refreshes assets/type sidecars. The Makefile's `site` target remains Bedrock's
backend-plus-website adapter.

## Isolation and compatibility

Each build owns `BookCatalog`, `Publication`, `PageRenderer`, `CodeContext` and
`AssetBundle`; no mutable book metadata is reused by another build. Browser keys
are namespace-prefixed. This includes theme, light/dark palettes, language,
completion and selected route. Existing Bedrock preference keys are unchanged.
The fixture tests build Lantern, Prism, then Lantern in one Python process and
check brand, source URLs, canonical metadata, agent output, assets and storage.

The shared browser transport is `window.outcrop`, its appearance service is
`window.outcropAppearance`, and definition frames use the `outcrop-modal` query
parameter. These names do not alter a configured historical storage namespace.
The transport includes `preludeModule` from `prelude_module` and
`levelNameConvention` from the explicit policy. Level typography for other names
still depends on compiler/binder evidence; the policy does not infer expressions
or rename primitives. Visible branding, source URLs, module exceptions and Ask AI
project text are supplied by configuration.

## Lint and publication

`outcrop.site.site_lint.lint_site(config)` returns structured diagnostics. Its strict shared
rules cover language grammar, parallel outlines, statements/QED, folds, syntax
safety/style, glossary forms, term introductions, prerequisite order, chapter
setup, figures and fence boundaries. Project mathematical policies are additional
gates, not silently disabled generic rules; the complete original gate mapping is
in the consuming project's gate documentation; the framework boundary is in
[ARCHITECTURE.md](ARCHITECTURE.md). Neither rendering nor lint runs
Agda automatically. A project's proof gate invokes its selected compiler itself.

The output is ordinary static files. The shared publisher emits relative
language links, canonical/JSON-LD metadata, source links, Markdown mirrors,
`llms.txt`, sitemap, robots, `_headers` and redirects. Hosting credentials and
deployment commands belong to the instance's build/deployment workflow. This
framework does not deploy or change a consuming project's host, nor require a new server.
