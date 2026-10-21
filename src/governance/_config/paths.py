"""Resolve data/configuration relative to an explicit workspace, never site-packages."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path


_WORKSPACE = ContextVar("governance_workspace", default=None)


@contextmanager
def workspace_scope(workspace):
    """Scope legacy helpers without changing process environment."""
    token = _WORKSPACE.set(Path(workspace).expanduser().resolve())
    try:
        yield
    finally:
        _WORKSPACE.reset(token)


def project_root() -> Path:
    """Return GOVERNANCE_WORKSPACE or the current working directory."""
    return Path(_WORKSPACE.get() or os.environ.get('GOVERNANCE_WORKSPACE', Path.cwd())).expanduser().resolve()


def resolve_config_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (project_root() / candidate).resolve()
