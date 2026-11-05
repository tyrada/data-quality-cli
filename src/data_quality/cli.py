"""Automation-friendly CLI and exit-code contract."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from data_quality.reporting import write_reports
from data_quality.validator import ConfigurationError, validate_csv

EXIT_VALID = 0
EXIT_UNEXPECTED = 1
EXIT_QUALITY_FAILURES = 2
EXIT_INPUT_OR_SCHEMA_ERROR = 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CSV data against a JSON quality schema")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
    try:
        result = validate_csv(args.input, args.schema)
        write_reports(result, args.output_dir)
        logging.info(json.dumps({"event": "validation_complete", **result.report}, sort_keys=True))
        return EXIT_QUALITY_FAILURES if result.report["rejected_rows"] else EXIT_VALID
    except ConfigurationError as exc:
        logging.error(json.dumps({"event": "configuration_or_input_error", "error": str(exc)}, sort_keys=True))
        return EXIT_INPUT_OR_SCHEMA_ERROR
    except Exception as exc:
        logging.exception(json.dumps({"event": "unexpected_error", "error": str(exc)}, sort_keys=True))
        return EXIT_UNEXPECTED


if __name__ == "__main__":
    raise SystemExit(main())

