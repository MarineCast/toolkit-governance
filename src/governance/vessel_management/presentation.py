"""One reference-presence measurement; retain every typed routing identity."""
import pyarrow as pa
import json
from governance.memberships import validate_memberships, MEMBERSHIP_TYPE, RECORD_FIELDS, definition
from .routing import ROLES

FAMILY_KEY = 'vessel_routing_regulations'
FAMILY_NAME = 'Vessel Routing & Regulations'
COLLECTIONS = ('shipping_lanes', 'traffic_separation_schemes', 'speed_restriction_zones')
PRESENCE = FAMILY_KEY + '__recorded_reference'
PRESENCE_NAME = 'Routing / regulation recorded'
GROUPS = tuple(sorted(f'{spec[0]}__{role}' for role,spec in ROLES.items())) + ('speed_restriction_zones',)
SHIPPING = FAMILY_KEY+'__shipping_lanes'
SEPARATION = FAMILY_KEY+'__traffic_separation_zones'
COMBINED = {SHIPPING:tuple(g for g in GROUPS if g.startswith('shipping_lanes__')),
    SEPARATION:tuple(g for g in GROUPS if g.startswith(('shipping_lanes__','traffic_separation_schemes__')))}
COMPONENT_VIEWS = {g for groups in COMBINED.values() for g in groups}
# Keep the old shipping-only view as hidden compatibility support; display one union.
VISIBLE_GROUPS = (SEPARATION,) + tuple(g for g in GROUPS if g not in COMPONENT_VIEWS)
IDENTITY_NAMES = {SHIPPING+'__feature_memberships_v1':'Shipping Lanes',
    SEPARATION+'__feature_memberships_v1':'Shipping Lanes & Traffic Separation Zones',
    'speed_restriction_zones__feature_memberships_v1':'Speed Restriction Zones'}
SEMANTICS = ('True means at least one retained routing/regulation reference feature is recorded in the native cell. '
    'This includes navigation lines, recommended routes, traffic-scheme components and seasonal speed references; '
    'it does not mean an unconditional mandatory restriction, current activation, vessel-specific applicability or legal compliance. '
    'False requires observed empty memberships for every expected component and independently evidenced complete geographic '
    'inventory coverage of the full supplied cells. Otherwise no-hit support is null (unknown/unavailable), never inferred false. '
    'Identity layers retain all source-qualified IDs, overlaps, source roles, advisory/conditional meanings and original details. '
    'Shipping Lanes & Traffic Separation Zones groups all eight shipping roles and seven traffic-scheme roles for display; navigation/recommended routes, boundaries, crossings, lane parts, separation lines, traffic lanes and separation zones retain their native types. '
    'Line and polygon memberships are combined as evidence of reference presence, never as pooled area/length coverage. '
    'No source acquisition, geometry overlay or artificial daily history is performed.')
SOURCE_CONTEXT = {
 **{f'chs_routing_layer_{n}': {'country':'Canada','agency':'Canadian Hydrographic Service',
     'boundary_type':'Typed chart routing component reference',
     'classification':'Navigation/recommended-route and traffic-scheme roles remain distinct; mandatory status and current applicability not inferred',
     'scope':'Selected layers/roles and bounded receipt; not complete geographic or legal coverage'} for n in (2,3,4,5)},
 'noaa_routing_2026': {'country':'United States','agency':'NOAA / Marine Cadastre',
     'boundary_type':'2026 archive typed vessel-routing reference',
     'classification':'Fairway, two-way/recommended route and traffic-scheme components are not pooled into unconditional restrictions',
     'scope':'Planning/reference snapshot; legal-effective dates and completeness unqualified'},
 'tc_srkw_interim_order_2026': {'country':'Canada','agency':'Transport Canada',
     'boundary_type':'Swiftsure closed-ring seasonal speed reference',
     'classification':'10 knots over ground, June 1–November 30 2026 inclusive, subject to source vessel/person/activity exceptions; current applicability unknown',
     'scope':'Swiftsure only; Nitinat coastline-dependent boundary and moving-animal rules excluded'},
}

def is_routing_column(name):
 return name.startswith(tuple(c+'__' for c in COLLECTIONS)) or name.startswith(FAMILY_KEY+'__')

