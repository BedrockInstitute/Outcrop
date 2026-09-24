/* A landscape reading surface for the existing DOM, not a second code renderer.
 * AGPL-3.0-only. Geometry is shared with popups and AST gestures. */
import { cfg, compactPointer, isDefinitionModalDocument, modalReadingScroller } from './document.js';
import { setCodeSurface } from './code-surface.js';

let view = null;
let nextSurface = 0;

export function initCodeFullscreen() {
  const labels = ({en: ['Read code in landscape', 'Close landscape reader'],
    zh: ['横屏全屏阅读代码', '退出横屏阅读'], ja: ['コードを横長の全画面で読む', '横長表示を閉じる']})[cfg.lang]
    || ['Read code in landscape', 'Close landscape reader'];
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'code-fullscreen-toggle';
  button.dataset.codeControl = ''; button.hidden = true;
  button.setAttribute('aria-label', labels[0]); button.title = labels[0];
  button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/></svg>';
  document.body.appendChild(button);
  let activeBlock = null;
  let pendingRestore = null;
  function notifyHost(active, surfaceId) {
    if (isDefinitionModalDocument && window.parent !== window)
      window.parent.postMessage({type: 'outcrop-code-fullscreen', active, surfaceId}, location.origin);
  }

  function positionButton() {
    const portrait = window.innerHeight > window.innerWidth;
    button.hidden = Boolean(view) || !compactPointer.matches || !portrait || !activeBlock?.isConnected;
    if (button.hidden) return;
    const rect = activeBlock.getBoundingClientRect();
    button.hidden = rect.bottom <= 0 || rect.top >= window.innerHeight;
    button.style.left = Math.max(4, Math.min(window.innerWidth - 48, rect.right - 44)) + 'px';
    button.style.top = Math.max(4, rect.top - 46) + 'px';
  }
  function size() {
    if (!view) { positionButton(); return; }
    const viewport = window.visualViewport;
    const width = viewport ? viewport.width : window.innerWidth;
    const height = viewport ? viewport.height : window.innerHeight;
    view.rotated = height > width;
    view.shell.style.width = width + 'px'; view.shell.style.height = height + 'px';
    view.shell.style.left = (viewport?.offsetLeft || 0) + 'px';
    view.shell.style.top = (viewport?.offsetTop || 0) + 'px';
    [view.plane, view.controls].forEach(node => {
      node.style.width = Math.max(width, height) + 'px';
      node.style.height = Math.min(width, height) + 'px';
      node.style.transform = view.rotated ? 'translateX(' + width + 'px) rotate(90deg)' : 'none';
      node.classList.toggle('is-rotated', view.rotated);
    });
    view.plane.style.setProperty('--code-surface-width', Math.max(width, height) + 'px');
    document.dispatchEvent(new Event('textbook:code-surface-change'));
  }
  function close(restoreFocus = true) {
    if (!view) return;
    const old = view; view = null; setCodeSurface(null);
    /* Clear popup requests before detaching their anchors. The normal modal
       listener can subsequently open in the restored portrait document. */
    old.marker.replaceWith(old.content);
    document.dispatchEvent(new CustomEvent('textbook:code-fullscreen-close', {detail: {block: old.block}}));
    if (old.module === null) old.block.removeAttribute('data-module');
    else old.block.setAttribute('data-module', old.module);
    old.inert.forEach(([node, inert]) => { node.inert = inert; });
    old.shell.remove(); document.body.classList.remove('code-fullscreen-open');
    const restore = () => (old.scroller || window).scrollTo({left: old.scrollX, top: old.scrollY, behavior: 'instant'});
    if (old.scroller && isDefinitionModalDocument && window.parent !== window)
      pendingRestore = {id: old.id, restore};
    else restore();
    notifyHost(false, old.id);
    activeBlock = old.block; positionButton();
    if (restoreFocus && !button.hidden) button.focus({preventScroll: true});
  }
  function open() {
    if (view || !activeBlock?.isConnected) return;
    pendingRestore = null;
    const block = activeBlock;
    const content = block.parentElement.matches('.statement-ending') ? block.parentElement : block;
    const marker = document.createElement('div');
    marker.style.height = content.getBoundingClientRect().height + 'px';
    marker.style.margin = getComputedStyle(content).margin;
    const shell = document.createElement('section'); shell.className = 'code-fullscreen';
    shell.setAttribute('role', 'dialog'); shell.setAttribute('aria-modal', 'true');
    shell.setAttribute('aria-label', labels[0]);
    const plane = document.createElement('div'); plane.className = 'code-fullscreen-plane';
    const controls = document.createElement('div'); controls.className = 'code-fullscreen-controls';
    const closeButton = document.createElement('button'); closeButton.type = 'button';
    closeButton.className = 'code-fullscreen-close'; closeButton.dataset.codeControl = '';
    closeButton.setAttribute('aria-label', labels[1]); closeButton.title = labels[1]; closeButton.textContent = '×';
    const module = block.getAttribute('data-module');
    const sourceModule = block.closest('[data-module]')?.dataset.module || cfg.chapter || cfg.module;
    const inert = [...document.body.children].filter(node =>
      !node.matches('.hover-popup, .ast-swipe-hint, .code-fullscreen-toggle, script, style'))
      .map(node => [node, node.inert]);
    const scroller = modalReadingScroller();
    view = {id: ++nextSurface, shell, plane, controls, block, content, marker, module, inert, scroller,
      scrollX: scroller ? scroller.scrollLeft : window.scrollX,
      scrollY: scroller ? scroller.scrollTop : window.scrollY, rotated: false};
    setCodeSurface(view);
    block.dataset.module = sourceModule;
    content.before(marker); plane.append(content); controls.append(closeButton); shell.append(plane, controls);
    document.body.appendChild(shell); document.body.classList.add('code-fullscreen-open');
    inert.forEach(([node]) => { node.inert = true; });
    button.hidden = true;
    closeButton.addEventListener('click', () => close());
    plane.addEventListener('scroll', () => document.dispatchEvent(new Event('textbook:code-surface-change')), {capture: true, passive: true});
    notifyHost(true, view.id); size(); closeButton.focus({preventScroll: true});
  }
  button.addEventListener('click', open);
  document.addEventListener('textbook:code-scope', event => {
    activeBlock = event.detail.block;
    positionButton();
  });
  document.addEventListener('outcrop:definition-modal-open', () => close(false));
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== window.parent
        || event.data?.type !== 'outcrop-code-surface-restored'
        || !pendingRestore || event.data.surfaceId !== pendingRestore.id) return;
    const saved = pendingRestore; pendingRestore = null;
    if (!view) { saved.restore(); positionButton(); }
  });
  document.addEventListener('keydown', event => {
    if (!view) return;
    if (event.key === 'Escape') { event.preventDefault(); close(); }
    if (event.key === 'Tab') {
      const targets = [...view.shell.querySelectorAll('button, a[href], [tabindex="0"]')]
        .filter(node => !node.hidden && node.getClientRects().length);
      const index = targets.indexOf(document.activeElement);
      if (event.shiftKey ? index <= 0 : index === targets.length - 1) {
        event.preventDefault(); targets[event.shiftKey ? targets.length - 1 : 0]?.focus();
      }
    }
  });
  window.addEventListener('resize', size);
  window.visualViewport?.addEventListener('resize', size);
  window.visualViewport?.addEventListener('scroll', size);
  document.addEventListener('scroll', positionButton, {capture: true, passive: true});
}
