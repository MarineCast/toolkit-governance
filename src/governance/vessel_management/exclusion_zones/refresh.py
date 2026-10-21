"""Offline, narrow staging refresh of exclusion references on existing supplied cells.

The returned directory is reviewable; this function never installs over the input.
All unrelated column arrays and all prior source memberships are preserved exactly.
Full standard ``build --original-data`` can subsequently replay the same normalizers.
"""
from pathlib import Path
from datetime import datetime, UTC
from dataclasses import replace
import copy
import json
import os

import geopandas as gpd
import h3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import Polygon

from governance.shared.config import load_governance_config
from governance.shared.acquisition import read_source_frame
from governance.shared.artifacts import source_record, sha256_file
from governance.shared.registry import normalize_collection
from governance.shared.spatial import clip_to_full_area
from governance.h3_matrix import overlay_collection
from governance.memberships import MEMBERSHIP_TYPE
from governance.products import validate_metric_table, validate_products
from .interface import annotate_product, annotate_catalog, COUNT, ASSIGNMENT
from .qualified import DFO, ENC, THEA, MPA, NAVY
from .standing import FWS,TORPEDO,SMITH

def stage_refresh(input_directory, output_directory, *, config_path='config/data/governance/governance.yaml'):
 root=Path(input_directory).resolve();out=Path(output_directory).resolve()
 if out==root or out.exists():raise ValueError('A new, separate staging directory is required')
 cfg=load_governance_config(config_path);catalog=json.loads((root/'catalog.json').read_text())
 before={name:sha256_file(root/name) for name in ['catalog.json',*[t['path'] for v in catalog['tables'].values() for t in v.values()]]}
 out.mkdir(parents=True);sources={};native=[];new_sources={DFO,ENC,THEA,NAVY,TORPEDO,SMITH}
 for sid,binding in catalog['original_data'].items():
  p=root/binding['path']
  if sha256_file(p)!=binding['sha256']:raise ValueError('Original checksum mismatch '+sid)
  target=out/binding['path'];target.parent.mkdir(parents=True,exist_ok=True);os.link(p,target)
 for sid in cfg.collections['exclusion_zones'].source_ids:
  source=cfg.sources[sid]
  if sid in catalog['original_data']:
   binding=catalog['original_data'][sid];p=root/binding['path']
   source=replace(source,local_path=p,snapshot_path=None,expected_sha256=binding['sha256'])
   frame=read_source_frame(source,bbox=cfg.bbox_tuple)
  elif sid in new_sources:
   frame=read_source_frame(source,bbox=cfg.bbox_tuple);attrs=copy.deepcopy(frame.attrs)
   receipt=json.loads(source.snapshot_path.with_suffix(source.snapshot_path.suffix+'.metadata.json').read_text())
   meta=source_record(source,source.snapshot_path);meta.pop('snapshot_path',None);sources[sid]=meta
   p=out/f'OriginalData/{sid}/geometry.parquet';p.parent.mkdir(parents=True)
   frame.attrs={};frame.to_parquet(p,index=False,compression='zstd');table=pq.read_table(p)
   original={'schema_version':1,'source':meta,'receipt':receipt,'frame_attributes':attrs,
    'selection_where':source.selection_where,'requested_grid_mask_sha256':source.requested_grid_mask_sha256,
    'geometry_support':'Full original query features, before study/H3 clipping. Explicit query/type/OID scope retained; not complete legal coverage.',
    'crs':'EPSG:4326','rows':len(frame)}
   pq.write_table(table.replace_schema_metadata({**table.schema.metadata,b'governance_original':json.dumps(original,sort_keys=True).encode()}),p,compression='zstd')
   assert table.equals(pq.read_table(p),check_metadata=False)
   frame.attrs=attrs
   catalog['original_data'][sid]={'path':str(p.relative_to(out)),'sha256':sha256_file(p),'rows':len(frame),'retrieved_at_utc':attrs.get('retrieved_at_utc')}
  else:raise ValueError('Unqualified new source '+sid)
  normalized,_=clip_to_full_area(normalize_collection(frame,source,cfg.collections['exclusion_zones']),cfg)
  native.append(normalized)
 all_native=gpd.GeoDataFrame(pd.concat(native,ignore_index=True),crs=4326)
 added=all_native[all_native.SOURCE_DATASET_ID.isin({DFO,ENC,THEA,MPA,NAVY,FWS,TORPEDO,SMITH})]
 source_ids=list(cfg.collections['exclusion_zones'].source_ids)
 report={'status':'staged','before_sha256':before,'source_counts_before_study_cell_selection':{sid:int(f.GOVERNANCE_FEATURE_ID.nunique()) for sid,f in all_native.groupby('SOURCE_DATASET_ID')},'tables':{}}
 for res,tables in catalog['tables'].items():
  if set(tables)!={'static'}:raise ValueError('Refresh supports current static-only delivery; no silent dynamic replacement')
  name=tables['static']['path'];old=pq.read_table(root/name);meta=json.loads(old.schema.metadata[b'governance']);old_meta=copy.deepcopy(meta)
  grid=gpd.GeoDataFrame(geometry=[Polygon([(lon,lat) for lat,lon in h3.cell_to_boundary(c)]) for c in old['h3_index'].to_pylist()],crs=4326)
  new=overlay_collection(grid,added,completeness='partial',length_crs='EPSG:32610',include_attributes=False)
  whole=overlay_collection(grid,all_native,completeness='partial',length_crs='EPSG:32610',include_attributes=False)
  prior=old[ASSIGNMENT].to_pylist()
  retained=[[m for m in row or [] if not any(r['source_dataset_id'] in {DFO,ENC,THEA,MPA,NAVY,FWS,TORPEDO,SMITH} for r in m['records'])] or None for row in prior]
  merged=[sorted((a or [])+(b or []),key=lambda x:x['feature_id']) or None for a,b in zip(retained,new['FEATURE_MEMBERSHIPS_V1'].to_pylist())]
  if any(len({m['feature_id'] for m in row or []})!=len(row or []) for row in merged):raise ValueError('Overlapping source identity collision')
  for row,expected in zip(merged,whole['FEATURE_MEMBERSHIPS_V1'].to_pylist()):
   if {m['feature_id'] for m in row or []}!={m['feature_id'] for m in expected or []}:raise ValueError('Original geometry does not reproduce prior source assignments')
  coverage='exclusion_zones__recorded_polygon_union_area_fraction'
  updates={ASSIGNMENT:pa.array(merged,MEMBERSHIP_TYPE),COUNT:pa.array([len(v) if v else None for v in merged],pa.int64()),coverage:whole['POLYGON_COVERAGE_FRAC']}
  for c in list(updates):updates[c+'_status']=pa.array(['partial' if v else 'unknown' for v in merged])
  product=old
  for c,v in updates.items():product=product.set_column(product.column_names.index(c),c,v)
  assert all(old[c].equals(product[c]) for c in old.column_names if c not in updates)
  meta['original_data']=copy.deepcopy(catalog['original_data']);meta['sources'].update(sources)
  meta['collections']['exclusion_zones'].update(source_ids=source_ids,normalization_profile='bounded_static_restriction_references')
  support=meta['coverage']['exclusion_zones'];support['configured_source_receipt'].update(numerator=len(source_ids),denominator=len(source_ids))
  support['original_source_bindings']={sid:catalog['original_data'][sid] for sid in source_ids}
  product=annotate_product(product,meta,out)
  meta['exclusion_zone_interface'].update(prior_qualified_spatial_caveats=old_meta.get('exclusion_zone_interface',{}),
   spatial_support='Positive polygon intersections with the full unchanged supplied H3 cells. Not water-only geometry coverage; reporting-mask differences retained.',
   source_counts_before_study_cell_selection=report['source_counts_before_study_cell_selection'],
   interpretation='Count recorded rule areas once, not chart parts or currently active bans. Geography and activity-specific qualifications remain source-specific.')
  validate_metric_table(product,meta)
  pq.write_table(product.replace_schema_metadata({**old.schema.metadata,b'governance':json.dumps(meta,sort_keys=True).encode()}),out/name,compression='zstd')
  tables['static']['sha256']=sha256_file(out/name)
  report['tables'][name]={'rows':old.num_rows,'columns':old.num_columns,'assigned_cells':sum(bool(v) for v in merged),
   'unrelated_arrays_preserved':sum(c not in updates for c in old.column_names),
   'prior_tc_lockheed_memberships_exact':all(a==([m for m in b or [] if not any(r['source_dataset_id'] in {DFO,ENC,THEA,MPA,NAVY,FWS,TORPEDO,SMITH} for r in m['records'])] or None) for a,b in zip(retained,merged)),
   'zone_ids':sorted({m['feature_id'] for row in merged for m in row or []})}
 annotate_catalog(catalog);now=datetime.now(UTC).isoformat();catalog['last_updated_utc']=now
 catalog['areas']['exclusion_zones'].update(last_updated_utc=now,source_ids=source_ids,source_scope='Partial BC/WA official agency/CFR/WAC static activity restriction references; Oregon unqualified; no current-activation/history inference')
 (out/'catalog.json').write_text(json.dumps(catalog,indent=2,sort_keys=True)+'\n')
 for name,digest in before.items():
  if sha256_file(root/name)!=digest:raise ValueError('Input changed during staging')
 report['validation']=validate_products(out);report['after_sha256']={name:sha256_file(out/name) for name in before}
 return report
