"""Native fishing-area/H3 relations; geometry fractions are not catch allocations."""
import json
import re
from pathlib import Path
import geopandas as gpd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from .h3_matrix import _grid
from .shared.artifacts import atomic_write_json, sha256_file
from .shared.schema import validate_governance_geometry

METHOD='native-fishing-area-crosswalk-1.0.0'
KEY=['source_dataset_id','source_feature_id','governance_feature_id','h3_index']
FIELDS={'agency':'AUTHORITY','system_id':'AREA_SYSTEM_ID','provider_area_id':'AREA_CODE',
        'hierarchy_level':'AREA_HIERARCHY_LEVEL','parent_provider_area_id':'PARENT_AREA_CODE',
        'fishery_sector':'FISHERY_SECTOR','effective_start':'EFFECTIVE_START',
        'effective_end':'EFFECTIVE_END','geometry_version':'GEOMETRY_VERSION'}


def _areas(frame):
    validate_governance_geometry(frame)
    if not frame.geometry.geom_type.isin(['Polygon','MultiPolygon']).all():
        raise ValueError('Fishing reference polygons required')
    for key,group in frame.to_crs(6933).groupby(['SOURCE_DATASET_ID','SOURCE_FEATURE_ID','GOVERNANCE_FEATURE_ID'],sort=True):
        identity=dict(zip(KEY[:3],key))
        for name,column in FIELDS.items():
            values=group[column].dropna().astype(str).unique() if column in group else []
            if len(values)>1:raise ValueError('Conflicting area identity/version: '+column)
            identity[name]=values[0] if len(values) and values[0] not in {'unknown','unavailable',''} else None
        if any(identity[k] is None for k in ['agency','system_id','provider_area_id','hierarchy_level','fishery_sector']):
            raise ValueError('Explicit agency/system/area/hierarchy/sector required')
        identity['area_geometry_part_ids']=sorted(group.GEOMETRY_PART_ID.astype(str))
        area=shapely.union_all(group.geometry.to_numpy())
        if area.area<=0:raise ValueError('Positive native area required')
        yield identity,area


def export_fishing_crosswalk(native,native_manifest,grids,output,*,release_id,software_revision):
    if not re.fullmatch('[0-9a-f]{40}',software_revision) or not release_id:
        raise ValueError('Explicit release identity and full software revision required')
    output=Path(output);output.mkdir(exist_ok=False)
    native=Path(native);native_manifest=Path(native_manifest)
    meta=json.loads(native_manifest.read_text())
    if sha256_file(native)!=meta['artifact']['sha256']:raise ValueError('Native checksum mismatch')
    areas=list(_areas(gpd.read_parquet(native)));written=[];seen=set()
    for path in grids:
        grid=_grid(path);resolutions=set(grid.H3_RESOLUTION)
        if len(resolutions)!=1:raise ValueError('One resolution per crosswalk table required')
        resolution=int(next(iter(resolutions)))
        if resolution in seen:raise ValueError('Duplicate resolution')
        seen.add(resolution);cells=grid.to_crs(6933);tree=shapely.STRtree(cells.geometry.to_numpy());rows=[]
        for identity,area in areas:
            indices=sorted(tree.query(area,predicate='intersects').tolist())
            values=shapely.area(shapely.intersection(cells.geometry.to_numpy()[indices],area))
            for index,value in zip(indices,values):
                if value<=0:continue
                cell_area=cells.geometry.iloc[index].area
                rows.append(identity | {'h3_index':grid.H3_INDEX.iloc[index],'h3_resolution':resolution,
                    'intersection_area_m2':float(value),'native_area_m2':float(area.area),
                    'full_cell_area_m2':float(cell_area),'fraction_of_native_area':float(value/area.area),
                    'fraction_of_full_cell':float(value/cell_area),'geometry_snapshot_sha256':meta['artifact']['sha256'],
                    'model_eligible':False})
        if not rows:raise ValueError('No positive fishing-area intersections')
        artifact=output/f'fishing-area-crosswalk-r{resolution}.parquet';companion=artifact.with_suffix('.manifest.json')
        pq.write_table(pa.Table.from_pylist(rows),artifact,compression='zstd')
        atomic_write_json(companion,{'schema_version':1,'scientific_method_version':METHOD,
            'data_release_id':release_id,'software_revision':software_revision,'model_eligible':False,
            'artifact':{'path':str(artifact.resolve()),'sha256':sha256_file(artifact),'rows':len(rows)},
            'native':{'artifact':str(native.resolve()),'sha256':sha256_file(native),'manifest':str(native_manifest.resolve()),'manifest_sha256':sha256_file(native_manifest)},
            'grid':{'path':str(Path(path).resolve()),'sha256':sha256_file(path),'resolution':resolution},
            'primary_key':KEY,'sources':meta['sources'],
            'method':'Union native parts within each provider source record; positive-area full H3 intersections in EPSG:6933.',
            'units':{'intersection_area_m2':'m2','native_area_m2':'m2','full_cell_area_m2':'m2','fraction_of_native_area':'dimensionless','fraction_of_full_cell':'dimensionless'},
            'denominator':'Retained full native source-record union and full H3 cell; never clipped/renormalized to reporting water or grid extent.',
            'limitations':['Geometric support fractions are not allocation weights. No catch/effort quantities or compliance evaluations. Never replicate an area total into every cell.','Source systems, sectors, records and resolutions are non-additive. Native companions retain original geometry, attributes and part relations.','Unknown validity/version/parent stays null; retrieval is not legal effective time. Missing intersection rows do not establish absence.','Current adapter is WDFW recreational only. Commercial, BC and Oregon systems require separate qualified sources; never infer common geometry or matching codes.','Local relational reference companion, not shared wide-table schema adoption.']})
        written.append({'artifact':str(artifact.resolve()),'manifest':str(companion.resolve())})
    return written


