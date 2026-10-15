"""Flat outputs retain science while removing release and duplicate-file surfaces."""
import json
from pathlib import Path

import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from shapely.geometry import box

from governance.cli import main
from governance.products import build_products, cleanup_workspace_data, validate_products, validate_metric_table
from governance.shared.config import load_governance_config
from governance.workspace import initialize_workspace


@pytest.fixture
def flat_inputs(tmp_path, monkeypatch, snapshot_fixture):
    workspace = tmp_path / 'workspace'
    initialize_workspace(workspace)
    monkeypatch.setenv('GOVERNANCE_WORKSPACE', str(workspace))
    config_path = workspace / 'config/data/governance/governance.yaml'
    values = yaml.safe_load(config_path.read_text())
    values['collections'] = {'management_areas': values['collections']['management_areas']}
    values['collections']['management_areas']['source_ids'] = ['wdfw_recreational_marine_areas']
    values['sources'] = {'wdfw_recreational_marine_areas': values['sources']['wdfw_recreational_marine_areas']}
    config_path.write_text(yaml.safe_dump(values))
    source = load_governance_config().sources['wdfw_recreational_marine_areas']
    raw = gpd.GeoDataFrame({'OBJECTID': [1], 'AreaName': ['7'], 'AreaTitle': ['Fixture'], 'WAC': ['fixture'], 'Unknown': [None]}, geometry=[box(-124, 30, -122, 50)], crs=4326)
    source.snapshot_path.parent.mkdir(parents=True)
    source.snapshot_path.write_text(json.dumps(snapshot_fixture(source, raw)))
    grid = tmp_path / 'grid.parquet'
    cells = [h3.latlng_to_cell(48.5, -123.5, r) for r in (6, 8)]
    pq.write_table(pa.table({'H3_INDEX': cells, 'H3_RESOLUTION': [6, 8]}), grid)
    return config_path, grid, raw


def test_build_has_only_resolution_parquets_catalog_and_originals(flat_inputs, tmp_path):
    config, grid, raw = flat_inputs
    output = build_products([grid], tmp_path / 'Governance', config_path=config, allow_partial=True)
    assert not (config.parents[3] / 'data').exists()
    assert validate_products(output) == {'status': 'passed', 'tables': 2, 'original_datasets': 1}
    assert {p.name for p in output.iterdir()} == {'governance-r6-static.parquet', 'governance-r8-static.parquet', 'catalog.json', 'OriginalData'}
    original = gpd.read_parquet(output / 'OriginalData/wdfw_recreational_marine_areas/geometry.parquet')
    assert original.geometry.to_wkb().tolist() == raw.geometry.to_wkb().tolist()
    assert original.total_bounds[1] == 30  # Outside native AOI, retained in OriginalData.
    assert original.Unknown.isna().all()
    for resolution in (6, 8):
        table = pq.read_table(output / f'governance-r{resolution}-static.parquet')
        assert table['management_areas__recorded_feature_count'].to_pylist() == [1]
        assert 'date' not in table.column_names
        metadata = json.loads(table.schema.metadata[b'governance'])
        assert metadata['model_eligible'] is False
        assert metadata['fields']['management_areas__recorded_polygon_union_area_fraction']['units'] == '1'
        assert 'data_release_id' not in metadata and 'native_manifests' not in metadata
    # A flat dataset itself is sufficient for a later offline rebuild. No ZIP/JSON copy.
    rebuilt = build_products([grid], tmp_path / 'rebuilt', config_path=config, original_data=output, allow_partial=True)
    for resolution in (6, 8):
        assert pq.read_table(output / f'governance-r{resolution}-static.parquet').equals(pq.read_table(rebuilt / f'governance-r{resolution}-static.parquet'), check_metadata=False)
    build_products([grid], output, config_path=config, original_data=output, allow_partial=True, overwrite=True)
    assert validate_products(output)['status'] == 'passed'


def test_refuses_extra_files_and_changed_metric_bytes(flat_inputs, tmp_path):
    config, grid, _ = flat_inputs
    output = build_products([grid], tmp_path / 'Governance', config_path=config, allow_partial=True)
    (output / 'duplicate.json').write_text('{}')
    with pytest.raises(ValueError, match='Unexpected'):
        validate_products(output)
    (output / 'duplicate.json').unlink()
    with (output / 'governance-r6-static.parquet').open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='checksum'):
        validate_products(output)


def test_unsupported_release_commands_are_not_public():
    with pytest.raises(SystemExit):
        main(['publish-generation'])


def test_failed_replacement_restores_previous_data(flat_inputs, tmp_path, monkeypatch):
    config, grid, _ = flat_inputs
    output = build_products([grid], tmp_path / 'Governance', config_path=config, allow_partial=True,
                            keep_workspace_data=True)
    source = load_governance_config(config).sources['wdfw_recreational_marine_areas'].snapshot_path
    previous_source = source.read_bytes()
    previous = (output / 'catalog.json').read_bytes()
    rename = Path.rename
    def interrupted(path, target):
        if path.name.startswith('.Governance.build-') and not path.name.endswith('.previous') and Path(target) == output:
            raise OSError('injected installation failure')
        return rename(path, target)
    monkeypatch.setattr(Path, 'rename', interrupted)
    with pytest.raises(OSError, match='injected'):
        build_products([grid], output, config_path=config, original_data=output, allow_partial=True, overwrite=True)
    assert (output / 'catalog.json').read_bytes() == previous
    assert validate_products(output)['status'] == 'passed'
    assert not list(tmp_path.glob('.Governance*'))
    assert source.read_bytes() == previous_source


