"""Serialization and stable hashing utilities for NormanJr."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel


class EntityJSONEncoder(json.JSONEncoder):
    """JSON Encoder for Pydantic models and custom types with stable formatting."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")
        return super().default(obj)


def to_canonical_json(data: Any, indent: int = 2) -> str:
    """Serialize object to deterministic canonical JSON with sorted keys."""
    if isinstance(data, BaseModel):
        dict_data = data.model_dump(mode="json")
    else:
        dict_data = data
    return json.dumps(dict_data, indent=indent, sort_keys=True, cls=EntityJSONEncoder)


def normalize_url(url: str, keep_query: bool = True) -> str:
    """Normalize URL by lowercasing scheme/host, stripping trailing slash, and optional query sanitization."""
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
        query = parsed.query if keep_query else ""
        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return url.strip().rstrip("/")


def compute_state_fingerprint(
    url: str,
    title: str,
    interactive_elements: list[dict[str, Any]] | list[Any],
    active_dialog: bool = False,
    step_indicator: str | None = None,
) -> str:
    """
    Compute a stable, deterministic state fingerprint from structural page characteristics.
    Ignores ephemeral element references, timestamps, and unstable dynamic content.
    """
    clean_url = normalize_url(url, keep_query=False)
    clean_title = " ".join(title.lower().split())

    # Build sorted list of normalized element signatures (role, normalized_name)
    elem_tuples: list[tuple[str, str, str]] = []
    for elem in interactive_elements:
        if hasattr(elem, "role") and hasattr(elem, "name"):
            role = str(elem.role).lower().strip()
            name = " ".join(str(elem.name).lower().split())
            elem_type = getattr(elem, "element_type", "")
            elem_tuples.append((role, name, elem_type))
        elif isinstance(elem, dict):
            role = str(elem.get("role", "")).lower().strip()
            name = " ".join(str(elem.get("name", "")).lower().split())
            elem_type = str(elem.get("element_type", ""))
            elem_tuples.append((role, name, elem_type))

    elem_tuples.sort()

    payload = {
        "v": "1.0",
        "url": clean_url,
        "title": clean_title,
        "dialog": active_dialog,
        "step": step_indicator or "",
        "elements": elem_tuples,
    }

    canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def compute_action_hash(
    action_type: str,
    target_role: str = "",
    target_name: str = "",
    value: str | None = None,
) -> str:
    """Compute a deterministic hash for a normalized user action to detect repetitive loops."""
    payload = {
        "action": action_type.lower().strip(),
        "role": target_role.lower().strip(),
        "name": " ".join(target_name.lower().split()),
        "val": (value or "").strip(),
    }
    canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
