"""Application-owned, read-only JavaScript DOM metric scripts."""

from __future__ import annotations

# Script to measure interactive element target sizes against WCAG 2.5.8 (min 24x24px)
DOM_TARGET_SIZE_SCRIPT = """() => {
  const selectors = ['button', 'a[href]', 'input', 'select', 'textarea', '[role="button"]', '[role="link"]', '[role="checkbox"]'];
  const elements = document.querySelectorAll(selectors.join(', '));
  const results = [];

  elements.forEach((el, index) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return;
    if (rect.width === 0 && rect.height === 0) return;

    const width = Math.round(rect.width);
    const height = Math.round(rect.height);
    const text = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('name') || '').trim();

    if (width < 24 || height < 24) {
      results.push({
        tag: el.tagName.toLowerCase(),
        name: text.slice(0, 50),
        width: width,
        height: height,
        selector: el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase()),
      });
    }
  });

  return JSON.stringify(results);
}"""

# Script to analyze heading hierarchy and detect level skips
DOM_HEADING_HIERARCHY_SCRIPT = """() => {
  const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
  const list = headings.map(h => ({
    level: parseInt(h.tagName[1]),
    text: (h.innerText || '').trim().slice(0, 60),
  }));

  const skips = [];
  let prevLevel = 0;
  for (let i = 0; i < list.length; i++) {
    const curr = list[i].level;
    if (prevLevel > 0 && curr > prevLevel + 1) {
      skips.push({
        fromLevel: prevLevel,
        toLevel: curr,
        text: list[i].text,
      });
    }
    prevLevel = curr;
  }

  return JSON.stringify({
    totalHeadings: list.length,
    hasH1: list.some(h => h.level === 1),
    skips: skips,
  });
}"""

# Script to verify form inputs have valid programmatic labels
DOM_FORM_LABEL_SCRIPT = """() => {
  const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select'));
  const unlabelled = [];

  inputs.forEach(input => {
    const id = input.id;
    const hasLabelFor = id ? document.querySelector('label[for="' + id + '"]') : null;
    const hasParentLabel = input.closest('label');
    const ariaLabel = input.getAttribute('aria-label');
    const ariaLabelledBy = input.getAttribute('aria-labelledby');
    const placeholder = input.getAttribute('placeholder');

    const isLabelled = Boolean(hasLabelFor || hasParentLabel || ariaLabel || ariaLabelledBy);

    if (!isLabelled) {
      unlabelled.push({
        id: id || '',
        tag: input.tagName.toLowerCase(),
        type: input.type || '',
        placeholder: placeholder || '',
        name: input.name || '',
      });
    }
  });

  return JSON.stringify(unlabelled);
}"""

# Script to detect images missing alt attributes
DOM_IMAGE_ALT_SCRIPT = """() => {
  const images = Array.from(document.querySelectorAll('img'));
  const missing = [];

  images.forEach(img => {
    const style = window.getComputedStyle(img);
    if (style.display === 'none' || style.visibility === 'hidden') return;
    if (!img.hasAttribute('alt')) {
      missing.push({
        src: (img.src || '').slice(0, 80),
        id: img.id || '',
      });
    }
  });

  return JSON.stringify(missing);
}"""
