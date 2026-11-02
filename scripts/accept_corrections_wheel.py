"""Run outside the checkout with an installed wheel and a fresh temporary workspace.

Usage: python /path/to/scripts/accept_corrections_wheel.py NEW_WORKSPACE [--h3]
"""
import importlib
import importlib.util
import json
import sys
import time
from importlib.resources import files
from pathlib import Path

class BlockApplication:
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'orcacast','domains','applications_data_explorer'}:
            raise ImportError('Application imports forbidden in standalone acceptance')
sys.meta_path.insert(0,BlockApplication())
import governance
assert Path(governance.__file__).is_relative_to(Path(sys.prefix))
assert governance.__version__=='0.4.0'
root=Path(sys.argv[1]).resolve()
assert not root.exists(), 'Use a NEW temporary workspace'
governance.initialize_workspace(root)
cfg=governance.load_governance_config(workspace=root)
from governance.shared.registry import CATEGORY_COLLECTIONS
for category,names in CATEGORY_COLLECTIONS.items():
    for name in names:
        if name in cfg.collections:
            for stage in ('normalize','build','download'):
                importlib.import_module(f'governance.{category}.{name}.{stage}')
for name in ('delivery','preflight','products'):
    importlib.import_module('governance.'+name)
resources=files('governance').joinpath('resources/config')
for config_path in sorted((root/'config').rglob('*')):
    if config_path.is_file():
        assert config_path.read_bytes()==resources.joinpath(config_path.relative_to(root/'config').as_posix()).read_bytes()
source=cfg.sources['wdfw_recreational_marine_areas']
# One feature/record, two disjoint native polygon parts; wholly synthetic.
coordinates=[[[[-123.008,48.492],[-123.002,48.492],[-123.002,48.498],[-123.008,48.498],[-123.008,48.492]]],[[[-122.998,48.502],[-122.992,48.502],[-122.992,48.508],[-122.998,48.508],[-122.998,48.502]]]]
feature={'type':'Feature','properties':{'OBJECTID':1,'AreaName':'7'},'geometry':{'type':'MultiPolygon','coordinates':coordinates}}
payload=dict(snapshot_schema_version=2,source_id=source.source_id,source_url=source.url,request_contract={'provider':source.provider,'source_as_of':source.source_as_of},retrieved_at_utc='2026-10-01T00:00:00Z',server_filtered=True,requested_bbox_wgs84=[-180,32,-109,72],selection_where='1=1',requested_grid_mask_sha256=None,object_id_field='OBJECTID',selected_object_ids=[1],expected_object_id_count=1,unreceived_object_ids=[],geometry_roster_complete=True,pages=[{'retrieved_at_utc':'2026-10-01T00:00:00Z','response':{'features':[feature]}}])
source.snapshot_path.parent.mkdir(parents=True)
source.snapshot_path.write_text(json.dumps(payload))
# Exercise the retained offline native pipeline with the qualified receipt.
import os
os.environ['GOVERNANCE_WORKSPACE']=str(root)
from governance.fisheries_management.management_areas.build import build
artifact=build(cfg.path,allow_partial=True)
import geopandas as gpd
native=gpd.read_parquet(artifact)
assert len(native)==2 and native.GOVERNANCE_FEATURE_ID.nunique()==1
assert native.SYSTEM_LEARNED_AT.tolist()==['2026-10-01T00:00:00Z']*2
print('installed_location',governance.__file__)
print('offline_native_parts',len(native))
