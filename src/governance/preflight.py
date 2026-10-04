"""Read-only inventory of all configured sources and catalog families."""
import yaml
from .shared.acquisition import resolve_source_path
from .shared.artifacts import source_record, load_manifest
from .shared.config import DEFAULT_CONFIG_PATH, load_governance_config


def preflight(config_path=DEFAULT_CONFIG_PATH):
    config = load_governance_config(config_path)
    sources = {name: source_record(source, resolve_source_path(source))
               for name, source in config.sources.items()}
    catalog = yaml.safe_load(config.catalog_path.read_text())
    products = {}
    for name, item in catalog['collections'].items():
        result = {'implementation_status': item['implementation_status'],
                  'readiness': 'unavailable', 'reason': 'No implemented collection pipeline'}
        if name in config.collections:
            collection = config.collections[name]
            result.update(source_ids=list(collection.source_ids),
                          missing_sources=[s for s in collection.source_ids
                                           if sources[s]['runtime_status'] != 'available'])
            try:
                manifest = load_manifest(collection.manifest_path)
                result.update(readiness='research_only', reason='Verified native inventory; no legal-time or model eligibility',
                              rows=manifest['artifact']['rows'], source_completeness=manifest['source_completeness'])
            except (ValueError, FileNotFoundError) as error:
                result['reason'] = str(error)
        products[name] = result
    return {'bounds_wgs84': dict(config.bounds), 'config_hash': config.config_hash,
            'temporal_support': 'Inventory snapshot; not legal effective-time history',
            'sources': sources, 'products': products,
            'all_catalog_products_ready': False}
