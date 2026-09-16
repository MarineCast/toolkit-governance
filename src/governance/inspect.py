"""Render the consolidated full-AOI governance inspection map."""

from __future__ import annotations

import argparse
import importlib
from datetime import date
from html import escape
from pathlib import Path
from typing import Sequence

import folium
import geopandas as gpd
import pandas as pd
from folium.plugins import GroupedLayerControl

from governance._config.presentation import load_presentation_settings

from .shared.artifacts import atomic_write_json, sha256_file
from .shared.catalog import validate_catalog
from .shared.config import DEFAULT_CONFIG_PATH, GovernanceConfig, load_governance_config
from .shared.layers import GovernanceLayerDescriptor

CATEGORY_LABELS = {
    "protected_areas": "Protected Areas",
    "jurisdiction": "Jurisdiction",
    "fisheries_management": "Fisheries Management",
    "vessel_management": "Vessel Management",
    "administrative_context": "Administrative Context",
}


def _leaf_descriptors(config: GovernanceConfig) -> list[GovernanceLayerDescriptor]:
    descriptors = []
    for collection_id, collection in config.collections.items():
        module = importlib.import_module(
            f"governance.{collection.category}.{collection_id}.inspect"
        )
        if hasattr(module, "layer_descriptors"):
            descriptors.extend(module.layer_descriptors(config.path))
        else:
            descriptors.append(module.layer_descriptor(config.path))
    return descriptors


def _filter_descriptor_frame(
    frame: gpd.GeoDataFrame, descriptor: GovernanceLayerDescriptor
) -> gpd.GeoDataFrame:
    keep = pd.Series(True, index=frame.index)
    for field, value in descriptor.filters:
        if field not in frame.columns:
            raise ValueError(f"Map layer {descriptor.layer_id!r} filters missing field {field!r}.")
        keep &= frame[field].astype("string").eq(value).fillna(False)
    return frame.loc[keep].copy()


def _slice_as_of(frame: gpd.GeoDataFrame, as_of: date) -> gpd.GeoDataFrame:
    keep = pd.Series(True, index=frame.index)
    target = pd.Timestamp(as_of)
    if "EFFECTIVE_START" in frame:
        starts = pd.to_datetime(frame["EFFECTIVE_START"], errors="coerce")
        keep &= starts.isna() | starts.le(target)
    if "EFFECTIVE_END" in frame:
        ends = pd.to_datetime(frame["EFFECTIVE_END"], errors="coerce")
        keep &= ends.isna() | ends.ge(target)
    return frame.loc[keep].copy()


