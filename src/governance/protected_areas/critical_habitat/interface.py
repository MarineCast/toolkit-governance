"""Two-layer source-qualified habitat interface; no ecological equivalence inferred."""
from .eccc import SOURCE as ECCC_SOURCE, CONDITIONS as ECCC_CONDITIONS, DOCUMENT as ECCC_DOCUMENT
GROUP = 'critical_habitat'
COUNT = GROUP + '__recorded_feature_count'
ASSIGNMENT = GROUP + '__feature_memberships_v1'
SCIENTIFIC_FEATURES = {
    COUNT: {'display_name': 'Critical Habitat Count'},
    ASSIGNMENT: {'display_name': 'Critical Habitat Assignment'},
}
SOURCE_CONTEXT = {name: {'country': 'United States', 'agency': 'NOAA National Marine Fisheries Service',
                         'boundary_type': 'NMFS proposed/final critical-habitat inventory reference',
                         'scope': 'Partial NOAA inventory; no Canadian SARA or USFWS completeness claim'}
                  for name in ('noaa_critical_habitat_polygon', 'noaa_critical_habitat_line')}
SOURCE_CONTEXT['dfo_aquatic_critical_habitat'] = {'country':'Canada', 'agency':'Fisheries and Oceans Canada',
    'boundary_type':'SARA aquatic critical-habitat inventory reference',
    'classification':'Provider Final/Proposed status retained unresolved; not equivalent to NOAA Final',
    'scope':'Bounded marine and freshwater source records; no exhaustive geographic or legal coverage claim'}
SOURCE_CONTEXT[ECCC_SOURCE] = {'country':'Canada', 'agency':'Environment and Climate Change Canada - Canadian Wildlife Service',
    'boundary_type':'Conditional SARA marine critical-habitat reference area',
    'classification':'Posted Final recovery document; required habitat conditions remain distinct from polygon membership',
    'scope':'Only the eleven reviewed public marine Marbled Murrelet areas; terrestrial nesting components excluded',
    'habitat_conditions':ECCC_CONDITIONS, 'source_document':ECCC_DOCUMENT}
PREVIOUS_LIMITATION = ('Distinct source-backed habitat feature records per native H3 cell, not species counts, '
              'unique habitat units or legally equivalent US/Canadian designations. Geometry parts never '
              'count as additional features. All overlapping species/entity labels and source-qualified IDs '
              'remain paired. Proposed/final status and source qualifications remain distinct. '
              'DFO Final/Proposed status stays unresolved; no final designation is inferred. '
              'Missing source coverage is unknown, never zero or proof of no critical habitat.')
LIMITATION = PREVIOUS_LIMITATION.replace('Missing source coverage',
              'ECCC murrelet polygons are conditional marine reference areas: required biophysical attributes '
              'must be present; polygon membership does not confirm habitat everywhere or current legal protection. '
              'Missing source coverage')


def annotate_fields(fields):
    """Expose exactly Count/Assignment while retaining every diagnostic array."""
    for name, field in fields.items():
        if name.startswith(GROUP + '__'):
            field.update(map_feature=name in SCIENTIFIC_FEATURES, display_family='Critical Habitat')
            field.update(SCIENTIFIC_FEATURES.get(name, {}))
            if name in SCIENTIFIC_FEATURES:
                field['support_limitation'] = LIMITATION
                field['source_context'] = SOURCE_CONTEXT
                if LIMITATION not in field.get('interpretation', ''):
                    previous = field.get('interpretation', '').replace(PREVIOUS_LIMITATION, '').strip()
                    field['interpretation'] = (previous + ' ' + LIMITATION).strip()


def annotate_catalog(catalog):
    if GROUP in catalog.get('areas', {}):
        catalog['areas'][GROUP]['scientific_features'] = SCIENTIFIC_FEATURES


