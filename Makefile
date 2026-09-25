PYTHON ?= python3
PY ?= .venv/bin/python
PORT ?= 8000
EXAMPLE_OUT ?= _build/example/academy
.DEFAULT_GOAL := help

.PHONY: help venv test lint example check serve
help:
	@printf '%s\n' 'Setup: venv' 'Checks: test lint example check' \
	  'Preview: serve (PORT=8000 EXAMPLE_OUT=_build/example/academy)' \
	  'example builds and checks links/search; check does not run browser acceptance.'

venv:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install -e .

test:
	$(PY) -m unittest discover -s tests -p 'test_*.py' -v

lint:
	$(PY) -m outcrop lint --config examples/renderer/project.json --project-root examples/renderer

example:
	$(PY) -m outcrop build --config examples/renderer/project.json --project-root examples/renderer --out $(EXAMPLE_OUT)
	$(PY) -m outcrop check-links $(EXAMPLE_OUT)
	$(PY) -m outcrop check-search $(EXAMPLE_OUT)

check: test lint example

serve:
	$(PY) -m http.server $(PORT) --directory $(dir $(EXAMPLE_OUT))
