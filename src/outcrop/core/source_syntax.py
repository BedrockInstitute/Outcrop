"""Shared source-level Agda fence/import grammar; no project discovery."""
import re

AGDA_FENCE = re.compile(r'^```agda\s*\n(.*?)^```\s*$', re.M | re.S)
# Agda names are tokens, not Python identifiers: hyphens, primes and many
# mathematical characters are legal. Never silently turn a complete module
# name into an unrelated prefix. Its internal qualified-name grammar remains
# the compiler's responsibility.
IMPORT = re.compile(r'^\s*(?:open\s+)?import\s+([^\s(){};]+)', re.M)
ROUTE_METADATA_RE = re.compile(r'<!--\s*outcrop-routes\s*\{.*?\}\s*-->', re.S)


def imports(text):
    return [name for block in AGDA_FENCE.findall(text) for name in IMPORT.findall(block)]


def strip_route_metadata(text):
    """Blank legacy route annotations while preserving source coordinates."""
    return ROUTE_METADATA_RE.sub(lambda match: re.sub(r'[^\n]', ' ', match[0]), text)
