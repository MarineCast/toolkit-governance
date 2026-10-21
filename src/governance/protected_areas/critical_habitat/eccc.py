"""Reviewed public marine component of the final 2023 murrelet habitat reference."""
from governance.shared.normalization import base_record, records_frame, clean

SOURCE = 'eccc_marbled_murrelet_marine_critical_habitat'
DOCUMENT = 'https://www.canada.ca/en/environment-climate-change/services/species-risk-public-registry/recovery-strategies/marbled-murrelet-amended-final-2023.html'
MARINE_AREAS = {
    21704:'Desolation Sound', 21707:'Toba Inlet', 21709:'Cortes',
    21710:'Discovery Passage', 21711:'Bute Inlet', 21712:'Sidney',
    21715:'Redonda', 21716:'Halfmoon', 21717:'Queens Reach',
    21718:'Malaspina', 21720:'Savary',
}
CONDITIONS = ('Geographic marine reference areas from the final 2023 amended Marbled Murrelet recovery strategy, '
              'sections 7.1.4-7.1.6 and Table 9. Critical habitat occurs only where the required biophysical '
              'attributes are present; the entire reference polygon is not confirmed habitat. Identification '
              'is partial and addresses adult breeding-period requirements in the Salish Sea and adjacent waters. '
              'Posted Final describes the recovery document, not a blanket current legal-protection determination.')


def normalize_eccc(frame, source):
    rows = []
    for values in frame.itertuples(index=False, name=None):
        row = dict(zip(frame.columns, values))
        identity = clean(row.get('OBJECTID'))
        try:
            oid = int(identity)
        except (TypeError, ValueError) as exc:
            raise ValueError('ECCC murrelet OBJECTID must be a reviewed integer identity') from exc
        if oid not in MARINE_AREAS or clean(row.get('SiteName_E')) != MARINE_AREAS[oid]:
            raise ValueError('ECCC murrelet record is outside the approved marine ID/site roster')
        if clean(row.get('COSEWIC_ID')) != '39' or clean(row.get('SciName')) != 'Brachyramphus marmoratus':
            raise ValueError('ECCC murrelet species identity changed')
        if clean(row.get('RD_Status')) != '1':
            raise ValueError('ECCC murrelet source requires Posted Final recovery-document status')
        if 'Amended Recovery Strategy for the Marbled Murrelet' not in (clean(row.get('RDoc_Name_E')) or ''):
            raise ValueError('ECCC murrelet recovery-document identity changed')
        if row['geometry'] is None or row['geometry'].geom_type not in ('Polygon', 'MultiPolygon'):
            raise ValueError('ECCC murrelet requires provider polygon geometry')
        qualified = f'{SOURCE}:{oid}'
        record = base_record(source, source_feature_id=qualified, governance_feature_id=qualified,
            feature_name='Marbled Murrelet [' + MARINE_AREAS[oid] + ']',
            feature_type='conditional_marine_critical_habitat_reference',
            authority='Environment and Climate Change Canada - Canadian Wildlife Service', jurisdiction='Canada',
            legal_authority='Species at Risk Act; final amended Marbled Murrelet recovery strategy (2023)',
            legal_source_url=DOCUMENT, source_coverage_status='partial_eccc_murrelet_marine_only')
        record.update(REGION=clean(row.get('ProvTerr_E')), AREA_SYSTEM_ID='Canada SARA marine critical habitat reference',
            AREA_CODE=str(oid), AREA_TITLE=MARINE_AREAS[oid], AREA_HIERARCHY_LEVEL='Marine reference area',
            HABITAT_CONDITIONS=CONDITIONS, geometry=row['geometry'])
        for name, value in row.items():
            if name != 'geometry':
                record['ECCC_' + name] = clean(value)
        rows.append(record)
    return records_frame(rows, frame.crs)
