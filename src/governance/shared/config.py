"""Validated shared configuration for governance feature families."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from governance._config.common_areas import bbox_for_area
from governance._config.document import ConfigDocument

DEFAULT_CONFIG_PATH = "config/data/governance/governance.yaml"
VALID_CATEGORIES = {
    "protected_areas",
    "jurisdiction",
    "fisheries_management",
    "vessel_management",
    "administrative_context",
}
VALID_COVERAGE_STATES = {
    "complete",
    "partial",
    "unavailable",
    "unknown",
    "not_applicable",
}
VALID_SOURCE_STATES = {"available", "available_after_download", "unavailable"}


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping.")
    return dict(value)


@dataclass(frozen=True)
class GovernanceSource:
    """One authoritative or explicitly unavailable source contract."""

    source_id: str
    provider: str
    acquisition_type: str
    url: str
    local_path: Path | None
    snapshot_path: Path | None
    archive_member: str | None
    archive_layer: str | None
    expected_sha256: str | None
    source_as_of: str
    license_name: str
    attribution: str
    legal_citation: str
    redistribution: str
    authority_scope: str
    source_status: str
    server_filter: bool
    page_size: int | None
    source_limitation: str
    coverage: Mapping[str, str]


@dataclass(frozen=True)
class GovernanceCollection:
    """One normalized governance geometry collection."""

    collection_id: str
    category: str
    display_name: str
    normalization_profile: str
    source_ids: tuple[str, ...]
    artifact_path: Path
    manifest_path: Path
    color: str
    default_visible: bool
    implementation_status: str


@dataclass(frozen=True)
class GovernanceConfig:
    """Fully resolved Phase 1 governance configuration."""

    document: ConfigDocument
    area_name: str
    common_config_path: Path
    bounds: Mapping[str, float]
    clip_crs: str
    clip_method: str
    clip_tolerance_degrees: float
    snapshot_root: Path
    processed_root: Path
    coverage_matrix_path: Path
    map_path: Path
    map_manifest_path: Path
    presentation_config_path: Path
    inspection_simplify_tolerance_meters: float
    category_colors: Mapping[str, str]
    catalog_path: Path
    coverage_regions: Mapping[str, str]
    sources: Mapping[str, GovernanceSource]
    collections: Mapping[str, GovernanceCollection]

    @property
    def path(self) -> Path:
        return self.document.source

    @property
    def config_hash(self) -> str:
        return self.document.config_hash

    @property
    def bbox_tuple(self) -> tuple[float, float, float, float]:
        return (
            self.bounds["min_lon"],
            self.bounds["min_lat"],
            self.bounds["max_lon"],
            self.bounds["max_lat"],
        )

    def manifest_safe(self) -> dict[str, Any]:
        return self.document.redacted_data()


def load_governance_config(path: str | Path = DEFAULT_CONFIG_PATH) -> GovernanceConfig:
    document = ConfigDocument.load(path)
    raw = _mapping(document.data, "governance configuration")
    if int(raw.get("schema_version", 0)) != 1:
        raise ValueError("Governance configuration schema_version must equal 1.")

    area_name = str(raw.get("area", "")).strip()
    if area_name != "full_area":
        raise ValueError("Governance Phase 1 requires the shared full_area scope.")
    common_config_path = document.resolve_path(str(raw.get("common_config_path", "")))
    bounds = bbox_for_area(area_name, common_config_path=common_config_path)

    clipping = _mapping(raw.get("clipping"), "clipping")
    if str(clipping.get("crs")) != "EPSG:4326":
        raise ValueError("Governance clipping CRS must be EPSG:4326.")
    tolerance = float(clipping.get("tolerance_degrees", 0.0))
    if tolerance < 0:
        raise ValueError("clipping.tolerance_degrees cannot be negative.")

    raw_paths = _mapping(raw.get("raw"), "raw")
    output = _mapping(raw.get("output"), "output")
    inspection = _mapping(raw.get("inspection"), "inspection")
    region_values = _mapping(raw.get("coverage_regions"), "coverage_regions")
    regions = {
        str(region_id): str(_mapping(value, f"coverage_regions.{region_id}")["label"])
        for region_id, value in region_values.items()
    }
    if not regions:
        raise ValueError("At least one governance coverage region is required.")

    source_values = _mapping(raw.get("sources"), "sources")
    sources: dict[str, GovernanceSource] = {}
    for source_id, value in source_values.items():
        values = _mapping(value, f"sources.{source_id}")
        coverage = _mapping(values.get("coverage"), f"sources.{source_id}.coverage")
        if set(coverage) != set(regions):
            missing = sorted(set(regions).difference(coverage))
            extra = sorted(set(coverage).difference(regions))
            raise ValueError(
                f"Source {source_id!r} coverage must match configured regions; "
                f"missing={missing}, extra={extra}."
            )
        invalid_coverage = sorted(
            {str(status) for status in coverage.values()}.difference(VALID_COVERAGE_STATES)
        )
        if invalid_coverage:
            raise ValueError(f"Source {source_id!r} has invalid coverage: {invalid_coverage}")
        source_status = str(values.get("source_status", "unknown"))
        if source_status not in VALID_SOURCE_STATES:
            raise ValueError(f"Source {source_id!r} has invalid source_status {source_status!r}.")
        local = values.get("local_path")
        snapshot = values.get("snapshot_path")
        archive_member = values.get("archive_member")
        archive_layer = values.get("archive_layer")
        expected_sha256 = values.get("expected_sha256")
        if expected_sha256 is not None:
            expected_sha256 = str(expected_sha256).strip().lower()
            if len(expected_sha256) != 64 or any(
                value not in "0123456789abcdef" for value in expected_sha256
            ):
                raise ValueError(
                    f"Source {source_id!r} expected_sha256 must be a lowercase SHA-256 digest."
                )
        sources[str(source_id)] = GovernanceSource(
            source_id=str(source_id),
            provider=str(values["provider"]),
            acquisition_type=str(values["acquisition_type"]),
            url=str(values["url"]),
            local_path=document.resolve_path(str(local)) if local else None,
            snapshot_path=document.resolve_path(str(snapshot)) if snapshot else None,
            archive_member=str(archive_member) if archive_member else None,
            archive_layer=str(archive_layer) if archive_layer else None,
            expected_sha256=expected_sha256,
            source_as_of=str(values.get("source_as_of", "unknown")),
            license_name=str(values["license"]),
            attribution=str(values["attribution"]),
            legal_citation=str(values["legal_citation"]),
            redistribution=str(values["redistribution"]),
            authority_scope=str(values["authority_scope"]),
            source_status=source_status,
            server_filter=bool(values.get("server_filter", True)),
            page_size=(int(values["page_size"]) if values.get("page_size") is not None else None),
            source_limitation=str(values.get("source_limitation", "")),
            coverage={str(key): str(status) for key, status in coverage.items()},
        )
        if sources[str(source_id)].page_size is not None and sources[str(source_id)].page_size <= 0:
            raise ValueError(f"Source {source_id!r} page_size must be positive.")

    collection_values = _mapping(raw.get("collections"), "collections")
    collections: dict[str, GovernanceCollection] = {}
    for collection_id, value in collection_values.items():
        values = _mapping(value, f"collections.{collection_id}")
        category = str(values["category"])
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Collection {collection_id!r} has invalid category {category!r}.")
        source_ids = tuple(str(item) for item in values.get("source_ids", ()))
        unknown_sources = sorted(set(source_ids).difference(sources))
        if unknown_sources:
            raise ValueError(
                f"Collection {collection_id!r} references unknown sources: {unknown_sources}"
            )
        collections[str(collection_id)] = GovernanceCollection(
            collection_id=str(collection_id),
            category=category,
            display_name=str(values["display_name"]),
            normalization_profile=str(values["normalization_profile"]),
            source_ids=source_ids,
            artifact_path=document.resolve_path(str(values["artifact_path"])),
            manifest_path=document.resolve_path(str(values["manifest_path"])),
            color=str(values["color"]),
            default_visible=bool(values.get("default_visible", False)),
            implementation_status=str(values.get("implementation_status", "planned")),
        )

    simplify_tolerance = float(inspection.get("simplify_tolerance_meters", 0.0))
    if simplify_tolerance < 0:
        raise ValueError("inspection.simplify_tolerance_meters cannot be negative.")
    category_colors = _mapping(inspection.get("category_colors"), "inspection.category_colors")
    if set(category_colors) != VALID_CATEGORIES:
        raise ValueError("inspection.category_colors must cover all governance categories.")

    return GovernanceConfig(
        document=document,
        area_name=area_name,
        common_config_path=common_config_path,
        bounds=bounds,
        clip_crs=str(clipping["crs"]),
        clip_method=str(clipping["method"]),
        clip_tolerance_degrees=tolerance,
        snapshot_root=document.resolve_path(str(raw_paths["snapshot_root"])),
        processed_root=document.resolve_path(str(output["processed_root"])),
        coverage_matrix_path=document.resolve_path(str(output["coverage_matrix_path"])),
        map_path=document.resolve_path(str(inspection["map_path"])),
        map_manifest_path=document.resolve_path(str(inspection["map_manifest_path"])),
        presentation_config_path=document.resolve_path(str(inspection["presentation_config_path"])),
        inspection_simplify_tolerance_meters=simplify_tolerance,
        category_colors={str(key): str(value) for key, value in category_colors.items()},
        catalog_path=document.resolve_path(str(raw["catalog_path"])),
        coverage_regions=regions,
        sources=sources,
        collections=collections,
    )
