/* Reading progress and prerequisite readiness shared by the route views. */
import { storageKey } from './preferences.js';

export const progressChanged = 'textbook:reading-progress';
export const progressStorageKey = storageKey('reading-progress-v1');

export function readProgress() {
  try {
    const saved = JSON.parse(localStorage.getItem(progressStorageKey) || '[]');
    return new Set(Array.isArray(saved) ? saved.filter(id => typeof id === 'string') : []);
  } catch (_) { return new Set(); }
}

export function writeProgress(completed) {
  try { localStorage.setItem(progressStorageKey, JSON.stringify([...completed])); }
  catch (_) { /* Progress remains usable for this session. */ }
  window.dispatchEvent(new Event(progressChanged));
}

export function chapterState(node, completed, nodes) {
  if (completed.has(node.id)) return 'complete';
  const missing = (node.prerequisites || []).some(id => {
    const prerequisite = nodes.get(id);
    return prerequisite && !prerequisite.preview && !completed.has(id);
  });
  return missing ? 'pending' : 'available';
}
