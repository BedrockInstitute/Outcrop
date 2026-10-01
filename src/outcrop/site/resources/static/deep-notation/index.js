/* The single deep-notation entry: ordered rules, labels and one lifecycle.
 * Original Agda text/identity is never replaced by the painted notation.
 * See README.md in this directory before adding, editing or removing a rule. */
import { codeScopes, excluded } from './source.js';
import * as universe from './universe.js';
import { naturalLiterals, inlineFinConstructors, inlineSuccessors,
  numericExpressions, elideAtomicParentheses } from './numeric.js';
import { recordProjections, pairProjections } from './projections.js';
import { vectors, vectorTerms } from './vectors.js';

export const sourceLabels = {
            universe: {en: "Universe level · Original Agda", zh: "宇宙层级 · 原始 Agda", ja: "宇宙レベル · 元の Agda"},
            fin: {en: "Finite index · Original Agda", zh: "有限指标 · 原始 Agda", ja: "有限添字 · 元の Agda"},
            'pair-projection': {en: "Pair projection · Original Agda", zh: "依值对投影 · 原始 Agda", ja: "依存対の射影 · 元の Agda"},
            'record-projection': {en: "Record projection · Original Agda", zh: "记录投影 · 原始 Agda", ja: "レコードの射影 · 元の Agda"},
            'nat-suc': {en: "Natural successor · Original Agda", zh: "自然数后继 · 原始 Agda", ja: "自然数の後続 · 元の Agda"},
            vector: {en: "Vector type · Original Agda", zh: "向量类型 · 原始 Agda", ja: "ベクトル型 · 元の Agda"},
            'vector-term': {en: "Vector · Original Agda", zh: "向量 · 原始 Agda", ja: "ベクトル · 元の Agda"}
          };
export function sourceLabel(kind, language) {
  return (sourceLabels[kind] || sourceLabels.universe)[language] || "Original Agda";
}

// Ordering is intentional: preserve whole vector terms, certify levels and numeric expressions,
// then compact vector types/projections, finally hide redundant successor parentheses.
export const rules = [
  { id: 'vector-term', decorate: vectorTerms },
  { id: 'universe', decorate: universe.decorate },
  { id: 'natural-literals', decorate: naturalLiterals },
  { id: 'inline-fin', decorate: inlineFinConstructors },
  { id: 'inline-successors', decorate: inlineSuccessors },
  { id: 'numeric-expressions', decorate: numericExpressions },
  { id: 'vector', decorate: vectors },
  { id: 'record-projection', decorate: recordProjections },
  { id: 'pair-projection', decorate: pairProjections },
  { id: 'atomic-parentheses', decorate: elideAtomicParentheses }
];

export function scan(scope) {
  if (!scope || scope.nodeType !== Node.ELEMENT_NODE) return;
  universe.prepare(scope);
  if (scope.closest(excluded)) return;
  function decorate(node) {
    if (!node.closest(excluded)) rules.forEach(rule => rule.decorate(node));
  }
  const parent = scope.closest(codeScopes);
  if (parent) decorate(parent);
  scope.querySelectorAll(codeScopes).forEach(node => {
    if (!node.parentElement.closest(codeScopes)) decorate(node);
  });
}

let observer;
export function initialize() {
  if (observer) return;
  universe.initialize();
  scan(document.body);
  observer = new MutationObserver(records => {
    const scopes = new Set();
    records.forEach(record => {
      if (record.type === 'characterData') scopes.add(record.target.parentElement);
      else record.addedNodes.forEach(node => {
        if (node.nodeType === Node.ELEMENT_NODE) scopes.add(node);
        else if (node.nodeType === Node.TEXT_NODE && node.parentElement) scopes.add(node.parentElement);
      });
    });
    scopes.forEach(scan);
  });
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
}
// Explicit fixture/dynamic-content API; no legacy aliases or parallel scanners.
window.outcropDeepNotation = { scan };
