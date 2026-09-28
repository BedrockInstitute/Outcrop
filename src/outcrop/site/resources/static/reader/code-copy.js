/* Copy the authored Agda source, not its visual mathematical notation.
 * AGPL-3.0-only. */
import { cfg, compactPointer } from './document.js';

const words = ({
  en: {copy: 'Copy Agda code', done: 'Code copied', failed: 'Could not copy code'},
  zh: {copy: '复制 Agda 代码', done: '代码已复制', failed: '复制失败'},
  ja: {copy: 'Agda コードをコピー', done: 'コードをコピーしました', failed: 'コピーできませんでした'},
})[cfg.lang] || {copy: 'Copy Agda code', done: 'Code copied', failed: 'Could not copy code'};
const feedbackTimers = new WeakMap();
let status;

function sourceText(block) {
  // Deep notation retains its original tokens in the source subtree. The
  // compiler-certified QED overlay and copy controls are outside that subtree.
  return (block.querySelector(':scope > .agda-code-content') || block).textContent;
}

function announce(button, message, success) {
  status ||= document.getElementById('code-copy-status');
  if (!status) {
    status = document.createElement('span');
    status.id = 'code-copy-status';
    status.className = 'sr-only';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    document.body.appendChild(status);
  }
  status.textContent = message;
  button.dataset.feedback = message;
  button.classList.toggle('is-copied', success);
  window.clearTimeout(feedbackTimers.get(button));
  feedbackTimers.set(button, window.setTimeout(() => {
    delete button.dataset.feedback;
    button.classList.remove('is-copied');
  }, 1800));
}

function fallbackCopy(text) {
  const field = document.createElement('textarea');
  field.value = text;
  field.readOnly = true;
  field.style.cssText = 'position:fixed;left:-10000px;top:0';
  document.body.appendChild(field);
  field.select();
  let copied = false;
  try { copied = document.execCommand('copy'); } catch (_) {}
  field.remove();
  return copied;
}

export async function copyCodeBlock(block, button) {
  const source = sourceText(block);
  let copied = false;
  if (navigator.clipboard?.writeText) {
    try { await navigator.clipboard.writeText(source); copied = true; } catch (_) {}
  }
  if (!copied) copied = fallbackCopy(source);
  announce(button, copied ? words.done : words.failed, copied);
  return copied;
}

export function createCodeCopyButton(block, className = '') {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `code-copy-button ${className}`.trim();
  button.dataset.codeControl = '';
  button.setAttribute('aria-label', words.copy);
  button.title = words.copy;
  button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg>';
  button.addEventListener('pointerdown', event => event.stopPropagation());
  button.addEventListener('click', event => {
    event.preventDefault();
    event.stopPropagation();
    const target = typeof block === 'function' ? block() : block;
    if (target?.isConnected) copyCodeBlock(target, button);
  });
  return button;
}

export function initCodeCopy() {
  const blocks = [...document.querySelectorAll('pre.Agda')];
  for (const block of blocks) block.appendChild(createCodeCopyButton(block, 'code-copy-inline'));

  let active = null;
  const mobile = createCodeCopyButton(() => active, 'code-copy-mobile');
  mobile.hidden = true;
  document.body.appendChild(mobile);
  let scheduled = false;
  // The shared mobile control changes its target, while fullscreen's control
  // is bound to the same original block before that block is moved.

  function position() {
    scheduled = false;
    const fullscreen = document.querySelector('.code-fullscreen-toggle:not([hidden])');
    const visible = compactPointer.matches && active?.isConnected
      && !document.body.classList.contains('code-fullscreen-open');
    if (!visible) { mobile.hidden = true; return; }
    const rect = active.getBoundingClientRect();
    if (rect.bottom <= 0 || rect.top >= window.innerHeight) {
      mobile.hidden = true; return;
    }
    mobile.hidden = false;
    mobile.style.left = Math.max(4, Math.min(window.innerWidth - 48,
      fullscreen ? fullscreen.getBoundingClientRect().left - 52 : rect.right - 44)) + 'px';
    mobile.style.top = Math.max(4, fullscreen
      ? fullscreen.getBoundingClientRect().top : rect.top - 46) + 'px';
  }
  function schedulePosition() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(position);
  }
  function activate(block) { active = block; schedulePosition(); }
  for (const block of blocks) {
    block.addEventListener('click', event => {
      if (compactPointer.matches && !event.target.closest('[data-code-control]')) activate(block);
    });
    block.addEventListener('focusin', () => {
      if (compactPointer.matches) activate(block);
    });
  }
  document.addEventListener('pointerdown', event => {
    if (!compactPointer.matches || event.target.closest('pre.Agda, [data-code-control]')) return;
    active = null; schedulePosition();
  }, true);
  document.addEventListener('textbook:code-scope', event => {
    if (compactPointer.matches && event.detail.block) activate(event.detail.block);
  });
  document.addEventListener('textbook:code-surface-change', () => {
    if (document.body.classList.contains('code-fullscreen-open')) mobile.hidden = true;
    schedulePosition();
  });
  document.addEventListener('textbook:code-fullscreen-close', schedulePosition);
  document.addEventListener('scroll', schedulePosition, {capture: true, passive: true});
  window.addEventListener('resize', schedulePosition);
  window.visualViewport?.addEventListener('resize', schedulePosition);
  window.visualViewport?.addEventListener('scroll', schedulePosition);
  compactPointer.addEventListener?.('change', schedulePosition);
}
