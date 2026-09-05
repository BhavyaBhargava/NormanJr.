"""Storage package for NormanJr."""

from normanjr.storage.artifacts import (
    atomic_write_bytes,
    atomic_write_text,
    save_metrics,
    save_screenshot,
    save_snapshot,
    verify_path_containment,
)
from normanjr.storage.manifest import generate_run_manifest
from normanjr.storage.run_repository import RunRepository

__all__ = [
    "RunRepository",
    "atomic_write_bytes",
    "atomic_write_text",
    "generate_run_manifest",
    "save_metrics",
    "save_screenshot",
    "save_snapshot",
    "verify_path_containment",
]