def annotate_fields(fields):
 for name,field in fields.items():
  if not is_routing_column(name):continue
  identity=field.get('membership_schema_version')==1
  group=name.rpartition('__')[0]
  field.update(display_family=FAMILY_NAME,map_feature=(identity and group in VISIBLE_GROUPS) or name==PRESENCE)
  if identity or name==PRESENCE:
   role=group.rpartition('__')[2]
   description=IDENTITY_NAMES.get(name) or (ROLES[role][3] if role in ROLES else 'Seasonal source speed-rule reference' if group=='speed_restriction_zones' else 'Combined recorded-reference presence')
   field.update(role='recorded_feature_identity' if identity else 'scientific_metric',support_limitation=description+'. '+SEMANTICS)
   sources={ROLES[g.rpartition('__')[2]][1] for g in COMBINED[group]} if group in COMBINED else {ROLES[role][1]} if role in ROLES else {'tc_srkw_interim_order_2026'} if group=='speed_restriction_zones' else set(SOURCE_CONTEXT)
   field['source_context']={s:SOURCE_CONTEXT[s] for s in sorted(sources)}
  if name in IDENTITY_NAMES:field['display_name']=IDENTITY_NAMES[name]
  if name==PRESENCE:field.update(display_name=PRESENCE_NAME)

def _complete(coverage,group):
 support=coverage.get(group,{}).get('geographic_inventory_coverage',{})
 return (support.get('status')=='complete' and support.get('scope')=='full_supplied_cells'
     and isinstance(support.get('evidence'),str) and bool(support['evidence'].strip()))

def add_features(table,fields,coverage):
 """Derive one nullable boolean from validated memberships; never alter components."""
 if not any(g+'__feature_memberships_v1' in table.column_names for g in GROUPS):
  annotate_fields(fields);return table
 validate_memberships(table,fields)
 rows=[];states=[]
 for group in GROUPS:
  column=group+'__feature_memberships_v1'
  rows.append(table[column].to_pylist() if column in table.column_names else [None]*table.num_rows)
  states.append(table[fields[column]['missing_reason_field']].to_pylist() if column in table.column_names else ['unavailable']*table.num_rows)
 complete=all(_complete(coverage,g) for g in GROUPS)
 values=[];support=[]
 for i in range(table.num_rows):
  positive=any(bool(row[i]) for row in rows)
  observed=all(state[i]=='observed' for state in states)
  empty=complete and observed and all(row[i]==[] for row in rows)
  values.append(True if positive else False if empty else None)
  support.append(('observed' if complete and observed else 'partial') if positive else 'observed' if empty else 'unavailable' if all(s[i]=='unavailable' for s in states) else 'unknown')
 for name,array in {PRESENCE:pa.array(values,pa.bool_()),PRESENCE+'_status':pa.array(support)}.items():
  table=table.set_column(table.column_names.index(name),name,array) if name in table.column_names else table.append_column(name,array)
 fields[PRESENCE]={'units':'1','nullable':True,'definition':SEMANTICS,'value_semantics':'boolean_overlap',
     'missing_reason_field':PRESENCE+'_status','coverage_reference':FAMILY_KEY,'interpretation':'Recorded-reference presence only; not current legal restriction or an absence map'}
 fields[PRESENCE+'_status']={'units':None,'definition':'Support for combined reference-presence boolean','nullable':False,'enum':['observed','partial','unknown','unavailable','not_applicable']}
 coverage[FAMILY_KEY]={'component_groups':list(GROUPS),
     'geographic_inventory_coverage':{'status':'complete' if complete else 'unknown','scope':'full_supplied_cells' if complete else 'not_qualified','meaning':'Every component requires independent full-cell inventory-completeness evidence; source receipts alone are insufficient'},
     'effect':SEMANTICS,'geometric_recomputation':False,'scope':'Existing supplied native H3 cells; static source-reference support'}
 table=_add_combined_views(table,fields,coverage)
 annotate_fields(fields);return table

def _merge(rows):
 features={}
 for row in rows:
  for member in row or []:
   records=features.setdefault(member['feature_id'],{})
   for record in member['records']:
    key=tuple(record[k] for k in RECORD_FIELDS)
    records.setdefault(key,set()).update(record['geometry_part_ids'])
 return [{'feature_id':fid,'records':[dict(zip(RECORD_FIELDS,key),geometry_part_ids=sorted(parts))
     for key,parts in sorted(records.items(),key=lambda pair:json.dumps(pair[0]))]} for fid,records in sorted(features.items())]

