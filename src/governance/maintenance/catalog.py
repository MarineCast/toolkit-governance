"""Generate the native-geometry governance feature catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from governance._config.paths import project_root
from governance.shared.config import load_governance_config

CATEGORY_COLLECTIONS = {
    "protected_areas": (
        "marine_protected_areas",
        "critical_habitat",
        "national_marine_sanctuaries",
        "wildlife_refuges",
        "conservation_designations",
    ),
    "jurisdiction": (
        "international_boundaries",
        "federal_waters",
        "state_provincial_waters",
        "county_regional_boundaries",
        "tribal_first_nations_areas",
    ),
    "fisheries_management": (
        "management_areas",
        "seasonal_closures",
        "gear_restrictions",
        "harvest_regulations",
        "salmon_management_zones",
    ),
    "vessel_management": (
        "shipping_lanes",
        "traffic_separation_schemes",
        "exclusion_zones",
        "speed_restriction_zones",
        "whale_approach_regulation_zones",
    ),
    "administrative_context": (
        "ports",
        "coast_guard_sectors",
        "management_regions",
        "reporting_areas",
    ),
}

CORE_FEATURES = (
    ("GOVERNANCE_FEATURE_ID", "support", "derived", "identifier"),
    ("SOURCE_DATASET_ID", "provenance", "observed", "identifier"),
    ("SOURCE_FEATURE_ID", "provenance", "observed", "identifier"),
    ("GEOMETRY_PART_ID", "support", "derived", "identifier"),
    ("FEATURE_NAME", "state", "observed", "text"),
    ("FEATURE_TYPE", "state", "observed", "category"),
    ("AUTHORITY", "provenance", "observed", "text"),
    ("JURISDICTION", "state", "observed", "category"),
    ("LEGAL_BINDING_STATUS", "evidence", "derived", "category"),
    ("LEGAL_AUTHORITY", "evidence", "observed", "citation"),
    ("LEGAL_SOURCE_URL", "provenance", "observed", "url"),
    ("EFFECTIVE_START", "support", "observed", "date"),
    ("EFFECTIVE_END", "support", "observed", "date"),
    ("SYSTEM_LEARNED_AT", "provenance", "derived", "datetime"),
    ("SOURCE_VINTAGE", "provenance", "observed", "date_or_unknown"),
    ("SOURCE_COVERAGE_STATUS", "coverage", "derived", "category"),
    ("MEASUREMENT_STATUS", "provenance", "derived", "category"),
    ("MODEL_ELIGIBLE", "qc", "derived", "boolean"),
    ("QC_STATUS", "qc", "derived", "category"),
    ("QC_REASON", "qc", "derived", "text"),
    ("CLIPPED_TO_FULL_AREA", "qc", "derived", "boolean"),
    ("SOURCE_MIN_LON", "provenance", "derived", "degrees_east"),
    ("SOURCE_MIN_LAT", "provenance", "derived", "degrees_north"),
    ("SOURCE_MAX_LON", "provenance", "derived", "degrees_east"),
    ("SOURCE_MAX_LAT", "provenance", "derived", "degrees_north"),
    ("RETAINED_GEOMETRY_TYPE", "qc", "derived", "category"),
    ("RETAINED_MEASURE_FRACTION", "qc", "derived", "fraction"),
    ("geometry", "support", "observed", "native_geometry"),
)

EXTRA_FEATURES = {
    "shipping_lanes": (
        ("ROUTING_ROLE", "state", "derived", "category"),
        ("ROUTING_SOURCE_TYPE", "state", "observed", "category"),
        ("ROUTING_IDENTITY_METHOD", "provenance", "derived", "text"),
    ),
    "traffic_separation_schemes": (
        ("ROUTING_ROLE", "state", "derived", "category"),
        ("ROUTING_SOURCE_TYPE", "state", "observed", "category"),
        ("ROUTING_IDENTITY_METHOD", "provenance", "derived", "text"),
    ),
    "wildlife_refuges": (
        ("REFUGE_SYSTEM_TYPE", "state", "observed", "category"),
    ),
    "marine_protected_areas": (
        ("SOURCE_RECORD_ID", "provenance", "observed", "identifier"),
        ("DESIGNATION_ID", "support", "derived", "identifier"),
        ("AUTHORITY_ID", "support", "derived", "identifier"),
        ("COUNTRY_CODE", "state", "observed", "iso_3166_1_alpha_3"),
        ("DESIGNATION_STATUS", "state", "derived", "category"),
        ("EFFECTIVE_STATUS", "state", "derived", "category"),
        ("MPA_PROGRAM", "state", "observed", "category"),
        ("MAP_GROUP", "support", "derived", "category"),
        ("MANAGEMENT_AUTHORITY", "provenance", "observed", "text"),
        ("AUTHORITY_SOURCE_URL", "provenance", "observed", "url"),
        ("GOVERNING_RULE_CITATION", "evidence", "observed", "citation_or_null"),
        ("GOVERNING_RULE_STATUS", "qc", "derived", "category"),
        ("INVENTORY_GOVERNMENT_LEVEL", "state", "observed", "category_or_null"),
        ("SOURCE_SUBDIVISION_CODE", "state", "observed", "postal_code_or_null"),
        ("SOURCE_DESIGNATION_TYPE", "state", "observed", "category_or_null"),
        ("SOURCE_ZONE_NAME", "state", "observed", "text_or_null"),
        ("PROTECTION_PURPOSE", "evidence", "observed", "text_or_null"),
        ("PROTECTION_PURPOSE_STATUS", "qc", "derived", "category"),
        ("PRIMARY_CONSERVATION_FOCUS", "evidence", "observed", "text_or_null"),
        ("CONSERVATION_FOCUS", "evidence", "observed", "text_or_null"),
        ("PROTECTION_FOCUS", "evidence", "observed", "text_or_null"),
        ("PROTECTION_LEVEL_REFERENCE", "evidence", "observed", "category_or_null"),
        ("NATIONAL_SYSTEM_STATUS", "state", "observed", "category_or_null"),
        ("MANAGEMENT_PLAN_STATUS", "state", "observed", "category_or_null"),
        ("PERMANENCE", "state", "observed", "category_or_null"),
        ("CONSTANCY", "state", "observed", "category_or_null"),
        (
            "FISHING_RESTRICTIONS_REFERENCE",
            "evidence",
            "observed",
            "category_or_null",
        ),
        (
            "VESSEL_RESTRICTIONS_REFERENCE",
            "evidence",
            "observed",
            "category_or_null",
        ),
        (
            "ANCHORING_RESTRICTIONS_REFERENCE",
            "evidence",
            "observed",
            "category_or_null",
        ),
        ("ALLOWED_ACTIVITIES", "evidence", "unavailable", "text_or_null"),
        ("PROHIBITED_ACTIVITIES", "evidence", "unavailable", "text_or_null"),
        ("ACTIVITY_METADATA_STATUS", "qc", "derived", "category"),
        ("IUCN_REPORTING_CLASS", "evidence", "unavailable", "category_or_null"),
        ("IUCN_CLASS_STATUS", "qc", "derived", "category"),
        ("SOURCE_AREA_KM2", "provenance", "observed", "square_kilometers_or_null"),
        ("SOURCE_GEOMETRY_STATUS", "qc", "derived", "category"),
        ("MPA_QC_REASON", "qc", "derived", "text"),
    ),
    "national_marine_sanctuaries": (
        ("SANCTUARY_ID", "support", "observed", "identifier"),
        ("AUTHORITY_ID", "support", "derived", "identifier"),
        ("COUNTRY_CODE", "state", "observed", "iso_3166_1_alpha_3"),
        ("SUBDIVISION_CODE", "state", "observed", "iso_3166_2"),
        ("DESIGNATION_TYPE", "state", "derived", "category"),
        ("DESIGNATION_STATUS", "state", "derived", "category"),
        ("EFFECTIVE_STATUS", "state", "derived", "category"),
        ("CFR_PART", "evidence", "observed", "citation"),
        ("CFR_SUBPART", "evidence", "observed", "identifier"),
        ("CFR_BOUNDARY_SECTION", "evidence", "observed", "citation"),
        ("DESIGNATION_FEDERAL_REGISTER", "evidence", "observed", "citation"),
        ("BOUNDARY_AMENDMENT_SUMMARY", "evidence", "observed", "text"),
        ("AMENDMENT_HISTORY_STATUS", "qc", "derived", "category"),
        ("LEGAL_BOUNDARY_STATUS", "qc", "derived", "category"),
        ("SOURCE_GEOMETRY_STATUS", "qc", "derived", "category"),
        ("SOURCE_POLYGON_NAME", "provenance", "observed", "text_or_null"),
        ("SOURCE_DATUM", "provenance", "observed", "crs_or_datum"),
        ("SOURCE_AREA_SQMI", "provenance", "observed", "square_miles_or_null"),
        (
            "SANCTUARY_GEOMETRY_AREA_SQMI",
            "qc",
            "derived",
            "square_miles",
        ),
        ("CFR_APPROX_AREA_SQMI", "evidence", "observed", "square_miles"),
        ("CFR_AREA_DIFFERENCE_PCT", "qc", "derived", "percent"),
        ("AREA_QC_STATUS", "qc", "derived", "category"),
        ("SANCTUARY_QC_REASON", "qc", "derived", "text"),
    ),
    "international_boundaries": (
        ("BOUNDARY_ID", "provenance", "observed", "identifier"),
        ("REGION", "state", "observed", "text"),
        ("COUNTRY_CODE", "state", "observed", "iso_3166_1_alpha_3_or_null"),
        ("SECTION_NUMBER", "provenance", "observed", "identifier_or_null"),
        ("SECTION_NAME", "state", "observed", "text_or_null"),
        ("PUBLICATION_DATE", "provenance", "observed", "date"),
        ("APPROVAL_DATE", "provenance", "observed", "date"),
        ("UNILATERAL_CLAIM", "evidence", "observed", "source_value"),
        ("SOURCE_ROLE", "provenance", "derived", "category"),
        ("SOURCE_SCALE", "provenance", "observed", "map_scale_or_null"),
        ("SOURCE_SCALE_DENOMINATOR", "provenance", "derived", "ratio_denominator"),
        ("SOURCE_POSITIONAL_ACCURACY_M", "provenance", "observed", "meters_or_null"),
        ("SOURCE_PRECISION_BASIS", "provenance", "derived", "text"),
        ("SOURCE_LEGAL_STATUS", "evidence", "derived", "category"),
        ("CANADIAN_SOURCE_AGENCY", "provenance", "observed", "text_or_null"),
        ("CANADIAN_SOURCE_STATUS", "provenance", "observed", "source_value_or_null"),
        ("CANADIAN_SOURCE_DESCRIPTION", "evidence", "observed", "text_or_null"),
        ("RECONCILIATION_STATUS", "qc", "derived", "category"),
        ("COUNTRY_ALLOCATION_MATCH_FRACTION", "qc", "derived", "fraction_or_null"),
        ("COUNTRY_ALLOCATION_CHECK_SOURCE", "provenance", "derived", "identifier_or_null"),
        ("BOUNDARY_QC_REASON", "qc", "derived", "text"),
    ),
    "federal_waters": (
        ("SOURCE_RECORD_ID", "provenance", "observed", "identifier"),
        ("REGION", "state", "observed", "text"),
        ("COUNTRY_CODE", "state", "observed", "iso_3166_1_alpha_3"),
        ("ZONE_TYPE", "state", "observed", "category"),
        ("ZONE_LIMIT_NM", "evidence", "derived", "nautical_miles"),
        ("GEOMETRY_ROLE", "state", "derived", "category"),
        ("SOURCE_LAYER_NAME", "provenance", "derived", "text"),
        ("SOURCE_RULE_ID", "provenance", "observed", "identifier_or_null"),
        ("SOURCE_RULE_LABEL", "provenance", "observed", "text_or_null"),
        ("PUBLICATION_DATE", "provenance", "observed", "date"),
        ("APPROVAL_DATE", "provenance", "observed", "date"),
        (
            "SOURCE_POSITIONAL_ACCURACY_M",
            "provenance",
            "observed",
            "meters_or_null",
        ),
        ("SOURCE_AGENCY", "provenance", "observed", "text"),
        ("SOURCE_STATUS", "provenance", "observed", "source_value_or_null"),
        ("ZONE_QC_REASON", "qc", "derived", "text"),
    ),
    "state_provincial_waters": (
        ("BOUNDARY_APPROVAL_DATE", "provenance", "observed", "date_or_unknown"),
        ("BLOCK_NUMBER", "provenance", "observed", "identifier"),
        ("PROVINCE_WATER_EQUIVALENT", "coverage", "unavailable", "category"),
    ),
    "management_areas": (
        ("MANAGEMENT_SYSTEM", "state", "observed", "category"),
        ("AREA_CODE", "support", "observed", "identifier"),
        ("AREA_TITLE", "state", "observed", "text"),
        ("SECTOR_APPLICABILITY", "evidence", "observed", "text"),
        ("GEOMETRY_VERSION", "provenance", "observed", "date_or_unknown"),
    ),
}


def _feature(values: tuple[str, str, str, str]) -> dict[str, Any]:
    name, role, measurement_status, unit = values
    return {
        "name": name,
        "role": role,
        "measurement_status": measurement_status,
        "model_eligible": False,
        "unit": unit,
    }


def build_catalog() -> dict[str, Any]:
    config = load_governance_config()
    collections: dict[str, Any] = {}
    for category, collection_ids in CATEGORY_COLLECTIONS.items():
        for collection_id in collection_ids:
            configured = config.collections.get(collection_id)
            if configured is None:
                collections[collection_id] = {
                    "category": category,
                    "display_name": collection_id.replace("_", " ").title(),
                    "implementation_status": "planned",
                    "artifact": None,
                    "manifest": None,
                    "map_layer": False,
                    "model_policy": "ineligible_not_implemented",
                    "features": [],
                }
                continue
            feature_values = [*CORE_FEATURES, *EXTRA_FEATURES.get(collection_id, ())]
            collections[collection_id] = {
                "category": category,
                "display_name": configured.display_name,
                "implementation_status": configured.implementation_status,
                "artifact": str(configured.artifact_path.relative_to(project_root())),
                "manifest": str(configured.manifest_path.relative_to(project_root())),
                "map_layer": True,
                "model_policy": "ineligible_pending_temporal_leakage_review",
                "features": [_feature(values) for values in feature_values],
            }
    return {
        "schema_version": 1,
        "generated_by": "governance.maintenance.catalog",
        "area": "full_area",
        "canonical_storage": "native_geometry",
        "h3_products": False,
        "measurement_statuses": [
            "observed",
            "derived",
            "estimated",
            "fallback",
            "unavailable",
        ],
        "roles": ["predictor", "state", "evidence", "coverage", "provenance", "support", "qc"],
        "default_model_policy": {},
        "collections": collections,
    }


def main() -> int:
    path = project_root() / "config/data/governance/feature_catalog.yaml"
    path.write_text(yaml.safe_dump(build_catalog(), sort_keys=False), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
