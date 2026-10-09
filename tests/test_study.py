import json
from pathlib import Path

import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import Point, box

from governance.h3_matrix import _grid
from governance.releases import publish_generation, resolve_current, activate_generation
from governance.study import study_preflight, _positive_mask_support, run_study
from governance.workspace import initialize_workspace


@pytest.fixture
def inputs(tmp_path):
    cache = tmp_path/'cache'; initialize_workspace(cache)
    study = tmp_path/'study.json'
    study.write_text(json.dumps({'schema_version': 1, 'time': {'timezone': 'UTC'},
        'domain': {'bbox_wgs84': [-124,48,-122,50], 'selection_policy': {'reporting_support': 'positive_area_intersection_with_materialized_coastal_plus_inland_water_mask'}},
        'grid_registry': {'status': 'pending'}}))
    grid = tmp_path/'r6.parquet'
    pq.write_table(pa.table({'H3_INDEX': [h3.latlng_to_cell(49,-123,6)], 'H3_RESOLUTION': [6]}),grid)
    mask = tmp_path/'water.gpkg'
    gpd.GeoDataFrame({'geometry':[box(-124,48,-122,50)]},crs=4326).to_file(mask,layer='water')
    from governance.shared.artifacts import sha256_file
    manifest=tmp_path/'mask-manifest.json'
    manifest.write_text(json.dumps({'source_mapped_geometry': {'raw_sha256': sha256_file(mask)}, 'domain': {'qualification': 'fixture only'}}))
    return dict(study=study, grids=[grid], mask=mask, mask_layer='water', mask_manifest=manifest, cache_workspace=cache)


def test_preflight_preserves_pending_registry_and_all_planned_products(inputs):
    result = study_preflight(**inputs)
    assert result['central_registry_status']=='pending'
    assert result['grids'][0]['rows']==1
    assert len(result['inventory']['products'])==24
    assert sum(p['implementation_status']=='planned' for p in result['inventory']['products'].values())==9
    assert all(s['study_geographic_completeness']=='unknown' for s in result['inventory']['sources'].values())
    assert result['new_acquisition_bytes']==0


def test_mask_requires_positive_area_not_touch_or_point(inputs):
    grid = _grid(inputs['grids'][0])
    assert _positive_mask_support(grid, gpd.read_file(inputs['mask'],layer='water'))==1
    point = gpd.GeoDataFrame({'geometry':[Point(grid.geometry.iloc[0].exterior.coords[0])]},crs=4326)
    with pytest.raises(ValueError,match='lack positive-area'):
        _positive_mask_support(grid,point)


def test_preflight_does_not_promote_old_mask_selection_to_expanded_coverage(inputs, monkeypatch):
    from governance.shared.artifacts import sha256_file
    import governance.study as module
    # A broad query envelope cannot override a narrower mask-selected ID roster.
    broad = dict(runtime_status='available', requested_bbox_wgs84=[-180,32,-109,72])
    sources = {
        'old': broad | {'requested_grid_mask_sha256': 'a'*64},
        'same': broad | {'requested_grid_mask_sha256': sha256_file(inputs['mask'])},
        'bbox': broad,
        'narrow': dict(runtime_status='available',requested_bbox_wgs84=[-123.5,48.5,-123,49]),
        'missing': broad | {'runtime_status': 'unavailable','requested_grid_mask_sha256': 'a'*64},
    }
    monkeypatch.setattr(module,'preflight',lambda: {'sources': sources})
    result=study_preflight(**inputs)['inventory']['sources']
    assert result['old']['study_cache_support']=='source_selected_against_different_mask_requires_requalification'
    assert result['same']['study_cache_support']=='source_selection_mask_matches_requires_roster_review'
    assert result['bbox']['study_cache_support']=='query_envelope_covers_study_planning_envelope_only'
    assert result['narrow']['study_cache_support']=='query_envelope_does_not_cover_expanded_study'
    assert result['missing']['study_cache_support']=='unavailable'
    assert all(s['study_geographic_completeness']=='unknown' for s in result.values())


def test_budget_fails_before_output_or_cache_mutation(inputs, tmp_path):
    output=tmp_path/'new';before=sorted(str(p) for p in inputs['cache_workspace'].rglob('*'))
    with pytest.raises(ValueError,match='staging estimate'):
        run_study(**inputs,output=output,permanent_release_path=tmp_path/'releases/new',release_id='new',
                  software_revision='a'*40,schema=Path(__file__).parent/'fixtures/reference-geometry-v0.2.schema.json',
                  schema_reference='pinned',staging_cap_bytes=1)
    assert not output.exists()
    assert before==sorted(str(p) for p in inputs['cache_workspace'].rglob('*'))


