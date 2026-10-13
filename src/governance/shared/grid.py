"""Supported internal grid readers and bounded generic H3 candidate generation."""
from pathlib import Path
import geopandas as gpd
import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import Polygon

def read_grid(path: Path) -> gpd.GeoDataFrame:
    import h3

    table = pq.read_table(path, columns=["H3_INDEX", "H3_RESOLUTION"])
    if not pa.types.is_integer(table.schema.field("H3_RESOLUTION").type):
        raise ValueError("H3_RESOLUTION must have an integer type.")
    frame = table.to_pandas()
    if frame.empty or frame.isna().any().any() or frame.duplicated().any():
        raise ValueError(
            "H3 grid must have non-null unique cell/resolution keys and be nonempty."
        )
    polygons = []
    for cell, resolution in frame.itertuples(index=False, name=None):
        if not isinstance(cell, str) or not h3.is_valid_cell(cell):
            raise ValueError(f"Invalid H3 cell: {cell!r}")
        if h3.get_resolution(cell) != resolution:
            raise ValueError(f"H3 resolution mismatch: {cell}")
        vertices = [(lon, lat) for lat, lon in h3.cell_to_boundary(cell)]
        if max(x for x, _ in vertices) - min(x for x, _ in vertices) > 180:
            raise ValueError(
                "Antimeridian-crossing H3 cells are unsupported by this overlay."
            )
        polygons.append(Polygon(vertices))
    output = gpd.GeoDataFrame(frame, geometry=polygons, crs=4326)
    if output.total_bounds[2] - output.total_bounds[0] > 180:
        raise ValueError("The H3 overlay requires a bounded non-antimeridian grid.")
    return output



def validate_resolution(resolution):
    if type(resolution) is not int or not 0 <= resolution <= 15:
        raise ValueError('h3_res must be an integer in [0, 15]')


def cell_geometry(cell):
    """Split dateline-crossing cells into native longitude pieces, preserving holes."""
    import h3
    from .spatial import _antimeridian_intersection
    from shapely.geometry import box
    return _antimeridian_intersection(Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(cell)]), box(-180, -90, 180, 90))


def candidate_grid(bbox, resolution, *, max_cells=100_000):
    import h3
    from shapely.ops import unary_union
    from .spatial import bbox_parts
    validate_resolution(resolution)
    if type(max_cells) is not int or max_cells <= 0:
        raise ValueError('max_cells must be a positive integer')
    parts = bbox_parts(bbox)
    import math
    west, south, east, north = bbox
    if south <= -89 or north >= 89:
        raise ValueError('Generic H3 polar bounding boxes require a separately qualified support contract')
    width = east-west if west < east else 360-west+east
    area = 6371008.8**2 * math.radians(width) * (math.sin(math.radians(north))-math.sin(math.radians(south)))
    perimeter = 2*6371008.8*(math.radians(north-south)+math.radians(width))
    if area / (h3.average_hexagon_area(resolution, unit='m^2') * 0.5) + perimeter / h3.average_hexagon_edge_length(resolution, unit='m') + 20 > max_cells:
        raise ValueError('Candidate H3 grid exceeds cell budget; use a smaller bounding_box or resolution')
    if not hasattr(h3, 'h3shape_to_cells_experimental'):
        raise ImportError('Generic H3 queries require h3>=4.2 with overlap containment')
    cells = set()
    # Avoid ambiguous >180-degree polygon edges even at coarse permitted resolutions.
    from shapely.geometry import box
    split_parts = []
    for part in parts:
        west, south, east, north = part.bounds
        sections = max(1, math.ceil((east-west)/90))
        split_parts.extend(box(west+i*(east-west)/sections,south,west+(i+1)*(east-west)/sections,north) for i in range(sections))
    for part in split_parts:
        shape = h3.LatLngPoly([(y, x) for x, y in part.exterior.coords])
        cells.update(h3.h3shape_to_cells_experimental(shape, resolution, contain='overlap'))
        if len(cells) > max_cells:
            raise ValueError('Candidate H3 grid exceeds cell budget')
    requested = unary_union(parts)
    rows = [(cell, cell_geometry(cell)) for cell in sorted(cells)]
    rows = [(cell, geometry) for cell, geometry in rows if geometry.intersects(requested)]
    return gpd.GeoDataFrame({'H3_INDEX': [cell for cell, _ in rows], 'H3_RESOLUTION': [resolution]*len(rows)}, geometry=[geom for _, geom in rows], crs=4326)
