/* Universe levels: certified operations and explicit naming convention. */
import { config, excluded } from './source.js';
import { text, sequence, group, successor, plain } from './presentation.js';
import { wrapRange } from './composition.js';
  var levelModules = new Set([config.preludeModule, 'Agda.Primitive',
    'Cubical.Core.Primitives', 'Cubical.Foundations.Prelude'].filter(Boolean));
  function levelLibraryLink(link) {
    if (!link) return false;
    try {
      var url = new URL(link.getAttribute('href'), document.baseURI);
      return !!url.hash && levelModules.has(decodeURIComponent(url.pathname.split('/').pop()).replace(/\.html$/, ''));
    } catch (_) { return false; }
  }
  var operations = {"ℓ-zero": "zero", "lzero": "zero", "ℓ-suc": "suc", "lsuc": "suc", "ℓ-max": "max", "⊔": "join"};

  // Parse only this tiny, closed grammar, never infer a level from arbitrary ⊔/0/⁺.
  export function parse(tokens, start, known, argument, levelAtom, atomOnly) {
    var node = parseAtom(tokens, start, known, argument, levelAtom);
    if (!node || atomOnly) return node;
    while (tokens[node.end] && tokens[node.end].text === "⊔" && known(node.end)) {
      var right = parse(tokens, node.end + 1, known, argument, levelAtom, true);
      if (!right) break;
      node = {op: "max", args: [node, right], start: start, end: right.end, changed: true};
    }
    return node;
  }
  function parseAtom(tokens, start, known, argument, levelAtom) {
    var token = tokens[start];
    if (!token) return null;
    var name = token.text;
    if (name === "(") {
      var inner = parse(tokens, start + 1, known, argument, levelAtom);
      if (!inner || !tokens[inner.end] || tokens[inner.end].text !== ")") return null;
      return {op: inner.op, args: inner.args, text: inner.text, start: start, end: inner.end + 1, changed: inner.changed};
    }
    var operation = Object.prototype.hasOwnProperty.call(operations, name) && known(start) && operations[name];
    if (operation === "zero") return {op: "atom", text: "0", start: start, end: start + 1, changed: true};
    if (operation && operation !== "join") {
      var first = parse(tokens, start + 1, known, true, levelAtom, true);
      if (!first) return null;
      var second = operation === "max" ? parse(tokens, first.end, known, true, levelAtom, true) : null;
      if (operation === "max" && !second) return null;
      return {op: operation, args: second ? [first, second] : [first], start: start,
        end: second ? second.end : first.end, changed: true};
    }
    if ((argument || levelAtom && levelAtom(start)) && !Object.prototype.hasOwnProperty.call(operations, name)
        && /^(?:[\p{L}\p{M}][\p{L}\p{M}\p{N}′″‴⁗'’₀-₉.-]*|_)$/u.test(name))
      return {op: "atom", text: name, start: start, end: start + 1, changed: false};
    return null;
  }
  export function model(node) {
    if (node.op === "atom") return text(node.text);
    if (node.op === "max") return sequence([model(node.args[0]), text(' ⊔ '), model(node.args[1])]);
    var child = node, count = 0;
    while (child.op === "suc") { count++; child = child.args[0]; }
    var value = model(child);
    return successor(child.op === 'max' ? group(value) : value, count);
  }
  export function tokenize(text) {
    var result = [], pattern = /[^\s(){};]+|[(){};]/gu, match;
    while ((match = pattern.exec(text))) result.push({text: match[0], start: match.index, end: pattern.lastIndex});
    return result;
  }
  function textMap(scope) {
    var walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT), nodes = [], text = "", node;
    while ((node = walker.nextNode())) { nodes.push({node: node, start: text.length, end: text.length + node.data.length}); text += node.data; }
    return {nodes: nodes, text: text};
  }
  // Book-wide notation convention, not type inference: ℓ and its numeric /
  // prime variants always denote levels, including prose and raw-code popups.
  // Do not match operator names (ℓ-max) or substrings of another identifier.
  function levelNamePattern() {
    return /(?<![\p{L}\p{M}\p{N}_′″‴⁗'’-])ℓ[\p{N}\p{M}′″‴⁗'’]*(?![\p{L}\p{M}\p{N}_′″‴⁗'’-])/gu;
  }
  function markConventionalLevels(scope) {
    if (!config.levelNameConvention) return;
    var skip = '.source-notation, .universe-source, .universe-parameter, script, style, template, textarea, input, select, [contenteditable], svg, math';
    if (scope.closest(skip)) return;
    var walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT), nodes = [], node;
    while ((node = walker.nextNode())) {
      if (node.data.includes('ℓ') && !node.parentElement.closest(skip)) nodes.push(node);
    }
    nodes.forEach(function (text) {
      var matches = Array.from(text.data.matchAll(levelNamePattern()));
      matches.reverse().forEach(function (match) {
        var range = document.createRange(); range.setStart(text, match.index);
        range.setEnd(text, match.index + match[0].length);
        var span = document.createElement('span'); span.className = 'universe-parameter';
        span.dataset.universeLevel = 'true'; range.surroundContents(span);
      });
    });
  }
  function markCertifiedLevels(scope) {
    var selector = '[data-universe-level="true"]';
    var nodes = Array.from(scope.querySelectorAll(selector));
    if (scope.matches(selector)) nodes.unshift(scope);
    nodes.forEach(function (node) {
      if (!node.closest('.source-notation, .universe-source, .appearance-preview')
          && !node.parentElement.closest('.universe-parameter')
          && !Object.prototype.hasOwnProperty.call(operations, node.textContent.trim()))
        node.classList.add('universe-parameter');
    });
  }
  function tokenElement(map, token) {
    var item = map.nodes.find(function (entry) { return token.start >= entry.start && token.start < entry.end; });
    return item && item.node.parentElement;
  }
  function knownOperator(map, tokens, index) {
    var token = tokens[index], element = tokenElement(map, token);
    if (!element || element.closest(excluded)) return false;
    var link = element.closest("a[href]");
    // Compiler/automatic-notation links certify the name; a same-spelled local
    // function, comment, string, or ordinary numeric/mixfix operator is untouched.
    if (!link && token.text === "⊔" && element.closest(".type-value")) return true;
    return !!(link && link.textContent.trim() === token.text
      && levelLibraryLink(link)
      && (link.matches(".Primitive, .Function, .Postulate, .inline-ref") || link.hasAttribute("data-name")));
  }
  var pageLevels = new Set();
  function collectPageLevels() {
    var names = new Map();
    document.querySelectorAll("pre.Agda a.Bound[data-type], pre.Agda a.Generalizable[data-type]").forEach(function (node) {
      var name = node.textContent.trim(), level = node.dataset.universeLevel === "true";
      names.set(name, (names.has(name) ? names.get(name) : true) && level);
    });
    names.forEach(function (level, name) { if (level) pageLevels.add(name); });
  }
  function markParameters(scope) {
    scope.querySelectorAll('[data-universe-level="true"]').forEach(function (node) {
      if (!node.closest(excluded) && !node.parentElement.closest('.universe-parameter') && !Object.prototype.hasOwnProperty.call(operations, node.textContent.trim()))
        node.classList.add("universe-parameter");
    });
    if (scope.closest(excluded)) return;
    var map = textMap(scope), tokens = tokenize(map.text), stack = [], closes = new Map(), parents = new Map(), binders = [];
    tokens.forEach(function (token, index) {
      if (token.text === "(" || token.text === "{") { parents.set(index, stack[stack.length - 1]); stack.push(index); }
      if (token.text === ")" || token.text === "}") { var open = stack.pop(); if (open !== undefined) closes.set(open, index); }
    });
    closes.forEach(function (close, open) {
      var colon = open + 1;
      while (colon < close && /^[\p{L}\p{M}][\p{L}\p{M}\p{N}′'₀-₉.-]*$/u.test(tokens[colon].text)) colon++;
      if (colon === open + 1 || !tokens[colon] || tokens[colon].text !== ":") return;
      var typeToken = tokens[colon + 1], typeElement = typeToken && tokenElement(map, typeToken);
      var typeLink = typeElement && typeElement.closest('a[href]');
      var level = colon + 2 === close && typeToken.text === "Level" && typeLink
        && levelLibraryLink(typeLink);
      binders.push({start: open + 1, end: closes.get(parents.get(open)) || tokens.length,
        names: new Set(tokens.slice(open + 1, colon).map(function (token) { return token.text; })), level: Boolean(level)});
    });
    binders.sort(function (a, b) { return b.start - a.start; });
    var inferred = [];
    tokens.forEach(function (token, index) {
      var element = tokenElement(map, token);
      if (!element || element.closest(excluded + ", a, .universe-parameter, [data-hover-help]")) return;
      var binder = binders.find(function (entry) { return index >= entry.start && index < entry.end && entry.names.has(token.text); });
      var level = binder ? binder.level : !scope.closest(".type-value") && pageLevels.has(token.text);
      if (!level) return;
      var item = map.nodes.find(function (entry) { return token.start >= entry.start && token.end <= entry.end; });
      if (item) inferred.push({item: item, token: token});
    });
    inferred.reverse().forEach(function (entry) {
      var range = document.createRange(); range.setStart(entry.item.node, entry.token.start - entry.item.start);
      range.setEnd(entry.item.node, entry.token.end - entry.item.start);
      var span = document.createElement("span"); span.className = "universe-parameter"; span.dataset.universeLevel = "true";
      range.surroundContents(span);
    });
  }
  function decorate(scope) {
    if (scope.closest(excluded)) return;
    markParameters(scope);
    var map = textMap(scope);
    if (!/ℓ-(?:zero|suc|max)|\bl(?:zero|suc)\b|⊔/.test(map.text)) return;
    var tokens = tokenize(map.text), matches = [], importNames = new Set();
    tokens.forEach(function (token, index) {
      if (!/^(?:using|hiding|renaming)$/.test(token.text) || !tokens[index + 1] || tokens[index + 1].text !== "(") return;
      var depth = 0;
      for (var cursor = index + 1; cursor < tokens.length; cursor++) {
        importNames.add(cursor);
        if (tokens[cursor].text === "(") depth++;
        if (tokens[cursor].text === ")" && --depth === 0) break;
      }
    });
    for (var i = 0; i < tokens.length; i++) {
      if (importNames.has(i)) continue;
      var levelAtom = function (index) {
        var element = tokenElement(map, tokens[index]);
        return !!(element && !element.closest(excluded) && element.closest('[data-universe-level="true"]'));
      };
      if (tokens[i].text !== "(" && !Object.prototype.hasOwnProperty.call(operations, tokens[i].text) && !levelAtom(i)) continue;
      var expression = parse(tokens, i, function (index) { return knownOperator(map, tokens, index); }, false, levelAtom);
      if (!expression || !expression.changed) continue;
      var begin = tokens[i].start, end = tokens[expression.end - 1].end;
      var first = tokenElement(map, tokens[i]), last = tokenElement(map, tokens[expression.end - 1]);
      if (!first || !last || first.closest(excluded) || last.closest(excluded)) continue;
      // A bare name in an import/renaming/declaration is not a level expression.
      var line = map.text.slice(map.text.lastIndexOf("\n", begin - 1) + 1, begin);
      if (/(?:\busing|\bhiding|\brenaming|\bimport|\bBUILTIN)\b/.test(line)
          || tokens[expression.end] && /^(?:;|:|to)$/.test(tokens[expression.end].text)) continue;
      // Source layout is significant; never collapse a multi-line expression.
      if (map.text.slice(begin, end).includes("\n")) continue;
      matches.push({start: begin, end: end, model: model(expression)}); i = expression.end - 1;
    }
    // Work backwards so earlier source offsets and nodes remain valid.
    matches.reverse().forEach(function (match) {
      wrapRange(scope, match.start, match.end, 'universe', plain(match.model), {model: match.model});
    });
  }

export function prepare(scope) {
  markCertifiedLevels(scope);
  markConventionalLevels(scope);
}
export { collectPageLevels as initialize, decorate };
