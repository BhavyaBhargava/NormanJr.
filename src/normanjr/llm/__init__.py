"""LLM package for NormanJr."""

from normanjr.llm.client import OpenRouterClient
from normanjr.llm.model_catalog import ModelCapability, ModelCatalog
from normanjr.llm.schemas import (
    ActionProposalResponse,
    HeuristicEvaluationResponse,
    HeuristicFindingProposal,
    JourneyListResponse,
    JourneyProposal,
)

__all__ = [
    "ActionProposalResponse",
    "HeuristicEvaluationResponse",
    "HeuristicFindingProposal",
    "JourneyListResponse",
    "JourneyProposal",
    "ModelCapability",
    "ModelCatalog",
    "OpenRouterClient",
]