def _add_combined_views(table,fields,coverage):
 for group,components in COMBINED.items():
  column=group+'__feature_memberships_v1';count=group+'__recorded_feature_count'
  arrays=[];states=[];context={}
  for component in components:
   native=component+'__feature_memberships_v1';role=component.rpartition('__')[2]
   rows=table[native].to_pylist() if native in table.column_names else [None]*table.num_rows
   arrays.append(rows);states.append(table[fields[native]['missing_reason_field']].to_pylist() if native in table.column_names else ['unavailable']*table.num_rows)
   prior=fields.get(native,{}).get('source_record_context',{})
   for row in rows:
    for member in row or []:
     for record in member['records']:
      identity=record['source_feature_id'];detail=context.setdefault(identity,{**prior.get(identity,{})})
      for key,value in [('routing_component_groups',component),('routing_role',role),('source_object_type',ROLES[role][2]),('source_role_description',ROLES[role][3])]:
       detail[key]=' / '.join(sorted(set(detail.get(key,'').split(' / '))-{''}|{value}))
      detail['legal_applicability']='Source role/reference only; recommended/advisory and mandatory/conditional meanings remain distinct, with current applicability unqualified'
  complete=all(_complete(coverage,c) for c in components);members=[];support=[]
  for i in range(table.num_rows):
   row=_merge([a[i] for a in arrays]);observed=all(s[i]=='observed' for s in states)
   empty=complete and observed and all(a[i]==[] for a in arrays)
   members.append(row if row or empty else None)
   support.append(('observed' if complete and observed else 'partial') if row else 'observed' if empty else 'unavailable' if all(s[i]=='unavailable' for s in states) else 'unknown')
  values={column:pa.array(members,MEMBERSHIP_TYPE),column+'_status':pa.array(support),
      count:pa.array([None if row is None else len(row) for row in members],pa.int64()),count+'_status':pa.array(support)}
  for name,array in values.items():table=table.set_column(table.column_names.index(name),name,array) if name in table.column_names else table.append_column(name,array)
  fields[column]={**definition(group),'source_record_context':context,
      'interpretation':'Combined display membership only; all underlying source-qualified identities, records and native part IDs retained. No physical-route or legal equivalence across sources.'}
  fields[count]={'units':'count','nullable':True,'definition':'Distinct recorded source-qualified feature IDs in this display view; parts and repeated records do not increase counts','missing_reason_field':count+'_status','coverage_reference':group}
  for name in [column+'_status',count+'_status']:fields[name]={'units':None,'nullable':False,'definition':'Support for grouped recorded identities','enum':['observed','partial','unknown','unavailable','not_applicable']}
  coverage[group]={'component_groups':list(components),'geographic_inventory_coverage':{'status':'complete' if complete else 'unknown'},'effect':'Union paired memberships for display, without merging source meanings, polygon area or line length'}
 validate_memberships(table,fields)
 return table

def family_definition(present=COLLECTIONS):
 identities=[g+'__feature_memberships_v1' for g in VISIBLE_GROUPS if g in COMBINED or g.split('__')[0] in present]
 return {
     'display_name':FAMILY_NAME,'source_collections':list(present),'scientific_features':{
         PRESENCE:{'display_name':PRESENCE_NAME,'role':'scientific_metric','value_semantics':'boolean_overlap'},
         **{n:{'role':'recorded_feature_identity',**({'display_name':IDENTITY_NAMES[n]} if n in IDENTITY_NAMES else {})} for n in identities}},
     'identity_columns':identities,'measurement_columns':[PRESENCE],
     'native_identity_columns':[g+'__feature_memberships_v1' for g in GROUPS],
     'retained_compatibility_identity_columns':[SHIPPING+'__feature_memberships_v1'],
     'saved_identity_aliases':{SHIPPING+'__feature_memberships_v1':SEPARATION+'__feature_memberships_v1'},
     'grouped_identity_components':{g:list(c) for g,c in COMBINED.items()},
     'retained_hidden_support':'Original count, area/length and status arrays remain exact; no additional measurement options',
     'interpretation':SEMANTICS}

def annotate_catalog(catalog):
 present=[n for n in COLLECTIONS if n in catalog.get('areas',{})]
 if not present:return
 catalog.setdefault('feature_families',{})[FAMILY_KEY]=family_definition(present)
 for n in present:catalog['areas'][n]['presentation_family']=FAMILY_KEY