def _json_safe_frame(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    output = frame.copy()
    for column in output.columns:
        if column == output.geometry.name:
            continue
        if pd.api.types.is_datetime64_any_dtype(output[column]):
            output[column] = output[column].map(
                lambda value: None if pd.isna(value) else pd.Timestamp(value).isoformat()
            )
        elif output[column].dtype == "object":
            output[column] = output[column].map(
                lambda value: value.isoformat() if hasattr(value, "isoformat") else value
            )
    return output


def _display_geometry(frame: gpd.GeoDataFrame, tolerance_meters: float) -> gpd.GeoDataFrame:
    output = frame
    if tolerance_meters > 0:
        output = frame.to_crs("EPSG:6933")
        output.geometry = output.geometry.simplify(
            tolerance_meters,
            preserve_topology=True,
        )
        output = output.to_crs("EPSG:4326")
    if (
        "GOVERNANCE_FEATURE_ID" in output.columns
        and output["GOVERNANCE_FEATURE_ID"].duplicated().any()
    ):
        output = output.dissolve(
            by="GOVERNANCE_FEATURE_ID",
            as_index=False,
            aggfunc="first",
        )
    return output


def _style(color: str):
    def style_function(feature):
        geometry_type = str(feature.get("geometry", {}).get("type", ""))
        polygon = "Polygon" in geometry_type
        return {
            "color": color,
            "weight": 1.8 if not polygon else 1.2,
            "opacity": 0.9,
            "fillColor": color,
            "fillOpacity": 0.16 if polygon else 0.0,
        }

    return style_function


def _status_panel(
    catalog: dict, runtime_status: dict[str, tuple[str, str | None]], as_of: date
) -> str:
    sections = []
    for category, label in CATEGORY_LABELS.items():
        items = []
        for collection_id, values in catalog["collections"].items():
            if values["category"] != category:
                continue
            status, reason = runtime_status.get(
                collection_id,
                (values["implementation_status"], "Producer is planned but not implemented."),
            )
            symbol = "●" if status == "available" else "○"
            title = escape(str(values["display_name"]))
            detail = f" — {escape(reason)}" if reason else ""
            items.append(f"<li><strong>{symbol} {title}</strong>: {escape(status)}{detail}</li>")
        sections.append(f"<strong>{escape(label)}</strong><ul>{''.join(items)}</ul>")
    return f"""
    <div style='position:fixed;bottom:18px;left:12px;z-index:9999;background:white;
                padding:8px 10px;border:1px solid #777;border-radius:4px;width:390px;
                max-height:38vh;overflow:auto;font-size:11px;line-height:1.28'>
      <details><summary><strong>Governance layer status — {as_of.isoformat()}</strong></summary>
      <p>Filled dot = built and checksum-verified. Open dot = planned, unavailable, or not built.
      Absence from a source is not interpreted as no governance. Display geometry is generalized
      for inspection only; canonical artifacts retain native clipped geometry.</p>
      {''.join(sections)}</details>
    </div>
    """


def _legend_html(category_colors: dict[str, str]) -> str:
    rows = "".join(
        "<div><span style='display:inline-block;width:12px;height:12px;background:{};"
        "margin-right:6px'></span>{}</div>".format(category_colors[key], escape(label))
        for key, label in CATEGORY_LABELS.items()
    )
    return f"""
    <div style='position:fixed;top:72px;left:12px;z-index:9999;background:white;
                padding:8px;border:1px solid #777;border-radius:4px;font-size:11px'>
      <strong>Symbology</strong>{rows}
      <div style='margin-top:4px'>Lines = legal/reference boundaries<br>Fills = source-native areas</div>
    </div>
    """


def render_map(
    *,
    config: GovernanceConfig,
    catalog: dict,
    descriptors: Sequence[GovernanceLayerDescriptor],
    as_of: date,
    output_path: str | Path | None = None,
) -> Path:
    settings = load_presentation_settings(config.presentation_config_path)
    options = {
        "location": [52.0, -137.0],
        "zoom_start": settings.default_zoom,
        "tiles": settings.basemap_tile_layer,
        "control_scale": True,
    }
    if settings.basemap_attribution:
        options["attr"] = settings.basemap_attribution
    map_ = folium.Map(**options)
    west, south, east, north = config.bbox_tuple
    map_.fit_bounds([[south, west], [north, east]])
    folium.Rectangle(
        bounds=[[south, west], [north, east]],
        color="#444444",
        weight=1,
        dash_array="5,5",
        fill=False,
        tooltip="Configured full_area",
        control=False,
    ).add_to(map_)
    map_.get_root().html.add_child(
        folium.Element(
            "<h3 style='position:fixed;top:8px;left:52px;z-index:9999;"
            "background:rgba(255,255,255,.9);padding:6px'>"
            f"Governance layers — full_area — as of {as_of.isoformat()}</h3>"
        )
    )

    grouped: dict[str, list[folium.FeatureGroup]] = {
        label: [] for label in CATEGORY_LABELS.values()
    }
    runtime_status: dict[str, tuple[str, str | None]] = {}
    rendered_collection_ids: set[str] = set()
    rendered_layer_ids = []
    descriptor_records = []
    for descriptor in descriptors:
        runtime_status[descriptor.collection_id] = (descriptor.status, descriptor.reason)
        if descriptor.status != "available":
            descriptor_records.append(descriptor.to_manifest_record())
            continue
        source_frame = gpd.read_parquet(descriptor.artifact_path)
        source_subset = _filter_descriptor_frame(source_frame, descriptor)
        frame = _slice_as_of(source_subset, as_of)
        layer_record = descriptor.to_manifest_record()
        layer_record.update(
            artifact_sha256=sha256_file(descriptor.artifact_path),
            collection_feature_count_total=int(len(source_frame)),
            feature_count_total=int(len(source_subset)),
            feature_count_as_of=int(len(frame)),
            effective_start_min=(
                str(pd.to_datetime(source_subset["EFFECTIVE_START"], errors="coerce").min())
                if pd.to_datetime(source_subset["EFFECTIVE_START"], errors="coerce").notna().any()
                else None
            ),
            effective_end_max=(
                str(pd.to_datetime(source_subset["EFFECTIVE_END"], errors="coerce").max())
                if pd.to_datetime(source_subset["EFFECTIVE_END"], errors="coerce").notna().any()
                else None
            ),
            style_id=f"{descriptor.category}-native-geometry-v1",
        )
        if frame.empty:
            descriptor_records.append(layer_record)
            runtime_status[descriptor.collection_id] = (
                "unavailable_at_date",
                "No active records exist for the selected as-of date.",
            )
            continue
        frame = _display_geometry(frame, config.inspection_simplify_tolerance_meters)
        layer_record.update(
            display_feature_count=int(len(frame)),
            display_dissolve_field=(
                "GOVERNANCE_FEATURE_ID"
                if "GOVERNANCE_FEATURE_ID" in source_subset.columns
                and source_subset["GOVERNANCE_FEATURE_ID"].duplicated().any()
                else None
            ),
        )
        descriptor_records.append(layer_record)
        frame = _json_safe_frame(frame)
        layer_id = descriptor.layer_id or descriptor.collection_id
        layer_name = f"{descriptor.display_name} [{layer_id}]"
        group = folium.FeatureGroup(name=layer_name, show=descriptor.default_visible)
        tooltip_fields = [
            field
            for field in (
                "FEATURE_NAME",
                "FEATURE_TYPE",
                "AUTHORITY",
                "JURISDICTION",
                "LEGAL_BINDING_STATUS",
                "EFFECTIVE_START",
                "EFFECTIVE_END",
                "SOURCE_VINTAGE",
                "SOURCE_COVERAGE_STATUS",
                "SOURCE_DATASET_ID",
                "COUNTRY_CODE",
                "ZONE_TYPE",
                "ZONE_LIMIT_NM",
                "GEOMETRY_ROLE",
                "DESIGNATION_ID",
                "DESIGNATION_STATUS",
                "EFFECTIVE_STATUS",
                "SANCTUARY_ID",
                "CFR_BOUNDARY_SECTION",
                "DESIGNATION_FEDERAL_REGISTER",
                "LEGAL_BOUNDARY_STATUS",
                "SOURCE_GEOMETRY_STATUS",
                "AREA_QC_STATUS",
                "MPA_PROGRAM",
                "MANAGEMENT_AUTHORITY",
                "SOURCE_SUBDIVISION_CODE",
                "SOURCE_DESIGNATION_TYPE",
                "GOVERNING_RULE_CITATION",
                "GOVERNING_RULE_STATUS",
                "PROTECTION_PURPOSE",
                "FISHING_RESTRICTIONS_REFERENCE",
                "ACTIVITY_METADATA_STATUS",
                "IUCN_REPORTING_CLASS",
                "SOURCE_ROLE",
                "SOURCE_SCALE",
                "SOURCE_POSITIONAL_ACCURACY_M",
                "RECONCILIATION_STATUS",
                "QC_STATUS",
                "QC_REASON",
                "BOUNDARY_QC_REASON",
                "ZONE_QC_REASON",
                "MPA_QC_REASON",
                "SANCTUARY_QC_REASON",
                "LEGAL_SOURCE_URL",
            )
            if field in frame.columns
        ]
        folium.GeoJson(
            data=frame.__geo_interface__,
            name=layer_name,
            style_function=_style(descriptor.color),
            highlight_function=lambda _feature: {"weight": 4, "fillOpacity": 0.32},
            tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, sticky=False),
            popup=folium.GeoJsonPopup(fields=tooltip_fields, max_width=480),
        ).add_to(group)
        group.add_to(map_)
        grouped[CATEGORY_LABELS[descriptor.category]].append(group)
        rendered_collection_ids.add(descriptor.collection_id)
        rendered_layer_ids.append(layer_id)

    active_groups = {name: layers for name, layers in grouped.items() if layers}
    if active_groups:
        GroupedLayerControl(
            groups=active_groups,
            exclusive_groups=False,
            collapsed=False,
        ).add_to(map_)
    built_catalog_ids = {
        descriptor.collection_id
        for descriptor in descriptors
        if descriptor.status == "available"
        and catalog["collections"].get(descriptor.collection_id, {}).get("map_layer")
    }
    if built_catalog_ids != rendered_collection_ids:
        raise ValueError(
            "Built governance catalog layers were omitted from the map: "
            f"{sorted(built_catalog_ids.difference(rendered_collection_ids))}"
        )
    map_.get_root().html.add_child(folium.Element(_legend_html(dict(config.category_colors))))
    map_.get_root().html.add_child(folium.Element(_status_panel(catalog, runtime_status, as_of)))

    destination = Path(output_path).expanduser().resolve() if output_path else config.map_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    map_.save(destination)
    collection_status = {}
    for collection_id, values in catalog["collections"].items():
        status, reason = runtime_status.get(
            collection_id,
            (values["implementation_status"], "Producer is planned but not implemented."),
        )
        collection_status[collection_id] = {
            "category": values["category"],
            "display_name": values["display_name"],
            "status": status,
            "reason": reason,
        }
    map_manifest = {
        "schema_version": 1,
        "map_path": str(destination),
        "map_sha256": sha256_file(destination),
        "as_of": as_of.isoformat(),
        "area_name": config.area_name,
        "resolved_bounds_wgs84": dict(config.bounds),
        "config_path": str(config.path),
        "config_sha256": sha256_file(config.path),
        "common_config_path": str(config.common_config_path),
        "common_config_sha256": sha256_file(config.common_config_path),
        "catalog_path": str(config.catalog_path),
        "catalog_sha256": sha256_file(config.catalog_path),
        "grouped_multi_select": True,
        "display_simplification_tolerance_meters": config.inspection_simplify_tolerance_meters,
        "rendered_collection_ids": sorted(rendered_collection_ids),
        "rendered_layer_ids": sorted(rendered_layer_ids),
        "catalogued_map_collection_ids": sorted(built_catalog_ids),
        "unavailable_or_planned_collection_ids": sorted(
            set(catalog["collections"]).difference(rendered_collection_ids)
        ),
        "category_colors": dict(config.category_colors),
        "collection_status": collection_status,
        "layer_descriptors": descriptor_records,
    }
    manifest_path = (
        destination.with_suffix(".manifest.json")
        if output_path is not None
        else config.map_manifest_path
    )
    atomic_write_json(manifest_path, map_manifest, overwrite=True)
    return destination


def inspect(
    *,
    as_of: date,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    output_path: str | Path | None = None,
) -> Path:
    config = load_governance_config(config_path)
    catalog = validate_catalog(verify_artifacts=True, config_path=config_path)
    return render_map(
        config=config,
        catalog=catalog,
        descriptors=_leaf_descriptors(config),
        as_of=as_of,
        output_path=output_path,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    print(inspect(as_of=args.as_of, config_path=args.config, output_path=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
