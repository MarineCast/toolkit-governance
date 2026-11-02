"""Prepare bounded real-data replay grids and compare all delivered values.

python scripts/review_replay.py prepare RETAINED_GOVERNANCE REVIEW_DIRECTORY
python scripts/review_replay.py compare RETAINED_GOVERNANCE REVIEW_DIRECTORY
The build itself uses the documented installed governance CLI. No acquisition.
"""
import argparse
import hashlib
import json
from pathlib import Path
import h3
import pyarrow as pa
import pyarrow.parquet as pq


def digest(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def prepare(source, review):
    review.mkdir(parents=True, exist_ok=True)
    for resolution in (6, 8):
        table = pq.read_table(source / f'governance-r{resolution}-static.parquet')
        rows = table.to_pylist()
        selected = set()
        for column in table.column_names[1:]:
            for predicate in (lambda v: v is None,
                              lambda v: v == [] or v == 0,
                              lambda v: v is not None and v != [] and v != 0):
                selected.update([r['h3_index'] for r in rows if predicate(r[column])][:2])
        # Nearest *delivered* cells to fixed regional reference locations, not
        # asserted observation sites or a representative random sample.
        for latitude, longitude in ((48.5,-123), (47.6,-122.4), (58.3,-134.5),
                                    (37.8,-122.5), (45,-124), (50,-127)):
            nearest = sorted(rows, key=lambda r: sum((a-b)**2 for a,b in
                zip(h3.cell_to_latlng(r['h3_index']), (latitude,longitude))))[:3]
            selected.update(r['h3_index'] for r in nearest)
        pq.write_table(pa.table({'h3_index': sorted(selected)}), review / f'grid-r{resolution}.parquet')
        print(f'R{resolution}: {len(selected)} replay cells')


def compare(source, review):
    from governance.products import validate_products
    result = {'validation': validate_products(review / 'rebuilt'), 'resolutions': {}}
    for resolution in (6, 8):
        filename = f'governance-r{resolution}-static.parquet'
        original = pq.read_table(source / filename)
        actual = pq.read_table(review / 'rebuilt' / filename)
        expected = {r['h3_index']:r for r in original.to_pylist()}
        keys = pq.read_table(review / f'grid-r{resolution}.parquet')['h3_index'].to_pylist()
        rows = actual.to_pylist()
        actual_meta = json.loads(actual.schema.metadata[b'governance'])
        original_meta = json.loads(original.schema.metadata[b'governance'])
        fields = {}
        for column in actual.column_names[1:]:
            values = [r[column] for r in rows]
            numeric = [v for v in values if type(v) in (int,float)]
            differences = [{'h3_index':r['h3_index'], 'actual':r[column],
                            'expected':expected.get(r['h3_index'], {}).get(column)}
                           for r in rows if r[column] != expected.get(r['h3_index'], {}).get(column)]
            fields[column] = {'nulls_actual':sum(v is None for v in values),
                              'nulls_expected':sum(expected[k][column] is None for k in keys),
                              'min':min(numeric,default=None), 'max':max(numeric,default=None),
                              'differences':differences}
        result['resolutions'][str(resolution)] = {
            'rows':len(rows), 'keys_equal':sorted(keys)==sorted(r['h3_index'] for r in rows),
            'columns_equal':actual.schema.remove_metadata()==original.schema.remove_metadata(),
            'temporal_equal':actual_meta['temporal']==original_meta['temporal'],
            'spatial_semantics_equal':all(actual_meta['spatial'][k]==original_meta['spatial'][k]
                                        for k in ('support','h3_resolution','area_crs','length_crs')),
            'input_sha256':digest(source/filename), 'output_sha256':digest(review/'rebuilt'/filename),
            'grid_sha256':digest(review/f'grid-r{resolution}.parquet'), 'fields':fields}
    (review/'comparison.json').write_text(json.dumps(result,indent=2))
    success=all(all(r[k] for k in ('keys_equal','columns_equal','temporal_equal','spatial_semantics_equal'))
                and not any(f['differences'] for f in r['fields'].values()) for r in result['resolutions'].values())
    print('Exact sampled value parity:',success)
    return 0 if success else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','compare'])
    parser.add_argument('source',type=Path)
    parser.add_argument('review',type=Path)
    args=parser.parse_args()
    if args.action=='prepare':prepare(args.source,args.review);return 0
    return compare(args.source,args.review)

if __name__=='__main__': raise SystemExit(main())
