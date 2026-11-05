"""Create deterministic valid and intentionally invalid sample datasets."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

FIELDS = ("customer_id", "age", "email", "signup_date", "status", "score", "marketing_opt_in")


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def generate_samples(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    valid = [
        {
            "customer_id": f"C-{index:04d}", "age": str(20 + index),
            "email": f"customer{index}@example.com" if index != 5 else "",
            "signup_date": f"2025-01-{index:02d}", "status": "active" if index % 2 else "inactive",
            "score": str(50 + index), "marketing_opt_in": "true" if index % 2 else "false",
        }
        for index in range(1, 11)
    ]
    invalid = [
        {**valid[0], "customer_id": ""},
        {**valid[1], "customer_id": "BAD-AGE", "age": "twenty"},
        {**valid[2], "customer_id": "TOO-YOUNG", "age": "17"},
        {**valid[3], "customer_id": "BAD-STATUS", "status": "unknown"},
        {**valid[4], "customer_id": "DUPLICATE"},
        {**valid[5], "customer_id": "DUPLICATE"},
        {**valid[6], "customer_id": "HIGH-SCORE", "score": "120"},
        {**valid[7], "customer_id": "BAD-DATE", "signup_date": "01/08/2025"},
        {**valid[8], "customer_id": "BAD-BOOL", "marketing_opt_in": "yes"},
        {**valid[9], "customer_id": "DUP-EMAIL", "email": valid[0]["email"]},
    ]
    _write(output_dir / "valid_customers.csv", valid)
    _write(output_dir / "invalid_customers.csv", invalid)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate valid and invalid quality-gate samples")
    parser.add_argument("--output-dir", type=Path, default=Path("samples"))
    args = parser.parse_args()
    generate_samples(args.output_dir)
    print(f"generated samples under {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

