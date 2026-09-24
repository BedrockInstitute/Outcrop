/* Outcrop reader: document. AGPL-3.0-only. */

  var cfg = window.outcrop || { baseUrl: "", lang: "en", module: "" };
  var compactPointer = window.matchMedia("(hover: none), (pointer: coarse)");
  var isDefinitionModalDocument =
    new URLSearchParams(location.search).get("outcrop-modal") === "1";
  if (isDefinitionModalDocument)
    document.documentElement.classList.add("definition-modal-document");
  function modalReadingScroller() {
    return isDefinitionModalDocument ? document.getElementById("main-content") : null;
  }


export { cfg, compactPointer, isDefinitionModalDocument, modalReadingScroller };
