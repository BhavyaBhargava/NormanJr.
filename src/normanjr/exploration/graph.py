"""LangGraph workflow assembly with persistence and conditional routing."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from normanjr.exploration.context import AuditContext
from normanjr.exploration.nodes.authorize import authorize_node
from normanjr.exploration.nodes.check_progress import check_progress_node
from normanjr.exploration.nodes.deterministic_audit import deterministic_audit_node
from normanjr.exploration.nodes.evaluate import evaluate_node
from normanjr.exploration.nodes.execute import execute_node
from normanjr.exploration.nodes.finalize_journey import finalize_journey_node
from normanjr.exploration.nodes.finalize_run import finalize_run_node
from normanjr.exploration.nodes.perceive import perceive_node
from normanjr.exploration.nodes.plan import plan_node
from normanjr.exploration.nodes.verify import verify_node
from normanjr.exploration.routing import (
    route_after_authorize,
    route_after_check_progress,
    route_after_finalize_journey,
)
from normanjr.exploration.state import AuditState


def _get_context(config: RunnableConfig) -> AuditContext:
    ctx = config.get("configurable", {}).get("context")
    if not ctx:
        raise RuntimeError("AuditContext missing from RunnableConfig['configurable']['context']")
    return ctx


async def _perceive_node_wrapper(state: AuditState, config: RunnableConfig) -> dict[str, Any]:
    return await perceive_node(state, _get_context(config))


async def _deterministic_audit_wrapper(state: AuditState, config: RunnableConfig) -> dict[str, Any]:
    return await deterministic_audit_node(state, _get_context(config))


async def _check_progress_wrapper(state: AuditState, config: RunnableConfig) -> dict[str, Any]:
    return await check_progress_node(state, _get_context(config))


async def _plan_wrapper(state: AuditState, config: RunnableConfig) -> dict[str, Any]:
    return await plan_node(state, _get_context(config))


async def _authorize_wrapper(state: AuditState, config: RunnableConfig) -> dict[str, Any]:
    return await authorize_node(state, _get_context(config))


async def _execute_wrapper(state: AuditState, config: RunnableConfig) -> dict[str, Any]:
    return await execute_node(state, _get_context(config))


async def _verify_wrapper(state: AuditState, config: RunnableConfig) -> dict[str, Any]:
    return await verify_node(state, _get_context(config))


async def _evaluate_wrapper(state: AuditState, config: RunnableConfig) -> dict[str, Any]:
    return await evaluate_node(state, _get_context(config))


async def _finalize_journey_wrapper(state: AuditState, config: RunnableConfig) -> dict[str, Any]:
    return await finalize_journey_node(state, _get_context(config))


async def _finalize_run_wrapper(state: AuditState, config: RunnableConfig) -> dict[str, Any]:
    return await finalize_run_node(state, _get_context(config))


def build_audit_graph(checkpointer: AsyncSqliteSaver | None = None):
    """Assemble and compile the stateful NormanJr LangGraph workflow."""
    builder = StateGraph(AuditState)

    # Add workflow nodes
    builder.add_node("perceive", _perceive_node_wrapper)
    builder.add_node("deterministic_audit", _deterministic_audit_wrapper)
    builder.add_node("check_progress", _check_progress_wrapper)
    builder.add_node("plan", _plan_wrapper)
    builder.add_node("authorize", _authorize_wrapper)
    builder.add_node("execute", _execute_wrapper)
    builder.add_node("verify", _verify_wrapper)
    builder.add_node("evaluate", _evaluate_wrapper)
    builder.add_node("finalize_journey", _finalize_journey_wrapper)
    builder.add_node("finalize_run", _finalize_run_wrapper)

    # Add edges
    builder.add_edge(START, "perceive")
    builder.add_edge("perceive", "deterministic_audit")
    builder.add_edge("deterministic_audit", "check_progress")

    builder.add_conditional_edges(
        "check_progress",
        route_after_check_progress,
        {
            "finalize_journey": "finalize_journey",
            "plan": "plan",
        },
    )

    builder.add_edge("plan", "authorize")

    builder.add_conditional_edges(
        "authorize",
        route_after_authorize,
        {
            "finalize_journey": "finalize_journey",
            "execute": "execute",
        },
    )

    builder.add_edge("execute", "verify")
    builder.add_edge("verify", "evaluate")
    builder.add_edge("evaluate", "perceive")

    builder.add_conditional_edges(
        "finalize_journey",
        route_after_finalize_journey,
        {
            "perceive": "perceive",
            "finalize_run": "finalize_run",
        },
    )

    builder.add_edge("finalize_run", END)

    return builder.compile(checkpointer=checkpointer)
