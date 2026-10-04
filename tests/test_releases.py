import json
from pathlib import Path
import pytest
from governance.releases import publish_generation, resolve_current, verify_generation, activate_generation


def publish(source, root, identity):
    return publish_generation(source, root, identity, scientific_method_version='inventory-1', software_revision='a'*40)


def test_generations_are_coherent_and_rollback_is_verified(tmp_path):
    source = tmp_path/'source'; source.mkdir()
    (source/'a').write_text('old-a'); (source/'b').write_text('old-b')
    root = tmp_path/'releases'
    first = publish(source, root, 'one')
    (source/'a').write_text('new-a'); (source/'b').write_text('new-b')
    second = publish(source, root, 'two')
    assert resolve_current(root) == second
    assert (first/'b').read_text() == 'old-b'
    activate_generation(root, 'one')
    assert resolve_current(root) == first
    with pytest.raises(FileExistsError): publish(source,root,'one')
    (second/'b').write_text('tampered')
    with pytest.raises(ValueError): activate_generation(root,'two')
    assert resolve_current(root) == first


def test_pointer_failure_preserves_previous_release(tmp_path, monkeypatch):
    source=tmp_path/'source'; source.mkdir(); (source/'data').write_text('data')
    root=tmp_path/'releases'; first=publish(source,root,'one')
    import governance.releases as releases
    def fail(*args): raise OSError('injected pointer failure')
    monkeypatch.setattr(releases.os,'replace',fail)
    with pytest.raises(OSError): publish(source,root,'two')
    assert resolve_current(root)==first
    assert verify_generation(root/'two')['release_id']=='two'
    assert not (root/'.publish.lock').exists()


def test_copy_failure_and_symlinks_fail_closed(tmp_path, monkeypatch):
    source=tmp_path/'source'; source.mkdir(); (source/'data').write_text('data')
    root=tmp_path/'releases'; first=publish(source,root,'one')
    import governance.releases as releases
    def fail(*args): raise OSError('injected copy failure')
    monkeypatch.setattr(releases.shutil,'copyfile',fail)
    with pytest.raises(OSError): publish(source,root,'two')
    assert resolve_current(root)==first
    assert not list(root.glob('.staging-*'))
    (source/'link').symlink_to(source/'data')
    with pytest.raises(ValueError): publish(source,root,'three')
    with pytest.raises(ValueError): publish(source,root,'../escape')


def test_lock_and_exact_membership(tmp_path):
    source=tmp_path/'source'; source.mkdir(); (source/'data').write_text('data')
    root=tmp_path/'releases'; first=publish(source,root,'one')
    (root/'.publish.lock').touch()
    with pytest.raises(FileExistsError): publish(source,root,'two')
    (first/'unexpected').write_text('x')
    with pytest.raises(ValueError): resolve_current(root)