def validate_fishing_crosswalk(artifact,companion,*,map_path=Path):
    meta=json.loads(Path(companion).read_text());artifact=Path(artifact)
    if meta['scientific_method_version']!=METHOD or meta['model_eligible'] is not False:raise ValueError('Crosswalk method/policy mismatch')
    if sha256_file(artifact)!=meta['artifact']['sha256']:raise ValueError('Crosswalk checksum mismatch')
    native=map_path(meta['native']['artifact']);manifest=map_path(meta['native']['manifest']);grid_path=map_path(meta['grid']['path'])
    if sha256_file(native)!=meta['native']['sha256'] or sha256_file(manifest)!=meta['native']['manifest_sha256'] or sha256_file(grid_path)!=meta['grid']['sha256']:
        raise ValueError('Crosswalk lineage mismatch')
    frame=pq.read_table(artifact).to_pandas();grid=_grid(grid_path).to_crs(6933)
    if len(frame)!=meta['artifact']['rows'] or frame.duplicated(KEY).any():raise ValueError('Crosswalk cardinality mismatch')
    if set(frame.h3_resolution)!={meta['grid']['resolution']} or not set(frame.h3_index)<=set(grid.H3_INDEX) or frame.model_eligible.any():raise ValueError('Crosswalk membership/policy mismatch')
    for name in meta['units']:
        if not np.isfinite(frame[name]).all() or (frame[name]<=0).any():raise ValueError('Invalid crosswalk measure')
    for name,denom in [('fraction_of_native_area','native_area_m2'),('fraction_of_full_cell','full_cell_area_m2')]:
        if (frame[name]>1+1e-8).any() or not np.allclose(frame[name],frame.intersection_area_m2/frame[denom],rtol=1e-9):raise ValueError('Crosswalk denominator mismatch')
    areas={tuple(row[k] for k in KEY[:3]):(row,g) for row,g in _areas(gpd.read_parquet(native))}
    cells=dict(zip(grid.H3_INDEX,grid.geometry));tree=shapely.STRtree(grid.geometry.to_numpy());samples=0
    expected_keys=set()
    for key,(identity,area) in areas.items():
        for index in tree.query(area,predicate='intersects'):
            if area.intersection(grid.geometry.iloc[index]).area>0:
                expected_keys.add(key+(grid.H3_INDEX.iloc[index],))
    if set(frame[KEY].itertuples(index=False,name=None))!=expected_keys:
        raise ValueError('Crosswalk relation completeness mismatch')
    if not frame.geometry_snapshot_sha256.eq(meta['native']['sha256']).all():
        raise ValueError('Crosswalk row snapshot mismatch')
    for key,rows in frame.groupby(KEY[:3],sort=True):
        if key not in areas:raise ValueError('Crosswalk native identity mismatch')
        identity,area=areas[key]
        if any(list(parts)!=identity['area_geometry_part_ids'] for parts in rows.area_geometry_part_ids):
            raise ValueError('Crosswalk native part relation mismatch')
        for name in FIELDS:
            if rows[name].isna().any() and identity[name] is not None:
                raise ValueError('Crosswalk missing provider identity')
            values=list(rows[name].dropna().astype(str).unique())
            if values!=([] if identity[name] is None else [identity[name]]):raise ValueError('Crosswalk provider identity mismatch')
        if rows.fraction_of_native_area.sum()>1+1e-8:raise ValueError('Crosswalk double-counts area support')
        for _,row in rows.iloc[sorted(set([0,len(rows)-1]))].iterrows():
            cell=cells[row.h3_index]
            if not np.isclose(area.intersection(cell).area,row.intersection_area_m2,rtol=1e-8) or not np.isclose(area.area,row.native_area_m2,rtol=1e-8) or not np.isclose(cell.area,row.full_cell_area_m2,rtol=1e-8):raise ValueError('Independent scalar crosswalk mismatch')
            samples+=1
    return {'status':'passed','rows':len(frame),'resolution':meta['grid']['resolution'],'native_source_records':len(areas),'scalar_samples':samples,'limit':'Separate scalar calculation, shared GEOS/projection libraries; no allocation or legal certification.'}
