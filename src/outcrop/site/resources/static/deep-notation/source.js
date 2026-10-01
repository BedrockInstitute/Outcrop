/* Shared source-preserving presentation primitives. */
export const config = window.outcrop || {};
export const codeScopes = 'pre.Agda, code.Agda, .Agda.inline-code, .single-line-code > code, .type-value.Agda';
export const excluded = ".source-notation, [data-universe-raw], [data-source-raw], [data-outcrop-notation='source'], .appearance-preview, .Comment, .String, .Pragma, script, style, template";
  function sourceMarkup(fragment, kind) {
    var holder = document.createElement("span"); holder.setAttribute(kind === 'universe' ? "data-universe-raw" : "data-source-raw", "");
    holder.appendChild(fragment.cloneNode(true));
    var moduleName = (window.outcrop || {}).chapter || (window.outcrop || {}).module || "";
    holder.querySelectorAll("[id]").forEach(function (node) { node.removeAttribute("id"); });
    holder.querySelectorAll(".expr-node").forEach(function (node) {
      node.classList.replace("expr-node", "type-node");
      if (moduleName && node.dataset.exprId) node.dataset.expressionType = moduleName + "#" + node.dataset.exprId;
    });
    // Rebase *all* structural ranges to the extracted fragment's Unicode text.
    holder.querySelectorAll(".type-node").forEach(function (node) {
      var before = document.createRange(); before.setStart(holder, 0); before.setEndBefore(node);
      var start = Array.from(before.toString()).length;
      node.dataset.exprStart = String(start); node.dataset.exprEnd = String(start + Array.from(node.textContent).length);
      node.classList.remove("expr-active", "type-active");
    });
    holder.querySelectorAll(".occ, .name-active").forEach(function (node) { node.classList.remove("occ", "name-active"); });
    holder.querySelectorAll(".universe-parameter").forEach(function (node) { node.classList.remove("universe-parameter"); });
    return holder.outerHTML;
  }
  function makeBadge(source, kind, label, options) {
    options = options || {};
    var element = document.createElement("span"); element.className = kind + "-notation source-notation";
    element.dataset.sourceKind = kind;
    element.dataset.mathLabel = label;
    if (kind === 'universe') element.dataset.levelMath = label;
    element.dataset.hoverHtml = (options.typeHtml ? '<span class="source-notation-type Agda">' + options.typeHtml + '</span>' : '') + sourceMarkup(source, kind);
    element.setAttribute("role", "button"); element.setAttribute("tabindex", "0");
    element.setAttribute("aria-haspopup", "dialog"); element.setAttribute("aria-expanded", "false");
    var copy = {zh: "{label}。展开原始 Agda 代码", ja: "{label}。元の Agda コードを表示", en: "{label}. Show original Agda code"};
    element.setAttribute("aria-label", (copy[document.documentElement.lang] || copy.en).replace("{label}", label));
    var original = document.createElement("span"); original.className = "universe-source";
    original.setAttribute("aria-hidden", "true"); original.setAttribute("inert", "");
    original.appendChild(source); element.appendChild(original); return element;
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

export { makeBadge, unparenthesize };
