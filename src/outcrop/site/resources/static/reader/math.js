/* Outcrop reader: math. AGPL-3.0-only. */

  /* ---- math (client-side KaTeX over pre-wrapped spans) -------------------- */
  function renderMath() {
    if (typeof katex === "undefined") return;
    document.querySelectorAll(".math:not([data-math-rendered])").forEach(function (el) {
      var disp = el.classList.contains("display");
      var tex = el.textContent.trim().replace(/^\${1,2}/, "").replace(/\${1,2}$/, "");
      try {
        katex.render(tex, el, { displayMode: disp, throwOnError: false });
        el.dataset.mathRendered = 'true';
      }
      catch (e) { /* leave the source text in place on error */ }
    });
  }


export { renderMath };
document.addEventListener('outcrop:math-ready', renderMath);
