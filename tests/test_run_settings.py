from pathlib import Path
import os
import pytest
from governance.run_settings import resolve_settings, KEYS
from governance._config.paths import project_root, workspace_scope

@pytest.fixture(autouse=True)
def clear_settings(monkeypatch):
    for key in KEYS | {'GOVERNANCE_WORKSPACE'}:
        monkeypatch.delenv(key, raising=False)

def test_precedence_and_path_origins(tmp_path, monkeypatch):
    settings_dir = tmp_path / 'settings'
    settings_dir.mkdir()
    (settings_dir / 'run.env').write_text("GOVERNANCE_OUTPUT_DIRECTORY=file\nGOVERNANCE_GRIDS='[\"grid.parquet\"]'\n")
    before = dict(os.environ)
    result = resolve_settings(workspace=tmp_path, env_file='settings/run.env', require_output=True, require_grids=True)
    assert result.output_directory == settings_dir / 'file'
    assert result.grid_paths == (settings_dir / 'grid.parquet',)
    assert dict(os.environ) == before
    monkeypatch.setenv('GOVERNANCE_OUTPUT_DIRECTORY', 'process')
    assert resolve_settings(workspace=tmp_path, env_file='settings/run.env').output_directory == Path.cwd() / 'process'
    assert resolve_settings(workspace=tmp_path, env_file='settings/run.env', output_directory='argument').output_directory == Path.cwd() / 'argument'

def test_unknown_secrets_ignored_and_workspace_not_redirected(tmp_path):
    (tmp_path / '.env').write_text('TOKEN="unterminated\nGOVERNANCE_WORKSPACE=/other\n')
    result = resolve_settings(workspace=tmp_path)
    assert result.workspace == tmp_path
    assert result.config_path == tmp_path / 'config/data/governance/governance.yaml'

@pytest.mark.parametrize('content', ['GOVERNANCE_GRIDS=nope', 'GOVERNANCE_OUTPUT_DIRECTORY=',
    'GOVERNANCE_OUTPUT_DIRECTORY=a\nGOVERNANCE_OUTPUT_DIRECTORY=b', 'GOVERNANCE_GRIDS=\'[null]\'',
    'GOVERNANCE_CONFIG=$HOME/file', 'GOVERNANCE_OUTPUT_DIRECTORY="sensitive invalid'])
def test_invalid_values_are_redacted(tmp_path, content):
    (tmp_path / '.env').write_text(content)
    with pytest.raises(ValueError) as error:
        resolve_settings(workspace=tmp_path)
    assert 'sensitive invalid' not in str(error.value)

def test_missing_explicit_file_and_required_inputs(tmp_path):
    with pytest.raises(ValueError, match='does not exist'):
        resolve_settings(workspace=tmp_path, env_file='missing')
    with pytest.raises(ValueError, match='grid_paths'):
        resolve_settings(workspace=tmp_path, require_grids=True)
    with pytest.raises(ValueError, match='output_directory'):
        resolve_settings(workspace=tmp_path, require_output=True)

def test_nested_workspace_scope_restores_without_environment_changes(tmp_path):
    original, environ = project_root(), dict(os.environ)
    with workspace_scope(tmp_path):
        assert project_root() == tmp_path
        with workspace_scope(tmp_path / 'nested'):
            assert project_root() == tmp_path / 'nested'
        assert project_root() == tmp_path
    assert project_root() == original
    assert dict(os.environ) == environ

def test_cli_passes_resolved_settings(tmp_path, monkeypatch):
    from governance import cli
    (tmp_path / '.env').write_text('GOVERNANCE_OUTPUT_DIRECTORY=out\nGOVERNANCE_GRIDS=\'["grid.parquet"]\'\n')
    captured = []
    monkeypatch.setattr(cli, '_dispatch', lambda args: captured.append(args) or 0)
    before = dict(os.environ)
    assert cli.main(['--workspace', str(tmp_path), 'build']) == 0
    assert captured[0].output_directory == tmp_path / 'out'
    assert captured[0].grid == (tmp_path / 'grid.parquet',)
    assert dict(os.environ) == before

def test_product_apis_share_resolver(tmp_path, monkeypatch):
    from governance import products
    (tmp_path / '.env').write_text('GOVERNANCE_OUTPUT_DIRECTORY=out\nGOVERNANCE_GRIDS=\'["grid.parquet"]\'\n')
    calls = []
    monkeypatch.setattr(products, '_build_products', lambda *args, **kwargs: calls.append((args, kwargs, project_root())) or 'done')
    assert products.build_products(workspace=tmp_path) == 'done'
    assert calls[0][0] == ((tmp_path / 'grid.parquet',), tmp_path / 'out')
    assert calls[0][2] == tmp_path
