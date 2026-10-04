"""Command-line interface for independent governance workspaces."""
from __future__ import annotations

import argparse
import importlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Sequence

from .shared.config import DEFAULT_CONFIG_PATH, load_governance_config
from .workspace import initialize_workspace


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, help='Data workspace (default: GOVERNANCE_WORKSPACE or cwd).')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('preflight', help='Read-only source and full catalog readiness inventory.')
    sub = commands.add_parser('export-delivery', help='Project a verified overlay into single-resolution wide tables.')
    sub.add_argument('--matrix', required=True, type=Path)
    sub.add_argument('--output-directory', required=True, type=Path)
    sub.add_argument('--release-id', required=True)
    sub.add_argument('--software-revision', required=True)
    sub = commands.add_parser('publish-generation', help='Verify and atomically publish a prepared local generation.')
    sub.add_argument('--source', required=True, type=Path)
    sub.add_argument('--release-root', required=True, type=Path)
    sub.add_argument('--release-id', required=True)
    sub.add_argument('--scientific-method-version', required=True)
    sub.add_argument('--software-revision', required=True)
    sub = commands.add_parser('activate-generation', help='Select a verified prior local generation for rollback.')
    sub.add_argument('--release-root', required=True, type=Path)
    sub.add_argument('--release-id', required=True)
    sub = commands.add_parser('verify-generation', help='Verify exact immutable generation membership and checksums.')
    sub.add_argument('path', type=Path)
    commands.add_parser('init', help='Copy missing configuration defaults; no downloads.')
    sub = commands.add_parser('export-h3-matrix', help='Derive an explicit H3 context overlay from verified native products.')
    sub.add_argument('--grid', required=True, type=Path)
    sub.add_argument('--output', required=True, type=Path)
    sub.add_argument('--length-crs', required=True)
    sub.add_argument('--config', default=DEFAULT_CONFIG_PATH)
    sub.add_argument('--allow-partial', action='store_true')
    sub.add_argument('--overwrite', action='store_true')
    for name in ('download', 'build'):
        sub = commands.add_parser(name)
        sub.add_argument('collection', help='Configured collection ID; use catalog to list.')
        sub.add_argument('--config', default=DEFAULT_CONFIG_PATH)
        sub.add_argument('--overwrite', action='store_true')
        if name == 'build':
            sub.add_argument('--allow-partial', action='store_true')
    sub = commands.add_parser('inspect', help='Render the consolidated map and map manifest.')
    sub.add_argument('--config', default=DEFAULT_CONFIG_PATH)
    sub.add_argument('--as-of', required=True, type=date.fromisoformat)
    sub.add_argument('--output')
    sub = commands.add_parser('catalog', help='Validate and print the native-geometry catalog.')
    sub.add_argument('--config', default=DEFAULT_CONFIG_PATH)
    sub.add_argument('--verify-artifacts', action='store_true')
    args = parser.parse_args(argv)
    previous = os.environ.get('GOVERNANCE_WORKSPACE')
    if args.workspace is not None:
        os.environ['GOVERNANCE_WORKSPACE'] = str(args.workspace.expanduser().resolve())
    try:
        if args.command == 'preflight':
            from .preflight import preflight
            print(json.dumps(preflight(), indent=2))
        elif args.command == 'export-delivery':
            from .delivery import export_delivery
            for path in export_delivery(args.matrix, args.output_directory, release_id=args.release_id, software_revision=args.software_revision):
                print(path)
        elif args.command == 'publish-generation':
            from .releases import publish_generation
            print(publish_generation(args.source, args.release_root, args.release_id, scientific_method_version=args.scientific_method_version, software_revision=args.software_revision))
        elif args.command == 'activate-generation':
            from .releases import activate_generation
            print(activate_generation(args.release_root, args.release_id))
        elif args.command == 'verify-generation':
            from .releases import verify_generation
            print(json.dumps(verify_generation(args.path), indent=2))
        elif args.command == 'init':
            from ._config.paths import project_root
            for path in initialize_workspace(project_root()):
                print(path)
        elif args.command == 'export-h3-matrix':
            from .h3_matrix import export_h3_matrix
            try:
                print(export_h3_matrix(args.grid, args.output, length_crs=args.length_crs,
                                      config_path=args.config, allow_partial=args.allow_partial,
                                      overwrite=args.overwrite))
            except (ValueError, FileNotFoundError, FileExistsError, ImportError) as error:
                parser.error(str(error))
        elif args.command == 'catalog':
            from .shared.catalog import validate_catalog
            print(json.dumps(validate_catalog(config_path=args.config, verify_artifacts=args.verify_artifacts), indent=2))
        elif args.command == 'inspect':
            from .inspect import inspect
            print(inspect(as_of=args.as_of, config_path=args.config, output_path=args.output))
        else:
            config = load_governance_config(args.config)
            if args.collection not in config.collections:
                parser.error(f'Unknown collection {args.collection!r}; choose from {", ".join(config.collections)}')
            collection = config.collections[args.collection]
            module = importlib.import_module(f'governance.{collection.category}.{args.collection}.{args.command}')
            kwargs = {'overwrite': args.overwrite}
            if args.command == 'build':
                kwargs['allow_partial'] = args.allow_partial
            result = getattr(module, args.command)(args.config, **kwargs)
            if isinstance(result, list):
                for path in result:
                    print(path)
            else:
                print(result)
        return 0
    finally:
        if args.workspace is not None:
            if previous is None:
                os.environ.pop('GOVERNANCE_WORKSPACE', None)
            else:
                os.environ['GOVERNANCE_WORKSPACE'] = previous
