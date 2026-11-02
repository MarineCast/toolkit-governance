"""Render all 20 delivered fields without downloads or inferred legal boundaries.

Usage: python scripts/example_maps.py DATA/Governance OUTPUT_DIRECTORY
Requires installed toolkit-governance and matplotlib. Output is local research
illustration; source-specific redistribution restrictions still apply.
"""
from pathlib import Path
import argparse
import hashlib
import json
import textwrap
import h3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import numpy as np
import pyarrow.parquet as pq
from pyproj import Transformer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    path = args.data / 'governance-r6-static.parquet'
    table = pq.read_table(path)
    metadata = json.loads(table.schema.metadata[b'governance'])
    # Center selection is intentional: do not pretend these are clipped cells.
    rows = [r for r in table.to_pylist() if
            47 <= h3.cell_to_latlng(r['h3_index'])[0] <= 50 and
            -125 <= h3.cell_to_latlng(r['h3_index'])[1] <= -122]
    if not rows:
        raise ValueError('No R6 cells in the fixed Salish Sea example window')
    transform = Transformer.from_crs(4326, 32610, always_xy=True)
    polygons = [np.array([transform.transform(lon, lat) for lat, lon in
                          h3.cell_to_boundary(r['h3_index'])]) / 1000 for r in rows]
    args.output.mkdir(parents=True, exist_ok=True)
    groups = [
        ('jurisdictions', ['country_membership', 'state_province_membership', 'county_district_count', 'has_international_boundary']),
        ('protection', ['critical_habitat_count', 'conservation_area_count', 'conservation_area_coverage_fraction', 'has_mapped_tribal_area']),
        ('management', ['fisheries_management_area_count', 'exclusion_zone_count', 'has_routing_reference', 'coast_guard_membership']),
        ('memberships', ['county_district_membership', 'critical_habitat_membership', 'fisheries_management_area_membership', 'conservation_area_membership']),
        ('other-memberships', ['mapped_tribal_area_membership', 'exclusion_zone_membership', 'speed_restriction_zone_membership', 'vessel_routing_membership']),
    ]
    palette = ['#2378a3', '#dbac37', '#bf6387', '#738649', '#da7843']
    evidence = {'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'rows': len(rows), 'resolution': 6, 'bbox_center_wgs84': [-125,47,-122,50],
                'projection':'EPSG:32610', 'review_date':'2026-10-29',
                'temporal':metadata['temporal'], 'fields':{}}
    for name, fields in groups:
        fig, axes = plt.subplots(2, 2, figsize=(12, 14))
        fig.subplots_adjust(left=.08, right=.95, bottom=.22, top=.91, wspace=.38, hspace=.48)
        fig.suptitle('Governance | Salish Sea · ' + name.replace('-', ' ').title(), fontsize=19, x=.08, ha='left')
        for ax, field in zip(axes.flat, fields):
            values = [r[field] for r in rows]
            missing = [v is None for v in values]
            ax.set_title(textwrap.fill(field.replace('_', ' ').title(), 32), fontsize=12, loc='left', pad=12)
            if field in ('country_membership', 'state_province_membership'):
                categories = sorted({tuple(v) for v in values if v})
                colors = {v:palette[i % len(palette)] for i,v in enumerate(categories)}
                fills = ['#c5c9ce' if v is None else '#ffffff' if not v else colors[tuple(v)] for v in values]
                labels = [Patch(facecolor=colors[v], label=' + '.join(v)) for v in categories]
                unit = 'Recorded geographic assignment; + means overlap'
            elif field.endswith('_membership') or field.startswith('has_'):
                def cls(v):
                    if v is None: return 0
                    if isinstance(v, list): return 1 if len(v)==0 else 2 if len(v)==1 else 3
                    return 2 if v else 1
                color = ['#c5c9ce','#ffffff','#2378a3','#dbac37']
                fills = [color[cls(v)] for v in values]
                labels = [Patch(facecolor=color[2], label='1 recorded name' if field.endswith('_membership') else 'True')]
                if field.endswith('_membership'): labels.append(Patch(facecolor=color[3], label='2+ names (overlap)'))
                unit = 'Name-list multiplicity' if field.endswith('_membership') else 'Nullable recorded intersection'
            else:
                fraction=field.endswith('_fraction')
                numeric=[v for v in values if v is not None]
                norm=Normalize(0,100 if fraction else max(numeric,default=1) or 1)
                cmap=plt.get_cmap('Blues')
                fills=['#c5c9ce' if v is None else cmap(norm(v * 100 if fraction else v)) for v in values]
                labels=[]
                bar=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=ax,shrink=.7,pad=.025)
                bar.set_label('Full H3 cell covered (%)' if fraction else 'Recorded features',fontsize=9)
                unit='Full-cell union fraction' if fraction else 'Recorded feature count'
            ax.add_collection(PolyCollection(polygons,facecolors=fills,edgecolors='#66717c',linewidths=.12))
            ax.autoscale_view(); ax.set_aspect('equal')
            ax.set_xlabel('UTM 10N easting (km)',fontsize=9); ax.set_ylabel('Northing (km)',fontsize=9)
            ax.tick_params(labelsize=8)
            labels += [Patch(facecolor='#c5c9ce',label='Null / unknown')]
            if field.endswith('_membership') or field.startswith('has_'):
                labels += [Patch(facecolor='white',edgecolor='#66717c',label='Empty list / false')]
            ax.legend(handles=labels,fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.18),ncol=2,frameon=False)
            evidence['fields'][field]={'nulls':sum(missing),'unit':unit,'definition_location':'Parquet governance metadata fields/' + field}
        fig.text(.08,.025,'Source: MarineCast retained Governance delivery (provider bindings in catalog.json / OriginalData).\nStatic recorded inventory; review 2026-10-29 is not a legal effective date. Full R6 cells; no basemap.\nBlank outside cells = outside supplied grid; gray = unknown. Geographic support is not legal jurisdiction.\nLocal research illustration only; source-specific rights apply. See reproduction review for attribution.',fontsize=9,linespacing=1.5)
        fig.savefig(args.output/f'{name}.png',dpi=130,facecolor='white');plt.close(fig)
    (args.output/'map-evidence.json').write_text(json.dumps(evidence,indent=2))

if __name__ == '__main__': main()
