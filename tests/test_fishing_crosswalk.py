import json
from pathlib import Path
import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import box
from governance.fisheries_management.management_areas.normalize import normalize
from governance.shared.config import load_governance_config
from governance.workspace import initialize_workspace
from governance.fishing_crosswalk import export_fishing_crosswalk, validate_fishing_crosswalk
from governance.shared.artifacts import sha256_file


def test_native_requires_original_ids_and_retains_provider_attributes():
    source=load_governance_config().sources['wdfw_recreational_marine_areas']
    raw=gpd.GeoDataFrame({'OBJECTID':[1],'AreaName':['7'],'provider_extra':['retained'],'geometry':[box(-123,48,-122,49)]},crs=4326)
    native=normalize(raw,source)
    assert native.WDFW_provider_extra.tolist()==['retained']
    assert native.AREA_SYSTEM_ID.tolist()==['wdfw.recreational_marine_catch_reporting']
    assert native.FISHERY_SECTOR.tolist()==['recreational']
    for field in ['OBJECTID','AreaName']:
        with pytest.raises(ValueError,match='identifiers required'):normalize(raw.drop(columns=field),source)


def test_crosswalk_preserves_nonadditive_system_relations_and_full_area_denominator(tmp_path,monkeypatch):
    initialize_workspace(tmp_path);monkeypatch.setenv('GOVERNANCE_WORKSPACE',str(tmp_path))
    import yaml
    p=tmp_path/'config/data/governance/governance.yaml';cfg=yaml.safe_load(p.read_text());cfg['collections']={'management_areas':cfg['collections']['management_areas']};p.write_text(yaml.safe_dump(cfg))
    source=load_governance_config().sources['wdfw_recreational_marine_areas'];source.snapshot_path.parent.mkdir(parents=True)
    raw=gpd.GeoDataFrame({'OBJECTID':[1,2],'AreaName':['7','8'],'geometry':[box(-123.2,48.3,-122.8,48.7)]*2},crs=4326)
    source.snapshot_path.write_text(json.dumps({'snapshot_schema_version':1,'pages':[{'response':json.loads(raw.to_json())}]}))
    from governance.fisheries_management.management_areas.build import build
    path=build(allow_partial=True);native=gpd.read_parquet(path)
    # Same provider area code in a distinct commercial system remains a separate relation.
    other=native.iloc[[0]].copy();other['SOURCE_DATASET_ID']='commercial_fixture';other['SOURCE_FEATURE_ID']='commercial:1';other['GOVERNANCE_FEATURE_ID']='commercial:7';other['GEOMETRY_PART_ID']='commercial:part';other['AREA_SYSTEM_ID']='fixture.commercial';other['FISHERY_SECTOR']='commercial'
    native=gpd.GeoDataFrame(__import__('pandas').concat([native,other],ignore_index=True),crs=4326);native.to_parquet(path,index=False)
    manifest=path.parent/'manifest.json';meta=json.loads(manifest.read_text());meta['artifact']['sha256']=sha256_file(path);manifest.write_text(json.dumps(meta))
    cells=sorted(h3.grid_disk(h3.latlng_to_cell(48.5,-123,6),1));grid=tmp_path/'grid.parquet';pq.write_table(pa.table({'H3_INDEX':cells,'H3_RESOLUTION':[6]*len(cells)}),grid)
    item=export_fishing_crosswalk(path,manifest,[grid],tmp_path/'crosswalk',release_id='test',software_revision='a'*40)[0]
    result=validate_fishing_crosswalk(item['artifact'],item['manifest']);assert result['status']=='passed' and result['native_source_records']==3
    table=pq.read_table(item['artifact']).to_pandas()
    assert set(table.fishery_sector)=={'commercial','recreational'}
    assert table.effective_start.isna().all() and table.geometry_version.isna().all()
    totals=table.groupby(['system_id','provider_area_id']).fraction_of_native_area.sum()
    assert (totals<1).all() # Grid subset cannot be renormalized to the full area.
    assert table.groupby('h3_index').fraction_of_full_cell.sum().max()>1 # Overlapping systems stay separate.
    assert not table.model_eligible.any()
    assert not any('catch' in name or 'quantity' in name for name in table.columns)
    assert all(len(x)>0 for x in table.area_geometry_part_ids)
    with pytest.raises(FileExistsError):export_fishing_crosswalk(path,manifest,[grid],tmp_path/'crosswalk',release_id='test',software_revision='a'*40)

    # Rehashed incomplete/corrupted relations must still fail semantic acceptance.
    artifact=Path(item['artifact']);companion=Path(item['manifest']);original=artifact.read_bytes();original_meta=companion.read_text()
    for label in ['missing_row','part_identity','snapshot']:
        broken=table.copy()
        if label=='missing_row':broken=broken.iloc[1:]
        elif label=='part_identity':broken.at[0,'area_geometry_part_ids']=['wrong-part']
        else:broken.at[0,'geometry_snapshot_sha256']='0'*64
        pq.write_table(pa.Table.from_pandas(broken,preserve_index=False),artifact)
        metadata=json.loads(original_meta);metadata['artifact'].update(sha256=sha256_file(artifact),rows=len(broken));companion.write_text(json.dumps(metadata))
        with pytest.raises(ValueError,match='completeness|part relation|snapshot'):validate_fishing_crosswalk(artifact,companion)
        artifact.write_bytes(original);companion.write_text(original_meta)
