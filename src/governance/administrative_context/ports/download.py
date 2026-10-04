"""Bounded public NGA World Port Index acquisition; no inferred legal authority."""
from datetime import datetime,UTC
import json
import requests
from governance.shared.config import load_governance_config,DEFAULT_CONFIG_PATH
from governance.shared.artifacts import atomic_write_geoparquet,atomic_write_json,sha256_file
from .normalize import source_frame


def download(config_path=DEFAULT_CONFIG_PATH, *, overwrite=False):
    source=load_governance_config(config_path).sources['nga_world_port_index']
    destination=source.snapshot_path
    if destination.exists() and not overwrite:return [destination]
    response=requests.get(source.url,timeout=60,stream=True);response.raise_for_status()
    chunks=[];size=0
    for chunk in response.iter_content(65536):
        size+=len(chunk)
        if size>20_000_000:raise ValueError('NGA source exceeds 20 MB acquisition cap')
        chunks.append(chunk)
    payload=json.loads(b''.join(chunks));frame=source_frame(payload)
    # Archive the exact original response separately; do not publish any partial frame.
    destination.parent.mkdir(parents=True,exist_ok=True)
    raw=destination.with_suffix('.raw.json')
    if raw.exists() and not overwrite:raise FileExistsError(raw)
    raw.write_bytes(b''.join(chunks))
    atomic_write_geoparquet(frame,destination,overwrite=overwrite)
    atomic_write_json(destination.with_suffix(destination.suffix+'.metadata.json'),
        {'retrieved_at_utc':datetime.now(UTC).isoformat(),'bytes':size,'url':source.url,
         'raw_response_path':str(raw),'raw_response_sha256':sha256_file(raw),'sha256':sha256_file(destination)},overwrite=overwrite)
    return [destination,raw]
