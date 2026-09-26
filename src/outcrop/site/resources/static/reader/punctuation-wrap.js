/* Conservative line-fit adjustment on top of the browser's native wrapping.
 * Never split/clone source nodes: Agda links, selection, and hover ranges stay put. */

const TERMINAL_PUNCTUATION = /[。．.!！?？]$/u;
const PROFILES = {
  en: { fit: [], rescue: [-.004, -.008, -.012, -.016, -.02, -.024, -.028, -.032, -.036, -.04] },
  zh: { fit: [-.004, .004, -.008, .008, -.012, -.016, -.02],
        rescue: [-.004, -.008, -.012, -.016, -.02, -.024, -.028, -.032, -.036, -.04] },
  ja: { fit: [-.003, .003, -.006, .006, -.009, -.012, -.015],
        rescue: [-.003, -.006, -.009, -.012, -.015, -.018, -.021, -.024, -.028, -.032, -.036, -.04] },
};

function finalGlyphs(paragraph) {
  const nodes = [];
  const walker = document.createTreeWalker(paragraph, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) nodes.push(node);
  const glyphs = [];
  for (let i = nodes.length - 1; i >= 0 && glyphs.length < 2; i--) {
    node = nodes[i];
    if (node.parentElement?.closest('[hidden], template, script, style, .sr-only, .katex-mathml, .prose-annotation-note, .single-line-code-note') ||
        !node.parentElement?.getClientRects().length) continue;
    const matches = [...node.data.matchAll(/\S/gu)];
    for (let j = matches.length - 1; j >= 0 && glyphs.length < 2; j--) {
      const match = matches[j];
      glyphs.push({ node, start: match.index, end: match.index + match[0].length, text: match[0] });
    }
  }
  return glyphs;
}

function glyphRect(glyph) {
  const range = document.createRange();
  range.setStart(glyph.node, glyph.start);
  range.setEnd(glyph.node, glyph.end);
  return range.getClientRects()[0];
}

export function strandedPunctuation(paragraph) {
  const [last, previous] = finalGlyphs(paragraph);
  if (!last || !previous || !TERMINAL_PUNCTUATION.test(last.text)) return false;
  const lastRect = glyphRect(last);
  const previousRect = glyphRect(previous);
  return !!(lastRect && previousRect && lastRect.top > previousRect.bottom + 1);
}

function lineFit(paragraph) {
  const style = getComputedStyle(paragraph);
  const em = parseFloat(style.fontSize);
  const right = paragraph.getBoundingClientRect().right - parseFloat(style.paddingRight);
  if (!em || !Number.isFinite(right)) return null;
  const rows = [];
  const walker = document.createTreeWalker(paragraph, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (!node.data.trim() || node.parentElement?.closest(
      '[hidden], template, script, style, .sr-only, .katex-mathml, .prose-annotation-note, .single-line-code-note')) continue;
    const range = document.createRange();
    range.selectNodeContents(node);
    for (const rect of range.getClientRects()) {
      if (!rect.width || !rect.height) continue;
      const middle = rect.top + rect.height / 2;
      let row = rows.find(item => Math.abs(item.middle - middle) < em * .45);
      if (!row) rows.push(row = { middle, right: rect.right });
      row.right = Math.max(row.right, rect.right);
    }
  }
  rows.sort((a, b) => a.middle - b.middle);
  if (rows.length < 2) return null;
  const gaps = rows.slice(0, -1).map(row => Math.max(0, (right - row.right) / em));
  return {
    count: rows.length,
    maxGap: Math.max(...gaps),
    score: gaps.reduce((sum, gap) => sum + Math.min(gap, 5) ** 2, 0),
  };
}

function applyTracking(paragraph, step) {
  if (step) {
    paragraph.style.setProperty('--punctuation-tracking', `${step}em`);
    paragraph.classList.add('punctuation-tracking');
  } else {
    paragraph.classList.remove('punctuation-tracking');
    paragraph.style.removeProperty('--punctuation-tracking');
  }
}

function chooseTracking(paragraph, profile) {
  applyTracking(paragraph, 0);
  const orphan = strandedPunctuation(paragraph);
  if (!orphan && (!profile.fit.length || paragraph.textContent.length > 1100)) return;
  const initial = lineFit(paragraph);
  if (!initial) return;
  if (orphan) {
    // Existing terminal-punctuation rescue remains the first priority. Choose
    // the smallest change that rejoins the glyph without adding another line.
    for (const step of profile.rescue) {
      applyTracking(paragraph, step);
      const fit = lineFit(paragraph);
      if (!strandedPunctuation(paragraph) && fit && fit.count <= initial.count) return;
    }
    applyTracking(paragraph, 0);
    return;
  }
  // English relies on native word wrapping/pretty; global letter spacing is a
  // poor substitute for word-space adjustment. CJK receives only small trials.
  if (initial.count > 12 ||
      initial.maxGap < 1.1) return;
  let bestStep = 0;
  let bestScore = initial.score;
  for (const step of profile.fit) {
    applyTracking(paragraph, step);
    const fit = lineFit(paragraph);
    if (!fit || fit.count > initial.count || strandedPunctuation(paragraph) ||
        fit.maxGap > initial.maxGap + .25) continue;
    const score = fit.score + Math.abs(step) * 24;
    if (score < bestScore) {
      bestStep = step;
      bestScore = score;
    }
  }
  // A fractional-em improvement is not worth visibly changing the texture.
  if (initial.score - bestScore < .35 || bestScore > initial.score * .88) bestStep = 0;
  applyTracking(paragraph, bestStep);
}

export function initPunctuationWrap() {
  const article = document.querySelector('article');
  if (!article) return;
  const profile = PROFILES[document.documentElement.lang] || PROFILES.en;
  let scheduled = false;
  function adjust() {
    scheduled = false;
    for (const paragraph of article.querySelectorAll('p')) chooseTracking(paragraph, profile);
  }
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(adjust);
  }
  schedule();
  document.fonts?.ready.then(schedule);
  if (window.ResizeObserver) {
    let width = 0;
    new ResizeObserver(entries => {
      const nextWidth = entries[0].contentRect.width;
      if (Math.abs(nextWidth - width) < 0.5) return;
      width = nextWidth;
      schedule();
    }).observe(article);
  } else window.addEventListener('resize', schedule);
}
