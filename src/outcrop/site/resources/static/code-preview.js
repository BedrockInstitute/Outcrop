/* Progressive disclosure for source-preserving Agda code previews. */
(function () {
  const labels = {
    en: ['Show remaining code', 'Collapse code'],
    zh: ['展开剩余代码', '收起代码'],
    ja: ['残りのコードを表示', 'コードを折りたたむ'],
  };

  function start() {
    const lang = document.documentElement.lang;
    const [expandLabel, collapseLabel] = labels[lang] || labels.en;
    document.querySelectorAll('.agda-code-preview[data-preview-lines]').forEach((preview, index) => {
      const clip = preview.querySelector(':scope > .agda-code-preview-clip');
      const pre = clip?.querySelector(':scope > pre.Agda');
      const code = pre?.querySelector('.agda-code-content');
      const toggle = preview.querySelector(':scope > .agda-code-preview-toggle');
      const count = Number(preview.dataset.previewLines);
      if (!pre || !code || !toggle || !Number.isSafeInteger(count) || count < 1) return;
      const sourceLines = code.textContent.replace(/\n$/, '').split('\n').length;
      if (sourceLines <= count) return;

      function measure() {
        const style = getComputedStyle(pre);
        const height = count * parseFloat(style.lineHeight)
          + parseFloat(style.paddingTop) + parseFloat(style.paddingBottom)
          + parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
        if (Number.isFinite(height)) preview.style.setProperty('--agda-preview-height', `${height}px`);
        const fullHeight = pre.getBoundingClientRect().height;
        if (fullHeight > 0) preview.style.setProperty('--agda-preview-full-height', `${Math.ceil(fullHeight) + 2}px`);
      }
      function setExpanded(expanded) {
        preview.classList.toggle('is-collapsed', !expanded);
        toggle.setAttribute('aria-expanded', String(expanded));
        toggle.textContent = expanded ? collapseLabel : expandLabel;
      }
      measure();
      clip.id ||= `agda-code-preview-${index}`;
      toggle.setAttribute('aria-controls', clip.id);
      setExpanded(false);
      toggle.hidden = false;
      requestAnimationFrame(() => preview.classList.add('is-ready'));
      toggle.addEventListener('click', () => setExpanded(preview.classList.contains('is-collapsed')));
      pre.addEventListener('focusin', () => setExpanded(true));
      function revealHash() {
        let id;
        try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
        if (id && preview.contains(document.getElementById(id))) setExpanded(true);
      }
      revealHash();
      window.addEventListener('hashchange', revealHash);
      window.addEventListener('resize', measure, { passive: true });
      document.fonts?.ready.then(measure);
      if ('ResizeObserver' in window) new ResizeObserver(measure).observe(pre);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
