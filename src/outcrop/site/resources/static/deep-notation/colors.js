/* Retain source highlighting roles, not a snapshot of the current palette.
 * No semantic targets/IDs are copied into the noninteractive painted tree. */
import {text, sequence, toned} from './presentation.js';

const roles = new Set(['Comment', 'Markup', 'Pragma', 'Keyword', 'String',
  'Number', 'Symbol', 'Bound', 'Generalizable', 'InductiveConstructor',
  'CoinductiveConstructor', 'Field', 'Module', 'Datatype', 'Function',
  'Postulate', 'Primitive', 'Record', 'PrimitiveType', 'Macro', 'syntax-symbol']);

function classesAt(element) {
  for (let node = element; node && !node.matches('.Agda'); node = node.parentElement) {
    // Source hover stop rules intentionally neutralize primitive names.
    if (node.matches('a[data-hover-stop], .type-value a:is(.Primitive, .PrimitiveType):not([data-type])')) return ['Bound'];
    if (node.classList.contains('universe-parameter')) return ['universe-parameter'];
    const classes = Array.from(node.classList).filter(name => roles.has(name));
    if (classes.length) return classes;
    if (node.matches('.inline-ref a, .hover-popup a')) return ['Function'];
  }
  return [];
}

export function colorAt(container, offset, model) {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let node, cursor = 0;
  while ((node = walker.nextNode())) {
    if (offset >= cursor && offset < cursor + node.length)
      return toned(classesAt(node.parentElement), model);
    cursor += node.length;
  }
  return toned([], model);
}

export function sourcePresentation(container, start, end) {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT), parts = [];
  let node, cursor = 0;
  while ((node = walker.nextNode())) {
    const left = Math.max(start, cursor), right = Math.min(end, cursor + node.length);
    if (left < right) parts.push(toned(classesAt(node.parentElement), text(node.data.slice(left - cursor, right - cursor))));
    cursor += node.length;
    if (cursor >= end) break;
  }
  return sequence(parts);
}
