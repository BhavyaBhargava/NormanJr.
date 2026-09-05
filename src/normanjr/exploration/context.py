"""Runtime context for LangGraph execution containing non-serializable dependencies."""

from __future__ import annotations

from typing import Any

from normanjr.audit.rubric import RubricDefinition
from normanjr.config import AppConfig
from normanjr.mcp.playwright_adapter import PlaywrightAdapter
from normanjr.security.action_policy import ActionPolicy
from normanjr.security.url_policy import UrlPolicy
from normanjr.storage.run_repository import RunRepository


class AuditContext:
    """Carries runtime instances that must not be serialized into SQLite graph checkpoints."""

    def __init__(
        self,
        adapter: PlaywrightAdapter,
        action_policy: ActionPolicy,
        url_policy: UrlPolicy,
        repo: RunRepository,
        config: AppConfig,
        rubric: RubricDefinition,
        llm_client: Any | None = None,
    ) -> None:
        self.adapter = adapter
        self.action_policy = action_policy
        self.url_policy = url_policy
        self.repo = repo
        self.config = config
        self.rubric = rubric
        self.llm_client = llm_client
