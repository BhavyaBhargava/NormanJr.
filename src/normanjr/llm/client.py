"""OpenRouter async HTTP client with structured outputs, retries, and usage tracking."""

from __future__ import annotations

import json
from typing import Any, Type, TypeVar

import httpx
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from normanjr.audit.rubric import RubricCriterion
from normanjr.config import ModelSettings
from normanjr.domain.models import ElementDescriptor, PageObservation
from normanjr.llm.prompts import (
    HEURISTIC_SYSTEM_PROMPT,
    JOURNEY_SYSTEM_PROMPT,
    PLANNER_SYSTEM_PROMPT,
)
from normanjr.llm.schemas import (
    ActionProposalResponse,
    HeuristicEvaluationResponse,
    JourneyListResponse,
)
from normanjr.security.prompt_boundary import wrap_untrusted_content

T = TypeVar("T", bound=BaseModel)


class OpenRouterClient:
    """Communicates with OpenRouter chat completions API."""

    def __init__(
        self,
        api_key: str,
        settings: ModelSettings | None = None,
        http_referer: str | None = "https://github.com/normanjr/normanjr",
        title: str | None = "NormanJr UX Auditor",
    ) -> None:
        self.api_key = api_key
        self.settings = settings or ModelSettings()
        self.http_referer = http_referer
        self.title = title
        self.total_tokens_used = 0
        self.total_calls = 0

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _post_chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Send chat completion request to OpenRouter with retries."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.http_referer or "",
            "X-Title": self.title or "",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.settings.requested_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            # Raise if 429 rate limit or 5xx server error
            if response.status_code in (429, 500, 502, 503, 504):
                response.raise_for_status()

            response.raise_for_status()
            data = response.json()

            # Track usage
            usage = data.get("usage", {})
            self.total_tokens_used += usage.get("total_tokens", 0)
            self.total_calls += 1

            return data

    async def propose_action(
        self,
        goal: str,
        observation: PageObservation,
        candidate_elements: list[ElementDescriptor],
    ) -> ActionProposalResponse:
        """Ask model planner to choose the next safe interaction."""
        elements_summary = [
            {"ref": e.ref, "role": e.role, "name": e.name, "value": e.value}
            for e in candidate_elements if e.ref and not e.ref.startswith("anon-")
        ]

        user_content = (
            f"User Goal: {goal}\n"
            f"Current Page: {observation.title} ({observation.url})\n\n"
            f"Available Interactive Elements:\n"
            f"{wrap_untrusted_content(json.dumps(elements_summary, indent=2), 'CANDIDATE_ELEMENTS')}\n\n"
            f"Respond with a JSON object matching this schema:\n"
            f"{json.dumps(ActionProposalResponse.model_json_schema(), indent=2)}"
        )

        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        res = await self._post_chat_completion(messages)
        content = res["choices"][0]["message"]["content"]
        return ActionProposalResponse.model_validate_json(content)

    async def evaluate_heuristics(
        self,
        observation: PageObservation,
        rubric_criteria: list[RubricCriterion],
    ) -> HeuristicEvaluationResponse:
        """Ask model heuristic evaluator to assess qualitative usability principles."""
        criteria_summary = [
            {"id": c.id, "title": c.title, "authority": c.authority}
            for c in rubric_criteria
        ]

        snapshot_content = ""
        if observation.snapshot_path:
            try:
                with open(observation.snapshot_path, "r", encoding="utf-8") as f:
                    snapshot_content = f.read()[:4000]
            except Exception:
                pass

        user_content = (
            f"Page Title: {observation.title}\n"
            f"Page URL: {observation.url}\n\n"
            f"Evaluated Rubric Criteria:\n"
            f"{json.dumps(criteria_summary, indent=2)}\n\n"
            f"Page DOM Snapshot:\n"
            f"{wrap_untrusted_content(snapshot_content, 'PAGE_SNAPSHOT')}\n\n"
            f"Return findings as a JSON object matching this schema:\n"
            f"{json.dumps(HeuristicEvaluationResponse.model_json_schema(), indent=2)}"
        )

        messages = [
            {"role": "system", "content": HEURISTIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        res = await self._post_chat_completion(messages)
        content = res["choices"][0]["message"]["content"]
        return HeuristicEvaluationResponse.model_validate_json(content)

    async def generate_journeys(self, url: str, snapshot_text: str) -> JourneyListResponse:
        """Propose safe exploratory journeys from the landing page snapshot."""
        user_content = (
            f"Target URL: {url}\n\n"
            f"Landing Page Snapshot:\n"
            f"{wrap_untrusted_content(snapshot_text[:5000], 'LANDING_PAGE_SNAPSHOT')}\n\n"
            f"Return proposed journeys as a JSON object matching this schema:\n"
            f"{json.dumps(JourneyListResponse.model_json_schema(), indent=2)}"
        )

        messages = [
            {"role": "system", "content": JOURNEY_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        res = await self._post_chat_completion(messages)
        content = res["choices"][0]["message"]["content"]
        return JourneyListResponse.model_validate_json(content)
