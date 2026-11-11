

## 1. Complete Architecture and Code Review

Act as a senior data engineer with 10+ years of experience. Review my complete Historical Employee SCD Type 2 Pipeline project, including Python modules, SQLite schema, ingestion, validation, transformation, and publishing layers. Identify architectural weaknesses, code duplication, missing edge cases, and production risks. Do not rewrite working code unnecessarily. Provide prioritized recommendations with explanations.

## 2. SCD Type 2 Historical Data Correctness

Act as an expert in data warehousing and dimensional modelling. Examine my SCD Type 2 implementation and verify that employee history is maintained correctly. Check effective_from, effective_to, is_current, attribute_hash, and deterministic version IDs. Verify half-open date intervals, change detection, consecutive identical records, and multiple updates for the same employee. Provide test cases for every identified edge case.

## 3. Late-Arriving and Out-of-Order Events

Act as a senior data engineer. Analyse how my pipeline processes late-arriving and out-of-order employee events. Consider a scenario where an employee's January record arrives after their February and March records have already been processed. Explain how to rebuild the employee timeline without losing valid history, creating overlapping date ranges, or producing multiple current records. Recommend an atomic and restart-safe implementation.

## 4. Idempotency and Duplicate-Event Handling

Review the idempotency mechanism in my historical employee pipeline. Test scenarios involving the same input file being executed multiple times, identical event IDs with identical payloads, identical event IDs with conflicting payloads, and duplicate employee events. Verify that rerunning the pipeline does not create duplicate source events or dimension versions. Identify any conditions that could cause incorrect updates during retries.

## 5. Failure Recovery and Transaction Safety

Act as a production data pipeline reliability engineer. Review my transaction strategy and restart-recovery mechanism. Simulate failures during ingestion, validation, employee timeline rebuilding, and dimension publishing. Determine whether partially processed employees can be safely recovered without corrupting previously published data. Recommend appropriate transaction boundaries, error logging, retry behaviour, and recovery tests.

## 6. Data Quality and Schema Validation

Perform a detailed data quality audit of my employee event ingestion pipeline. Evaluate missing required fields, invalid timestamps, timezone handling, negative salaries, invalid department references, duplicate records, malformed CSV files, and unexpected schema changes. Recommend measurable data quality metrics, rejection reasons, quarantine handling, and automated tests. Preserve valid records even when other records in the batch are rejected.

## 7. Performance Optimization for 1 Million Records

Act as a senior Python and database performance engineer. Evaluate my pipeline's performance using its existing 100,000-record benchmark as a baseline. Identify bottlenecks in CSV ingestion, validation, hashing, SQLite queries, timeline reconstruction, indexing, and publishing. Explain how to scale towards 1 million records using batching, executemany, efficient queries, and bounded parallelism. Preserve data correctness, deterministic IDs, and idempotency. Avoid introducing unnecessary infrastructure.

## 8. Automated Testing and Edge-Case Coverage

Act as a senior QA automation engineer specialising in data engineering. Review my existing pytest suite and identify missing test coverage. Design tests for happy paths, empty input, malformed CSV, missing fields, duplicate events, conflicting IDs, late-arriving events, out-of-order updates, invalid references, same-input reruns, partial failures, and recovery. Include assertions for database integrity, historical versions, current records, and rejection counts. Do not modify production code just to make tests pass.





