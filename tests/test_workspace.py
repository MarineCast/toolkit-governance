from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
import yaml

from governance import initialize_workspace, load_governance_config
from governance.cli import main
from governance._config.document import ConfigDocument
from governance.shared.catalog import validate_catalog


def test_workspace_init_is_complete_and_preserves_edits(tmp_path, monkeypatch):
    created = initialize_workspace(tmp_path)
    assert len(created) == 10
    common = tmp_path / 'config/common.yaml'
    common.write_text(common.read_text() + '\n# user edit\n')
    assert initialize_workspace(tmp_path) == []
    assert common.read_text().endswith('# user edit\n')
    monkeypatch.setenv('GOVERNANCE_WORKSPACE', str(tmp_path))
    monkeypatch.chdir(tmp_path.parent)
    config = load_governance_config()
    assert config.path == tmp_path / 'config/data/governance/governance.yaml'
    assert config.processed_root.is_relative_to(tmp_path)
    assert config.catalog_path.is_file()
    assert len(validate_catalog()['collections']) == 24
    for collection_id, collection in config.collections.items():
        for stage in ('build', 'download', 'inspect'):
            importlib.import_module(f'governance.{collection.category}.{collection_id}.{stage}')


def test_config_composition_hash_and_secret_redaction(tmp_path, monkeypatch):
    monkeypatch.setenv('GOVERNANCE_WORKSPACE', str(tmp_path))
    monkeypatch.setenv('TEST_GOVERNANCE_SECRET', 'not-a-real-credential')
    (tmp_path/'base.yaml').write_text('nested: {one: 1, two: 2}\nitems: [1, 2]\n')
    child=tmp_path/'child.yaml'
    child.write_text('extends: base.yaml\nnested: {two: 3}\nitems: [4]\napi_key: ${env:TEST_GOVERNANCE_SECRET}\n')
    doc=ConfigDocument.load(child)
    assert doc.data['nested']=={'one':1,'two':3}
    assert doc.data['items']==[4]
    assert doc.redacted_data()['api_key']=='<redacted>'
    assert doc.config_hash==ConfigDocument.load(child).config_hash
    child.write_text('extends: child.yaml\n')
    with pytest.raises(ValueError, match='cycle'):
        ConfigDocument.load(child)


def test_cli_external_workspace_does_not_change_environment(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv('GOVERNANCE_WORKSPACE', raising=False)
    assert main(['--workspace',str(tmp_path),'init'])==0
    capsys.readouterr()
    assert main(['--workspace',str(tmp_path),'catalog'])==0
    assert len(json.loads(capsys.readouterr().out)['collections'])==24
    import os
    assert 'GOVERNANCE_WORKSPACE' not in os.environ


def test_catalog_uses_explicit_config_instead_of_default(tmp_path, monkeypatch):
    initialize_workspace(tmp_path)
    monkeypatch.setenv('GOVERNANCE_WORKSPACE',str(tmp_path))
    custom=tmp_path/'custom.yaml'
    custom.write_text('extends: config/data/governance/governance.yaml\ncatalog_path: absent.yaml\n')
    with pytest.raises(FileNotFoundError, match='absent.yaml'):
        validate_catalog(config_path=custom)


def test_packaged_defaults_match_checkout():
    root=Path(__file__).resolve().parents[1]
    for config in (root/'config').rglob('*.yaml'):
        packaged=root/'src/governance/resources/config'/config.relative_to(root/'config')
        assert config.read_bytes()==packaged.read_bytes()


def test_no_application_imports():
    import ast
    root=Path(__file__).resolve().parents[1]/'src/governance'
    for p in root.rglob('*.py'):
        for node in ast.walk(ast.parse(p.read_text())):
            modules = [node.module] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names] if isinstance(node,ast.Import) else []
            assert not any(m and m.split('.')[0]=='orcacast' for m in modules),p
