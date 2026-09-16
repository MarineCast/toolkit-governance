"""Initialize an explicit data workspace from shipped configuration resources."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def initialize_workspace(path: str | Path) -> list[Path]:
    """Copy missing defaults only; never overwrite configuration or acquire data."""
    root = Path(path).expanduser().resolve()
    created = []

    def copy_tree(source, destination):
        for child in sorted(source.iterdir(), key=lambda item: item.name):
            target = destination / child.name
            if child.is_dir():
                copy_tree(child, target)
            elif not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(child.read_bytes())
                created.append(target)

    copy_tree(files('governance').joinpath('resources/config'), root / 'config')
    return created
