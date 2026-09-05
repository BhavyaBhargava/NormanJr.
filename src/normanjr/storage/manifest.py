"""Manifest creation capturing runtime versions and artifact digests."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from normanjr.storage.artifacts import atomic_write_text
from normanjr.version import __version__


def hash_file(path: Path) -> str:
    """Calculate SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_run_manifest(run_dir: Path, rubric_version: str = "1.0.0") -> dict[str, Any]:
    """Inspect run directory and produce manifest dictionary."""
    artifacts: list[dict[str, Any]] = []

    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            rel_path = str(path.relative_to(run_dir))
            artifacts.append({
                "path": rel_path,
                "size_bytes": path.stat().st_size,
                "sha256": hash_file(path),
            })

    manifest = {
        "schema_version": "1.0",
        "normanjr_version": __version__,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "rubric_version": rubric_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifacts_count": len(artifacts),
        "artifacts": artifacts,
    }

    target = run_dir / "manifest.json"
    atomic_write_text(target, json.dumps(manifest, indent=2, sort_keys=True))
    return manifest
