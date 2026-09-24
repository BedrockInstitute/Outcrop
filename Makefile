PYTHON ?= python3
PY ?= .venv/bin/python

.PHONY: venv test lint example check serve
venv:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install -e .

test:
	$(PY) -m unittest discover -s tests -p 'test_*.py' -v

lint:
	$(PY) -m outcrop lint --config examples/renderer/project.json --project-root examples/renderer

example:
	$(PY) -m outcrop build --config examples/renderer/project.json --project-root examples/renderer --out _build/example/academy
	$(PY) -m outcrop check-links _build/example/academy

check: test lint example

serve:
	$(PY) -m http.server 8000 --directory _build/example