def test_success_removes_old_processed_files_and_finder_metadata(flat_inputs, tmp_path):
    config, grid, _ = flat_inputs
    settings = load_governance_config(config)
    root = settings.document.workspace / 'data'
    settings.processed_root.mkdir(parents=True)
    (settings.processed_root / 'old.parquet').write_bytes(b'old intermediate')
    (root / '.DS_Store').write_bytes(b'Finder metadata')
    build_products([grid], tmp_path / 'Governance', config_path=config, allow_partial=True)
    assert not root.exists()
    assert config.is_file()
    assert grid.is_file()


def test_failed_build_keeps_source_cache(flat_inputs, tmp_path):
    config, grid, _ = flat_inputs
    source = load_governance_config(config).sources['wdfw_recreational_marine_areas'].snapshot_path
    previous = source.read_bytes()
    grid.write_bytes(b'invalid grid')
    with pytest.raises(pa.ArrowInvalid):
        build_products([grid], tmp_path / 'Governance', config_path=config, allow_partial=True)
    assert source.read_bytes() == previous
    assert not (tmp_path / 'Governance').exists()


@pytest.mark.parametrize('reason', ['unrelated', 'unretained', 'receipt', 'symlink', 'protected'])
def test_cleanup_preserves_data_when_it_cannot_prove_it_is_disposable(flat_inputs, tmp_path, reason):
    config, grid, _ = flat_inputs
    settings = load_governance_config(config)
    source = settings.sources['wdfw_recreational_marine_areas'].snapshot_path
    root = settings.document.workspace / 'data'
    output = build_products([grid], tmp_path / 'Governance', config_path=config,
                            allow_partial=True, keep_workspace_data=True)
    protected = []
    if reason == 'unrelated':
        (root / 'other-toolkit.txt').write_text('keep')
    elif reason == 'unretained':
        source.write_bytes(source.read_bytes() + b' ')
    elif reason == 'receipt':
        source.with_suffix(source.suffix + '.metadata.json').write_text('{"new_receipt": true}')
    elif reason == 'symlink':
        (root / 'external').symlink_to(grid)
    else:
        protected = [source]
    previous = source.read_bytes()
    assert cleanup_workspace_data(output, config_path=config, protected_paths=protected) is False
    assert source.read_bytes() == previous
    assert validate_products(output)['status'] == 'passed'


def test_cleanup_preserves_symlinked_data_root(flat_inputs, tmp_path):
    config, grid, _ = flat_inputs
    root = load_governance_config(config).document.workspace / 'data'
    output = build_products([grid], tmp_path / 'Governance', config_path=config,
                            allow_partial=True, keep_workspace_data=True)
    external = tmp_path / 'external-data'
    root.rename(external)
    root.symlink_to(external, target_is_directory=True)
    assert cleanup_workspace_data(output, config_path=config) is False
    assert root.is_symlink()
    assert external.is_dir()


def test_output_inside_workspace_data_is_preserved(flat_inputs, tmp_path):
    config, grid, _ = flat_inputs
    root = load_governance_config(config).document.workspace / 'data'
    output = build_products([grid], root / 'Governance', config_path=config, allow_partial=True)
    assert validate_products(output)['status'] == 'passed'
    assert root.exists()


def test_invalid_installed_output_prevents_cleanup(flat_inputs, tmp_path):
    config, grid, _ = flat_inputs
    root = load_governance_config(config).document.workspace / 'data'
    output = build_products([grid], tmp_path / 'Governance', config_path=config,
                            allow_partial=True, keep_workspace_data=True)
    (output / 'governance-r6-static.parquet').write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='checksum'):
        cleanup_workspace_data(output, config_path=config)
    assert root.exists()


def test_cli_can_keep_then_clean_workspace_data(flat_inputs, tmp_path):
    config, grid, _ = flat_inputs
    root = load_governance_config(config).document.workspace / 'data'
    output = tmp_path / 'Governance'
    assert main(['build', '--config', str(config), '--grid', str(grid),
                 '--output-directory', str(output), '--allow-partial', '--keep-workspace-data']) == 0
    assert root.exists()
    assert main(['clean-workspace', str(output), '--config', str(config)]) == 0
    assert not root.exists()


def test_dynamic_grain_requires_typed_dates_and_unique_cell_date():
    from datetime import date
    cell = h3.latlng_to_cell(48.5, -123.5, 6)
    metadata = {'schema_version': 1, 'model_eligible': False, 'spatial': {'h3_resolution': 6},
                'temporal': {'type': 'dynamic'}, 'fields': {'h3_index': {}, 'date': {}}}
    table = pa.table({'h3_index': [cell, cell], 'date': pa.array([date(2020, 1, 1), date(2021, 1, 1)], type=pa.date32())})
    validate_metric_table(table, metadata)
    with pytest.raises(ValueError, match='Duplicate'):
        validate_metric_table(pa.concat_tables([table, table.slice(0, 1)]), metadata)
    with pytest.raises(ValueError, match='typed date'):
        validate_metric_table(pa.table({'h3_index': [cell], 'date': ['2020-01-01']}), metadata)
    with pytest.raises(ValueError, match='Static'):
        validate_metric_table(table, dict(metadata, temporal={'type': 'static'}))
