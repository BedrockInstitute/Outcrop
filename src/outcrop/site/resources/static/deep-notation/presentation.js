/* A small mathematical presentation tree, independent of Agda and the DOM.
 * Recognition decides meaning/eligibility; this model only retains layout. */
export const text = value => ({form: 'text', value: String(value)});
export const sequence = parts => ({form: 'sequence', parts});
export const superscript = (base, index) => ({form: 'script', position: 'super', base, index});
export const subscript = (base, index) => ({form: 'script', position: 'sub', base, index});
export const group = body => sequence([text('('), body, text(')')]);
export const styled = (name, body) => ({form: 'style', name, body});
export const successor = (base, count) => count
  ? superscript(base, text(count > 2 ? '+' + count : '+'.repeat(count))) : base;

export function mapText(model, transform) {
  if (model.form === 'text') return text(transform(model.value));
  if (model.form === 'sequence') return sequence(model.parts.map(part => mapText(part, transform)));
  if (model.form === 'style') return styled(model.name, mapText(model.body, transform));
  return {...model, base: mapText(model.base, transform), index: mapText(model.index, transform)};
}

export function plain(model) {
  if (model.form === 'text') return model.value;
  if (model.form === 'sequence') return model.parts.map(plain).join('');
  if (model.form === 'style') return plain(model.body);
  if (model.form === 'script') {
    const index = plain(model.index), digits = model.position === 'super' ? '⁰¹²³⁴⁵⁶⁷⁸⁹⁺' : '₀₁₂₃₄₅₆₇₈₉₊';
    const suffix = /^[0-9+]+$/u.test(index)
      ? index.replace(/[0-9+]/g, d => digits[d === '+' ? 10 : Number(d)])
      : (model.position === 'super' ? '^' : '_') + index;
    return plain(model.base) + suffix;
  }
  throw new Error('Unknown notation presentation: ' + model.form);
}

// Generated glyphs are CSS content, never source text. Selecting/copying and
// compiler ranges therefore still see the unchanged Agda, even at nested depth.
export function paint(model, document) {
  const node = document.createElement('span');
  node.className = 'notation-' + model.form;
  if (model.form === 'text') node.dataset.notationText = model.value;
  else if (model.form === 'sequence') model.parts.forEach(part => node.append(paint(part, document)));
  else if (model.form === 'style') {
    node.classList.add('notation-style-' + model.name); node.append(paint(model.body, document));
  } else if (model.form === 'script') {
    node.append(paint(model.base, document));
    const index = document.createElement('span'); index.className = 'notation-index notation-' + model.position;
    index.append(paint(model.index, document)); node.append(index);
  } else throw new Error('Unknown notation presentation: ' + model.form);
  return node;
}
