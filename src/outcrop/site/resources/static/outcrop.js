import { writePreference } from './reader/preferences.js';
import './reading-routes.js';
/* Reader composition only. Each feature owns its state and event handlers.
 * Code inspection is adapted from the 1lab (AGPL-3.0); see NOTICE. */
import './reader/glyphs.js';
import './reader/guide.js';
import './reader/diagrams.js';
import { cfg } from './reader/document.js';
import { renderMath } from './reader/math.js';
import { initSearch } from './reader/search.js';
import { initHover } from './reader/hover.js';
import { initDefinitionModals } from './reader/definition-modal.js';
import { initOccur } from './reader/occurrences.js';
import { initCodeNotes } from './reader/notes.js';
import { initTermHover } from './reader/terms.js';
import { initSubmoduleFolds } from './reader/disclosure.js';
import { initNav, initPageScroll, initHeaderOffset, initSectionTracking } from './reader/navigation.js';
import { initHeaderControls } from './reader/header-controls.js';
import { initCurrentRoute } from './reader/current-route.js';
import { initCodeFullscreen } from './reader/code-fullscreen.js';
import { initPunctuationWrap } from './reader/punctuation-wrap.js';

function start() {
  try { writePreference('lang', cfg.lang); } catch (_) {}
  renderMath();
  initPunctuationWrap();
  initSearch();
  initCodeFullscreen();
  initHover();
  initDefinitionModals();
  initOccur();
  initCodeNotes();
  initTermHover();
  initSubmoduleFolds();
  initNav();
  initPageScroll();
  initHeaderOffset();
  initSectionTracking();
  initHeaderControls();
  initCurrentRoute();
  // A modal parent must not align or reveal the mirrored page until its own
  // reading controls (notably the sticky section directory) are initialized.
  document.documentElement.dataset.outcropReaderReady = 'true';
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
else start();
