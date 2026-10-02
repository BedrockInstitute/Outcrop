/* Source-coordinate composition shared by all notation owners.
 * DOM offsets are UTF-16; compiler Unicode coordinates are never rewritten.
 * This module reads source/presentation, not types or mathematical spellings. */
import { codeScopes, makeBadge, unparenthesize } from './source.js';
import { sequence, text as literal } from './presentation.js';
import {sourcePresentation} from './colors.js';

export function sourceOffset(container, node) {
  const range = document.createRange();
  range.setStart(container, 0); range.setEndBefore(node);
  return range.toString().length;
}

export function atomAt(text, start) {
  let end = start;
  if (text[start] === '(') {
    let depth = 0;
    do {
      if (text[end] === '(') depth++;
      if (text[end] === ')') depth--;
      end++;
    } while (depth && end < text.length);
    if (depth) return null;
  } else {
    const atom = /^[^\s():→]+/u.exec(text.slice(start));
    if (!atom) return null;
    end += atom[0].length;
  }
  return {start, end, text: text.slice(start, end)};
}

export function applicationAt(text, offset, head, arity) {
  if (text.slice(offset, offset + head.length) !== head) return null;
  let cursor = offset + head.length;
  const args = [];
  for (let index = 0; index < arity; index++) {
    const space = /^[ \t]+/u.exec(text.slice(cursor));
    if (!space) return null;
    const argument = atomAt(text, cursor + space[0].length);
    if (!argument) return null;
    args.push(argument); cursor = argument.end;
  }
  return {start: offset, end: cursor, args};
}

// Read the already-certified child presentation, regardless of its rule owner.
// Parents never reparse a child's mathematical syntax or infer its type.
export function presentation(container, start = 0, end = container.textContent.length) {
  const source = container.textContent.slice(start, end), replacements = [];
  for (const badge of container.querySelectorAll('.source-notation, .notation-elided-parenthesis')) {
    if (badge.parentElement.closest('.source-notation')) continue;
    const left = sourceOffset(container, badge), right = left + badge.textContent.length;
    const elided = badge.classList.contains('notation-elided-parenthesis');
    if (left >= start && right <= end) replacements.push({
      start: left - start, end: right - start, text: elided ? '' : badge.dataset.mathLabel,
      model: elided ? literal('') : JSON.parse(badge.dataset.notationModel),
      elided,
      atomic: badge.dataset.notationAtomic === 'true'
    });
  }
  let text = source;
  for (const part of replacements.slice().reverse()) text = text.slice(0, part.start) + part.text + text.slice(part.end);
  const visible = replacements.filter(part => !part.elided);
  const only = visible.length === 1 && visible[0];
  const atomic = !!only && only.atomic &&
    !source.slice(0, only.start).replace(/[\s(]/gu, '') &&
    !source.slice(only.end).replace(/[\s)]/gu, '');
  if (atomic) {
    let unwrapped;
    do { unwrapped = text; text = unparenthesize(text.trim()); } while (unwrapped !== text);
  }
  let cursor = 0;
  const parts = [];
  for (const part of replacements) {
    parts.push(sourcePresentation(container, start + cursor, start + part.start), part.model); cursor = part.end;
  }
  parts.push(sourcePresentation(container, start + cursor, end));
  return {text, model: atomic ? only.model : sequence(parts), changed: replacements.length > 0, atomic};
}

// Move, never recreate, source nodes so IDs and semantic identity survive.
export function wrapRange(container, start, end, kind, label, options) {
  if (start === 0 && end === container.textContent.length &&
      container.matches('.expr-node, .type-node') && !container.matches(codeScopes)) {
    const placeholder = document.createComment('notation'); container.replaceWith(placeholder);
    const badge = makeBadge(container, kind, label, options); placeholder.replaceWith(badge);
    return badge;
  }
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  let cursor = 0, text, begun = false;
  while ((text = walker.nextNode())) {
    const next = cursor + text.length;
    if (!begun && start < next) { range.setStart(text, start - cursor); begun = true; }
    if (begun && end <= next) { range.setEnd(text, end - cursor); break; }
    cursor = next;
  }
  if (!begun || !text) return null;
  let boundary = range.commonAncestorContainer;
  if (boundary.nodeType === Node.TEXT_NODE) boundary = boundary.parentNode;
  if (range.toString() === boundary.textContent) boundary = boundary.parentNode;
  let first = range.startContainer, last = range.endContainer;
  if (range.startOffset === 0) {
    while (first.parentNode !== container && first.parentNode !== boundary && first === first.parentNode.firstChild) first = first.parentNode;
    range.setStartBefore(first);
  }
  if (range.endOffset === last.textContent.length) {
    while (last.parentNode !== container && last.parentNode !== boundary &&
           !Array.from(last.parentNode.childNodes).slice(Array.from(last.parentNode.childNodes).indexOf(last) + 1).some(n => n.textContent)) last = last.parentNode;
    range.setEndAfter(last);
  }
  const fragment = range.cloneContents();
  const originalNodes = Array.from(container.querySelectorAll('.expr-node, .type-node'));
  if (Array.from(fragment.querySelectorAll('.expr-node, .type-node')).some(node => {
    const key = node.dataset.exprId || node.dataset.expressionType;
    if (!key) return false;
    const original = originalNodes.find(candidate => (candidate.dataset.exprId || candidate.dataset.expressionType) === key);
    return original && node.textContent !== original.textContent;
  })) return null;
  const source = document.createElement('span'); source.append(range.extractContents());
  const badge = makeBadge(source, kind, label, options); range.insertNode(badge);
  return badge;
}
