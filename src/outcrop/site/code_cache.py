"""Optional, explicit cache of the compiler-derived book-wide code context."""
from dataclasses import fields
import gzip
import json
from pathlib import Path

from outcrop.core.document_renderer import CodeContext


def _pack(value):
    if isinstance(value, tuple):
        return {'__outcrop_tuple__': [_pack(item) for item in value]}
    if isinstance(value, set):
        return {'__outcrop_set__': [_pack(item) for item in sorted(value, key=repr)]}
    if isinstance(value, list):
        return [_pack(item) for item in value]
    if isinstance(value, dict):
        return {key: _pack(item) for key, item in value.items()}
    return value


def _unpack(value):
    if isinstance(value, list):
        return [_unpack(item) for item in value]
    if isinstance(value, dict):
        if set(value) == {'__outcrop_tuple__'}:
            return tuple(_unpack(item) for item in value['__outcrop_tuple__'])
        if set(value) == {'__outcrop_set__'}:
            return {_unpack(item) for item in value['__outcrop_set__']}
        return {key: _unpack(item) for key, item in value.items()}
    return value


def read_context(path, key, semantics, internal, rendered):
    try:
        payload = json.loads(gzip.decompress(Path(path).read_bytes()))
        if payload.get('schema') != 1 or payload.get('key') != key:
            return None
        values = _unpack(payload['context'])
        if values['internal'] != set(internal) or values['rendered'] != set(rendered):
            return None
        expected = {field.name for field in fields(CodeContext)} - {'semantics'}
        if set(values) != expected:
            return None
        return CodeContext(semantics=semantics, **values)
    except (OSError, EOFError, ValueError, TypeError, KeyError, gzip.BadGzipFile):
        return None


def write_context(path, key, code):
    values = {field.name: getattr(code, field.name) for field in fields(CodeContext)
              if field.name != 'semantics'}
    payload = json.dumps({'schema': 1, 'key': key, 'context': _pack(values)},
                         ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(gzip.compress(payload, compresslevel=1))
    temporary.replace(path)
