"""Resolve data/configuration relative to an explicit workspace, never site-packages."""
from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    """Return GOVERNANCE_WORKSPACE or the current working directory."""
    return Path(os.environ.get('GOVERNANCE_WORKSPACE', Path.cwd())).expanduser().resolve()


def resolve_config_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (project_root() / candidate).resolve()
