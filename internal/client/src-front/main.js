import { initializeStudio } from "./studio.js";

function disableNativeTooltips() {
  const root = document.documentElement;
  const stripTitles = (element) => {
    element.removeAttribute("title");
    element.querySelectorAll("[title]").forEach((child) => child.removeAttribute("title"));
  };

  stripTitles(root);
  const observer = new MutationObserver((records) => {
    for (const record of records) {
      if (record.type === "attributes") {
        record.target.removeAttribute("title");
      } else {
        for (const node of record.addedNodes) {
          if (node instanceof Element) stripTitles(node);
        }
      }
    }
  });
  observer.observe(root, {
    subtree: true,
    childList: true,
    attributeFilter: ["title"],
  });
}

disableNativeTooltips();
initializeStudio();
