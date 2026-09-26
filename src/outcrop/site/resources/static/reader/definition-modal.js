import { alignModalDefinition, sizeModalReadingScroller, definitionPageKey } from './definition-layout.js';
import { DefinitionSession } from './definition-session.js';
/* Outcrop reader: definition-modal. AGPL-3.0-only. */
import { cfg, compactPointer, isDefinitionModalDocument } from "./document.js";
import { isDefinitionPopupAction } from "./code-targets.js";
const isDarkTheme = () => window.outcropAppearance.effectiveMode() === "dark";

  /* ---- in-page definition previews --------------------------------------- */
  function initDefinitionModals() {
    const session = new DefinitionSession();
    var view = null;
    var isModalDocument = isDefinitionModalDocument;
    var copy = ({
      en: { title: "Definition", loading: "Loading definition…", loadingPage: "Loading page…",
        missing: "The target definition could not be loaded from this page.",
        missingPage: "The linked passage could not be loaded from this page.", close: "Close",
        back: "Back", forward: "Forward", jump: "Go to this location" },
      zh: { title: "定义", loading: "正在载入定义…", loadingPage: "正在载入正文…",
        missing: "无法从该页面载入目标定义。",
        missingPage: "无法从该页面载入链接所指的正文。", close: "关闭",
        back: "后退", forward: "前进", jump: "跳转进入" },
      ja: { title: "定義", loading: "定義を読み込んでいます…", loadingPage: "本文を読み込んでいます…",
        missing: "このページから対象の定義を読み込めませんでした。",
        missingPage: "リンク先の本文を読み込めませんでした。", close: "閉じる",
        back: "戻る", forward: "進む", jump: "この位置へ移動" }
    })[cfg.lang] || {
      title: "Definition", loading: "Loading definition…", loadingPage: "Loading page…",
      missing: "The target definition could not be loaded from this page.",
      missingPage: "The linked passage could not be loaded from this page.", close: "Close",
      back: "Back", forward: "Forward", jump: "Go to this location"
    };

    function targetFor(link) {
      if (!link || link.classList.contains("definition-modal-title")) return null;
      var raw = link.getAttribute("href");
      if (!raw) return null;
      var url;
      try { url = new URL(raw, document.baseURI); } catch (_) { return null; }
      if (url.origin !== location.origin) return null;
      if (!url.hash && !link.matches(".Module, [data-module-target]")) return null;
      url.searchParams.delete("outcrop-modal");
      url.searchParams.delete("outcrop-modal-scroll");
      var spec = link.getAttribute("data-type");
      var filename = decodeURIComponent(url.pathname.split("/").pop() || "");
      return { url: url, module: spec ? spec.split("#")[0] : filename.replace(/\.html$/, "") };
    }
    function proseTargetFor(link) {
      if (!link || (!link.closest("article") && !link.hasAttribute("data-content-modal"))
          || link.closest("nav, #reading-explorer")) return null;
      if (link.closest(".Agda, code") || link.hasAttribute("download")
          || (link.target && link.target !== "_self")) return null;
      var url;
      try { url = new URL(link.getAttribute("href"), document.baseURI); }
      catch (_) { return null; }
      var samePageAnchor = !!url.hash
        && url.pathname === new URL(document.baseURI).pathname;
      if (url.origin !== location.origin
          || (!/\.(?:html?)$/i.test(url.pathname) && !samePageAnchor)) return null;
      // These anchors select the directory's application views, not book content.
      if (/^#(?:reading-explorer|dependency-map|term-glossary)$/.test(url.hash)) return null;
      url.searchParams.delete("outcrop-modal");
      url.searchParams.delete("outcrop-modal-scroll");
      return { url: url, module: decodeURIComponent(url.pathname.split("/").pop() || "").replace(/\.html?$/, ""), kind: "prose" };
    }
    document.querySelectorAll("article a[href]").forEach(function (link) {
      if (proseTargetFor(link)) link.setAttribute("aria-haspopup", "dialog");
    });
    function close() {
      if (!view) return;
      var focus = view.opener;
      if (view.frameSizeObserver) view.frameSizeObserver.disconnect();
      session.close();
      view.backdrop.remove();
      view = null;
      document.body.classList.remove("definition-modal-open");
      if (focus && focus.isConnected && focus.focus) focus.focus({ preventScroll: true });
    }
    function createView(opener) {
      var backdrop = document.createElement("div");
      backdrop.className = "definition-modal-backdrop";
      var modal = document.createElement("section");
      modal.className = "definition-modal";
      modal.setAttribute("role", "dialog");
      modal.setAttribute("aria-modal", "true");
      var titleId = "definition-modal-title-" + Date.now();
      modal.setAttribute("aria-labelledby", titleId);
      var header = document.createElement("header");
      header.className = "definition-modal-header";
      var title = document.createElement("div");
      title.className = "definition-modal-title";
      title.id = titleId;
      title.textContent = copy.title;
      var historyActions = document.createElement("div");
      historyActions.className = "definition-modal-history";
      var back = document.createElement("button");
      back.className = "definition-modal-history-button";
      back.type = "button";
      back.setAttribute("aria-label", copy.back);
      back.title = copy.back;
      back.textContent = "←";
      var forward = document.createElement("button");
      forward.className = "definition-modal-history-button";
      forward.type = "button";
      forward.setAttribute("aria-label", copy.forward);
      forward.title = copy.forward;
      forward.textContent = "→";
      var closeButton = document.createElement("button");
      closeButton.className = "definition-modal-close";
      closeButton.type = "button";
      closeButton.setAttribute("aria-label", copy.close);
      closeButton.textContent = "×";
      var jump = document.createElement("a");
      jump.className = "definition-modal-jump";
      jump.setAttribute("aria-label", copy.jump);
      jump.title = copy.jump;
      jump.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' +
        '<path d="M13 4h7v16h-7M3 12h12M10 7l5 5-5 5"/></svg>';
      var body = document.createElement("div");
      body.className = "definition-modal-body";
      historyActions.appendChild(back);
      historyActions.appendChild(forward);
      header.appendChild(historyActions);
      header.appendChild(title);
      header.appendChild(jump);
      header.appendChild(closeButton);
      modal.appendChild(header);
      modal.appendChild(body);
      backdrop.appendChild(modal);
      document.body.appendChild(backdrop);
      view = { backdrop: backdrop, modal: modal, opener: opener, title: title,
        body: body, back: back, forward: forward, jump: jump, frame: null,
        frameSizeObserver: null };
      document.body.classList.add("definition-modal-open");
      closeButton.addEventListener("click", close);
      backdrop.addEventListener("pointerdown", function (event) {
        if (event.target === backdrop) close();
      });
      back.addEventListener("click", function () {
        if (!session.move(-1)) return;
        renderHistoryEntry();
      });
      forward.addEventListener("click", function () {
        if (!session.move(1)) return;
        renderHistoryEntry();
      });
      closeButton.focus({ preventScroll: true });
    }
    function renderHistoryEntry() {
      if (!view || !session.current) return;
      if (view.frameSizeObserver) {
        view.frameSizeObserver.disconnect();
        view.frameSizeObserver = null;
      }
      var entry = session.current;
      var request = session.begin();
      view.title.textContent = entry.label;
      // Use the history entry's definition anchor, never the iframe's scroll
      // position or its fragment-free internal loading URL.
      view.jump.href = entry.target.url.href;
      view.back.disabled = !session.canBack;
      view.forward.disabled = !session.canForward;
      view.body.setAttribute("aria-busy", "true");
      var loading = document.createElement("div");
      loading.className = "definition-modal-loading";
      loading.setAttribute("role", "status");
      var indicator = document.createElement("span");
      indicator.className = "definition-modal-loading-indicator";
      indicator.setAttribute("aria-hidden", "true");
      var loadingText = document.createElement("span");
      loadingText.textContent = entry.target.kind === "prose" ? copy.loadingPage : copy.loading;
      loading.append(indicator, loadingText);
      var frame = document.createElement("iframe");
      frame.className = "definition-modal-frame";
      frame.title = entry.label;
      frame.style.colorScheme = isDarkTheme() ? "dark" : "light";
      frame.setAttribute("aria-hidden", "true");
      frame.setAttribute("inert", "");
      var revealed = false, failed = false;
      function isCurrentFrame() {
        return view && session.isCurrent(request) && view.frame === frame;
      }
      function showMissing() {
        if (!isCurrentFrame()) return;
        failed = true;
        view.body.setAttribute("aria-busy", "false");
        loading.classList.add("is-error");
        loadingText.textContent = entry.target.kind === "prose" ? copy.missingPage : copy.missing;
        indicator.remove();
        view.body.replaceChildren(loading);
      }
      function revealFrame() {
        if (revealed || failed || !isCurrentFrame()) return;
        revealed = true;
        frame.classList.add("is-ready");
        frame.removeAttribute("aria-hidden");
        frame.removeAttribute("inert");
        view.body.setAttribute("aria-busy", "false");
        loading.remove();
      }
      var frameUrl = new URL(entry.target.url.href);
      frameUrl.searchParams.set("outcrop-modal", "1");
      /* A frame URL with a fragment starts a second, native anchor scroll which
         can race the code-block alignment, especially in mobile WebKit. */
      frameUrl.hash = "";
      var readyAttempts = 0;
      frame.addEventListener("load", function onFrameLoad() {
        if (!isCurrentFrame()) return;
        var frameDocument, loadedUrl;
        try {
          frameDocument = frame.contentDocument;
          loadedUrl = new URL(frame.contentWindow.location.href);
        } catch (_) { showMissing(); return; }
        if (definitionPageKey(loadedUrl) !== definitionPageKey(entry.target.url)) {
          showMissing();
          return;
        }
        // The parent owns this reading plane. Apply its scroll-container class
        // here as well as in the child runtime: on a cold/slow load the iframe
        // may fire `load` before its module initialization has decorated the
        // root, leaving #main-content non-scrollable during first alignment.
        frameDocument.documentElement.classList.add("definition-modal-document");
        if (frameDocument.documentElement.dataset.outcropReaderReady !== "true") {
          // The iframe's load event does not guarantee its module graph has
          // initialized the sticky directory. Align only after that handshake;
          // otherwise a cold mirror can appear at the wrong chapter position.
          if (++readyAttempts > 400) { showMissing(); return; }
          setTimeout(onFrameLoad, 50);
          return;
        }
        var id;
        try { id = decodeURIComponent(entry.target.url.hash.slice(1)); }
        catch (_) { id = entry.target.url.hash.slice(1); }
        var target = frameDocument && (id ? frameDocument.getElementById(id)
          : frameDocument.querySelector("article h1, h1, pre.Agda"));
        if (!target) {
          showMissing();
          return;
        }
        /* Match the reader's current theme before exposing the new document.
           Opacity keeps layout measurable without painting the iframe's blank canvas. */
        frameDocument.documentElement.classList.remove("theme-light", "theme-dark");
        frameDocument.documentElement.classList.add(isDarkTheme() ? "theme-dark" : "theme-light");
        if (window.outcropAppearance) window.outcropAppearance.syncFrame(frame);
        var chapterConfig = frame.contentWindow.outcrop || {};
        var chapterHeading = frameDocument.querySelector("article h1, h1");
        var chapterText = chapterConfig.title || (chapterHeading ? chapterHeading.textContent.trim() : entry.target.module);
        var moduleName = chapterConfig.chapter || entry.target.module;
        var definitionName = entry.label.indexOf(moduleName + ".") === 0
          ? entry.label.slice(moduleName.length + 1) : entry.label;
        if (entry.target.kind === "prose") {
          var sectionLabel = target.closest("h1, h2, h3, h4")?.textContent.trim()
            || entry.label;
          var heading = sectionLabel && sectionLabel !== chapterText
            ? chapterText + " · " + sectionLabel : chapterText;
          view.title.textContent = heading;
          frame.title = heading;
        } else {
          var titleName = document.createElement("code");
          titleName.className = "Agda";
          var titleToken = document.createElement("span");
          titleToken.className = target.getAttribute("class") || "";
          titleToken.textContent = definitionName;
          titleName.appendChild(titleToken);
          view.title.replaceChildren(document.createTextNode(chapterText + " "), titleName);
          frame.title = chapterText + " " + definitionName;
        }
        // Prelude re-exports are introduced by their explanatory import. In
        // the inspection modal show that import's enclosing section first,
        // including nested sections. Keep the definition URL/identity itself
        // unchanged for history, enter-page and same-definition navigation.
        var importSection = preludeImportSection(entry, target);
        var targetBlock = importSection || (entry.target.kind === "prose"
          ? target.closest("pre.Agda, figure, h1, h2, h3, h4, p, li, table") || target
          : chapterConfig.external && target.closest("pre.Agda")
            // External Agda HTML has one pre for the whole module. Aligning its
            // top sends every definition to the start of the file instead of
            // its declaration line; internal chapters use one pre per block.
            ? target : target.closest("pre.Agda, h1") || target);
        var scroller = sizeModalReadingScroller(frameDocument, view.body);
        if (!scroller) {
          showMissing();
          return;
        }
        if (frame.contentWindow.getComputedStyle(scroller).overflowY !== "auto") {
          // A missing stylesheet must not expose a seemingly valid modal at
          // the top of the chapter with an inert anchor.
          showMissing();
          return;
        }
        var alignmentRun = 0;
        function alignTarget() {
          if (!alignmentActive || !view || !session.isCurrent(request) || view.frame !== frame
              || !targetBlock.isConnected) return false;
          return alignModalDefinition(frameDocument, targetBlock);
        }
        function requestAlignment() {
          if (!alignmentActive) return;
          var run = ++alignmentRun;
          function settle(remaining) {
            if (!alignmentActive || run !== alignmentRun) return;
            var pending = alignTarget();
            if (pending && remaining > 0)
              frame.contentWindow.requestAnimationFrame(function () {
                settle(remaining - 1);
              });
            else revealFrame();
          }
          settle(8);
        }
        var alignmentActive = true;
        var alignmentObserver = null;
        function stopAlignment() {
          alignmentActive = false;
          alignmentRun += 1;
          if (alignmentObserver) alignmentObserver.disconnect();
        }
        ["pointerdown", "touchstart", "wheel", "keydown"].forEach(function (type) {
          frame.contentWindow.addEventListener(type, stopAlignment,
            { capture: true, passive: type !== "keydown", once: true });
        });
        /* Allow iframe styles and the explicit scroller size to take effect
           before aligning and replacing the loading surface. */
        frame.contentWindow.requestAnimationFrame(requestAlignment);
        if (frameDocument.fonts && frameDocument.fonts.ready) {
          frameDocument.fonts.ready.then(function () {
            frame.contentWindow.requestAnimationFrame(requestAlignment);
          });
        }
        if (frame.contentWindow.ResizeObserver) {
          alignmentObserver = new frame.contentWindow.ResizeObserver(function () {
            frame.contentWindow.requestAnimationFrame(requestAlignment);
          });
          alignmentObserver.observe(targetBlock);
          if (targetBlock.parentElement) alignmentObserver.observe(targetBlock.parentElement);
          var article = frameDocument.querySelector("article");
          if (article) alignmentObserver.observe(article);
          alignmentObserver.observe(scroller);
        }
        if (window.ResizeObserver) {
          view.frameSizeObserver = new ResizeObserver(function () {
            if (!view || !session.isCurrent(request) || view.frame !== frame) return;
            sizeModalReadingScroller(frameDocument, view.body);
            requestAlignment();
          });
          view.frameSizeObserver.observe(view.body);
        }
        frame.contentWindow.addEventListener("resize", requestAlignment, { passive: true });
        session.own(function () {
          stopAlignment();
          frame.contentWindow.removeEventListener("resize", requestAlignment);
        });
      });
      frame.addEventListener("error", showMissing);
      view.frame = frame;
      frame.src = frameUrl.href;
      view.body.replaceChildren(loading, frame);
    }
    function qualifiedLabel(target, name) {
      return name === target.module || name.indexOf(target.module + ".") === 0
        ? name : target.module + "." + name;
    }
    function push(target, label, opener) {
      document.dispatchEvent(new CustomEvent("outcrop:definition-modal-open"));
      if (!view) createView(opener);
      session.push(target, label);
      renderHistoryEntry();
    }

    function open(link, target) {
      var name = link.getAttribute("data-name")
        || link.textContent.trim() || target.module;
      push(target, qualifiedLabel(target, name), link);
    }

    function preludeImportSection(entry, target) {
      if (entry.target.module !== cfg.preludeModule) return null;
      var code = target.closest('pre.Agda');
      if (!code || !/(?:^|\n)\s*(?:open\s+)?import\s+\S/u.test(code.textContent)) return null;
      var article = code.closest('article');
      if (!article) return null;
      var section = null;
      article.querySelectorAll('h2[id], h3[id], h4[id], h5[id], h6[id]').forEach(function (heading) {
        if (heading.compareDocumentPosition(code) & Node.DOCUMENT_POSITION_FOLLOWING) section = heading;
      });
      return section;
    }

    document.addEventListener("click", function (event) {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      var clickedLink = event.target.closest && event.target.closest("a[href]");
      if (!clickedLink) return;
      if (clickedLink.matches("[data-hover-help], [data-hover-html], [data-hover-template]")) {
        if (compactPointer.matches || clickedLink.dataset.hoverNavigate !== "modal") {
          event.preventDefault(); return;
        }
      }
      var definitionLink = clickedLink.matches(
        '.Agda a[href], .type-definition-link[href], [data-hover-navigate="modal"]'
      ) ? clickedLink : null;
      if (!definitionLink && event.defaultPrevented) return;
      var target = targetFor(definitionLink);
      var proseTarget = !definitionLink && !event.defaultPrevented
        ? proseTargetFor(clickedLink) : null;
      if (proseTarget) {
        event.preventDefault();
        event.stopPropagation();
        var proseLabel = clickedLink.textContent.trim() || proseTarget.module;
        if (isModalDocument && window.parent !== window) {
          window.parent.postMessage({ type: "outcrop-prose-open",
            href: proseTarget.url.href, module: proseTarget.module,
            label: proseLabel }, location.origin);
        } else {
          push(proseTarget, proseLabel, clickedLink);
        }
        return;
      }
      if (!target) {
        if (isModalDocument && window.parent !== window && !event.defaultPrevented
            && !clickedLink.hasAttribute('download')
            && (!clickedLink.target || clickedLink.target === '_self')) {
          var pageTarget;
          try { pageTarget = new URL(clickedLink.href, document.baseURI); }
          catch (_) { return; }
          pageTarget.searchParams.delete("outcrop-modal");
          pageTarget.searchParams.delete("outcrop-modal-scroll");
          event.preventDefault();
          event.stopPropagation();
          window.parent.postMessage({ type: "outcrop-page-navigate",
            href: pageTarget.href }, location.origin);
        }
        return;
      }
      if (compactPointer.matches && !isDefinitionPopupAction(definitionLink)) {
        /* The hover subsystem owns this first tap. Its explicit arrow is the
           only compact-pointer action that advances from hover to modal. */
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      if (isModalDocument && window.parent !== window) {
        document.dispatchEvent(new CustomEvent('outcrop:definition-modal-open'));
        var embeddedName = definitionLink.getAttribute("data-name")
          || definitionLink.textContent.trim() || target.module;
        window.parent.postMessage({ type: "outcrop-definition-open",
          href: target.url.href, module: target.module,
          label: qualifiedLabel(target, embeddedName) }, location.origin);
        return;
      }
      open(definitionLink, target);
    });
    window.addEventListener("message", function (event) {
      if (!view || event.origin !== location.origin
          || !view.frame || event.source !== view.frame.contentWindow
          || !event.data) return;
      if (event.data.type === 'outcrop-code-fullscreen') {
        view.backdrop.classList.toggle('has-fullscreen-code', event.data.active === true);
        if (event.data.active !== true) {
          const frame = view.frame, surfaceId = event.data.surfaceId;
          /* Acknowledge only after the normal iframe viewport has reflowed.
             Earlier restoration can clamp a saved near-bottom position. */
          requestAnimationFrame(function () {
            if (view && view.frame === frame) {
              sizeModalReadingScroller(frame.contentDocument, view.body);
              frame.getBoundingClientRect();
              frame.contentWindow.postMessage({type: 'outcrop-code-surface-restored', surfaceId}, location.origin);
            }
          });
        }
        return;
      }
      if (event.data.type === "outcrop-page-navigate") {
        var pageUrl;
        try { pageUrl = new URL(event.data.href, document.baseURI); }
        catch (_) { return; }
        if (!/^(https?:|mailto:)$/.test(pageUrl.protocol)) return;
        location.href = pageUrl.href;
        return;
      }
      if (event.data.type !== "outcrop-definition-open"
          && event.data.type !== "outcrop-prose-open") return;
      var targetUrl;
      try { targetUrl = new URL(event.data.href, document.baseURI); }
      catch (_) { return; }
      targetUrl.searchParams.delete("outcrop-modal");
      targetUrl.searchParams.delete("outcrop-modal-scroll");
      var current = session.current;
      if (current && definitionPageKey(current.target.url) === definitionPageKey(targetUrl)
          && current.target.url.hash === targetUrl.hash) {
        if (event.data.type === "outcrop-definition-open") location.href = targetUrl.href;
        else renderHistoryEntry();
        return;
      }
      push({ url: targetUrl, module: event.data.module,
        kind: event.data.type === "outcrop-prose-open" ? "prose" : "definition" },
        event.data.label, view.opener);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      if (isModalDocument && window.parent !== window) {
        window.parent.postMessage({ type: "outcrop-definition-close" }, location.origin);
      } else if (view) {
        event.preventDefault();
        close();
      }
    });
    window.addEventListener("message", function (event) {
      if (view && event.origin === location.origin && view.frame
          && event.source === view.frame.contentWindow && event.data
          && event.data.type === "outcrop-definition-close") close();
    });
  }

export { initDefinitionModals, alignModalDefinition, sizeModalReadingScroller, definitionPageKey };
