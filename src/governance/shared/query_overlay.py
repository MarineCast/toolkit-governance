"""Exact, source-grouped generic H3 metrics with explicit relational memberships."""
from __future__ import annotations
import pandas as pd
from shapely.ops import unary_union
from .spatial import _measure, _dimension_family

MEMBERSHIP_FIELDS = ('H3_INDEX', 'H3_RESOLUTION', 'SOURCE_DATASET_ID', 'GOVERNANCE_FEATURE_ID', 'SOURCE_FEATURE_ID', 'GEOMETRY_PART_ID', 'GEOMETRY_FAMILY', 'INTERSECTION_AREA_M2', 'INTERSECTION_LENGTH_M', 'POINT_COUNT')


def overlay(grid, native, *, source_ids, coverage, max_memberships):
    if type(max_memberships) is not int or max_memberships <= 0:
        raise ValueError('max_memberships must be a positive integer')
    metrics, relations = [], []
    availability = {row['source_id']: row['status'] for row in coverage}
    for _, cell in grid.iterrows():
        row = {'H3_INDEX': cell.H3_INDEX, 'H3_RESOLUTION': int(cell.H3_RESOLUTION), 'MODEL_ELIGIBLE': False}
        indices = native.sindex.query(cell.geometry, predicate='intersects') if not native.empty else []
        hits = {}
        for index in indices:
            feature = native.iloc[index]
            intersection = cell.geometry.intersection(feature.geometry)
            family = _dimension_family(feature.geometry)
            measure = _measure(intersection)
            if intersection.is_empty or (family != 'point' and measure <= 0) or _dimension_family(intersection) != family:
                continue
            hits.setdefault(feature.SOURCE_DATASET_ID, []).append((feature, intersection, family))
            relations.append(dict(zip(MEMBERSHIP_FIELDS, (cell.H3_INDEX, int(cell.H3_RESOLUTION), feature.SOURCE_DATASET_ID, feature.GOVERNANCE_FEATURE_ID, feature.SOURCE_FEATURE_ID, feature.GEOMETRY_PART_ID, family, measure if family == 'polygon' else None, measure if family == 'line' else None, int(measure) if family == 'point' else None))))
            if len(relations) > max_memberships:
                raise ValueError('Cell-to-part membership budget exceeded; reduce query scope')
        # Metrics stay per provider source, never pool incompatible fisheries/routing systems.
        for source in source_ids:
            groups = [('designated', [hit for hit in hits.get(source, []) if hit[0].get('DESIGNATION_STATUS') != 'area_of_interest'])]
            if any(hit[0].get('DESIGNATION_STATUS') == 'area_of_interest' for hit in hits.get(source, [])) or source == 'dfo_oceans_act_areas_of_interest':
                groups.append(('proposed', [hit for hit in hits.get(source, []) if hit[0].get('DESIGNATION_STATUS') == 'area_of_interest']))
            for group, selected in groups:
                prefix = source + ('__proposed' if group == 'proposed' else '') + '__'
                polygons = [geometry for _, geometry, family in selected if family == 'polygon']
                lines = [geometry for _, geometry, family in selected if family == 'line']
                points = [geometry for _, geometry, family in selected if family == 'point']
                row[prefix+'feature_count'] = len({feature.GOVERNANCE_FEATURE_ID for feature, _, _ in selected}) if selected else None
                row[prefix+'source_record_count'] = len({feature.SOURCE_FEATURE_ID for feature, _, _ in selected}) if selected else None
                row[prefix+'part_count'] = len(selected) if selected else None
                if 'DESIGNATION_ID' in native:
                    row[prefix+'designation_count'] = len({feature.DESIGNATION_ID for feature, _, _ in selected if pd.notna(feature.DESIGNATION_ID)}) if selected else None
                row[prefix+'polygon_coverage_full_cell_fraction'] = min(1., _measure(unary_union(polygons))/_measure(cell.geometry)) if polygons else None
                row[prefix+'line_union_length_m'] = _measure(unary_union(lines)) if lines else None
                row[prefix+'point_count'] = int(_measure(unary_union(points))) if points else None
                row[prefix+'status'] = 'partial' if selected else 'unknown' if availability.get(source) in {'available', 'empty'} else 'unavailable'
        metrics.append(row)
    table = pd.DataFrame(metrics) if metrics else pd.DataFrame({'H3_INDEX': pd.Series(dtype='str'), 'H3_RESOLUTION': pd.Series(dtype='int64'), 'MODEL_ELIGIBLE': pd.Series(dtype='bool')})
    return table, pd.DataFrame(relations, columns=MEMBERSHIP_FIELDS)
