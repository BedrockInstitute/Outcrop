# Optional Agda integration

Outcrop owns both the producer and consumer of Agda semantic evidence. The
producer lives in `outcrop.adapters.agda`; it is an optional integration of
Outcrop Core, not a third product layer. Site consumes its highlighted documents,
name types and expression ranges. Ordinary Markdown rendering, lint and the
recorded example work without GHC, Cabal, Agda or any Agda library.

## Ownership

| Outcrop mechanism | Consuming-project choice |
| --- | --- |
| Type-trace overlay and version adapter | When to typecheck or regenerate semantic data |
| Checksummed compiler build and identity | Build/cache directories and available host tools |
| Checksummed library installer | Library names, versions, source URLs and hashes |
| Import-DAG scheduler and trace merging | Source directory, entry module, flags and worker budget |
| Name/expression extraction | Libraries and options needed by the project's loader |
| Weaving and source metrics | Edition paths, library descriptor and editorial budgets |
| Structural lint and tests | Mathematical correctness gates and explicit allowances |

The compiler resources ship inside the Python distribution, under
`outcrop/adapters/agda/resources`. They do not reference a sibling Bedrock
checkout. `manifest.json` pins Agda 2.8.0, its archive hash, the version patch,
Happy, Cabal bounds and tested host versions. The builder's identity also covers
the entire overlay and build/archive implementation. It is independent of the
installation path. A verified installed identity can be reused without Cabal or
network access.

## Build and use

Install Python 3.11+, GHC/Cabal, `patch` and a native C toolchain. CI tests GHC
9.4.8 and Cabal 3.12.1.0. Select a compatible GHC explicitly through `PATH` when
the host also has a newer unsupported release; the builder does not change a
global compiler selection.

Scope `GHCRTS` to compiler/build invocations, not the entire setup job. Tools such
as `ghcup` reject RTS flags even though Agda accepts them; CI tests this boundary.

```sh
python -m outcrop agda-build --identity
python -m outcrop agda-build --build-dir _build/outcrop-agda
_build/outcrop-agda/bin/outcrop-agda --outcrop-version
```

All generated files remain inside that build directory. The local Happy wrapper
removes `GHCRTS` only for Happy; the Agda process retains the caller's heap guard.
Neither installation nor importing the package changes `~/.agda`.

Tracing is disabled by default. `OUTCROP_AGDA_TYPES` supplies a JSONL output path;
`OUTCROP_AGDA_RUN` identifies the invocation. The overlay records complete
declarations after local metas have been solved, preserves Unicode source ranges
and source hashes, deduplicates records and flushes buffered output. Module
application telescopes containing Agda's internal `Dummy` are rejected before
queueing. Their ordinary argument/binder types are retained. The normalizer also
rejects legacy diagnostic records, never publishing an error stack as a type.

`Outcrop.Agda.TypeTrace` owns tracing policy. Version-specific patches only
register it and call the semantic hooks. Keep old patches when adding support
for another Agda version. The old `BEDROCK_AGDA_*` activation names are not used;
regenerate evidence when switching compiler identities.

Declaration tracing emits `signature` and `definition-end` records from Agda's
abstract declarations. Only signatures with source ranges count, not inferred
signatures inserted by the compiler. Function clauses include their complete
where bodies, but `envCheckingWhere` excludes nested helpers from independent
end markers. Data/record declarations, module imports and signature-only axioms
have no equation end. Normalization joins signatures to ends by binding position,
permits a definition to span literate fences, and keeps these records separate
from hover expressions. No Markdown marker or textual equals-sign heuristic is
used. Regenerate traced interfaces and the semantic package after this overlay
changes; unchanged source hashes alone cannot upgrade an old trace's schema.

For parallel checking or HTML plus traces:

