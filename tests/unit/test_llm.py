"""Unit tests for OpenRouter client and model catalog using respx mocks."""

import json
from pathlib import Path
import pytest
import respx
from httpx import Response

from normanjr.audit.rubric import RubricCriterion
from normanjr.domain.enums import ActionType, FindingSeverity
from normanjr.domain.models import ElementDescriptor, PageObservation
from normanjr.llm.client import OpenRouterClient
from normanjr.llm.model_catalog import ModelCatalog


@pytest.mark.asyncio
@respx.mock
async def test_openrouter_propose_action():
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "action_type": "click",
                        "target_ref": "e12",
                        "value": None,
                        "rationale": "Click the pricing link to view subscription tiers.",
                        "expected_change": "Navigation to /pricing",
                    })
                }
            }
        ],
        "usage": {"total_tokens": 150},
    }

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=mock_response)
    )

    client = OpenRouterClient(api_key="test-key")
    obs = PageObservation(
        observation_id="obs-1",
        url="https://example.com",
        title="Example Site",
        timestamp="2026-09-05T12:00:00Z",
    )
    candidates = [
        ElementDescriptor(ref="e12", role="link", name="Pricing", is_enabled=True)
    ]

    action = await client.propose_action(
        goal="View pricing", observation=obs, candidate_elements=candidates
    )

    assert action.action_type == ActionType.CLICK
    assert action.target_ref == "e12"
    assert "pricing" in action.rationale.lower()
    assert client.total_tokens_used == 150
    assert client.total_calls == 1


@pytest.mark.asyncio
@respx.mock
async def test_openrouter_evaluate_heuristics():
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "findings": [
                            {
                                "criterion_id": "NORMAN-AFFORDANCE-SIGNIFIER",
                                "title": "Low affordance on primary call to action",
                                "description": "The checkout button resembles a flat text banner without borders.",
                                "user_impact": "Users may not recognize the element as clickable.",
                                "severity": "major",
                                "target_ref": "e5",
                                "recommendation": "Add a prominent background color and hover effect.",
                                "confidence": "high",
                            }
                        ]
                    })
                }
            }
        ],
        "usage": {"total_tokens": 200},
    }

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json=mock_response)
    )

    client = OpenRouterClient(api_key="test-key")
    obs = PageObservation(
        observation_id="obs-1",
        url="https://example.com/checkout",
        title="Checkout",
        timestamp="2026-09-05T12:00:00Z",
    )
    criteria = [
        RubricCriterion(
            id="NORMAN-AFFORDANCE-SIGNIFIER",
            category_id="discoverability_affordance",
            title="Affordances",
            authority="Norman",
            default_severity=FindingSeverity.MAJOR,
        )
    ]

    eval_result = await client.evaluate_heuristics(obs, criteria)
    assert len(eval_result.findings) == 1
    assert eval_result.findings[0].criterion_id == "NORMAN-AFFORDANCE-SIGNIFIER"
    assert eval_result.findings[0].severity == FindingSeverity.MAJOR


@pytest.mark.asyncio
@respx.mock
async def test_model_catalog_caching(tmp_path: Path):
    mock_catalog = {
        "data": [
            {
                "id": "google/gemini-2.5-flash",
                "name": "Gemini 2.5 Flash",
                "context_length": 1000000,
                "architecture": {"modality": "text+image->text"},
                "pricing": {"prompt": "0", "completion": "0"},
            }
        ]
    }

    respx.get("https://openrouter.ai/api/v1/models").mock(
        return_value=Response(200, json=mock_catalog)
    )

    catalog = ModelCatalog(cache_dir=tmp_path)
    models = await catalog.get_model_capabilities()

    assert len(models) == 1
    model = models[0]
    assert model.model_id == "google/gemini-2.5-flash"
    assert model.supports_vision is True
    assert model.is_free is True

    # Check cache file was created
    assert catalog.cache_file.exists()
