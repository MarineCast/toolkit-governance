"""Build configured full-AOI fisheries management areas."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from governance.shared.pipeline import build_collection

from .config import COLLECTION_ID, DEFAULT_CONFIG_PATH
from .normalize import NORMALIZATION_PROFILE, normalize


def build(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    allow_partial: bool = False,
    overwrite: bool = False,
) -> Path:
    return build_collection(
        COLLECTION_ID,
        normalize,
        normalization_profile=NORMALIZATION_PROFILE,
        config_path=config_path,
        allow_partial=allow_partial,
        overwrite=overwrite,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    print(build(args.config, allow_partial=args.allow_partial, overwrite=args.overwrite))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
