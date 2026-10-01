/* Resolved vector type applications with single-letter parameters. */
import { config, excluded as skipped, makeBadge } from './source.js';
  function vectors(scope) {
    var declarations = config.vectorNotation || [];
    if (!declarations.length) return;
    scope.querySelectorAll('a[data-type][data-name]').forEach(function (operator) {
      if (operator.closest(skipped)) return;
      var module = operator.dataset.type.split('#')[0];
      if (!declarations.includes(module + '.' + operator.dataset.name)) return;
      // Prefer the exact existing semantic subtree. No new AST/type is inferred.
      var container = operator.parentElement;
      var head = operator.textContent.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      var application = head + '[ \\t]+(\\p{L}\\p{M}*)[ \\t]+(\\p{L}\\p{M}*)';
      var pattern = new RegExp('^\\s*' + application + '\\s*$', 'u');
      while (container !== scope && !pattern.test(container.textContent)) container = container.parentElement;
      var match = pattern.exec(container.textContent);
      var start = 0, end = container.textContent.length;
      if (!match) {
        // Untraced inline/type text: require an entire delimited type component,
        // not a fragment of a larger application or a three-argument call.
        // Formal source requires an existing expression node; never rewrite a
        // declaration's pattern merely because its left-hand side looks alike.
        if (scope.matches('pre.Agda')) return;
        container = scope;
        var before = document.createRange();
        before.setStart(container, 0); before.setEndBefore(operator);
        var offset = before.toString().length;
        var candidates = container.textContent.matchAll(new RegExp('(?:^|[:→(])[ \\t]*' + application + '(?=[ \\t]*(?:$|[→)]))', 'gu'));
        for (var candidate of candidates) {
          var applicationAt = candidate.index + candidate[0].indexOf(operator.textContent);
          if (applicationAt !== offset) continue;
          match = candidate;
          start = applicationAt;
          end = candidate.index + candidate[0].length;
          break;
        }
        if (!match) return;
      } else if (scope.matches('pre.Agda') &&
                 (container === scope || !container.matches('.expr-node, .type-node'))) return;
      var source, placeholder = document.createComment('vector notation');
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
      var badge = makeBadge(source, 'vector', match[1] + '^' + match[2]);
      badge.dataset.mathBase = match[1]; badge.dataset.mathPower = match[2];
      placeholder.replaceWith(badge);
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
    candidates.forEach(function (node) {
      if (!node.isConnected || node.closest(skipped) || !node.dataset.vectorItems) return;
      if (node.parentElement.closest('[data-vector-candidate]')) return;
      var items = JSON.parse(node.dataset.vectorItems);
      // Require actual constructor links as well as the whole term's Vec type.
      // An unlinked prose spelling or a List constructor cannot earn a badge.
      var constructors = Array.from(node.querySelectorAll('a')).filter(a => /^(?:∷|\[\])$/u.test(a.textContent));
      if (constructors.length !== items.length + 1 || !constructors.every(function (a) {
        return a.dataset.type && a.classList.contains('InductiveConstructor') &&
          (config.vectorNotation || []).includes(a.dataset.constructorFamily);
      })) return;
      var families = new Set(constructors.map(a => a.dataset.constructorFamily));
      if (families.size !== 1) return;
      var checkedFamily = node.dataset.vectorChecked === 'true' ? constructors[0].dataset.constructorFamily : '';
      if (!resolvedVectorType(node.dataset.vectorType || '', checkedFamily)) return;
      var placeholder = document.createComment('vector term notation'), source;
      if (node === scope) {
        source = document.createElement('span');
        while (node.firstChild) source.appendChild(node.firstChild);
        node.appendChild(placeholder);
        for (var attribute of ['data-hover-html', 'role', 'tabindex', 'aria-haspopup', 'aria-label']) node.removeAttribute(attribute);
      } else { node.replaceWith(placeholder); source = node; }
      placeholder.replaceWith(makeBadge(source, 'vector-term', '[' + items.join(', ') + ']', {typeHtml: node.dataset.vectorType}));
    });
  }

export { vectors, vectorTerms };
