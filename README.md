# Historical Employee Data Pipeline – SCD Type 2

## 1. Project Overview

This project implements a reliable historical employee data processing pipeline using Python and SQLite.

It uses Slowly Changing Dimension Type 2 (SCD Type 2) to maintain employee history whenever tracked employee attributes change, such as employee name, department, or salary.

The pipeline supports CSV ingestion, data validation, duplicate detection, historical version management, late-arriving events, and safe recovery after publishing failures.

## 2. Objectives

- Maintain complete employee history using SCD Type 2.
- Process large CSV datasets efficiently.
- Detect and reject invalid records.
- Handle duplicate and conflicting events.
- Support late-arriving and out-of-order events.
- Ensure safe reruns and recovery after failures.
- Maintain processing logs and run-level statistics.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.15 | Pipeline implementation |
| SQLite | Persistent data storage |
| CSV | Source data format |
| Pytest | Automated testing |
| SHA-256 | Deterministic IDs and payload hashing |

## 4. Architecture

The pipeline follows this processing flow:

1. **Ingestion:** Reads employee records from CSV files.
2. **Validation:** Checks required fields, data types, timestamps, salary and department references.
3. **Event Storage:** Stores accepted source events and prevents duplicate event IDs.
4. **SCD Type 2 Processing:** Builds employee timelines and maintains historical versions.
5. **Publishing:** Updates the employee dimension table.
6. **Monitoring:** Records pipeline execution status, accepted records, rejected records and processing logs.

## 5. Project Structure

```text
historical-employee-pipeline/
│
├── src/
│   ├── __init__.py
│   ├── database.py
│   ├── ingestion.py
│   ├── validation.py
│   ├── scd2_processor.py
│   ├── publisher.py
│   └── generator.py
│
├── data/
│   ├── input/
│   │   ├── employees.csv
│   │   └── employees_100k.csv
│   │
│   └── output/
│       └── scd2_pipeline.db
│
├── tests/
│   ├── test_scd2.py
│   ├── test_validation.py
│   └── test_publisher.py
│
├── docs/
├── logs/
├── reports/
├── outputs/
├── requirements.txt
├── pytest.ini
└── README.md
```

## 6. Database Design

The database contains the following main tables:

- **pipeline_runs:** Tracks pipeline execution, status and processing counts.
- **ref_department:** Stores valid department reference data.
- **source_events:** Stores accepted source employee events.
- **dim_employee:** Maintains historical employee versions.
- **rejected_records:** Stores invalid or conflicting records.
- **event_processing_log:** Tracks event-level processing activity.

## 7. SCD Type 2 Implementation

The employee dimension maintains historical records using:

- `effective_from`
- `effective_to`
- `is_current`
- `attribute_hash`
- `employee_version_id`

When tracked employee attributes change, a new historical version is created.

The previous version receives an end timestamp, and the latest version is marked as current.

The implementation also rebuilds employee timelines when late-arriving events are received.

## 8. Reliability and Data Quality

The pipeline implements:

- Required-field validation.
- Timestamp and data-type validation.
- Department reference validation.
- Duplicate event detection.
- Conflicting event detection.
- Deterministic employee version IDs.
- Idempotent processing.
- Rejected-record tracking.
- Failure recovery and safe restart.

## 9. Performance Testing

The pipeline was tested using a synthetic dataset containing 100,000 employee events.

| Metric | Result |
|---|---:|
| Input records | 100,000 |
| Accepted records | 100,000 |
| Rejected records | 0 |
| Distinct employees | 1,000 |
| Historical versions | 40,653 |
| Processing time | 33.30 seconds |
| Throughput | 3,002.67 records/second |

A second execution using the same input produced:

- Zero newly accepted records.
- Zero rejected records.
- No additional source events.
- No changes to existing employee history.

All five SCD Type 2 integrity checks also passed.

*Performance results are from the local test environment and may vary across machines.*

## 10. Automated Testing

The project currently contains 19 automated tests covering:

- Employee record validation.
- Missing and invalid fields.
- Department validation.
- Salary validation.
- Timestamp validation.
- Initial employee version creation.
- Department changes.
- Late-arriving events.
- Identical snapshots.
- Duplicate event handling.
- Empty input.
- Invalid CSV schema.
- Failure recovery and safe restart.

Run the test suite:

```bash
pytest -v
```

Latest verified result: **19 tests passed.**

## 11. Setup Instructions

### Step 1: Create a virtual environment

```bash
python -m venv .venv
```

### Step 2: Activate the environment (Windows PowerShell)

```powershell
.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Initialize the database

```bash
python -m src.database
```

### Step 5: Generate synthetic data

```bash
python -m src.generator
```

### Step 6: Execute the pipeline

```bash
python -m src.publisher
```

### Step 7: Run automated tests

```bash
pytest -v
```

## 12. Future Enhancements

- Cloud-based deployment.
- Incremental and scheduled ingestion.
- Enhanced pipeline monitoring and reporting.
- Parallel processing for larger datasets.
- Additional data-quality metrics.
- Integration with enterprise data platforms.

## 13. Conclusion

This project demonstrates a reliable employee historical data pipeline using Python, SQLite and SCD Type 2 methodology.

It focuses on data correctness, historical consistency, idempotency, late-arriving events, failure recovery and measurable processing performance.