def test_semantic_failure_blocks_publication_and_rollback(tmp_path):
    source=tmp_path/'source';source.mkdir();(source/'data').write_text('original')
    root=tmp_path/'releases'
    kwargs=dict(scientific_method_version='test',software_revision='a'*40)
    good=publish_generation(source,root,'good',**kwargs)
    pointer=(root/'current.json').read_bytes()
    (source/'study-contract.json').write_text('{"schema_version": 999}')
    with pytest.raises(ValueError,match='Unsupported study release'):
        publish_generation(source,root,'bad',**kwargs)
    assert (root/'current.json').read_bytes()==pointer
    assert resolve_current(root)==good
    with pytest.raises(ValueError,match='Unsupported study release'):
        activate_generation(root,'bad')
    assert (root/'current.json').read_bytes()==pointer
    assert not (root/'.publish.lock').exists()


def test_deferred_generation_does_not_change_pointer(tmp_path):
    source=tmp_path/'source';source.mkdir();(source/'data').write_text('original')
    root=tmp_path/'releases';kwargs=dict(scientific_method_version='test',software_revision='a'*40)
    good=publish_generation(source,root,'good',**kwargs)
    publish_generation(source,root,'candidate',activate=False,**kwargs)
    assert resolve_current(root)==good


def test_offline_study_bundle_relocates_and_validates_from_permanent_path(inputs,tmp_path,monkeypatch):
    import yaml
    cache=inputs['cache_workspace'];config_path=cache/'config/data/governance/governance.yaml'
    config=yaml.safe_load(config_path.read_text())
    config['collections']={'management_areas':config['collections']['management_areas']}
    config['sources']['wdfw_recreational_marine_areas']['local_path']='data/raw/test.geojson'
    config_path.write_text(yaml.safe_dump(config))
    (cache/'data/raw').mkdir(parents=True)
    gpd.GeoDataFrame({'OBJECTID':[1],'AreaName':['fixture'],'geometry':[box(-123.02,48.98,-122.98,49.02)]},crs=4326).to_file(cache/'data/raw/test.geojson',driver='GeoJSON')
    raw=(cache/'data/raw/test.geojson').read_bytes()
    root=tmp_path/'releases';identity='regional';permanent=root/identity
    output=tmp_path/'prepared'
    schema=Path(__file__).parent/'fixtures/reference-geometry-v0.2.schema.json'
    import governance.study as study_module
    original_export = study_module.export_h3_matrix
    def interrupted(*args, **kwargs):
        raise RuntimeError('interrupted overlay')
    monkeypatch.setattr(study_module, 'export_h3_matrix', interrupted)
    kwargs = dict(output=output,permanent_release_path=permanent,release_id=identity,
                  software_revision='a'*40,schema=schema,schema_reference='pinned-fixture')
    with pytest.raises(RuntimeError,match='interrupted overlay'):
        run_study(**inputs,**kwargs)
    native_files = {str(p): (p.stat().st_mtime_ns,p.read_bytes()) for p in (output/'workspace/data/processed').rglob('*.parquet')}
    monkeypatch.setattr(study_module, 'export_h3_matrix', original_export)
    run_study(**inputs,**kwargs,resume_native=True)
    assert native_files == {str(p): (p.stat().st_mtime_ns,p.read_bytes()) for p in (output/'workspace/data/processed').rglob('*.parquet')}
    assert (cache/'data/raw/test.geojson').read_bytes()==raw
    assert (output/'workspace/data/raw/test.geojson').read_bytes()==raw
    final=publish_generation(output,root,identity,scientific_method_version='native-inventory-overlay-1.3.0',software_revision='a'*40)
    assert resolve_current(root)==final
    result=json.loads((final/'validation.json').read_text())
    assert result['native_collections']==1
    assert len(result['independent_samples'])==1
    pointer=(root/'current.json').read_bytes()
    envelope=final/'generation.json';original=envelope.read_bytes()
    for field,value in [('scientific_method_version','incorrect-method'),('software_revision','b'*40)]:
        altered=json.loads(original);altered[field]=value
        envelope.write_text(json.dumps(altered))
        try:
            with pytest.raises(ValueError,match='generation method/software mismatch'):
                activate_generation(root,identity)
            assert (root/'current.json').read_bytes()==pointer
        finally:
            envelope.write_bytes(original)
    # A schema-valid shared producer revision must still match its local companion.
    contract=json.loads((output/'study-contract.json').read_text())
    shared=Path(contract['tables'][0]['shared_manifest'].replace(str(permanent),str(output)))
    original=shared.read_bytes();altered=json.loads(original)
    altered['producer']['git_sha']='b'*40;shared.write_text(json.dumps(altered))
    try:
        with pytest.raises(ValueError,match='Shared/local software identity mismatch'):
            study_module.validate_study_release(output,independent=False)
    finally:
        shared.write_bytes(original)
