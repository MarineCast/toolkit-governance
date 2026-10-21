"""Synthetic source receipts; these never establish live geographic acceptance."""
import json
import pytest
import pandas as pd

@pytest.fixture
def snapshot_fixture():
    def make(source, frame, bbox=(-180., 32., -109., 72.), **extra):
        features = json.loads(frame.to_json())['features']
        ids = [feature['properties']['OBJECTID'] for feature in features]
        return dict(snapshot_schema_version=2, source_id=source.source_id, source_url=source.url,
                    request_contract={'provider': source.provider, 'source_as_of': source.source_as_of},
                    retrieved_at_utc='2026-10-01T00:00:00Z', server_filtered=True,
                    requested_bbox_wgs84=list(bbox), selection_where=source.selection_where,
                    requested_grid_mask_sha256=source.requested_grid_mask_sha256,
                    object_id_field='OBJECTID', selected_object_ids=ids,
                    expected_object_id_count=len(ids), unreceived_object_ids=[], geometry_roster_complete=True,
                    metadata_response={'fields': [{'name': field, 'type': 'esriFieldTypeInteger' if pd.api.types.is_integer_dtype(frame[field].dtype) else 'esriFieldTypeString'} for field in frame.columns if field != 'geometry']},
                    pages=[{'retrieved_at_utc':'2026-10-01T00:00:00Z', 'response':{'type':'FeatureCollection','features':features}}], **extra)
    return make


@pytest.fixture
def projected_matrix():
    """Exercise production projection, round-tripping only the Arrow test result."""
    def project(matrix_path):
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
        from governance.delivery import project_delivery
        table = pq.read_table(matrix_path)
        metadata = json.loads(table.schema.metadata[b'governance_h3_matrix'])
        results = []
        for resolution in sorted(set(table['H3_RESOLUTION'].to_pylist())):
            selected = table.filter(pc.equal(table['H3_RESOLUTION'], resolution))
            projected, context = project_delivery(selected, metadata, resolution, 'a' * 40)
            buffer = pa.BufferOutputStream()
            pq.write_table(projected, buffer)
            results.append((pq.read_table(pa.BufferReader(buffer.getvalue())), context))
        return results
    return project
