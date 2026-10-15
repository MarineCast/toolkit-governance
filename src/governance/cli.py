"""Build flat governance Parquets from explicit local sources and H3 grids."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from .shared.config import DEFAULT_CONFIG_PATH, load_governance_config
from .workspace import initialize_workspace


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, help='Data workspace (GOVERNANCE_WORKSPACE or cwd by default).')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init', help='Copy missing configuration; acquire no data.')
    commands.add_parser('availability', help='Read source availability.')
    commands.add_parser('preflight', help='Read source readiness; acquire no data.')
    sub = commands.add_parser('catalog', help='Read the configured source/collection catalog.')
    sub.add_argument('--config', default=DEFAULT_CONFIG_PATH)
    sub.add_argument('--verify-artifacts', action='store_true', help='Check retained internal native products, when present.')
    sub = commands.add_parser('download', help='Explicitly acquire one configured collection into the source workspace.')
    sub.add_argument('collection')
    sub.add_argument('--config', default=DEFAULT_CONFIG_PATH)
    sub.add_argument('--overwrite', action='store_true')
    for name in ('build', 'export-data'):
        sub = commands.add_parser(name, help='Write flat metric Parquets, OriginalData, and catalog.json.')
        sub.add_argument('--config', default=DEFAULT_CONFIG_PATH)
        sub.add_argument('--output-directory', required=True, type=Path)
        sub.add_argument('--software-revision')
        sub.add_argument('--overwrite', action='store_true')
        if name == 'build':
            sub.add_argument('--grid', required=True, action='append', type=Path)
            sub.add_argument('--original-data', type=Path, help='Reuse a verified flat data directory offline.')
            sub.add_argument('--length-crs', default='EPSG:32610')
            sub.add_argument('--allow-partial', action='store_true')
            sub.add_argument('--keep-workspace-data', action='store_true',
                             help='Retain disposable source caches and old processed data after a successful build.')
        else:
            sub.add_argument('--matrix', required=True, type=Path)
    sub = commands.add_parser('validate-data', help='Check the flat catalog, checksums, and embedded contracts.')
    sub.add_argument('directory', type=Path)
    sub = commands.add_parser('clean-workspace', help='Remove disposable workspace data after verifying saved outputs and originals.')
    sub.add_argument('directory', type=Path, help='Verified flat governance output to retain.')
    sub.add_argument('--config', default=DEFAULT_CONFIG_PATH)
    sub = commands.add_parser('get', help='Query one layer in memory with bounded acquisition.')
    sub.add_argument('collection')
    sub.add_argument('--bbox', nargs=4, type=float, required=True)
    sub.add_argument('--h3-res', type=int)
    sub.add_argument('--source', action='append')
    sub.add_argument('--cache', type=Path)
    sub.add_argument('--mode', choices=('cache-first', 'refresh', 'offline'), default='cache-first')
    sub.add_argument('--allow-partial', action='store_true')
    sub.add_argument('--include-proposed', action='store_true')
    sub.add_argument('--as-of')
    args = parser.parse_args(argv)
    previous = os.environ.get('GOVERNANCE_WORKSPACE')
    if args.workspace is not None:
        os.environ['GOVERNANCE_WORKSPACE'] = str(args.workspace.expanduser().resolve())
    try:
        if args.command == 'build':
            from .products import build_products
            print(build_products(args.grid, args.output_directory, config_path=args.config,
                  original_data=args.original_data, length_crs=args.length_crs,
                  allow_partial=args.allow_partial, software_revision=args.software_revision, overwrite=args.overwrite,
                  keep_workspace_data=args.keep_workspace_data))
        elif args.command == 'export-data':
            from .products import export_products
            print(export_products(args.matrix, args.output_directory, config_path=args.config,
                  software_revision=args.software_revision, overwrite=args.overwrite))
        elif args.command == 'validate-data':
            from .products import validate_products
            print(json.dumps(validate_products(args.directory), indent=2))
        elif args.command == 'clean-workspace':
            from .products import cleanup_workspace_data
            cleanup_workspace_data(args.directory, config_path=args.config)
        elif args.command == 'download':
            from .shared.pipeline import download_collection
            for path in download_collection(args.collection, args.config, overwrite=args.overwrite):
                print(path)
        elif args.command == 'init':
            from ._config.paths import project_root
            for path in initialize_workspace(project_root()):
                print(path)
        elif args.command == 'availability':
            from .shared.availability import availability_matrix
            print(json.dumps(availability_matrix(load_governance_config()), indent=2))
        elif args.command == 'preflight':
            from .preflight import preflight
            print(json.dumps(preflight(), indent=2))
        elif args.command == 'catalog':
            from .shared.catalog import validate_catalog
            print(json.dumps(validate_catalog(config_path=args.config, verify_artifacts=args.verify_artifacts), indent=2))
        elif args.command == 'get':
            from .query import get_layer
            collection_id = {'fishery_management_areas': 'management_areas', 'vessel_exclusion_zones': 'exclusion_zones'}.get(args.collection.replace('-', '_'), args.collection.replace('-', '_'))
            result = get_layer(collection_id, args.bbox, workspace=args.workspace or os.environ.get('GOVERNANCE_WORKSPACE'),
                make_h3=args.h3_res is not None, h3_res=args.h3_res if args.h3_res is not None else 7,
                sources=args.source, cache=args.cache, mode=args.mode, allow_partial=args.allow_partial,
                include_proposed=args.include_proposed, as_of=args.as_of)
            print(json.dumps({'features': len(result.features), 'h3_cells': None if result.h3 is None else len(result.h3), 'coverage': result.coverage.to_dict('records')}, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, ImportError) as error:
        parser.error(str(error))
    finally:
        if args.workspace is not None:
            if previous is None:
                os.environ.pop('GOVERNANCE_WORKSPACE', None)
            else:
                os.environ['GOVERNANCE_WORKSPACE'] = previous
