#!/usr/bin/env python3
"""Exercise the real optional producer without Bedrock or Cubical installed."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agda', type=Path, required=True)
    args = parser.parse_args()
    agda = args.agda.resolve()
    with tempfile.TemporaryDirectory(prefix='outcrop-agda-smoke-') as temporary:
        root = Path(temporary).resolve()
        source = root / 'chapters'
        source.mkdir()
        (root / 'agda-home').mkdir()
        (root / 'smoke.agda-lib').write_text('name: smoke\ninclude: chapters\n')
        (source / 'Seed.lagda.md').write_text('''# Seed

```agda
{-# OPTIONS --safe #-}
module Seed where

data Marker : Set where
  mark : Marker

identity : {A : Set} → A → A
identity x = x

module Box (A : Set) where
  same : A → A
  same x = x
```
''', encoding='utf-8')
        (source / 'Start.lagda.md').write_text('''# Start

```agda
{-# OPTIONS --safe #-}
module Start where
open import Seed

result : Marker
result = identity mark

boxed : Marker → Marker
boxed x = same x
  where open Box Marker

local : Marker → Marker
local x = helper x
  where
  helper : Marker → Marker
  helper y = y

split : Marker → Marker
```

The body is deliberately in a separate literate fence.

```agda
split x = x

inferred = mark

explicitHole : _
explicitHole = mark

withClause : Marker → Marker
withClause x with x
... | mark = mark

data Empty : Set where
absurd : Empty → Marker
absurd ()

data Flag : Set where
  on : Flag

mutual
  data Left : Set where
    left : Right → Left

  data Right : Set where
    right : Left → Right

mutual
  data TypeCode : Set where
    atom : TypeCode
    arrow : (a : TypeCode) (b : Meaning a → TypeCode) → TypeCode

  Meaning : TypeCode → Set
  Meaning atom = Marker
  Meaning (arrow a b) = (x : Meaning a) → Meaning (b x)

interleaved mutual
  data U : Set
  El : U → Set

  data U where
    base : U
  El _ = Marker
  data _ where
    later : U
```
''', encoding='utf-8')
        environment = {**os.environ, 'GHCRTS': '-A64m -I0 -M8g',
                       'AGDA_DIR': str(root / 'agda-home')}
        def run(*options):
            subprocess.run([sys.executable, '-m', 'outcrop', *options], env=environment, check=True)
        check_options = ('agda-check', '--agda', str(agda), '--project-root', str(root),
            '--src', 'chapters', '--root', 'Start', '--jobs', '2',
            '--options=--safe',
            '--trace-out', str(root / 'trace.jsonl'), '--html-dir', str(root / 'html'))
        run(*check_options)
        evidence = (root / 'trace.jsonl').read_bytes()
        run(*check_options)
        assert (root / 'trace.jsonl').read_bytes().startswith(evidence), 'warm build discarded trace'
        run('extract-expressions', '--src', str(source), '--html-dir', str(root / 'html'),
            '--trace', str(root / 'trace.jsonl'), '--out', str(root / 'expressions.json'))
        run('extract-types', '--src', str(source), '--html-dir', str(root / 'html'),
            '--agda', str(agda), '--entry', 'Start', '--options=--safe',
            '--out', str(root / 'types.json'))
        types = json.loads((root / 'types.json').read_text())
        assert types['Start']['result'] == 'Seed.Marker', types
        trace = (root / 'trace.jsonl').read_text()
        assert '__DUMMY_TYPE__' not in trace and 'dummyType' not in trace
        expressions = json.loads((root / 'expressions.json').read_text())
        assert expressions['Start'], expressions
        ends = {module: {node['name']: node for node in nodes if node['kind'] == 'definition-end'}
                for module, nodes in expressions.items()}
        declarations = [(record['kind'], record['path'].rsplit('/', 1)[-1],
                         record['start'], record['end'])
                        for line in trace.splitlines() if
                        (record := json.loads(line))['kind'] in
                        {'signature', 'definition-end', 'data-end', 'mutual-data-end'}]
        assert set(ends['Seed']) == {'Marker', 'identity', 'same'}, (ends, declarations)
        assert set(ends['Start']) == {
            'result', 'boxed', 'local', 'split', 'explicitHole', 'withClause',
            'Empty', 'Flag', 'Left, Right', 'TypeCode, Meaning', 'U, El',
        }, ends
        text = (source / 'Start.lagda.md').read_text()
        assert text[ends['Start']['local']['end'] - 2] == 'y', ends
        assert text[ends['Start']['split']['start'] - 1:].startswith('split :'), ends
        for name, last_line in (
            ('Empty', 'data Empty : Set where'),
            ('Flag', 'on : Flag'),
            ('Left, Right', 'right : Left → Right'),
            ('TypeCode, Meaning', 'Meaning (arrow a b) = (x : Meaning a) → Meaning (b x)'),
            ('U, El', 'later : U'),
        ):
            expected_end = text.index(last_line) + len(last_line) + 1
            assert ends['Start'][name]['end'] == expected_end, (name, ends['Start'][name], expected_end)
        seed = (source / 'Seed.lagda.md').read_text()
        assert ends['Seed']['Marker']['end'] == seed.index('mark : Marker') + len('mark : Marker') + 1
        print('Outcrop Agda smoke: real safe non-Cubical source, Unicode ranges, name types, expression trace and module application passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
