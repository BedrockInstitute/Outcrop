"""Explicit project data for framework tests; no consuming repository is read."""
from pathlib import Path
from outcrop.site.site_config import SiteConfig

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples/renderer'


def site_config(**overrides):
    # Some historical scenarios use these synthetic module labels. Their meaning
    # comes only from this supplied policy, never a framework special case.
    return SiteConfig.load(EXAMPLE / 'project.json', root=EXAMPLE).with_overrides(
        **{'landing_module': 'Origin', 'prelude_module': 'Base.Prelude',
           'visible_import_chapters': ['Origin'], 'base_url': '',
           'canonical': 'https://lantern.example',
           'source_tree': 'https://code.example/lantern/text/chapters',
           'source_extension': '.lagda.md', **overrides})
