"""Mark off-site HTML anchors without changing local navigation or markup."""

from html import unescape
import re
from urllib.parse import urlsplit


ANCHOR = re.compile(r'<a\b(?:"[^"]*"|\'[^\']*\'|[^\'">])*?>', re.I)
ATTRIBUTE = re.compile(r'([\w:-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)


def external_links_new_window(html: str, canonical: str) -> str:
    """Open absolute HTTP(S) links to other origins in a separate browser tab.

    Local paths, fragments and absolute canonical URLs remain ordinary site links,
    so their existing modal and structural navigation rules still apply.
    """
    site = urlsplit(canonical)

    def origin(address):
        scheme = (address.scheme or site.scheme).lower()
        if scheme not in {'http', 'https'} or not address.hostname:
            return None
        return scheme, address.hostname.lower(), address.port or (443 if scheme == 'https' else 80)

    site_origin = origin(site)

    def mark(match: re.Match[str]) -> str:
        tag = match.group()
        attrs = {name.lower(): unescape(quoted or single or bare or '')
                 for name, quoted, single, bare in ATTRIBUTE.findall(tag)}
        href = attrs.get('href', '')
        try:
            address = urlsplit(href)
            link_origin = origin(address) if address.netloc else None
        except ValueError:
            return tag
        if link_origin is None:
            return tag
        if link_origin == site_origin:
            return tag
        if attrs.get('target') != '_blank':
            if 'target' in attrs:
                tag = re.sub(r'\btarget\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)',
                             'target="_blank"', tag, count=1, flags=re.I)
            else:
                tag = tag[:-1] + ' target="_blank">'
        rel = attrs.get('rel', '').split()
        missing = {'noopener', 'noreferrer'} - set(rel)
        if missing:
            value = ' '.join([*rel, *sorted(missing)])
            if 'rel' in attrs:
                tag = re.sub(r'\brel\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)',
                             f'rel="{value}"', tag, count=1, flags=re.I)
            else:
                tag = tag[:-1] + f' rel="{value}">'
        return tag

    return ANCHOR.sub(mark, html)
