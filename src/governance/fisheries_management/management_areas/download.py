"""Acquire configured fisheries management-area snapshots."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from governance.shared.pipeline import download_collection

from .config import COLLECTION_ID, DEFAULT_CONFIG_PATH


def download(
    config_path: str | Path = DEFAULT_CONFIG_PATH, *, overwrite: bool = False
) -> list[Path]:
    return download_collection(COLLECTION_ID, config_path, overwrite=overwrite)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    for path in download(args.config, overwrite=args.overwrite):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
