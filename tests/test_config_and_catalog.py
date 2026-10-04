from __future__ import annotations

from governance.maintenance.catalog import build_catalog

import yaml

from governance._config.paths import project_root
from governance.shared.catalog import validate_catalog
from governance.shared.config import load_governance_config


def test_governance_config_uses_shared_full_area_without_h3_products() -> None:
    config = load_governance_config()
    assert config.area_name == "full_area"
    assert config.bbox_tuple == (-180.0, 32.0, -109.0, 72.0)
    assert set(config.collections) == {
        "marine_protected_areas",
        "national_marine_sanctuaries",
        "international_boundaries",
        "federal_waters",
        "state_provincial_waters",
        "management_areas",
    }
    for collection in config.collections.values():
        assert "H3" not in str(collection.artifact_path).upper()
    for source in config.sources.values():
        assert set(source.coverage) == set(config.coverage_regions)

    federal = config.collections["federal_waters"]
    assert federal.normalization_profile == ("reconciled_us_canada_federal_maritime_zone_limits")
    assert federal.source_ids == (
        "noaa_us_territorial_sea_dynamic",
        "noaa_us_contiguous_zone_dynamic",
        "noaa_us_eez_dynamic",
        "nrcan_canadian_geopolitical_boundaries_lines",
    )
    assert "noaa_us_maritime_limits" not in federal.source_ids

    mpa = config.collections["marine_protected_areas"]
    assert mpa.source_ids == (
        "noaa_mpa_inventory_2023",
        "dfo_oceans_act_marine_protected_areas",
        "dfo_oceans_act_areas_of_interest",
    )
    noaa_mpa = config.sources["noaa_mpa_inventory_2023"]
    assert noaa_mpa.acquisition_type == "direct_archive"
    assert noaa_mpa.archive_layer == "NOAA_MPA_Inventory"

    sanctuaries = config.collections["national_marine_sanctuaries"]
    assert sanctuaries.implementation_status == "implemented"
    assert sanctuaries.source_ids == (
        "noaa_onms_channel_islands_boundary",
        "noaa_onms_chumash_heritage_boundary",
        "noaa_onms_cordell_bank_boundary",
        "noaa_onms_greater_farallones_boundary",
        "noaa_onms_monterey_bay_boundary",
        "noaa_onms_olympic_coast_boundary",
    )
    for source_id in sanctuaries.source_ids:
        source = config.sources[source_id]
        assert source.acquisition_type == "direct_archive"
        assert source.expected_sha256 is not None
        assert source.archive_member is not None


def test_governance_root_is_public_surface_and_shared_code_is_packaged() -> None:
    governance_root = project_root() / "src/governance"
    assert {path.name for path in governance_root.glob("*.py")} == {
        "__init__.py",
        "inspect.py",
        "__main__.py",
        "cli.py",
        "workspace.py",
        "h3_matrix.py",
        "delivery.py",
        "preflight.py",
        "releases.py",
    }
    assert {
        "acquisition.py",
        "artifacts.py",
        "catalog.py",
        "config.py",
        "coverage.py",
        "layers.py",
        "normalization.py",
        "pipeline.py",
        "schema.py",
        "spatial.py",
    }.issubset({path.name for path in (governance_root / "shared").glob("*.py")})


def test_governance_catalog_is_generated_and_model_safe() -> None:
    root = project_root()
    generated = build_catalog()
    catalog = yaml.safe_load(
        (root / "config/data/governance/feature_catalog.yaml").read_text(encoding="utf-8")
    )
    assert catalog == generated
    assert len(catalog["collections"]) == 24
    assert sum(value["map_layer"] for value in catalog["collections"].values()) == 6
    assert catalog["canonical_storage"] == "native_geometry"
    assert catalog["h3_products"] is False
    for collection in catalog["collections"].values():
        assert all(feature["model_eligible"] is False for feature in collection["features"])
    assert validate_catalog(verify_artifacts=False) == catalog
