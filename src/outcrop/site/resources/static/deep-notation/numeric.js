/* Natural literals, natural successors and finite indices. */
import { config, excluded as skipped, makeBadge, unparenthesize } from './source.js';
import { applicationAt, sourceOffset, wrapRange } from './composition.js';
import { text, successor, plain } from './presentation.js';
const natType = '<span class="Agda">ℕ</span>';
// Shared display algebra; callers, not spelling, certify the natural type.
export function successorNotation(base, count) {
  var power = count > 2 ? '+' + count : '+'.repeat(count);
  var model = successor(text(base), count);
  return {base, power, model, label: plain(model)};
}
export function naturalNotation(source) {
  function ungroup(text) {
    let previous;
    do { previous = text; text = unparenthesize(text.trim()); } while (previous !== text);
    return text;
  }
  var term = ungroup(source), count = 0;
  while (/^suc\s+/u.test(term)) {
    term = ungroup(term.replace(/^suc\s+/u, '')); count++;
  }
  if (term === 'zero' || /^(?:0|[1-9][0-9]*)$/u.test(term)) {
    var value = (term === 'zero' ? 0n : BigInt(term)) + BigInt(count);
    return {base: String(value), power: '', label: String(value), model: text(value)};
  }
  if (!/^[\p{L}\p{M}_][\p{L}\p{M}\p{N}_′″‴⁗'’₀-₉]*$/u.test(term) || term === 'suc') return null;
  return successorNotation(term, count);
}

// Canonical builtin constructors carry a complete, unambiguous Nat signature.
// Unlike overloaded spelling, that identity justifies a display-only application
// in prose/type surfaces, independently of any parent (Vec, Fin, Formula, ...).
// Formal code retains compiler-certified ranges and never rewrites patterns.
export function naturalConstructors(scope) {
  if (scope.matches('pre.Agda')) return;
  const source = scope.textContent;
  const anchors = Array.from(scope.querySelectorAll('a')).map(node => ({
    node, start: sourceOffset(scope, node), text: node.textContent
  }));
  for (const item of anchors) {
    if (item.node.closest(skipped) || !/^(zero|suc)$/u.test(item.text)) continue;
    let end = item.start + item.text.length;
    if (item.text === 'suc') {
      if (!/(?:^|[:→=(])[ \t]*$/u.test(source.slice(0, item.start))) continue;
      const application = applicationAt(source, item.start, item.text, 1);
      if (!application || !/^[ \t]*(?:$|[):→=])/u.test(source.slice(application.end))) continue;
      end = application.end;
    }
    const original = source.slice(item.start, end), notation = naturalNotation(original);
    if (!notation) continue;
    const names = original.match(/\b(?:suc|zero)\b/gu) || [];
    const constructors = anchors.filter(a => a.start >= item.start && a.start < end && /^(zero|suc)$/u.test(a.text));
    if (names.length !== constructors.length || !constructors.every(a =>
      a.node.dataset.type && a.node.classList.contains('InductiveConstructor') &&
      a.node.dataset.constructorFamily === 'Agda.Builtin.Nat.Nat')) continue;
    const kind = notation.power ? 'nat-suc' : 'nat';
    wrapRange(scope, item.start, end, kind, notation.label,
      {typeHtml: natType, atomic: true, model: notation.model});
  }
}
  function precedingSourceLine(element) {
    // Agda highlights a fixity precedence as Number too, but it is syntax,
    // not an ℕ term. Read only the DOM text on this source line: anchors and
    // expression wrappers must not affect the declaration classification.
    var parts = [], node = element;
    while (node && !node.matches?.('pre.Agda')) {
      while (node.previousSibling) {
        node = node.previousSibling;
        var content = node.textContent || '';
        var breakAt = content.lastIndexOf('\n');
        parts.unshift(breakAt < 0 ? content : content.slice(breakAt + 1));
        if (breakAt >= 0) return parts.join('');
      }
      node = node.parentElement;
    }
    return parts.join('');
  }
  function markLiteral(element) {
    if (element.closest(skipped) || element.hasAttribute('data-hover-html')) return;
    if (element.closest('pre.Agda') && /^\s*infix(?:l|r)?\s+$/u.test(precedingSourceLine(element))) return;
    element.dataset.hoverHtml = natType;
    element.classList.add('natural-literal');
    element.setAttribute('role', 'button');
    element.setAttribute('tabindex', '0');
    element.setAttribute('aria-haspopup', 'dialog');
    element.setAttribute('aria-label', element.textContent + ' : ℕ');
  }
  function naturalLiterals(scope) {
    if (!config.naturalLiteralDefault) return;
    scope.querySelectorAll('a.Number').forEach(markLiteral);
    // Inline Agda does not carry compiler-highlighted Number anchors. This
    // project policy is explicit: unqualified literals default to builtin ℕ.
    if (scope.matches('pre.Agda')) return;
    var walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT), textNodes = [], node;
    while ((node = walker.nextNode())) {
      if (!node.parentElement.closest('a, .natural-literal, ' + skipped)) textNodes.push(node);
    }
    textNodes.forEach(function (textNode) {
      var pattern = /(?<![\p{L}\p{M}\p{N}_])(?:0|[1-9][0-9]*)(?![\p{L}\p{M}\p{N}_])/gu;
      var matches = Array.from(textNode.data.matchAll(pattern));
      matches.reverse().forEach(function (match) {
        var range = document.createRange();
        range.setStart(textNode, match.index); range.setEnd(textNode, match.index + match[0].length);
        var literal = document.createElement('span'); literal.className = 'Number';
        range.surroundContents(literal); markLiteral(literal);
      });
    });
  }
  function numericExpressions(scope) {
    var candidates = Array.from(scope.querySelectorAll('.expr-node[data-source-notation]'));
    candidates.forEach(function (node) {
      if (!node.isConnected || node.closest('.source-notation') || node.closest(skipped)) return;
      var ancestor = node.parentElement.closest('.expr-node[data-source-notation]');
      if (ancestor && ancestor !== node && scope.contains(ancestor)) return;
      var kind = node.dataset.sourceNotation;
      var value = node.dataset.notationValue;
      var type = node.dataset.notationType;
      if (!value || !type || !['fin', 'nat', 'nat-suc'].includes(kind)) return;
      var count = Number(node.dataset.notationCount);
      if (kind === 'nat-suc' && (!Number.isSafeInteger(count) || count < 1)) return;
      var notation = successorNotation(value, count);
      var label = kind === 'nat-suc' ? notation.label : value;
      var placeholder = document.createComment('source notation');
      node.replaceWith(placeholder);
      var badge = makeBadge(node, kind, label, {typeHtml: type, atomic: true,
        model: kind === 'nat-suc' ? notation.model : text(value)});
      placeholder.replaceWith(badge);
    });
  }
  function finConstructorValue(source) {
    var term = source.trim(), count = 0;
    while (term !== 'zero') {
      if (!/^suc\s+/u.test(term)) return null;
      term = unparenthesize(term.replace(/^suc\s+/u, '').trim());
      count++;
    }
    return count;
  }
  function inlineFinConstructors(scope) {
    if (!scope.matches('code.Agda[data-agda-inline-type]') || scope.querySelector('.source-notation')) return;
    var type = scope.dataset.agdaInlineType.trim();
    if (!/^Fin\s+\S/u.test(type)) return;
    var value = finConstructorValue(scope.textContent);
    if (value === null) return;
    var literalIndex = /^Fin\s+([0-9]+)$/u.exec(type);
    if (literalIndex && value >= Number(literalIndex[1])) return;
    var source = document.createElement('span');
    while (scope.firstChild) source.appendChild(scope.firstChild);
    var badge = makeBadge(source, 'fin', String(value), {typeHtml: scope.dataset.hoverHtml, atomic: true});
    scope.appendChild(badge);
    clearOuterPopup(scope);
  }
  function clearOuterPopup(scope) {
    // The compact badge owns the same type/source popup. Keep one keyboard
    // stop and one hover target instead of nesting an interactive code wrapper.
    for (var attribute of ['data-hover-html', 'role', 'tabindex', 'aria-haspopup', 'aria-label']) {
      scope.removeAttribute(attribute);
    }
  }
  function inlineSuccessors(scope) {
    if (!scope.matches('code.Agda[data-agda-inline-type]') || scope.querySelector('.source-notation')) return;
    if (!/^(?:ℕ|Nat)$/u.test(scope.dataset.agdaInlineType.trim())) return;
    var notation = naturalNotation(scope.textContent);
    if (!notation || !/\b(?:zero|suc)\b/u.test(scope.textContent)) return;
    var source = document.createElement('span');
    while (scope.firstChild) source.appendChild(scope.firstChild);
    var badge = makeBadge(source, notation.power ? 'nat-suc' : 'nat', notation.label,
                               {typeHtml: scope.dataset.hoverHtml, atomic: true, model: notation.model});
    scope.appendChild(badge);
    clearOuterPopup(scope);
  }
  function elideAtomicParentheses(scope) {
    // Compact successors and bracketed vectors are atomic displayed terms. Preserve the Agda
    // tokens for source copying and offsets; only suppress their paint.
    function neighbor(badge, direction) {
      var node = direction === 'left' ? badge.previousSibling : badge.nextSibling;
      while (node && ((node.nodeType === 1 && node.classList.contains('notation-elided-parenthesis')) ||
                     (node.nodeType === Node.TEXT_NODE && !node.data)))
        node = direction === 'left' ? node.previousSibling : node.nextSibling;
      return node;
    }
    function candidate(node, direction) {
      if (!node) return null;
      var delimiter = direction === 'left' ? '(' : ')';
      if (node.nodeType === 1 && node.matches('a.Symbol:not([href])') && node.textContent === delimiter)
        return {node: node, element: true};
      if (node.nodeType !== 3) return null;
      var match = direction === 'left' ? /\(\s*$/u.exec(node.data) : /^\s*\)/u.exec(node.data);
      return match ? {node: node, element: false,
        start: direction === 'left' ? match.index : 0,
        end: direction === 'left' ? node.length : match[0].length} : null;
    }
    function hide(part) {
      if (part.element) {
        part.node.classList.add('notation-elided-parenthesis');
        part.node.setAttribute('aria-hidden', 'true');
        return;
      }
      var range = document.createRange();
      range.setStart(part.node, part.start); range.setEnd(part.node, part.end);
      var wrapper = document.createElement('span');
      wrapper.className = 'notation-elided-parenthesis';
      wrapper.setAttribute('aria-hidden', 'true');
      range.surroundContents(wrapper);
    }
    scope.querySelectorAll('.source-notation[data-notation-atomic="true"]').forEach(function (badge) {
      if (badge.parentElement.closest('.source-notation')) return;
      while (true) {
        var left = candidate(neighbor(badge, 'left'), 'left');
        var right = candidate(neighbor(badge, 'right'), 'right');
        if (!left || !right) break;
        hide(left); hide(right);
      }
    });
  }

export { naturalLiterals, numericExpressions, inlineFinConstructors, inlineSuccessors, elideAtomicParentheses };
