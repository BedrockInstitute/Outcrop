# Deep notation

Start here for every compact mathematical presentation of Agda code.
`index.js` is the only runtime entry: it owns the ordered rule list, localized
source-popup labels, initial scan and one mutation observer. The reader calls
`initialize()` once; repeated calls are harmless. Dynamic content and browser
fixtures use `scan(element)` / `window.outcropDeepNotation.scan(element)`.

| Owner | Edit here |
| --- | --- |
| `index.js` | Enable/remove/reorder rules; source-popup titles |
| `styles.css` | All compact notation typography, colors, source cues and hidden original source |
| `source.js` | Common surfaces/opt-out boundary, preserved source DOM, Unicode popup ranges, accessible source buttons |
| `presentation.js` | Pure presentation trees: text, sequences, grouping, superscripts, subscripts and inherited style; one DOM painter |
| `composition.js` | Source-coordinate ranges, lexical application boundaries, child presentation reads and source-preserving range moves; no datatype knowledge |
| `universe.js` | Level primitives, explicit level-name convention, level parameter marking |
| `numeric.js` | Natural literal help, certified/explicit/resolved-builtin natural expressions, Fin indices and shared atomic-notation parenthesis elision |
| `projections.js` | Record subscripts and pair postfixes |
| `vectors.js` | Configured resolved vector types with single-letter bases and compact natural indices, and certified closed vector terms |

Keep rules small and without independent listeners/observers. Register them in
`rules` in `index.js`, preserving its child-before-parent order: universe and
numeric rules publish child presentations before vector types consume
them; projections then run before bottom-up vector terms. Nested vectors inside
elements compose independently, while a cons-tail subtree remains a suffix
barrier. Redundant parentheses are hidden last. Original-source popups unwrap
presentation layers centrally, not in each rule. The
universe preparation pass also styles certified/conventional parameters outside
code. Raw opt-out disables compact rewriting, not this existing parameter font
convention. Do not add a second scanner or globals for individual rule families.

To add a kind: add its recognizer here, register its rule and source title in
`index.js`, add its CSS in `styles.css`, and test eligibility, negative examples,
raw opt-out, original copied text, Unicode anchors, repeated/dynamic scans and
hover/modal behavior. To remove a kind, remove its rule/title/style and any
unused producer metadata together; do not leave compatibility scanners behind.

The template loads the stylesheet with an AssetBundle content version. Relative
font URLs resolve from this directory; JavaScript imports resolve within the
same immutable runtime generation as the reader and modal documents.

## Semantic producers are not display owners

Core remains independent of Site. `core/agda_semantics.py` emits certified
numeric/level attributes; `core/projection_notation.py` validates projection
evidence from the optional Agda adapter. `core/vector_notation.py` publishes
source-shape candidates with checked or explicitly authored types, or untyped
inline candidates without invented AST/type metadata; the Site
rule still verifies configured linked type/constructor identities. They do not choose CSS, scan browser DOM
or own popup behavior. Keep this distinction: moving compiler inference into
this browser registry would lose reliable semantic boundaries.

Syntax/term highlighting, QED endings and the dotted-operator font repair are
not compact mathematical rewrites and retain their existing owners.

Consecutive successors use `⁺` once, `⁺⁺` twice and a superscript count from
three onward (`⁺³`, `⁺⁴`, `⁺¹²`) for both natural numbers and universe levels.
Universe joins retain their grouping, for example `(ℓ₁ ⊔ ℓ₂)⁺³`.
## Composition contract

1. Each recognizer certifies only its own mathematical operation. Numeric
   evidence is independent of the surrounding datatype; a vector recognizer
   never parses `zero`/`suc` or imports the numeric owner.
2. Recognizers produce trees from `presentation.js`, not flattened display
   strings or custom `::before`/`::after` layouts. `superscript(A, successor(n, 3))`
   retains both levels. `plain` supplies a readable label, not the painted tree.
   All existing notation families use the same painter and CSS primitives.
3. `makeBadge` stores the tree and atomicity alongside unchanged source DOM.
   Its generated glyph spans use CSS content and contain no text nodes, so
   source offsets and copying are independent of nesting depth.
4. Children run before consuming parents. `composition.presentation` reads
   child trees by source range; vector exponents/entries and record indices
   consume those trees without understanding the child's syntax. A parent's
   visual eligibility bounds are independent of a child's meaning. Rejecting
   a parent does not suppress an eligible child.
5. `wrapRange` moves complete source nodes and rejects partial compiler wrappers.
   Source popups centrally unwrap nested badges and rebase Unicode ranges.
   No per-family clone, copy handler, hover listener or observer is needed.

New notation should add a recognizer, tree construction, registry entry and
eligibility/composition tests. Add a CSS primitive only for a genuinely new
layout operation, not for every combination of existing scripts/styles. Test
composition both when the parent renders and when it stays raw, plus original
text/IDs, repeat scans, raw opt-out and popup/modal behavior. Do not add
parent-specific numeric fallbacks or flatten child trees into labels.

## Regression entry points

- `tests/test_universe_levels.py`, `tests/test_deep_notation.py`
- `tests/browser-projections.html`
- Consumer integration: universe, mathematical-notation and mobile-reader
  fixtures, served against the newly built runtime, not copied scripts

Refactoring must not alter rendered notation, source text, links, AST identity,
keyboard/touch behavior or the independently configured instance policies.
