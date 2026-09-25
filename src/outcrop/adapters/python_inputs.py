"""Collect a conservative, non-executing Python dependency closure for build keys.

The caller supplies the package and entry files, and must separately fingerprint
resources, configuration and external dependencies. No project is discovered.
"""
import ast
from pathlib import Path


def dependency_files(package: Path, entries):
    package = package.resolve()
    name = package.name
    modules = {}
    for path in package.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        parts = path.relative_to(package).with_suffix('').parts
        if parts[-1] == '__init__':
            parts = parts[:-1]
        modules['.'.join((name, *parts))] = path
    if name not in modules:
        raise ValueError(f'not a Python package: {package}')
    pending = [Path(path).resolve() for path in entries]
    seen = set()

    def include(module, *, required=False):
        if module != name and not module.startswith(name + '.'):
            return
        if required and module not in modules:
            raise ValueError(f'unresolved package import: {module}')
        parts = module.split('.')
        for end in range(1, len(parts) + 1):
            prefix = '.'.join(parts[:end])
            if prefix in modules:
                pending.append(modules[prefix])

    by_path = {path: module for module, path in modules.items()}
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        module = by_path.get(path)
        if module:
            include(module)
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'importlib' or alias.name.startswith('importlib.'):
                        pending.extend(modules.values())
                    include(alias.name, required=True)
            elif isinstance(node, ast.ImportFrom):
                target = node.module or ''
                if target == 'importlib' or target.startswith('importlib.'):
                    pending.extend(modules.values())
                if node.level:
                    if not module:
                        raise ValueError(f'relative import outside package: {path}')
                    context = module.split('.') if path.name == '__init__.py' else module.split('.')[:-1]
                    if node.level > len(context):
                        raise ValueError(f'relative import escapes package: {path}')
                    target = '.'.join(context[:len(context) - node.level + 1] +
                                      (target.split('.') if target else []))
                include(target, required=True)
                for alias in node.names:
                    include(target + '.' + alias.name)
            # Dynamic imports cannot be resolved soundly by an ordinary static
            # import walk. Include the whole supplied package instead of guessing.
            elif (isinstance(node, ast.Call) and
                  ((isinstance(node.func, ast.Name) and node.func.id in {'__import__', 'import_module'})
                   or (isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module'))):
                pending.extend(modules.values())
    return sorted(seen)
