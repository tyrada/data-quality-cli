"""Schema configuration parsing and row-level CSV validation."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

SUPPORTED_TYPES = {"string", "integer", "number", "date", "boolean"}


class ConfigurationError(ValueError):
    """Raised for an invalid schema or incompatible input structure."""


@dataclass(frozen=True)
class ValidationResult:
    report: dict[str, object]
    rejected: pd.DataFrame


def load_schema(path: Path) -> dict[str, object]:
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"could not read schema: {exc}") from exc
    columns = schema.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise ConfigurationError("schema.columns must be a non-empty object")
    for name, rule in columns.items():
        if not isinstance(rule, dict) or rule.get("type") not in SUPPORTED_TYPES:
            raise ConfigurationError(f"column {name} has unsupported or missing type")
    unique_keys = schema.get("unique_keys", [])
    if not isinstance(unique_keys, list) or any(not isinstance(key, list) or not key for key in unique_keys):
        raise ConfigurationError("unique_keys must be a list of non-empty column lists")
    return schema


def _convert(value: str, data_type: str, date_format: str) -> object:
    if data_type == "string":
        return value
    if data_type == "integer":
        number = Decimal(value)
        if not number.is_finite() or number != number.to_integral_value():
            raise InvalidOperation
        return int(number)
    if data_type == "number":
        number = Decimal(value)
        if not number.is_finite():
            raise InvalidOperation
        return number
    if data_type == "date":
        return datetime.strptime(value, date_format).date()
    if data_type == "boolean":
        normalized = value.lower()
        if normalized not in {"true", "false"}:
            raise ValueError
        return normalized == "true"
    raise ValueError(f"unsupported type: {data_type}")


def validate_frame(frame: pd.DataFrame, schema: dict[str, object], source_name: str = "input.csv") -> ValidationResult:
    columns: dict[str, dict[str, object]] = schema["columns"]  # type: ignore[assignment]
    missing_columns = [name for name, rule in columns.items() if rule.get("required", True) and name not in frame.columns]
    if missing_columns:
        raise ConfigurationError(f"input missing required columns: {', '.join(missing_columns)}")

    work = frame.copy()
    errors: dict[object, list[str]] = {index: [] for index in work.index}
    failure_counts: Counter[str] = Counter()

    for name, rule in columns.items():
        if name not in work.columns:
            continue
        values = work[name].astype("string").fillna("").str.strip()
        data_type = str(rule["type"])
        nullable = bool(rule.get("nullable", False))
        date_format = str(rule.get("format", "%Y-%m-%d"))
        accepted = rule.get("accepted_values")
        for index, value in values.items():
            if value == "":
                if not nullable:
                    reason = f"{name}: missing value"
                    errors[index].append(reason)
                    failure_counts[reason] += 1
                continue
            try:
                converted = _convert(value, data_type, date_format)
            except (ValueError, InvalidOperation):
                reason = f"{name}: invalid {data_type}"
                errors[index].append(reason)
                failure_counts[reason] += 1
                continue

            if accepted is not None and value not in accepted:
                reason = f"{name}: value not accepted"
                errors[index].append(reason)
                failure_counts[reason] += 1
            if data_type in {"integer", "number"}:
                if "min" in rule and converted < Decimal(str(rule["min"])):  # type: ignore[operator]
                    reason = f"{name}: below minimum"
                    errors[index].append(reason)
                    failure_counts[reason] += 1
                if "max" in rule and converted > Decimal(str(rule["max"])):  # type: ignore[operator]
                    reason = f"{name}: above maximum"
                    errors[index].append(reason)
                    failure_counts[reason] += 1

    for key_columns in schema.get("unique_keys", []):
        missing_key_columns = [column for column in key_columns if column not in work.columns]
        if missing_key_columns:
            raise ConfigurationError(f"unique key references missing columns: {', '.join(missing_key_columns)}")
        key_frame = work[key_columns].astype("string").fillna("").apply(lambda column: column.str.strip())
        complete = key_frame.ne("").all(axis=1)
        duplicated = complete & key_frame.duplicated(keep=False)
        label = ", ".join(key_columns)
        reason = f"unique key ({label}): duplicated"
        for index in work.index[duplicated]:
            errors[index].append(reason)
            failure_counts[reason] += 1

    rejected_mask = pd.Series({index: bool(row_errors) for index, row_errors in errors.items()})
    rejected = work.loc[rejected_mask].copy()
    rejected["failure_reasons"] = ["; ".join(errors[index]) for index in rejected.index]
    report: dict[str, object] = {
        "schema_name": schema.get("name", "unnamed"),
        "source": source_name,
        "input_rows": len(work),
        "accepted_rows": int((~rejected_mask).sum()),
        "rejected_rows": int(rejected_mask.sum()),
        "failure_count": sum(failure_counts.values()),
        "rule_failures": dict(sorted(failure_counts.items())),
    }
    return ValidationResult(report, rejected.reset_index(drop=True))


def validate_csv(input_path: Path, schema_path: Path) -> ValidationResult:
    try:
        frame = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ConfigurationError(f"could not read input CSV: {exc}") from exc
    return validate_frame(frame, load_schema(schema_path), input_path.name)

