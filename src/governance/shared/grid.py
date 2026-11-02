"""Validate and read explicit consumer-supplied H3 grids."""
from pathlib import Path
import geopandas as gpd
import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import Polygon

def read_grid(path: Path) -> gpd.GeoDataFrame:
    import h3

    schema = pq.read_schema(path)
    if 'h3_index' in schema.names:
        cells = pq.read_table(path, columns=['h3_index'])['h3_index']
        table = pa.table({'H3_INDEX': cells, 'H3_RESOLUTION': [h3.get_resolution(c) for c in cells.to_pylist()]})
    else:
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
