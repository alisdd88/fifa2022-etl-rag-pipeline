"""Shared filesystem helpers."""

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Create a directory when needed and return the same path."""
    path.mkdir(parents=True, exist_ok=True)
    return path
