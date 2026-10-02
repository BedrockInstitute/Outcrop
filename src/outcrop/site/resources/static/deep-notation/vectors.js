/* Resolved vector type applications with single-letter parameters. */
import { config, excluded as skipped, makeBadge, unparenthesize } from './source.js';
import { applicationAt, presentation, sourceOffset, wrapRange } from './composition.js';
import { text, sequence, superscript } from './presentation.js';
import {colorAt} from './colors.js';

  // Read exactly two syntactic arguments, retaining their source offsets.
  // This is a display boundary, never a fabricated Agda AST.
  function vectorApplication(text, offset, head) {
    const match = applicationAt(text, offset, head, 2);
    return match && /^[ \t]*(?:$|[→)])/u.test(text.slice(match.end)) ? match : null;
  }
  function vectors(scope) {
    var declarations = config.vectorNotation || [];
    if (!declarations.length) return;
    scope.querySelectorAll('a[data-type][data-name]').forEach(function (operator) {
      if (operator.closest(skipped)) return;
      var module = operator.dataset.type.split('#')[0];
      if (!declarations.includes(module + '.' + operator.dataset.name)) return;
      // Prefer the exact existing semantic subtree. No new AST/type is inferred.
      var container = operator.parentElement;
      var match;
      while (true) {
        var offset = sourceOffset(container, operator);
        match = vectorApplication(container.textContent, offset, operator.textContent);
        if (match && !container.textContent.slice(0, offset).trim() &&
            !container.textContent.slice(match.end).trim()) break;
        if (container === scope) { match = null; break; }
        container = container.parentElement;
      }
      if (!match) {
        // Untraced inline/type text: require an entire delimited type component,
        // not a fragment of a larger application or a three-argument call.
        // Formal source requires an existing expression node; never rewrite a
        // declaration's pattern merely because its left-hand side looks alike.
        if (scope.matches('pre.Agda')) return;
        container = scope;
        var offset = sourceOffset(container, operator);
        if (!/(?:^|[:→(])[ \t]*$/u.test(container.textContent.slice(0, offset))) return;
        match = vectorApplication(container.textContent, offset, operator.textContent);
        if (!match) return;
      } else if (scope.matches('pre.Agda') &&
                 (container === scope || !container.matches('.expr-node, .type-node'))) return;
      if (!/^\p{L}\p{M}*$/u.test(match.args[0].text)) return;
      var exponent = presentation(container, match.args[1].start, match.args[1].end);
      // A visual bound, not knowledge of any child notation's syntax or type.
      if (!/^(?:\p{L}\p{M}*|[0-9]+)$/u.test(match.args[1].text) &&
          !(exponent.atomic && /^(?:\p{L}\p{M}*[⁺⁰¹²³⁴⁵⁶⁷⁸⁹]*|[0-9]+)$/u.test(exponent.text))) return;
      wrapRange(container, match.start, match.end, 'vector',
        match.args[0].text + '^' + exponent.text,
        {atomic: true, model: superscript(presentation(container, match.args[0].start, match.args[0].end).model, exponent.model)});
    });
  }

  function resolvedVectorType(markup, checkedFamily) {
    var holder = document.createElement('span'); holder.innerHTML = markup;
    var head = holder.querySelector('a[data-type]');
    var headText;
    if (head) {
      var prefix = document.createRange(); prefix.setStart(holder, 0); prefix.setEndBefore(head);
      if (prefix.toString().trim()) head = null;
    }
    if (head) {
      var identity = head.dataset.type.split('#')[0] + '.' + (head.dataset.name || head.textContent);
      if (!(config.vectorNotation || []).includes(identity)) return false;
      headText = head.textContent;
    } else {
      // Pretty-printed compiler types sometimes omit qualification/links.
      // A checked application AND the constructors' declaring datatype supply
      // the missing identity; prose spelling alone still earns nothing.
      if (!checkedFamily || !(config.vectorNotation || []).includes(checkedFamily)) return false;
      headText = holder.textContent.trim().split(/\s/u)[0];
      if (headText !== checkedFamily && headText !== checkedFamily.split('.').pop()) return false;
    }
    // Reject partial applications, arrows and Vec appearing inside another type.
    var tail = holder.textContent.trim().slice(headText.length).trim();
    var depth = 0, words = 0, inWord = false;
    for (var character of tail) {
      if (!depth && /[→:{}]/u.test(character)) return false;
      if (character === '(') depth++;
      if (character === ')' && --depth < 0) return false;
      if (!depth && /\s/u.test(character)) inWord = false;
      else if (!inWord) { words++; inWord = true; }
    }
    return depth === 0 && words === 2;
  }
  function vectorTerms(scope) {
    if (!(config.vectorNotation || []).length) return;
    var candidates = Array.from(scope.querySelectorAll('[data-vector-candidate]'));
    if (scope.matches('[data-vector-candidate]')) candidates.unshift(scope);
    function itemRanges(node) {
      var cursor = 0;
      return JSON.parse(node.dataset.vectorItems || '[]').map(item => {
        var start = node.textContent.indexOf(item, cursor), end = start + item.length;
        cursor = end;
        return {start, end};
      });
    }
    candidates.reverse().forEach(function (node) {
      if (!node.isConnected || node.closest(skipped) || !node.dataset.vectorItems) return;
      var parent = node.parentElement.closest('[data-vector-candidate]');
      if (parent) {
        var offset = sourceOffset(parent, node);
        // Elements may contain vectors; tails of the same chain may not become
        // separate brackets. Pattern/ineligible parents remain suffix barriers.
        if (!itemRanges(parent).some(r => r.start <= offset && offset + node.textContent.length <= r.end)) return;
      }
      var items = JSON.parse(node.dataset.vectorItems);
      var ranges = itemRanges(node);
      // Inline prose may rely on resolved cons identities alone, without a
      // fabricated whole-expression type. Formal source keeps its stronger gate.
      var inline = node.dataset.vectorInline === 'true';
      var constructors = Array.from(node.querySelectorAll('a')).filter(a => {
        if (!/^(?:∷|\[\])$/u.test(a.textContent)) return false;
        var offset = sourceOffset(node, a);
        return !ranges.some(r => r.start <= offset && offset < r.end);
      });
      var required = inline ? constructors.filter(a => a.textContent === '∷') : constructors;
      if (required.length !== items.length + (inline ? 0 : 1) || !required.every(function (a) {
        return a.dataset.type && a.classList.contains('InductiveConstructor') &&
          (config.vectorNotation || []).includes(a.dataset.constructorFamily);
      })) return;
      var families = new Set(required.map(a => a.dataset.constructorFamily));
      if (families.size !== 1) return;
      if (constructors.some(a => a.textContent === '[]' && a.dataset.constructorFamily &&
          !families.has(a.dataset.constructorFamily))) return;
      var checkedFamily = node.dataset.vectorChecked === 'true' || inline ? required[0].dataset.constructorFamily : '';
      if ((!inline || node.dataset.vectorType) && !resolvedVectorType(node.dataset.vectorType || '', checkedFamily)) return;
      // Entry syntax was certified by the producer; reuse child presentation
      // without teaching vector notation about any child datatype.
      var displayedItems = ranges.map(function (range) {
        var {start, end} = range;
        var original = node.textContent.slice(start, end), inner = unparenthesize(original);
        // A comma-bearing element must retain grouping inside comma-separated
        // brackets (e.g. a Sigma pair is one element, not two).
        while (inner !== original && !inner.includes(',')) {
          start += original.indexOf(inner); end = start + inner.length;
          original = inner; inner = unparenthesize(original);
        }
        return presentation(node, start, end);
      });
      var punctuation = value => colorAt(required[0], 0, text(value));
      var parts = [punctuation('[')];
      displayedItems.forEach((item, index) => { if (index) parts.push(punctuation(', ')); parts.push(item.model); });
      parts.push(punctuation(']'));
      var placeholder = document.createComment('vector term notation'), source;
      if (node === scope) {
        source = document.createElement('span');
        while (node.firstChild) source.appendChild(node.firstChild);
        node.appendChild(placeholder);
        for (var attribute of ['data-hover-html', 'role', 'tabindex', 'aria-haspopup', 'aria-label']) node.removeAttribute(attribute);
        // The persistent code surface is scanned again after DOM mutations.
        // Its consumed candidate must not wrap the badge a second time.
        for (var attribute of ['data-vector-candidate', 'data-vector-items', 'data-vector-inline', 'data-vector-checked']) node.removeAttribute(attribute);
      } else { node.replaceWith(placeholder); source = node; }
      placeholder.replaceWith(makeBadge(source, 'vector-term', '[' + displayedItems.map(item => item.text).join(', ') + ']',
        {typeHtml: node.dataset.vectorType, atomic: true, model: sequence(parts)}));
    });
  }

export { vectors, vectorTerms };
