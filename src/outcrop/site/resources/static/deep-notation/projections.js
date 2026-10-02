/* Certified record subscripts and single-letter pair suffixes. */
import { excluded as skipped, makeBadge } from './source.js';
import { text, subscript, mapText } from './presentation.js';
import { presentation, sourceOffset } from './composition.js';
import {colorAt} from './colors.js';
  function pairProjections(scope) {
    scope.querySelectorAll('a[data-pair-projection]').forEach(function (field) {
      if (field.closest(skipped)) return;
      var digit = field.dataset.pairProjection;
      if (!['1', '2'].includes(digit)) return;
      // Compact postfix syntax only. Imports, prefix forms from third-party
      // sources, signatures and same-spelled unrelated fields remain verbatim.
      var previous = field.previousSibling;
      var dot = null;
      if (previous?.nodeType === Node.ELEMENT_NODE && previous.matches('a.Symbol:not([href])')
          && previous.textContent === '.') dot = previous;
      else if (previous?.nodeType === Node.TEXT_NODE && previous.data.endsWith('.')) {
        dot = previous;
      }
      if (!dot) return;
      var expression = field.closest('.expr-node, .type-node') || scope;
      var before = document.createRange();
      before.setStart(expression, 0);
      if (dot.nodeType === Node.TEXT_NODE) before.setEnd(dot, dot.length - 1);
      else before.setEndBefore(dot);
      var receiver = before.toString().trim();
      if (receiver.includes('(')) receiver = receiver.slice(receiver.lastIndexOf('(') + 1).trim();
      // A compiler expression gives an exact receiver. Untraced inline text
      // is deliberately narrower: only a complete single-letter expression
      // is eligible, not the last letter of a larger function application.
      if (!/^\p{L}\p{M}*(?:\s*\.\s*(?:fst|snd))*$/u.test(receiver)) return;
      var chain = receiver.match(/\.\s*(?:fst|snd)/gu) || [];
      var prefix = before.toString(), receiverStart = prefix.lastIndexOf(receiver);
      var certified = Array.from(expression.querySelectorAll('.pair-projection-notation')).filter(badge => {
        var start = sourceOffset(expression, badge);
        return start >= receiverStart && start + badge.textContent.length <= prefix.length;
      });
      if (certified.length !== chain.length) return;
      if (dot.nodeType === Node.TEXT_NODE) dot = dot.splitText(dot.length - 1);
      var placeholder = document.createComment('pair projection');
      dot.before(placeholder);
      var label = '․' + (digit === '1' ? '₁' : '₂');
      var model = colorAt(field, 0, text(label));
      var source = document.createElement('span');
      source.append(dot, field);
      var badge = makeBadge(source, 'pair-projection', label,
        {model});
      placeholder.replaceWith(badge);
      // Remove only the painted horizontal separator, preserving source text,
      // line breaks, compiler offsets and copying. Each suffix is independent.
      var gap = badge.previousSibling;
      if (gap?.nodeType === Node.TEXT_NODE && /[ \t]+$/u.test(gap.data)) {
        var start = gap.data.search(/[ \t]+$/u);
        var spaces = gap.splitText(start);
        var hidden = document.createElement('span');
        hidden.className = 'notation-elided-parenthesis';
        hidden.setAttribute('aria-hidden', 'true');
        spaces.replaceWith(hidden); hidden.append(spaces);
      }
    });
  }
  function recordProjections(scope) {
    scope.querySelectorAll('[data-projection-head][data-projection-argument]').forEach(function (node) {
      if (node.closest(skipped)) return;
      var head = node.dataset.projectionHead, argument = node.dataset.projectionArgument;
      if (!/^\p{L}\p{M}*$/u.test(head) || !argument || argument.length > 24) return;
      var start = node.textContent.lastIndexOf(argument);
      if (start < 0 || node.querySelector('[data-projection-head]')) return;
      var shown = presentation(node, start, start + argument.length);
      var compactArgument = shown.text.replace(/\s+/gu, '');
      var style = getComputedStyle(node), size = parseFloat(style.fontSize);
      if (!Number.isFinite(size) || size < 14) return;
      var canvas = document.createElement('canvas'), context = canvas.getContext('2d');
      if (!context) return;
      context.font = style.font;
      var width = context.measureText(compactArgument).width * .72;
      // Do not squeeze long instance expressions into illegible subscripts.
      if (width > size * 4.5) return;
      var model = subscript(colorAt(node, node.textContent.indexOf(head), text(head)),
        mapText(shown.model, value => value.replace(/\s+/gu, '')));
      var placeholder = document.createComment('record projection');
      node.replaceWith(placeholder);
      var badge = makeBadge(node, 'record-projection', head + ' (' + argument + ')',
        {atomic: true, model});
      placeholder.replaceWith(badge);
    });
  }

export { pairProjections, recordProjections };
