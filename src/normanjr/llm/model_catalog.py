"""OpenRouter model catalog querying and capability caching."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, NamedTuple

import httpx
from platformdirs import user_cache_dir

CACHE_EXPIRY_SECONDS = 3600  # 1 hour


class ModelCapability(NamedTuple):
    model_id: str
    name: str
    context_length: int
    supports_vision: bool
    supports_structured_output: bool
    is_free: bool
    pricing_prompt: float
    pricing_completion: float


class ModelCatalog:
    """Discovers and caches model capabilities from OpenRouter."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path(user_cache_dir("normanjr"))
        self.cache_file = self.cache_dir / "model_catalog.json"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def get_model_capabilities(self, api_key: str | None = None) -> list[ModelCapability]:
        """Retrieve model catalog from disk cache or remote API."""
        cached_data = self._read_cache()
        if cached_data:
            return [self._parse_model_entry(m) for m in cached_data]

        # Fetch from OpenRouter API
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
                if res.status_code == 200:
                    models_json = res.json().get("data", [])
                    self._write_cache(models_json)
                    return [self._parse_model_entry(m) for m in models_json]
        except Exception:
            pass

        # If remote fetch failed, try stale cache
        stale_data = self._read_cache(ignore_expiry=True)
        if stale_data:
            return [self._parse_model_entry(m) for m in stale_data]

        return []

    def _parse_model_entry(self, data: dict[str, Any]) -> ModelCapability:
        model_id = data.get("id", "")
        name = data.get("name", model_id)
        context_length = data.get("context_length", 4096)

        # Vision check
        architecture = data.get("architecture", {})
        modality = str(architecture.get("modality", "")).lower()
        supports_vision = "image" in modality or "multimodal" in modality

        pricing = data.get("pricing", {})
        prompt_cost = float(pricing.get("prompt", "0") or 0)
        completion_cost = float(pricing.get("completion", "0") or 0)
        is_free = prompt_cost == 0 and completion_cost == 0 or model_id.endswith(":free")

        # OpenRouter supports structured output for most modern models
        supports_structured = True

        return ModelCapability(
            model_id=model_id,
            name=name,
            context_length=context_length,
            supports_vision=supports_vision,
            supports_structured_output=supports_structured,
            is_free=is_free,
            pricing_prompt=prompt_cost,
            pricing_completion=completion_cost,
        )

    def _read_cache(self, ignore_expiry: bool = False) -> list[dict[str, Any]] | None:
        if not self.cache_file.exists():
            return None
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            timestamp = payload.get("timestamp", 0)
            if ignore_expiry or (time.time() - timestamp < CACHE_EXPIRY_SECONDS):
                return payload.get("models")
        except Exception:
            pass
        return None

    def _write_cache(self, models: list[dict[str, Any]]) -> None:
        try:
            payload = {
                "timestamp": time.time(),
                "models": models,
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception:
            pass