```sh
GHCRTS="-A64m -I0 -M8g" python -m outcrop agda-check \
  --agda _build/outcrop-agda/bin/outcrop-agda --project-root . \
  --src chapters --root Start --jobs 2 --options="--safe" \
  --trace-out _build/types.jsonl --html-dir _build/html
python -m outcrop extract-types --agda _build/outcrop-agda/bin/outcrop-agda \
  --src chapters --html-dir _build/html --entry Start --options="--safe" \
  --out _build/types.json
python -m outcrop extract-expressions --src chapters --html-dir _build/html \
  --trace _build/types.jsonl --out _build/expressions.json
```

The scheduler handles `.agda` and `.lagda.md`, rejects duplicate module files and
cycles, precompiles external dependencies serially, then schedules independent
project modules. `--options` sets the generated dependency seed's local OPTIONS
pragma, not global command-line flags; imported built-ins must retain their own
checking mode. Authored modules keep their own pragmas and project library flags.
Root and options are explicit: there is no `Origin`, Cubical or
Bedrock assumption. Markdown intended for Agda checking must be staged with an
Agda-supported suffix; rendering alone accepts ordinary `.md` directly. Use
`--incremental --interface-root PATH` only with that compiler's compatible
interfaces and trace. Pure-check and traced interface caches must stay separate:
a pure interface can skip the elaboration needed to collect hover data.

The batch module-content query omits some nested constructors. A qualified
inference can recover them, but Agda sometimes prints module parameters as
internal names such as `_A_4`. These are not reader-facing types: extraction
discards them. Site indexing also rejects them in older semantic packages and
uses the compiler-highlighted declaration signature when one exists. A simple
unused named argument in that signature is displayed as an ordinary arrow;
dependent arguments and complex binders retain their original form. If neither
source provides a precise type, the name has no type hover rather than a
misleading placeholder.
For constructors with a highlighted source signature, that scoped declaration
takes precedence even over a precise interaction answer: the latter can expand
hidden parameters of the enclosing datatype that the declaration intentionally
leaves implicit. This is a constructor-wide rule, not a notation-specific fix.

For a dedicated source mirror used by a pure-check project:

```sh
python -m outcrop agda-stage --source chapters --destination _build/typecheck/chapters
```

This copies changed `.lagda.md` sources, removes deleted or renamed sources from
the mirror and leaves interfaces and unrelated files untouched. Unchanged files
retain their timestamps. `--extension .agda` selects plain Agda instead; this
command does not convert Markdown or rename suffixes. Source and destination
must be disjoint directories. Reserve the destination for this mirror: matching
files absent from the source are removed. Symlinks inside its write set are
rejected before mutation. The caller owns the staged library descriptor and
compiler invocation.

Expression extraction discovers both `.agda` and `.lagda.md` under its explicit
`--src` directory and rejects duplicate module names across those formats before
writing output. Plain Agda uses the whole source as its code interval; literate
Markdown uses only its `agda` fences. All ranges are one-based Unicode code-point
offsets with an exclusive end, not byte or UTF-16 offsets. Highlighting may be
provided as Agda's `.html` or `.md` output. A full extraction compacts the input
trace to the latest matching-source records for these local modules, including
plain Agda; it intentionally excludes sources outside `--src`. A selected
`--module` extraction does not compact the trace. Ordinary `.md` still requires
staging under an Agda-supported suffix before compilation and extraction.
Constructor patterns have a distinct `pattern` trace kind; normalization retains
their source-node behavior while recording pattern context. Keep that context
separate from expression `application` records: the natural-literal lint must
never suggest replacing a constructor pattern with a number literal.

## Libraries

`agda-libraries --lock libraries.json --build-dir _build/dependencies
--agda-dir _build/agda-home` takes a version 1 lock with a `libraries` list. Each
entry supplies `name`, `version`, HTTPS `url`, lowercase `sha256`, `archive_root`
and relative `library` descriptor path. The installer verifies downloads,
rejects escaping archive paths/links/devices and writes exactly that lock's
entries into the explicitly supplied local registry. It does not inherit or edit
a global registry, infer Cubical, or retain stale library versions in the list.
Run subsequent Agda commands with `AGDA_DIR` set to that local directory.

Bedrock's `site/agda-libraries.json` is one consumer of this format, not a default.
The small example and compiler smoke test need no external library.
