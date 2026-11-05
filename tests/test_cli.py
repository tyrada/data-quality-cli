import json
import sys
from pathlib import Path

from data_quality.cli import EXIT_INPUT_OR_SCHEMA_ERROR, EXIT_QUALITY_FAILURES, EXIT_VALID, main
from data_quality.generator import generate_samples


def run_cli(monkeypatch, input_path, schema_path, output_dir):
    monkeypatch.setattr(sys, "argv", ["data-quality", "--input", str(input_path), "--schema", str(schema_path), "--output-dir", str(output_dir)])
    return main()


def test_cli_exit_codes_and_reports(monkeypatch, tmp_path):
    samples = tmp_path / "samples"
    generate_samples(samples)
    schema = samples.parent / "schema.json"
    schema.write_text((Path(__file__).parents[1] / "samples" / "customer_schema.json").read_text(), encoding="utf-8")

    valid_output = tmp_path / "valid-output"
    assert run_cli(monkeypatch, samples / "valid_customers.csv", schema, valid_output) == EXIT_VALID
    assert json.loads((valid_output / "quality_report.json").read_text())["rejected_rows"] == 0

    invalid_output = tmp_path / "invalid-output"
    assert run_cli(monkeypatch, samples / "invalid_customers.csv", schema, invalid_output) == EXIT_QUALITY_FAILURES
    report = json.loads((invalid_output / "quality_report.json").read_text())
    assert report["rejected_rows"] > 0
    assert (invalid_output / "quality_summary.txt").exists()
    assert (invalid_output / "rejected_rows.csv").exists()

    assert run_cli(monkeypatch, tmp_path / "missing.csv", schema, tmp_path / "missing-output") == EXIT_INPUT_OR_SCHEMA_ERROR
