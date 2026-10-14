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
