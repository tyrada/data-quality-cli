# Data Quality CLI

A small automation-friendly command that validates CSV files against a JSON schema before data reaches an ETL load. It distinguishes absent values from failed conversions, preserves rejected source rows, emits structured logs, and returns exit codes suitable for shell pipelines and schedulers.

## Architecture

```text
CSV + JSON schema -> column/schema checks -> row rules -> unique-key rules
                                                ├─ quality_report.json
                                                ├─ quality_summary.txt
                                                └─ rejected_rows.csv
```

The schema supports:

- required versus optional columns;
- `string`, `integer`, `number`, `date`, and `boolean` types;
- nullable versus non-nullable values;
- numeric minimum and maximum values;
- accepted-value lists;
- one or more single-column or composite unique keys.

An empty non-nullable field produces `missing value`; a present value that cannot convert produces `invalid integer`, `invalid number`, `invalid date`, or `invalid boolean`. This distinction helps separate source completeness issues from format problems.

See [`samples/customer_schema.json`](samples/customer_schema.json), [`samples/valid_customers.csv`](samples/valid_customers.csv), and [`samples/invalid_customers.csv`](samples/invalid_customers.csv).

## Setup and commands

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'

generate-quality-samples --output-dir samples
data-quality --input samples/valid_customers.csv \
  --schema samples/customer_schema.json --output-dir outputs/valid
data-quality --input samples/invalid_customers.csv \
  --schema samples/customer_schema.json --output-dir outputs/invalid
pytest -q --cov=data_quality --cov-report=term-missing
```

Exit-code contract:

| Code | Meaning |
| ---: | --- |
| 0 | File passed every configured rule |
| 1 | Unexpected internal failure |
| 2 | Validation completed and one or more rows failed quality rules |
| 3 | Input CSV or schema could not be read, or required columns are missing |

Log lines are JSON objects written through Python logging. The machine report is deterministic JSON containing input, accepted, rejected, and failure counts plus per-rule totals. The readable summary contains the same counts; the rejected CSV adds `failure_reasons` to original columns.

## Pre-ETL gate example

Shell `&&` prevents the database loader from running unless validation returns 0:

```bash
data-quality --input incoming/customers.csv --schema schemas/customers.json --output-dir quality/latest \
  && python load_customers.py incoming/customers.csv
```

A production workflow can archive the JSON report, route the rejected CSV to data owners, and alert differently for code 2 (data problem) and code 3 (contract/configuration problem).

## Actual results

Verified locally on November 5, 2026 with Python 3.12.16:

- **13 tests passed** with **89% total statement coverage**.
- The valid 10-row sample returned exit code **0**, with 10 accepted and 0 rejected.
- The invalid 10-row sample returned exit code **2**, with 0 accepted, 10 rejected, and 11 rule failures.
- The invalid sample exercised missing value, invalid integer, below minimum, above maximum, invalid date, invalid boolean, accepted values, customer-ID uniqueness, and email uniqueness.

## Scope and limitations

This is a local Python project. It has no AWS component, mocked AWS test, cloud deployment, credentials, IAM policy, or cloud cost.

Limitations: the complete CSV is loaded into memory; uniqueness is checked only within one file; date ranges are not yet supported; accepted values compare exact case-sensitive text; schemas have no formal JSON Schema meta-schema; and rejected rows are not automatically corrected or loaded.

## Interview questions and answers

1. **Why distinguish missing from invalid?** Missing data points to completeness or upstream extraction problems; invalid conversion points to formatting or contract drift.
2. **Why return a special quality-failure code?** Automation can stop a load while distinguishing expected bad data from tool crashes or configuration errors.
3. **Why mark every duplicated key row?** No member of a duplicate group can be assumed authoritative without an explicit survivorship rule.
4. **How would global uniqueness be checked?** Compare incoming keys with a durable target index or key registry in addition to within-file duplicates.
5. **Where should this run?** Immediately after landing the immutable source and before transforming or committing data to downstream database tables.
