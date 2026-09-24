"""Input discovery helpers. Callers provide paths and source conventions."""
import os
import re
from pathlib import Path
from outcrop.core.term_registry import TERM_MARK_RE


def source_paths(root, extension):
    """Discover authored modules using the caller's explicit suffix convention."""
    root = Path(root)
    return {str(path.relative_to(root))[:-len(extension)].replace(os.sep, '.'): path
            for path in sorted(root.rglob('*' + extension))}


class SourceCorpus:
    """Explicit document inputs; compiler output may supplement plain masters."""
    def __init__(self, config, *, source_dir=None, highlighted_dir=None):
        self.source_dir = Path(source_dir) if source_dir else config.path(config.sources)
        self.sources = source_paths(self.source_dir, config.source_extension)
        self.documents = {module: (path, True) for module, path in self.sources.items()}
        highlighted = highlighted_dir or (config.path(config.highlighted) if config.highlighted else None)
        if highlighted:
            self.documents = {}
            for path in sorted(Path(highlighted).glob('*')):
                if path.suffix in ('.md', '.html'):
                    self.documents[path.stem] = (path, path.suffix == '.md')
            missing = set(self.sources) - self.documents.keys()
            if missing:
                raise ValueError('compiler input missing project chapters: ' + ', '.join(sorted(missing)))

    def read(self, module):
        path, literate = self.documents[module]
        return path.read_text(encoding='utf-8'), literate

    def closure(self, selected):
        """Reachable highlighted pages, including transitive modal destinations."""
        visited, pending = set(), list(selected)
        while pending:
            module = pending.pop()
            if module in visited:
                continue
            visited.add(module)
            text, _ = self.read(module)
            linked = set(re.findall(r'href="([^"#]+)\.html(?:#[^"]*)?"', text))
            pending.extend((linked & self.documents.keys()) - visited)
        return visited


def sort_reader_terms(terms, reading_data, src, extension=".lagda.md"):
    """Order terms by their first marked introduction in the reading order."""
    chapter_order = {node["id"]: node["order"] for node in reading_data["nodes"]}
    positions = {}
    for entry in terms:
        path = os.path.join(src, entry["introduced_in"].replace(".", os.sep) + extension)
        try:
            text = Path(path).read_text(encoding='utf-8')
        except OSError:
            text = ""
        match = next((m for m in TERM_MARK_RE.finditer(text)
                      if m.group(2) == "intro" and m.group(3) == entry["id"]), None)
        positions[entry["id"]] = (chapter_order.get(entry["introduced_in"], 10**9),
                                   match.start() if match else 10**9)
    return sorted(terms, key=lambda entry: positions[entry["id"]])
