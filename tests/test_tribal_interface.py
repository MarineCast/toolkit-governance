import copy
import pyarrow as pa
import pytest
from governance.memberships import MEMBERSHIP_TYPE, RECORD_FIELDS, definition
from governance.jurisdiction.tribal_first_nations_areas.interface import (
    AREA, ASSIGNMENT, COUNT, COMPONENTS, FAMILY, SCIENTIFIC_FEATURES, SOURCE_CONTEXT, add_features,
)


def member(source, name="Same name", parts=None):
    record = dict.fromkeys(RECORD_FIELDS)
    record.update(source_dataset_id=source, source_feature_id=source + ":record:01", feature_name=name,
        feature_type="provider_administrative_reference", geometry_part_ids=parts or ["part-a"])
    return {"feature_id": source + ":area:01", "records": [record]}


def fixture():
    us, ca = member("bia_administrative_lar"), member("nrcan_indian_reserves")
    values = [[[us], None, [], None, [us]], [[ca], None, [], None, None]]
    statuses = [["partial", "partial", "observed", "unavailable", "partial"]] * 2
    columns, fields = {}, {}
    for group, rows, states in zip(COMPONENTS, values, statuses):
        name = group + "__feature_memberships_v1"
        columns.update({name: pa.array(rows, MEMBERSHIP_TYPE), name + "_status": pa.array(states),
            group + "__recorded_feature_count": pa.array([None if row is None else len(row) for row in rows], pa.int64()),
            group + "__recorded_feature_count_status": pa.array(states)})
        fields.update({key: {} for key in (name, name + "_status", group + "__recorded_feature_count", group + "__recorded_feature_count_status")})
        fields[name] = definition(group)
    return pa.table(columns), fields, {group: {} for group in COMPONENTS}


def test_combines_qualified_ids_names_and_overlaps_without_country_collision():
    table, fields, coverage = fixture()
    original = table
    result = add_features(table, fields, coverage)
    assert result[AREA].type == pa.bool_()
    assert result[AREA].to_pylist() == [True, None, None, None, True]
    assert result[COUNT].to_pylist() == [2, None, None, None, 1]
    assert result[ASSIGNMENT + "_status"].to_pylist() == ["partial", "partial", "partial", "unavailable", "partial"]
    row = result[ASSIGNMENT][0].as_py()
    assert [entry["feature_id"] for entry in row] == ["bia_administrative_lar:area:01", "nrcan_indian_reserves:area:01"]
    assert [entry["records"][0]["feature_name"] for entry in row] == ["Same name", "Same name"]
    for column in original.column_names:
        assert original[column].equals(result[column])
    assert {name for name, field in fields.items() if field.get("map_feature")} == set(SCIENTIFIC_FEATURES)
    assert fields[ASSIGNMENT]["source_context"] == SOURCE_CONTEXT
    assert result.equals(add_features(result, fields, coverage))


def test_false_requires_geographic_evidence_for_both_sources_not_observed_receipts():
    table, fields, coverage = fixture()
    for group in COMPONENTS:
        coverage[group] = {"geographic_inventory_coverage": {"status": "complete", "scope": "country", "evidence": "National ID roster"}}
    assert add_features(table, copy.deepcopy(fields), coverage)[AREA][2].as_py() is None
    for group in COMPONENTS:
        coverage[group]["geographic_inventory_coverage"].update(scope="full_supplied_cells", evidence="Independently qualified full-cell inventory")
    result = add_features(table, fields, coverage)
    assert result[AREA][2].as_py() is False
    assert result[ASSIGNMENT][2].as_py() == []
    assert result[COUNT][2].as_py() == 0
    assert result[AREA + "_status"][2].as_py() == "observed"
    coverage[COMPONENTS[1]]["geographic_inventory_coverage"]["evidence"] = ""
    assert add_features(result, fields, coverage)[AREA][2].as_py() is None


def test_missing_source_never_invents_absence_but_received_hits_stay_true():
    table, fields, coverage = fixture()
    removed = [name for name in table.column_names if name.startswith(COMPONENTS[1] + "__")]
    for name in removed: fields.pop(name)
    result = add_features(table.drop(removed), fields, coverage)
    assert result[AREA].to_pylist() == [True, None, None, None, True]
    assert result[COUNT][0].as_py() == 1


def test_legacy_without_memberships_is_not_fabricated():
    table = pa.table({"h3_index": ["cell"]})
    assert add_features(table, {}, {}) is table


def test_catalog_declares_exact_two_choices():
    from governance.maintenance.catalog import build_catalog
    assert build_catalog()["collections"][FAMILY]["scientific_features"] == SCIENTIFIC_FEATURES


def test_boolean_overlap_contract_rejects_numeric_encoding():
    import h3
    from governance.products import validate_metric_table
    table=pa.table({"h3_index":[h3.latlng_to_cell(48.5,-123,6)],AREA:[1.0],AREA+"_status":["partial"]})
    meta={"schema_version":1,"model_eligible":False,"spatial":{"h3_resolution":6},"temporal":{"type":"static"},
        "fields":{"h3_index":{},AREA:{"units":"1","value_semantics":"boolean_overlap","missing_reason_field":AREA+"_status"},AREA+"_status":{}}}
    with pytest.raises(ValueError,match="Arrow boolean"):
        validate_metric_table(table,meta)
