"""Read the toolkit's named processing extent without an application config loader."""
from __future__ import annotations

import math
from pathlib import Path
from collections.abc import Mapping
from .document import ConfigDocument


def bbox_for_area(area_name_value: str, *, common_config_path: str | Path) -> dict[str, float]:
    raw = ConfigDocument.load(common_config_path).data
    areas = raw.get('areas')
    if not isinstance(areas, Mapping):
        raise ValueError('Common configuration must define areas.')
    area = areas.get(area_name_value)
    if not isinstance(area, Mapping):
        raise KeyError(f'Unknown common area: {area_name_value!r}')
    bbox = area.get('bbox_wgs84')
    required = ('min_lon', 'min_lat', 'max_lon', 'max_lat')
    if not isinstance(bbox, Mapping) or not set(required) <= bbox.keys():
        raise ValueError('Common area must define all four bbox_wgs84 bounds.')
    out = {key: float(bbox[key]) for key in required}
    if not all(math.isfinite(v) for v in out.values()):
        raise ValueError('Bounds must be finite.')
    if not (-180 <= out['min_lon'] < out['max_lon'] <= 180
            and -90 <= out['min_lat'] < out['max_lat'] <= 90):
        raise ValueError(f'Invalid bbox_wgs84: {out}')
    return out
