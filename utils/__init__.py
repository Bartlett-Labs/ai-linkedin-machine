"""Utility modules - kill switch, dedup, retry logic."""

import os
from pathlib import Path

# Absolute path to the project root directory.
# All relative paths in the codebase should be resolved against this.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def project_path(*parts: str) -> str:
    """Resolve a path relative to the project root.

    Usage:
        project_path("config", "personas.json")
        project_path("queue/posts/")
    """
    return str(PROJECT_ROOT / os.path.join(*parts))
