/* Outcrop reader: current-route. AGPL-3.0-only. */
import { cfg } from './document.js';
import { routes, preferredRoute, routeChanged } from './route-store.js';
import { chapterState, progressChanged, progressStorageKey, readProgress } from './reading-progress.js';

const reviewIcon = {
  true: '<path d="M12 3 20 6v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
  false: '<path d="m12 3 10 18H2Z"/><path d="M12 9v5m0 3v.1"/>',
};

export function initCurrentRoute() {
  const section = document.querySelector('#toc .current-route');
  if (!section) return;
  const list = section.querySelector('.route-nav');
  const name = section.querySelector('.current-route-name');
  const current = section.dataset.current;
  let data = null;
  let nodes = new Map();
  for (const link of list.querySelectorAll('[data-chapter]')) {
    const id = link.dataset.chapter;
    const prerequisites = link.parentElement.dataset.prerequisites.split(' ').filter(Boolean);
    nodes.set(id, { id, prerequisites });
    for (const prerequisite of prerequisites) {
      if (!nodes.has(prerequisite)) nodes.set(prerequisite, { id: prerequisite });
    }
  }

  function showRoute() {
    if (!data) return;
    const preferred = preferredRoute();
    const route = data.routes.find(item => item.id === preferred && (!current || item.chapters.includes(current)))
      || data.routes.find(item => item.chapters.includes(current)) || data.routes[0];
    if (!route) return;
    name.textContent = route.title[cfg.lang] || route.title.en;
    if (list.dataset.route === route.id) return;
    list.dataset.route = route.id;
    list.replaceChildren(...route.chapters.map(id => routeItem(nodes.get(id))).filter(Boolean));
    showProgress();
  }

  function routeItem(node) {
    if (!node) return null;
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = node.page + node.anchor;
    link.dataset.chapter = node.id;
    if (node.id === current) link.setAttribute('aria-current', 'page');
    const title = document.createElement('span');
    title.className = 'route-chapter-title';
    title.textContent = node.title[cfg.lang] || node.title.en;
    const statuses = document.createElement('span');
    statuses.className = 'route-statuses';
    const reading = document.createElement('span');
    reading.className = 'route-reading-status';
    reading.setAttribute('role', 'img');
    const reviewed = !!node.human_reviewed;
    const review = document.createElement('span');
    review.className = `route-review-status is-${reviewed ? 'reviewed' : 'unreviewed'}`;
    review.setAttribute('role', 'img');
    const reviewLabel = section.dataset[reviewed ? 'reviewedLabel' : 'unreviewedLabel'];
    review.setAttribute('aria-label', reviewLabel);
    review.title = reviewLabel;
    review.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">${reviewIcon[reviewed]}</svg>`;
    statuses.append(reading, review);
    link.append(title, statuses);
    item.append(link);
    return item;
  }

  function showProgress() {
    const completed = readProgress();
    for (const link of list.querySelectorAll('[data-chapter]')) {
      const state = chapterState(nodes.get(link.dataset.chapter), completed, nodes);
      const badge = link.querySelector('.route-reading-status');
      if (!badge) continue;
      const label = section.dataset[`${state}Label`];
      badge.className = `route-reading-status is-${state}`;
      badge.setAttribute('aria-label', label);
      badge.title = label;
    }
  }

  window.addEventListener(routeChanged, showRoute);
  window.addEventListener(progressChanged, showProgress);
  window.addEventListener('storage', event => {
    if (!event.key || event.key === progressStorageKey) showProgress();
  });
  showProgress();
  routes().then(loaded => {
    data = loaded;
    nodes = new Map(data.nodes.map(node => [node.id, node]));
    showRoute();
    showProgress();
  }).catch(() => { /* The server-rendered route remains usable. */ });
}