def annotate_product(table, metadata, original_root):
    """Attach retained provider classifications without changing any metric value."""
    import hashlib
    from pathlib import Path
    import pyarrow.parquet as pq
    annotate_fields(metadata['fields'])
    if ASSIGNMENT not in table.column_names:
        return table
    from governance.memberships import qualify_unknown_no_hit
    table = qualify_unknown_no_hit(table, (COUNT, ASSIGNMENT))
    wanted = {}
    for row in table[ASSIGNMENT].to_pylist():
        for member in row or []:
            for record in member['records']:
                wanted.setdefault(record['source_dataset_id'], set()).add(record['source_feature_id'])
    context = {}
    labels = {'ID':'provider_feature_id', 'SCIENAME':'scientific_name', 'COMNAME':'common_name',
              'LISTENTITY':'listed_entity', 'LISTSTATUS':'listing_status', 'CHSTATUS':'habitat_status',
              'UNIT':'habitat_unit', 'TAXON':'taxon', 'HABTYPE':'habitat_type',
              'PUBDATE':'source_publication_date', 'EFFECTDATE':'source_effective_date',
              'ECFR':'legal_reference', 'INPORTURL':'source_metadata'}
    for source, identities in wanted.items():
        if source not in SOURCE_CONTEXT:
            continue  # New providers require an explicit source-specific attribute contract.
        binding = metadata.get('original_data', {}).get(source)
        if binding is None:
            continue
        path = Path(original_root) / binding['path']
        if not path.resolve().is_relative_to(Path(original_root).resolve()):
            raise ValueError('Critical habitat original path escapes its root')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != binding['sha256']:
                raise ValueError('Critical habitat original source checksum mismatch')
        if source == 'dfo_aquatic_critical_habitat':
            source_labels = {'COMMON_E':'common_name', 'POP_E':'population', 'COMMON_F':'common_name_french',
                'POP_F':'population_french', 'SCIENTIFIC':'scientific_name', 'CH_STATUS_E':'habitat_status',
                'TAXON_E':'taxon', 'ECO_TYPE_E':'habitat_type', 'Waterbody':'waterbody', 'SARASTAT_E':'listing_status',
                'COMMENT_E':'source_comment', 'LEAD_REG_E':'lead_region', 'SUP_REG_E':'support_region', 'PROFILE_E':'source_metadata'}
        elif source == ECCC_SOURCE:
            source_labels = {'CommName_E':'common_name', 'Population_E':'population', 'Sub_Species_E':'subspecies',
                'SciName':'scientific_name', 'COSEWIC_ID':'species_registry_id', 'SiteID':'source_site_id',
                'SiteName_E':'habitat_reference_area', 'ProvTerr_E':'province', 'RDoc_Name_E':'recovery_document',
                'RD_Status':'recovery_document_status_code', 'SARA_Status':'listing_status_code',
                'SARA_Agency':'source_agency_code', 'Taxon':'taxon_code', 'MigBird':'migratory_bird_code',
                'Sensitive_E':'source_sensitivity'}
        else:
            source_labels = labels
        columns = pq.read_schema(path).names
        selected = [name for name in source_labels if name in columns]
        for row in pq.read_table(path, columns=['OBJECTID', *selected]).to_pylist():
            identity = source + ':' + str(row['OBJECTID'])
            if identity in identities:
                context[identity] = {label: None if row.get(name) is None else str(row[name])
                                     for name,label in source_labels.items() if name in selected}
                if source == ECCC_SOURCE:
                    context[identity].update(habitat_status='Posted Final recovery document; conditional marine reference',
                        habitat_type='Marine reference area', habitat_conditions=ECCC_CONDITIONS,
                        source_metadata=ECCC_DOCUMENT)
        if identities.difference(context):
            raise ValueError('Critical habitat membership lacks original source attributes')
    metadata['fields'][ASSIGNMENT]['source_record_context'] = context
    gaps = ['USFWS critical habitat is outside the retained NOAA NMFS scope']
    if 'dfo_aquatic_critical_habitat' in metadata.get('original_data', {}):
        gaps.append('DFO source selection is bounded; bounding-box descriptors and some riparian habitat are omitted by the provider; Final/Proposed status remains unresolved')
    else:
        gaps.insert(0, 'Canadian SARA critical habitat has not been acquired')
    if ECCC_SOURCE in metadata.get('original_data', {}):
        gaps.append('ECCC selection includes only eleven public marine murrelet reference areas; conditional biophysical habitat support is not a blanket polygon designation')
    else:
        gaps.append('ECCC marine critical-habitat references have not been acquired')
    gaps.append('Northern Abalone detailed habitat geometry is withheld by the provider and is not inferred')
    metadata.setdefault('coverage', {}).setdefault(GROUP, {})['scope_gaps'] = gaps
    return table
