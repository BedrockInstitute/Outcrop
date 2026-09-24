/* Frame decoration only; source text and statement grammar remain untouched.
 * AGPL-3.0-only. */

function overlapsCode(pre, mark) {
  const box = mark.getBoundingClientRect();
  if (!box.width || !box.height) return false;
  const clip = (pre.querySelector(':scope > .agda-code-content') || pre).getBoundingClientRect();
  const intersects = rect => rect.width > 0 && rect.height > 0 &&
    Math.max(rect.left, clip.left) < Math.min(box.right, clip.right) &&
    Math.min(rect.right, clip.right) > Math.max(box.left, clip.left) &&
    Math.max(rect.top, clip.top) < Math.min(box.bottom, clip.bottom) &&
    Math.min(rect.bottom, clip.bottom) > Math.max(box.top, clip.top);
  const walker = document.createTreeWalker(pre, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  for (let text; (text = walker.nextNode());) {
    // Ignore whitespace and invisible source retained by specialized renderers.
    if (text.parentElement.closest('.universe-source, [hidden]') ||
        !intersects(text.parentElement.getBoundingClientRect())) continue;
    for (const match of text.data.matchAll(/\S+/gu)) {
      range.setStart(text, match.index);
      range.setEnd(text, match.index + match[0].length);
      if ([...range.getClientRects()].some(intersects)) return true;
    }
  }
  return false;
}

export function initStatementEndings() {
  const frames = new Map(), pending = new Set();
  let queued = false;
  function schedule(frame) {
    if (!frames.has(frame)) return;
    pending.add(frame);
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      const changes = [];
      for (const frame of pending) {
        const {pre, mark} = frames.get(frame);
        if (!frame.isConnected) {
          resize?.unobserve(pre);
          frames.delete(frame);
        } else changes.push([mark, overlapsCode(pre, mark)]);
      }
      pending.clear();
      // Batch geometry reads before opacity writes; no layout-affecting styles.
      for (const [mark, overlaps] of changes) mark.classList.toggle('over-code', overlaps);
    });
  }
  const resize = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(entries => {
    for (const {target} of entries) schedule(target.parentElement);
  });
  function discover(node) {
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const found = [...node.querySelectorAll('.statement-ending')];
    const parent = node.closest('.statement-ending');
    if (parent) found.push(parent);
    for (const frame of found) {
      if (!frames.has(frame)) {
        if (!frame.isConnected) continue;
        const pre = frame.querySelector(':scope > pre.Agda');
        const mark = frame.querySelector(':scope > .statement-qed');
        if (!pre || !mark) continue;
        frames.set(frame, {pre, mark});
        resize?.observe(pre);
      }
      schedule(frame);
    }
  }
  discover(document.body);
  new MutationObserver(records => {
    for (const record of records) {
      const parent = record.target.nodeType === Node.ELEMENT_NODE ? record.target : record.target.parentElement;
      schedule(parent?.closest('.statement-ending'));
      for (const node of record.addedNodes) discover(node);
      for (const node of record.removedNodes) discover(node);
    }
  }).observe(document.body, {childList: true, subtree: true, characterData: true});
  document.addEventListener('scroll', event => {
    schedule(event.target.closest?.('.statement-ending'));
  }, {capture: true, passive: true});
  const refresh = () => frames.forEach((_, frame) => schedule(frame));
  window.addEventListener('resize', refresh, {passive: true});
  document.fonts?.ready.then(refresh);
  document.fonts?.addEventListener('loadingdone', refresh);
}
