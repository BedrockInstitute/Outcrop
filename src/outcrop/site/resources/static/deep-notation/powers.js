/* Explicitly configured, resolved single-letter infix powers. */
import { config, excluded as skipped, makeBadge } from './source.js';
  function powers(scope) {
    var declarations = config.powerNotation || [];
    if (!declarations.length) return;
    scope.querySelectorAll('a[data-type][data-name]').forEach(function (operator) {
      if (operator.textContent !== '^' || operator.closest(skipped)) return;
      var module = operator.dataset.type.split('#')[0];
      if (!declarations.includes(module + '.' + operator.dataset.name)) return;
      // Prefer the exact existing semantic subtree. No new AST/type is inferred.
      var container = operator.parentElement;
      var pattern = /^\s*(\p{L}\p{M}*)[ \t]+\^[ \t]+(\p{L}\p{M}*)\s*$/u;
      while (container !== scope && !pattern.test(container.textContent)) container = container.parentElement;
      var match = pattern.exec(container.textContent);
      var start = 0, end = container.textContent.length;
      if (!match) {
        // Untraced inline/type text: require an entire delimited type component,
        // not the final letters of an application, identifier or chained power.
        // Formal source requires an existing expression node; never rewrite a
        // declaration's pattern merely because its left-hand side looks alike.
        if (scope.matches('pre.Agda')) return;
        container = scope;
        var before = document.createRange();
        before.setStart(container, 0); before.setEndBefore(operator);
        var offset = before.toString().length;
        var candidates = container.textContent.matchAll(/(?:^|[:→(])[ \t]*(\p{L}\p{M}*)[ \t]+\^[ \t]+(\p{L}\p{M}*)(?=[ \t]*(?:$|[→)]))/gu);
        for (var candidate of candidates) {
          var powerAt = candidate.index + candidate[0].indexOf('^');
          if (powerAt !== offset) continue;
          match = candidate;
          start = powerAt - candidate[0].slice(0, candidate[0].indexOf('^')).match(/\p{L}\p{M}*[ \t]+$/u)[0].length;
          end = candidate.index + candidate[0].length;
          break;
        }
        if (!match) return;
      } else if (scope.matches('pre.Agda') &&
                 (container === scope || !container.matches('.expr-node, .type-node'))) return;
      var source, placeholder = document.createComment('power notation');
      if (start === 0 && end === container.textContent.length && container !== scope) {
        container.replaceWith(placeholder); source = container;
      } else if (start === 0 && end === container.textContent.length) {
        source = document.createElement('span');
        while (container.firstChild) source.appendChild(container.firstChild);
        container.appendChild(placeholder);
      } else {
        var walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
        var range = document.createRange(), cursor = 0, text, begun = false;
        while ((text = walker.nextNode())) {
          var next = cursor + text.length;
          if (!begun && start < next) { range.setStart(text, start - cursor); begun = true; }
          if (begun && end <= next) { range.setEnd(text, end - cursor); break; }
          cursor = next;
        }
        if (!begun || !text) return;
        // Include whole boundary elements rather than cloning partial anchors
        // (which would duplicate IDs and detach their semantic identity).
        var first = range.startContainer, last = range.endContainer;
        if (range.startOffset === 0) {
          while (first.parentNode !== container && first === first.parentNode.firstChild) first = first.parentNode;
          range.setStartBefore(first);
        }
        if (range.endOffset === last.textContent.length) {
          while (last.parentNode !== container && last === last.parentNode.lastChild) last = last.parentNode;
          range.setEndAfter(last);
        }
        source = document.createElement('span'); source.append(range.extractContents());
        range.insertNode(placeholder);
      }
      var badge = makeBadge(source, 'power', match[1] + '^' + match[2]);
      badge.dataset.mathBase = match[1]; badge.dataset.mathPower = match[2];
      placeholder.replaceWith(badge);
    });
  }

export { powers };
