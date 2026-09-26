/* Optional, compiler-aware presentation of numeric notation.
   The original Agda DOM remains inside each source badge, so source positions,
   links and copied text do not become a second authored code language. */
(function () {
  'use strict';
  var config = window.outcrop || {};
  var lens = window.outcropSourceNotation;
  if (!lens) return;
  var codeScopes = 'pre.Agda, code.Agda, .Agda.inline-code, .single-line-code > code, .type-value.Agda';
  var skipped = '.source-notation, [data-universe-raw], [data-source-raw], [data-outcrop-notation="source"], .appearance-preview, .Comment, .String, .Pragma';
  var natType = '<span class="Agda">ℕ</span>';

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
      if (!value || !type || !['fin', 'nat-suc'].includes(kind)) return;
      var count = Number(node.dataset.notationCount);
      if (kind === 'nat-suc' && (!Number.isSafeInteger(count) || count < 1)) return;
      var power = count > 2 ? '+' + count : '+'.repeat(count);
      var superscript = '⁰¹²³⁴⁵⁶⁷⁸⁹';
      var exponent = count > 2 ? '⁺' + String(count).replace(/[0-9]/g, function (digit) {
        return superscript[Number(digit)];
      }) : '⁺'.repeat(count);
      var label = kind === 'fin' ? value : value + exponent;
      var placeholder = document.createComment('source notation');
      node.replaceWith(placeholder);
      var badge = lens.makeBadge(node, kind, label, {typeHtml: type});
      if (kind === 'nat-suc') {
        badge.dataset.mathBase = value;
        badge.dataset.mathPower = power;
      }
      placeholder.replaceWith(badge);
    });
  }
  function unparenthesize(value) {
    if (!value.startsWith('(') || !value.endsWith(')')) return value;
    var depth = 0;
    for (var index = 0; index < value.length; index++) {
      if (value[index] === '(') depth++;
      else if (value[index] === ')' && --depth === 0 && index !== value.length - 1) return value;
      if (depth < 0) return value;
    }
    return depth === 0 ? value.slice(1, -1).trim() : value;
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
    var badge = lens.makeBadge(source, 'fin', String(value), {typeHtml: scope.dataset.hoverHtml});
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
    var term = scope.textContent.trim(), count = 0;
    while (/^suc\s+/u.test(term)) {
      term = unparenthesize(term.replace(/^suc\s+/u, '').trim());
      count++;
    }
    if (!count || !/^[\p{L}\p{M}_][\p{L}\p{M}\p{N}_′″‴⁗'’₀-₉]*$/u.test(term)
        || term === 'zero' || term === 'suc') return;
    var superscript = '⁰¹²³⁴⁵⁶⁷⁸⁹';
    var exponent = count > 2 ? '⁺' + String(count).replace(/[0-9]/g, function (digit) {
      return superscript[Number(digit)];
    }) : '⁺'.repeat(count);
    var source = document.createElement('span');
    while (scope.firstChild) source.appendChild(scope.firstChild);
    var badge = lens.makeBadge(source, 'nat-suc', term + exponent,
                               {typeHtml: scope.dataset.hoverHtml});
    badge.dataset.mathBase = term;
    badge.dataset.mathPower = count > 2 ? '+' + count : '+'.repeat(count);
    scope.appendChild(badge);
    clearOuterPopup(scope);
  }
  function elideSuccessorParentheses(scope) {
    // The compact successor is an atomic displayed term. Preserve the Agda
    // tokens for source copying and offsets; only suppress their paint.
    function neighbor(badge, direction) {
      var node = direction === 'left' ? badge.previousSibling : badge.nextSibling;
      while (node && node.nodeType === 1 && node.classList.contains('notation-elided-parenthesis'))
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
    scope.querySelectorAll('.nat-suc-notation').forEach(function (badge) {
      while (true) {
        var left = candidate(neighbor(badge, 'left'), 'left');
        var right = candidate(neighbor(badge, 'right'), 'right');
        if (!left || !right) break;
        hide(left); hide(right);
      }
    });
  }
  function decorate(scope) {
    if (!scope || scope.closest(skipped)) return;
    naturalLiterals(scope);
    inlineFinConstructors(scope);
    inlineSuccessors(scope);
    numericExpressions(scope);
    elideSuccessorParentheses(scope);
  }
  function scan(scope) {
    if (!scope || scope.nodeType !== Node.ELEMENT_NODE || scope.closest(skipped)) return;
    var parent = scope.closest(codeScopes);
    if (parent) decorate(parent);
    scope.querySelectorAll(codeScopes).forEach(function (node) {
      if (!node.parentElement.closest(codeScopes)) decorate(node);
    });
  }
  window.outcropMathematicalNotation = {scan: scan};
  document.addEventListener('DOMContentLoaded', function () {
    scan(document.body);
    new MutationObserver(function (records) {
      var scopes = new Set();
      records.forEach(function (record) {
        if (record.type === 'characterData') scopes.add(record.target.parentElement);
        else record.addedNodes.forEach(function (node) {
          if (node.nodeType === Node.ELEMENT_NODE) scopes.add(node);
          else if (node.nodeType === Node.TEXT_NODE && node.parentElement) scopes.add(node.parentElement);
        });
      });
      scopes.forEach(scan);
    }).observe(document.body, {childList: true, subtree: true, characterData: true});
  });
})();
