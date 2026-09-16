"""Publish normalized sanctuary authority records and collection QC metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from governance.shared.artifacts import (
    atomic_write_json,
    sha256_file,
)
from governance.shared.config import load_governance_config
from governance.shared.schema import validate_governance_geometry

EXPECTED_SANCTUARY_IDS = {"CINMS", "CHNMS", "CBNMS", "GFNMS", "MBNMS", "OCNMS"}


def authority_records(frame: gpd.GeoDataFrame) -> list[dict[str, Any]]:
    """Return one legal-authority record per sanctuary, separate from geometry parts."""

    fields = (
        "GOVERNANCE_FEATURE_ID",
        "SANCTUARY_ID",
        "FEATURE_NAME",
        "AUTHORITY_ID",
        "AUTHORITY",
        "COUNTRY_CODE",
        "SUBDIVISION_CODE",
        "DESIGNATION_STATUS",
        "EFFECTIVE_START",
        "EFFECTIVE_END",
        "CFR_PART",
        "CFR_SUBPART",
        "CFR_BOUNDARY_SECTION",
        "DESIGNATION_FEDERAL_REGISTER",
        "BOUNDARY_AMENDMENT_SUMMARY",
        "AMENDMENT_HISTORY_STATUS",
        "LEGAL_AUTHORITY",
        "LEGAL_SOURCE_URL",
        "LEGAL_BOUNDARY_STATUS",
        "SOURCE_GEOMETRY_STATUS",
        "SOURCE_DATASET_ID",
        "SOURCE_VINTAGE",
        "SOURCE_COVERAGE_STATUS",
        "MODEL_ELIGIBLE",
    )
    records = frame.drop_duplicates("SANCTUARY_ID").sort_values("SANCTUARY_ID")
    return [
        {
            field: (None if value is None or pd.isna(value) else value)
            for field, value in row.items()
        }
        for row in records.loc[:, fields].to_dict(orient="records")
    ]


def publish_sanctuary_products(
    artifact_path: str | Path,
    config_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Verify the six-site roster and publish legal records without flattening parts."""

    artifact_path = Path(artifact_path)
    frame = gpd.read_parquet(artifact_path)
    required = (
        "SANCTUARY_ID",
        "AUTHORITY_ID",
        "COUNTRY_CODE",
        "SUBDIVISION_CODE",
        "DESIGNATION_STATUS",
        "CFR_SUBPART",
        "CFR_BOUNDARY_SECTION",
        "LEGAL_BOUNDARY_STATUS",
        "SOURCE_GEOMETRY_STATUS",
        "AREA_QC_STATUS",
        "SANCTUARY_QC_REASON",
    )
    validate_governance_geometry(frame, required_extra_fields=required)
    sanctuary_ids = set(frame["SANCTUARY_ID"].dropna().astype(str))
    if sanctuary_ids != EXPECTED_SANCTUARY_IDS:
        raise ValueError(
            "NOAA West Coast sanctuary roster mismatch: "
            f"missing={sorted(EXPECTED_SANCTUARY_IDS.difference(sanctuary_ids))}, "
            f"extra={sorted(sanctuary_ids.difference(EXPECTED_SANCTUARY_IDS))}"
        )
    if not frame["DESIGNATION_STATUS"].eq("active_designated").all():
        raise ValueError("National marine sanctuary collection contains a non-active record.")
    if not frame["AREA_QC_STATUS"].eq("within_0_5_percent_of_current_cfr_approx_area").all():
        raise ValueError("A sanctuary GIS boundary failed the CFR approximate-area QC check.")

    records = authority_records(frame)
    authority_path = artifact_path.parent / "sanctuary_authority_records.json"
    atomic_write_json(
        authority_path,
        {
            "schema_version": 1,
            "record_type": "national_marine_sanctuary_authority",
            "geometry_is_legal_authority": False,
            "current_cfr_text_and_coordinates_control": True,
            "records": records,
        },
        overwrite=overwrite,
    )

    config = load_governance_config(config_path)
    manifest_path = config.collections["national_marine_sanctuaries"].manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_completeness"] = "complete_current_noaa_west_coast_sanctuary_roster"
    manifest["sanctuary_policy"] = {
        "current_roster_count": len(EXPECTED_SANCTUARY_IDS),
        "native_source_geometry": True,
        "geometry_is_legal_authority": False,
        "current_cfr_text_and_coordinates_control": True,
        "overlapping_sanctuaries_preserved": True,
        "geometry_parts_preserved": True,
        "model_eligible": False,
    }
    manifest["sanctuary_count"] = int(frame["SANCTUARY_ID"].nunique())
    manifest["geometry_part_count"] = int(len(frame))
    manifest["source_vintages"] = {
        str(source_id): sorted(
            source_frame["SOURCE_VINTAGE"].dropna().astype(str).unique().tolist()
        )
        for source_id, source_frame in frame.groupby("SOURCE_DATASET_ID")
    }
    manifest["related_artifacts"] = {
        "sanctuary_authority_records": {
            "path": str(authority_path),
            "records": len(records),
            "sha256": sha256_file(authority_path),
            "bytes": authority_path.stat().st_size,
        }
    }
    atomic_write_json(manifest_path, manifest, overwrite=True)
    return artifact_path
