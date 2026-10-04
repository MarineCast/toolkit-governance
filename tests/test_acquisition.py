from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from governance.shared import acquisition
from governance.shared.config import load_governance_config


def test_arcgis_acquisition_archives_pages_and_bounded_query(monkeypatch, tmp_path) -> None:
    source = replace(
        load_governance_config().sources["wdfw_recreational_marine_areas"],
        snapshot_path=tmp_path / "snapshot.pages.json",
    )
    requests = []

    def fake_response(url, *, params, timeout):
        requests.append((url, dict(params), timeout))
        if params["f"] == "json":
            return {"maxRecordCount": 2, "geometryType": "esriGeometryPoint"}
        offset = params["resultOffset"]
        features = [
            {
                "type": "Feature",
                "properties": {"OBJECTID": offset + index},
                "geometry": {"type": "Point", "coordinates": [-123.0, 48.0]},
            }
            for index in range(2 if offset == 0 else 1)
        ]
        return {"type": "FeatureCollection", "features": features}

    monkeypatch.setattr(acquisition, "_response_json", fake_response)
    path = acquisition.download_arcgis_snapshot(
        source,
        bbox=(-180.0, 32.0, -109.0, 72.0),
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["server_filtered"] is True
    assert len(payload["pages"]) == 2
    assert payload["pages"][0]["request_params"]["geometry"] == "-180.0,32.0,-109.0,72.0"
    assert [request[1].get("resultOffset") for request in requests[1:]] == [0, 2]
    assert len(acquisition.read_source_frame(source)) == 3


def test_direct_archive_is_checksum_pinned_and_metadata_is_archived(monkeypatch, tmp_path) -> None:
    content = b"pinned governance archive fixture"
    source = replace(
        load_governance_config().sources["international_boundary_commission_v1_3"],
        snapshot_path=tmp_path / "boundary.zip",
        expected_sha256=hashlib.sha256(content).hexdigest(),
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def raise_for_status(self):
            return None

        def iter_content(self, *, chunk_size):
            assert chunk_size == 1024 * 1024
            yield content

    monkeypatch.setattr(acquisition.requests, "get", lambda *_args, **_kwargs: FakeResponse())
    path = acquisition.download_direct_snapshot(source)
    assert path.read_bytes() == content
    metadata = json.loads(path.with_suffix(".zip.metadata.json").read_text(encoding="utf-8"))
    assert metadata["sha256"] == source.expected_sha256
    assert metadata["archive_member"] == source.archive_member
    assert metadata["archive_layer"] == source.archive_layer

    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        acquisition.download_direct_snapshot(source)

    with pytest.raises(acquisition.SourceUnavailableError, match='byte cap'):
        acquisition.download_direct_snapshot(source, overwrite=True, max_bytes=3)
    assert path.read_bytes() == b'changed'
    assert not list(tmp_path.glob('*.part'))
