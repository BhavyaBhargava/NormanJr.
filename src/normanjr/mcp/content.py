"""Normalization utilities for MCP content blocks and responses."""

from __future__ import annotations

import base64
from typing import Any


class NormalizedContent:
    """Represents a normalized MCP tool execution result."""

    def __init__(
        self,
        text: str = "",
        images: list[bytes] | None = None,
        is_error: bool = False,
        error_message: str | None = None,
        raw_blocks: list[Any] | None = None,
    ) -> None:
        self.text = text
        self.images = images or []
        self.is_error = is_error
        self.error_message = error_message
        self.raw_blocks = raw_blocks or []


def normalize_tool_result(result: Any) -> NormalizedContent:
    """Normalize CallToolResult into a structured, JSON-serializable NormalizedContent."""
    if result is None:
        return NormalizedContent(is_error=True, error_message="Null result received from MCP tool.")

    is_error = bool(getattr(result, "is_error", False))
    content_blocks = getattr(result, "content", []) or []

    text_parts: list[str] = []
    images: list[bytes] = []

    for block in content_blocks:
        block_type = getattr(block, "type", "")
        if block_type == "text" or hasattr(block, "text"):
            text_parts.append(getattr(block, "text", ""))
        elif block_type == "image" or hasattr(block, "data"):
            raw_data = getattr(block, "data", "")
            if isinstance(raw_data, str):
                try:
                    images.append(base64.b64decode(raw_data))
                except Exception:
                    pass
            elif isinstance(raw_data, bytes):
                images.append(raw_data)

    full_text = "\n".join(text_parts).strip()
    error_message = full_text if is_error else None

    return NormalizedContent(
        text=full_text,
        images=images,
        is_error=is_error,
        error_message=error_message,
        raw_blocks=content_blocks,
    )
