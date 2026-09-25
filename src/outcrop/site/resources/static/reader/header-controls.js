/* Explicit compact-header disclosures. AGPL-3.0-only. */
import { cfg } from './document.js';

export function initHeaderControls() {
  const header = document.getElementById('topbar');
  const search = header?.querySelector('.search-form');
  const languages = document.getElementById('lang-switch');
  if (!search || !languages) return;
  const compact = window.matchMedia('(max-width: 42rem)');
  const labels = {
    en: ['Search', 'Choose language'],
    zh: ['搜索', '切换语言'],
    ja: ['検索', '言語を切り替える']
  }[cfg.lang] || ['Search', 'Choose language'];
  const icons = [
    '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    '<path d="M3 5h12M9 3v2M5 5c1 5 4 8 9 10M13 5c-1 5-4 8-10 11M14 21l4-10 4 10M16 17h4"/>'
  ];
  search.id = 'header-search';
  let active = null;
  const entries = [search, languages].map((panel, index) => {
    const button = document.createElement('button');
    button.id = index ? 'language-toggle' : 'search-toggle';
    button.className = 'header-disclosure';
    button.type = 'button';
    button.title = labels[index];
    button.setAttribute('aria-label', labels[index]);
    button.setAttribute('aria-controls', panel.id);
    button.setAttribute('aria-expanded', 'false');
    button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + icons[index] + '</svg>';
    panel.before(button);
    const entry = { panel, button };
    button.addEventListener('click', event => {
      // Focusing the search may start a request; the same click is not outside it.
      event.stopPropagation();
      const opening = active !== entry;
      setActive(opening ? entry : null);
      if (opening) panel.querySelector(index ? 'a' : 'input')?.focus({ preventScroll: true });
    });
    return entry;
  });
  function setActive(entry, restoreFocus = false) {
    const previous = active;
    active = compact.matches ? entry : null;
    entries.forEach(item => {
      const open = active === item;
      item.panel.classList.toggle('header-panel-open', open);
      item.panel.inert = compact.matches && !open;
      item.button.setAttribute('aria-expanded', String(open));
    });
    if (restoreFocus && previous) previous.button.focus({ preventScroll: true });
  }
  document.addEventListener('click', event => {
    if (active && !active.panel.contains(event.target) && !active.button.contains(event.target)) setActive(null);
  });
  document.addEventListener('focusin', event => {
    if (active && !active.panel.contains(event.target) && !active.button.contains(event.target)) setActive(null);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && active && !event.isComposing) {
      event.preventDefault();
      setActive(null, true);
    }
  });
  function resize() {
    const focused = entries.find(item => item.panel.contains(document.activeElement));
    setActive(null);
    if (compact.matches && focused) focused.button.focus({ preventScroll: true });
  }
  compact.addEventListener('change', resize);
  document.addEventListener('outcrop:sidebar-open', () => setActive(null));
  document.addEventListener('outcrop:section-menu-open', () => setActive(null));
  header.classList.add('header-controls-ready');
  resize();
}
