"""Unit tests for domain models, state hashing, and storage repository."""

from pathlib import Path
from normanjr.config import load_config
from normanjr.domain.enums import ActionType, AuditStatus
from normanjr.domain.models import AuditRun, ElementDescriptor, ProposedAction
from normanjr.domain.serialization import (
    compute_action_hash,
    compute_state_fingerprint,
    to_canonical_json,
)
from normanjr.storage.artifacts import save_metrics, save_screenshot, save_snapshot
from normanjr.storage.manifest import generate_run_manifest
from normanjr.storage.run_repository import RunRepository


def test_state_fingerprint_stability():
    elements_a = [
        {"role": "button", "name": "Submit", "element_type": "button"},
        {"role": "link", "name": "Home", "element_type": "a"},
    ]
    # Reverse order
    elements_b = [
        {"role": "link", "name": "Home", "element_type": "a"},
        {"role": "button", "name": "Submit", "element_type": "button"},
    ]
    hash_a = compute_state_fingerprint("https://example.com/checkout", "Checkout Page", elements_a)
    hash_b = compute_state_fingerprint("https://example.com/checkout", "Checkout Page", elements_b)
    assert hash_a == hash_b


def test_action_hash_stability():
    h1 = compute_action_hash("click", "button", "Next Step")
    h2 = compute_action_hash("CLICK", "button", "next step")
    assert h1 == h2


def test_run_repository_and_artifacts(tmp_path: Path):
    repo = RunRepository(base_dir=tmp_path, run_id="run-test-001")
    cfg = load_config()
    repo.save_config_snapshot(cfg)

    # Save artifact
    target, digest = save_screenshot(repo.run_dir, b"fake_png_data", "j1", 1, "before")
    assert target.exists()
    assert len(digest) == 64

    # Log event
    repo.log_event("STEP_COMPLETED", {"step": 1, "status": "ok"})
    events_file = repo.run_dir / "events.jsonl"
    assert events_file.exists()

    # Save and load canonical result
    audit_run = AuditRun(
        run_id="run-test-001",
        target_url="https://example.com",
        created_at="2026-09-05T12:00:00Z",
        status=AuditStatus.COMPLETED,
    )
    repo.save_result(audit_run)
    loaded = repo.load_result()
    assert loaded.run_id == "run-test-001"
    assert loaded.status == AuditStatus.COMPLETED

    # Generate manifest
    manifest = generate_run_manifest(repo.run_dir)
    assert manifest["artifacts_count"] >= 3
