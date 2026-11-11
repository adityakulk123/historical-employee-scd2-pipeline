# Test and Performance Evidence

## 1. Automated Test Results

The project automated test suite was executed using Pytest.

**Latest verified result: 19 passed.**

Test coverage includes:

- Valid employee record processing.
- Missing required fields.
- Invalid department codes.
- Invalid salary values.
- Invalid timestamps.
- Initial SCD Type 2 version creation.
- Employee attribute changes.
- Late-arriving events.
- Identical employee snapshots.
- Duplicate event handling.
- Conflicting event IDs.
- Empty input files.
- Invalid CSV schema.
- Safe recovery after publishing failure.

Execution command:

```bash
pytest -v
```

## 2. Large Dataset Performance Test

A synthetic dataset containing 100,000 employee events was used to evaluate pipeline performance.

| Metric | Verified Result |
|---|---:|
| Input records | 100,000 |
| Accepted records | 100,000 |
| Rejected records | 0 |
| Distinct employees | 1,000 |
| Historical employee versions | 40,653 |
| Employees rebuilt | 1,000 |
| Processing time | 33.30 seconds |
| Throughput | 3,002.67 records/second |

**Execution status:** COMPLETED

## 3. Database Integrity Verification

The resulting SQLite database was checked for SCD Type 2 consistency.

| Integrity Check | Result |
|---|---|
| Employee versions created | 40,653 |
| Current employee versions | 1,000 |
| Employees with multiple current versions | 0 |
| Invalid effective date ranges | 0 |
| Employees without a current version | 0 |

**Result:** All five integrity checks passed.

## 4. Index Performance Verification

The employee timeline lookup was checked using SQLite's `EXPLAIN QUERY PLAN`.

The query used:

`idx_source_events_employee_timeline`

This index supports employee event retrieval using employee ID, effective timestamp and source sequence.

## 5. Reproducibility

The synthetic data generator uses a fixed random seed.

Two generations using the same configuration produced identical CSV file hashes:

`4ACC94E545A59D7A5BE3E1A04FA33C194602C211F12D4EE5F262F996394A651C`

This confirms reproducibility for the tested generator configuration.

## 6. Test Environment

- Operating System: Windows
- Python: 3.15.0
- Database: SQLite 3.53.4
- Testing Framework: Pytest 9.2.0
- Development Environment: Visual Studio Code

## 7. Conclusion

The pipeline passed its latest 19 automated tests and successfully processed a 100,000-record synthetic dataset.

Database integrity checks confirmed that employee historical versions maintained the expected SCD Type 2 constraints.