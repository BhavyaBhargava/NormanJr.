"""Accessibility snapshot parsing and ElementDescriptor construction."""

from __future__ import annotations

import re
from typing import Any

from normanjr.domain.models import BoundingBox, ElementDescriptor

# Regular expressions to parse Playwright MCP markdown accessibility snapshots
# Example lines:
# - button "Submit Button" [ref=e2]
# - textbox "Username" [ref=e4] [disabled]
# - link "Home" [ref=e1]
# - heading "Dashboard" [level=1]
SNAPSHOT_LINE_REGEX = re.compile(
    r"^(?P<indent>\s*)[-*]\s+(?P<role>[a-zA-Z0-9_\-]+)(?:\s+\"(?P<name>[^\"]*)\")?(?:\s+(?P<attrs>\[.*\]))?"
)
ATTR_REGEX = re.compile(r"\[(?P<key>[a-zA-Z0-9_\-]+)(?:=(?P<val>[^\]]+))?\]")


def parse_snapshot_elements(snapshot_text: str) -> list[ElementDescriptor]:
    """Parse accessibility snapshot markdown into a list of ElementDescriptor instances."""
    elements: list[ElementDescriptor] = []

    for line in snapshot_text.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("###") or line_clean.startswith("Page URL"):
            continue

        match = SNAPSHOT_LINE_REGEX.match(line)
        if not match:
            continue

        role = match.group("role").lower()
        name = match.group("name") or ""
        attrs_str = match.group("attrs") or ""

        # Parse bracketed attributes
        attributes: dict[str, Any] = {}
        ref: str | None = None

        for attr_match in ATTR_REGEX.finditer(attrs_str):
            k = attr_match.group("key")
            v = attr_match.group("val")
            if k == "ref":
                ref = v
            else:
                attributes[k] = v if v is not None else True

        # Only track elements that have a target reference or are interactive roles
        is_interactive = role in (
            "button",
            "link",
            "textbox",
            "checkbox",
            "radio",
            "combobox",
            "menuitem",
            "tab",
            "switch",
            "slider",
            "searchbox",
        )

        if ref or is_interactive:
            element_ref = ref or f"anon-{len(elements)}"
            fingerprint = f"{role}:{name.lower().strip()}"
            is_enabled = "disabled" not in attributes

            elem = ElementDescriptor(
                ref=element_ref,
                role=role,
                name=name,
                element_type=role,
                value=attributes.get("value"),
                is_visible=True,
                is_enabled=is_enabled,
                is_focusable=is_interactive,
                states=attributes,
                fingerprint=fingerprint,
            )
            elements.append(elem)

    return elements
