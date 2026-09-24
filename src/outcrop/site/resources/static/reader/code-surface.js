/* Coordinate service shared by native code, rotated code and their popups. */
let view = null;
export function setCodeSurface(surface) { view = surface; }

export function codePoint(point, target) {
  if (!view || !view.plane.contains(target)) return {x: point.clientX, y: point.clientY};
  const rect = view.plane.getBoundingClientRect();
  return view.rotated
    ? {x: point.clientY - rect.top, y: rect.right - point.clientX}
    : {x: point.clientX - rect.left, y: point.clientY - rect.top};
}

export function codeSurface(anchor) {
  if (!view || !view.plane.contains(anchor)) return null;
  const rect = anchor.getBoundingClientRect();
  const a = codePoint({clientX: rect.left, clientY: rect.top}, anchor);
  const b = codePoint({clientX: rect.right, clientY: rect.bottom}, anchor);
  return {host: view.plane, width: view.plane.clientWidth, height: view.plane.clientHeight,
    scrollX: view.plane.scrollLeft, scrollY: view.plane.scrollTop,
    rect: {left: Math.min(a.x, b.x), right: Math.max(a.x, b.x),
      top: Math.min(a.y, b.y), bottom: Math.max(a.y, b.y)}};
}
