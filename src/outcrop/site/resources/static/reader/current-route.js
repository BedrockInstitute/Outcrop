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
  let openStatus = null;
  function updateTitleOverflow() {
    for (const link of list.querySelectorAll('[data-chapter]')) {
      const viewport = link.querySelector('.route-chapter-viewport');
      const title = viewport?.querySelector('.route-chapter-title');
      if (!title || !viewport.clientWidth) continue;
      const overflow = Math.max(0, Math.ceil(title.getBoundingClientRect().width - viewport.clientWidth));
      link.classList.toggle('is-title-overflowing', overflow > 1);
      link.style.setProperty('--route-title-overflow', `${overflow}px`);
      link.style.setProperty('--route-title-duration', `${Math.min(16, Math.max(7, 4 + overflow / 16))}s`);
    }
  }
  function closeStatus() {
    openStatus?.classList.remove('is-tip-open');
    openStatus = null;
  }
  list.addEventListener('click', event => {
    const button = event.target.closest('.route-statuses > button');
    if (!button || !list.contains(button)) return;
    const opening = openStatus !== button;
    closeStatus();
    if (opening) {
      button.classList.add('is-tip-open');
      openStatus = button;
    }
  });
  function closeStatusOutside(event) {
    if (openStatus && !openStatus.contains(event.target)) closeStatus();
  }
  document.addEventListener('pointerdown', closeStatusOutside, true);
  document.addEventListener('click', closeStatusOutside);
  document.addEventListener('focusin', closeStatusOutside);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeStatus();
  });
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
    closeStatus();
    list.dataset.route = route.id;
    list.replaceChildren(...route.chapters.map(id => routeItem(nodes.get(id))).filter(Boolean));
    showProgress();
    requestAnimationFrame(updateTitleOverflow);
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
    link.dataset.fullTitle = title.textContent;
    const viewport = document.createElement('span');
    viewport.className = 'route-chapter-viewport';
    viewport.append(title);
    const statuses = document.createElement('span');
    statuses.className = 'route-statuses';
    const reading = document.createElement('button');
    reading.type = 'button';
    reading.className = 'route-reading-status';
    const reviewed = !!node.human_reviewed;
    const review = document.createElement('button');
    review.type = 'button';
    review.className = `route-review-status is-${reviewed ? 'reviewed' : 'unreviewed'}`;
    const reviewLabel = section.dataset[reviewed ? 'reviewedLabel' : 'unreviewedLabel'];
    review.setAttribute('aria-label', reviewLabel);
    review.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">${reviewIcon[reviewed]}</svg>`;
    statuses.append(review, reading);
    link.append(viewport);
    item.append(link, statuses);
    return item;
  }

  function showProgress() {
    const completed = readProgress();
    for (const link of list.querySelectorAll('[data-chapter]')) {
      const state = chapterState(nodes.get(link.dataset.chapter), completed, nodes);
      const badge = link.parentElement.querySelector('.route-reading-status');
      if (!badge) continue;
      const label = section.dataset[`${state}Label`];
      badge.className = `route-reading-status is-${state}`;
      badge.setAttribute('aria-label', label);
    }
  }

  window.addEventListener(routeChanged, showRoute);
  window.addEventListener(progressChanged, showProgress);
  window.addEventListener('resize', updateTitleOverflow);
  section.addEventListener('toggle', updateTitleOverflow);
  if (window.ResizeObserver) new ResizeObserver(updateTitleOverflow).observe(list);
  document.fonts?.ready.then(updateTitleOverflow);
  requestAnimationFrame(updateTitleOverflow);
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
