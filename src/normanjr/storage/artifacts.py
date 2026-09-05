"""Artifact storage with atomic writes and path safety checks."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def verify_path_containment(base_dir: Path, target_path: Path) -> None:
    """Ensure target_path does not escape base_dir via directory traversal."""
    resolved_base = base_dir.resolve()
    resolved_target = target_path.resolve()
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError as e:
        raise PermissionError(
            f"Path traversal detected: {resolved_target} is outside {resolved_base}"
        ) from e


def atomic_write_bytes(target_path: Path, data: bytes) -> str:
    """Write bytes to target_path atomically using a temporary file. Returns SHA-256 hex digest."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = target_path.parent
    digest = hashlib.sha256(data).hexdigest()

    with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False) as tf:
        temp_name = tf.name
        tf.write(data)
        tf.flush()
        os.fsync(tf.fileno())

    os.replace(temp_name, target_path)
    return digest


def atomic_write_text(target_path: Path, text: str) -> str:
    """Write text to target_path atomically using a temporary file. Returns SHA-256 hex digest."""
    return atomic_write_bytes(target_path, text.encode("utf-8"))


def save_screenshot(
    run_dir: Path,
    image_bytes: bytes,
    journey_id: str,
    step_number: int,
    suffix: str = "before",
) -> tuple[Path, str]:
    """Save screenshot into run_dir/screenshots/ with deterministic filename."""
    screenshots_dir = run_dir / "screenshots"
    filename = f"{journey_id}-step-{step_number:03d}-{suffix}.png"
    target = screenshots_dir / filename
    verify_path_containment(run_dir, target)
    digest = atomic_write_bytes(target, image_bytes)
    return target, digest


def save_snapshot(
    run_dir: Path,
    snapshot_text: str,
    journey_id: str,
    step_number: int,
) -> tuple[Path, str]:
    """Save accessibility snapshot into run_dir/snapshots/ with deterministic filename."""
    snapshots_dir = run_dir / "snapshots"
    filename = f"{journey_id}-step-{step_number:03d}.md"
    target = snapshots_dir / filename
    verify_path_containment(run_dir, target)
    digest = atomic_write_text(target, snapshot_text)
    return target, digest


def save_metrics(
    run_dir: Path,
    metrics: dict[str, Any],
    journey_id: str,
    step_number: int,
    prefix: str = "",
) -> tuple[Path, str]:
    """Save metrics JSON into run_dir/metrics/ with deterministic filename."""
    metrics_dir = run_dir / "metrics"
    p = f"{prefix}-" if prefix else ""
    filename = f"{p}{journey_id}-step-{step_number:03d}.json"
    target = metrics_dir / filename
    verify_path_containment(run_dir, target)
    text = json.dumps(metrics, indent=2, sort_keys=True)
    digest = atomic_write_text(target, text)
    return target, digest
