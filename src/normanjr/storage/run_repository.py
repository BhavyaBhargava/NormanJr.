"""Repository for audit runs and execution artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from normanjr.config import AppConfig
from normanjr.domain.models import AuditRun
from normanjr.domain.serialization import to_canonical_json
from normanjr.storage.artifacts import atomic_write_text, verify_path_containment


class RunRepository:
    """Manages files and data records for an individual audit run."""

    def __init__(self, base_dir: Path | str, run_id: str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.run_id = run_id
        self.run_dir = self.base_dir / run_id
        self._initialize_directories()

    def _initialize_directories(self) -> None:
        verify_path_containment(self.base_dir, self.run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "screenshots").mkdir(exist_ok=True)
        (self.run_dir / "snapshots").mkdir(exist_ok=True)
        (self.run_dir / "metrics").mkdir(exist_ok=True)
        (self.run_dir / "traces").mkdir(exist_ok=True)
        (self.run_dir / "errors").mkdir(exist_ok=True)

    def save_config_snapshot(self, config: AppConfig) -> Path:
        """Save a redacted configuration snapshot into the run directory."""
        target = self.run_dir / "config.redacted.json"
        text = json.dumps(config.redacted_dict(), indent=2, sort_keys=True)
        atomic_write_text(target, text)
        return target

    def log_event(self, event_name: str, payload: dict[str, Any]) -> None:
        """Append a structured JSON line to events.jsonl."""
        event_entry = {
            "run_id": self.run_id,
            "event": event_name,
            **payload,
        }
        target = self.run_dir / "events.jsonl"
        with open(target, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_entry, sort_keys=True) + "\n")

    def save_result(self, audit_run: AuditRun) -> Path:
        """Persist canonical result.json atomically."""
        target = self.run_dir / "result.json"
        text = to_canonical_json(audit_run)
        atomic_write_text(target, text)
        return target

    def load_result(self) -> AuditRun:
        """Load canonical result.json."""
        target = self.run_dir / "result.json"
        if not target.exists():
            raise FileNotFoundError(f"result.json not found in {self.run_dir}")
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AuditRun(**data)
