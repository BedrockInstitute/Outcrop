# Initial extraction acceptance, 2026-09-24

Outcrop Core and Outcrop Site were extracted from Bedrock revision
`956682cba77d75259b7b2584dd0e071a6ab7b42d`. No mathematical source or compiler
instrumentation was changed. The independent Python production implementation
and real Bedrock adapters total 9,700 lines versus 9,881 before this cleanup;
new browser code implements the additionally requested landscape reading feature.

## Verified

- 130 reusable unit tests pass, including installed-package boundaries, real
  owner interfaces, 120-level hover/history lifetimes and rotated coordinates.
- Strict example lint and a complete trilingual example build pass; its 393
  relative links across 17 pages have no missing targets.
- An isolated Python 3.11 environment installs the wheel and runs the reusable
  tests. Outside the Bedrock checkout, with no Agda on PATH, it builds the example.
  The wheel contains templates, JavaScript modules, workers, fonts and vendor data.
- A real Chrome session through computer-use tools exercises two independently
  branded sites on one origin, namespaced preferences/progress, ordinary Markdown,
  semantic data and publication: 22 browser assertions pass.
- Bedrock integration runs its 256 unit tests and whole-project gates. The full
  282-module, three-edition build has 1,116,324 relative links across 854 pages,
  with no broken target. Its 44,808 search records resolve to 80,196 edition
  targets, all present.
- Reader browser fixtures cover source/type hover and modal inspection (132),
  directory/search/graph gestures (90), horizontal code padding (28), appearance
  palettes (136), universe notation (65) and dotted fonts (15).
- A 390px simulated coarse-pointer fixture adds 25 checks: immediate loading,
  cancellation and persistence, original-DOM landscape code, transformed leaf/
  parent gestures, recursive hover, safe-area variables, a non-scrolling close
  control, modal transition, near-bottom restoration, Escape and search hysteresis.
  Actual button clicks additionally verify the landscape entry and exit controls.

The final reader runtime is `f0e5481f2e1a2907`. Source-level independent review
found two landscape edge cases, both fixed before this acceptance: a scrolling
close control, and restoring modal scroll before the parent iframe had resized.
The latter now uses a source-validated, surface-ID-correlated layout acknowledgement.

## Limits and reproduction

The browser runs are Chrome with actual interaction plus explicitly synthesized
touch/gesture scenarios. A narrow/coarse-pointer frame is **not an iPhone Safari
test**. The native Safari automation window was unavailable; physical-device
Safari behavior remains a manual acceptance step. Browser viewport filling uses
a rotated CSS surface, not device orientation locking or a promise to hide browser
chrome. Safe-area variables are checked structurally, not measured on an iPhone.

Run `make check` in Outcrop after installation. Build browser fixtures with
`python scripts/build-renderer-fixtures.py --out _build/browser`, serve that
directory, and open `/renderer-regression.html`. Bedrock's integration fixtures
remain with its real corpus in `scripts/tests/`; its local regression server
must point to the newly built output. Network timing probes impose a 500ms type
request delay and record events in the same frame's clock. They do not claim
Core Web Vitals or mobile-device performance measurements.
