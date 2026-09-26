/* Explicit compact-header disclosures. AGPL-3.0-only. */
export function initHeaderControls() {
  const header = document.getElementById('topbar');
  const search = header?.querySelector('.search-form');
  const languages = document.getElementById('lang-switch');
  if (!search || !languages) return;
  const compact = window.matchMedia('(max-width: 42rem)');
  let active = null;
  const entries = [search, languages].map((panel, index) => {
    const button = document.getElementById(index ? 'language-toggle' : 'search-toggle');
    if (!button) return null;
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
  if (entries.some(entry => !entry)) return;
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
