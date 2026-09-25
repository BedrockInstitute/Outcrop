"""Conservative documentation-only CI classification from explicit Git inputs.

No network or implicit project discovery. Unknown paths, missing history, manual
runs and invalid policies select the full pipeline. Lightweight checks always
remain the caller's responsibility.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE)


def revision(value: str) -> str:
    if not re.fullmatch(r'[0-9a-f]{40,64}', value) or not value.strip('0'):
        raise ValueError('missing or invalid comparison revision')
    return value


def read_policy(path: Path) -> dict:
    policy = json.loads(path.read_text(encoding='utf-8'))
    if set(policy) != {'files', 'markdown_trees', 'submodules'}:
        raise ValueError('invalid documentation policy keys')
    for key in ('files', 'markdown_trees'):
        if not isinstance(policy[key], list):
            raise ValueError('documentation paths must be lists')
    if not isinstance(policy['submodules'], dict):
        raise ValueError('submodules must map paths to policy paths')
    paths = [*policy['files'], *policy['markdown_trees'],
             *policy['submodules'], *policy['submodules'].values()]
    for item in paths:
        if (not isinstance(item, str) or not item or
                PurePosixPath(item).is_absolute() or '..' in PurePosixPath(item).parts):
            raise ValueError('policy paths must be relative and contained')
    return policy


def documentation(path: str, policy: dict) -> bool:
    # Literate source is executable even when it lives in a documentation tree.
    if path.endswith('.lagda.md'):
        return False
    return path in policy['files'] or (
        path.endswith('.md') and any(path.startswith(tree.rstrip('/') + '/')
                                   for tree in policy['markdown_trees']))


def gitlink(root: Path, commit: str, path: str) -> str:
    entry = git(root, 'ls-tree', '-z', commit, '--', path).rstrip('\0')
    metadata, name = entry.split('\t')
    mode, kind, sha = metadata.split()
    if mode != '160000' or kind != 'commit' or name != path:
        raise ValueError('changed path is not an existing submodule')
    return revision(sha)


def docs_diff(root: Path, base: str, head: str, policy: dict,
              *, merge_base: bool = False) -> bool:
    base, head = revision(base), revision(head)
    if merge_base:
        base = revision(git(root, 'merge-base', base, head).strip())
    # No rename folding: both the removed and added paths must be safe. NUL
    # delimiters preserve spaces/newlines; Git's full diff has no API file cap.
    paths = git(root, 'diff', '--name-only', '--no-renames', '-z',
                base, head, '--').split('\0')
    for path in filter(None, paths):
        if path in policy['submodules']:
            child = root / path
            nested = read_policy(child / policy['submodules'][path])
            if nested['submodules']:
                raise ValueError('nested submodule policies are not supported')
            if not docs_diff(child, gitlink(root, base, path),
                             gitlink(root, head, path), nested):
                return False
        elif not documentation(path, policy):
            return False
    return True


def classify(root: Path, policy_path: Path, event_name: str,
             event: dict, head: str) -> tuple[bool, str]:
    """Return (full_pipeline, reason); uncertainty never skips a check."""
    if event_name not in {'push', 'pull_request'}:
        return True, 'manual or unsupported event: full pipeline'
    try:
        base = (event['before'] if event_name == 'push'
                else event['pull_request']['base']['sha'])
        docs_only = docs_diff(root, base, head, read_policy(policy_path),
                              merge_base=event_name == 'pull_request')
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
        return True, 'comparison unavailable or invalid: full pipeline'
    return (False, 'documentation-only changes') if docs_only else (
        True, 'changes outside documentation allowlist: full pipeline')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        full, reason = classify(args.project_root, args.policy,
                                os.environ.get('GITHUB_EVENT_NAME', ''), event,
                                os.environ.get('GITHUB_SHA', ''))
    except (OSError, ValueError, KeyError):
        full, reason = True, 'event payload unavailable: full pipeline'
    result = 'true' if full else 'false'
    print(f'CI scope: full={result}; {reason}')
    if output := os.environ.get('GITHUB_OUTPUT'):
        with open(output, 'a', encoding='utf-8') as stream:
            stream.write(f'full={result}\n')
    if summary := os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write(f'### CI scope\n\n`full={result}`: {reason}.\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
