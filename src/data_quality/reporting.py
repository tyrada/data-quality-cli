"""Write deterministic machine-readable and human-readable quality artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from data_quality.validator import ValidationResult


def write_reports(result: ValidationResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "quality_report.json").write_text(json.dumps(result.report, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"Schema: {result.report['schema_name']}",
        f"Source: {result.report['source']}",
        f"Input rows: {result.report['input_rows']}",
        f"Accepted rows: {result.report['accepted_rows']}",
        f"Rejected rows: {result.report['rejected_rows']}",
        f"Rule failures: {result.report['failure_count']}",
    ]
    failures = result.report["rule_failures"]
    if failures:
        lines.append("Failures by rule:")
        lines.extend(f"  - {reason}: {count}" for reason, count in failures.items())
    (output_dir / "quality_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    result.rejected.to_csv(output_dir / "rejected_rows.csv", index=False)

