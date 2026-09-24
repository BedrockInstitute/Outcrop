/* Surface-independent presentation rules. No semantic lookup or lifetime state. */
import { codeSurface } from './code-surface.js';
export function belowSource(rect, popupWidth, viewport) {
  const width = Math.min(popupWidth, viewport.width - 16);
  return {
    left: viewport.scrollX + Math.max(8, Math.min(rect.left, viewport.width - width - 8)),
    top: viewport.scrollY + rect.bottom
  };
}

export function positionBelow(popup, anchor) {
  if (!popup.isConnected || !anchor.isConnected) return;
  const surface = codeSurface(anchor);
  const host = surface ? surface.host : document.body;
  if (popup.parentElement !== host) host.appendChild(popup);
  const point = belowSource(surface ? surface.rect : anchor.getBoundingClientRect(), popup.offsetWidth, surface || {
    width: window.innerWidth, scrollX: window.scrollX, scrollY: window.scrollY
  });
  popup.style.left = point.left + 'px';
  popup.style.top = point.top + 'px';
}

export function clearCodeSelection(scope) {
  scope.querySelectorAll('.expr-active, .name-active, .type-active, .occ').forEach(node => {
    node.classList.remove('expr-active', 'name-active', 'type-active', 'occ');
  });
}
