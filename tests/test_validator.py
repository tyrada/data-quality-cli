import json

import pandas as pd
import pytest

from data_quality.validator import ConfigurationError, load_schema, validate_frame


@pytest.fixture
def schema():
    return {
        "name": "test",
        "columns": {
            "id": {"type": "string", "required": True, "nullable": False},
            "age": {"type": "integer", "required": True, "nullable": False, "min": 18, "max": 100},
            "score": {"type": "number", "required": True, "nullable": False, "min": 0, "max": 10},
            "day": {"type": "date", "required": True, "nullable": False},
            "status": {"type": "string", "required": True, "nullable": False, "accepted_values": ["active"]},
            "flag": {"type": "boolean", "required": True, "nullable": False},
            "note": {"type": "string", "required": True, "nullable": True},
        },
        "unique_keys": [["id"]],
    }


def valid_row(**changes):
    row = {"id": "A", "age": "20", "score": "5.5", "day": "2025-01-01", "status": "active", "flag": "true", "note": ""}
    row.update(changes)
    return row


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"age": ""}, "age: missing value"),
        ({"age": "twenty"}, "age: invalid integer"),
        ({"age": "17"}, "age: below minimum"),
        ({"age": "101"}, "age: above maximum"),
        ({"score": "bad"}, "score: invalid number"),
        ({"day": "01/01/2025"}, "day: invalid date"),
        ({"status": "inactive"}, "status: value not accepted"),
        ({"flag": "yes"}, "flag: invalid boolean"),
    ],
)
def test_each_validation_rule_distinguishes_failures(schema, changes, reason):
    result = validate_frame(pd.DataFrame([valid_row(**changes)]), schema)
    assert result.report["rejected_rows"] == 1
    assert reason in result.rejected.iloc[0]["failure_reasons"]


def test_nullable_value_is_distinct_from_invalid_conversion(schema):
    result = validate_frame(pd.DataFrame([valid_row(note="")]), schema)
    assert result.report["accepted_rows"] == 1
    assert result.rejected.empty


def test_unique_key_marks_every_duplicate(schema):
    result = validate_frame(pd.DataFrame([valid_row(id="A"), valid_row(id="A")]), schema)
    assert result.report["rejected_rows"] == 2
    assert result.report["rule_failures"]["unique key (id): duplicated"] == 2


def test_missing_required_column_is_configuration_error(schema):
    with pytest.raises(ConfigurationError, match="missing required columns"):
        validate_frame(pd.DataFrame([{"id": "A"}]), schema)


def test_invalid_schema_is_rejected(tmp_path):
    path = tmp_path / "schema.json"
    path.write_text(json.dumps({"columns": {"id": {"type": "mystery"}}}), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="unsupported"):
        load_schema(path)

