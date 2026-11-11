# Data Dictionary – Historical Employee SCD Type 2 Pipeline

## 1. Overview

This document describes the database schema used by the Historical Employee Data Pipeline.

The database uses SQLite and contains six main tables to manage employee events, historical employee versions, pipeline execution, reference data, rejected records, and processing logs.

## 2. Database Tables

### 2.1 pipeline_runs

**Purpose:** Stores information about each pipeline execution.

| Column | Data Type | Constraint | Description |
|---|---|---|---|
| run_id | TEXT | Primary Key | Unique pipeline execution identifier |
| source_file | TEXT | NOT NULL | Input CSV file name |
| status | TEXT | NOT NULL, CHECK | Execution status: RUNNING, COMPLETED or FAILED |
| started_at | TEXT | NOT NULL | Pipeline start timestamp |
| completed_at | TEXT | Nullable | Pipeline completion timestamp |
| input_count | INTEGER | Default 0 | Total input records |
| accepted_count | INTEGER | Default 0 | Accepted records |
| rejected_count | INTEGER | Default 0 | Rejected records |
| inserted_count | INTEGER | Default 0 | Newly inserted employee versions |
| updated_count | INTEGER | Default 0 | Updated employee versions |
| error_message | TEXT | Nullable | Error details if execution fails |

### 2.2 ref_department

**Purpose:** Maintains valid department reference data.

| Column | Data Type | Constraint | Description |
|---|---|---|---|
| department_code | TEXT | Primary Key | Unique department code |
| department_name | TEXT | NOT NULL, UNIQUE | Department name |

Seeded departments: IT, FIN, HR, OPS, SALES and ENG.

### 2.3 source_events

**Purpose:** Stores accepted employee source events and provides the historical event data used to rebuild employee timelines.

| Column | Data Type | Constraint | Description |
|---|---|---|---|
| event_id | TEXT | Primary Key | Unique source event identifier |
| employee_id | TEXT | NOT NULL | Employee business identifier |
| employee_name | TEXT | NOT NULL | Employee name |
| department_code | TEXT | NOT NULL, Foreign Key | References ref_department |
| salary | INTEGER | NOT NULL, CHECK | Employee salary; must be non-negative |
| effective_at | TEXT | NOT NULL | Timestamp when the event becomes effective |
| source_sequence | INTEGER | NOT NULL, CHECK | Event sequence; must be at least 1 |
| payload_hash | TEXT | NOT NULL | Hash representing the event payload |
| source_file | TEXT | NOT NULL | Original source file |
| source_row_number | INTEGER | NOT NULL | Original CSV row number |
| first_seen_run_id | TEXT | NOT NULL, Foreign Key | Pipeline run that first accepted the event |
| created_at | TEXT | NOT NULL | Event storage timestamp |

**Index:** `idx_source_events_employee_timeline`

Supports employee timeline retrieval ordered by employee ID, effective timestamp and source sequence.

### 2.4 dim_employee

**Purpose:** Maintains employee historical versions using Slowly Changing Dimension Type 2.

| Column | Data Type | Constraint | Description |
|---|---|---|---|
| employee_version_id | TEXT | Primary Key | Deterministic employee version identifier |
| employee_id | TEXT | NOT NULL | Employee business identifier |
| employee_name | TEXT | NOT NULL | Employee name for this version |
| department_code | TEXT | NOT NULL | Department for this version |
| salary | INTEGER | NOT NULL, CHECK | Salary for this version |
| effective_from | TEXT | NOT NULL | Start of version validity |
| effective_to | TEXT | Nullable | End of version validity |
| is_current | INTEGER | NOT NULL, CHECK | 1 for current version; 0 for historical version |
| attribute_hash | TEXT | NOT NULL | Hash of tracked employee attributes |
| source_event_id | TEXT | NOT NULL, Foreign Key | Source event associated with this version |
| created_run_id | TEXT | NOT NULL, Foreign Key | Pipeline run that created the version |
| last_updated_run_id | TEXT | NOT NULL, Foreign Key | Most recent pipeline run that updated the version |

**Important constraints:**

- Only one current version is allowed per employee.
- Current versions must have `effective_to` as NULL.
- Historical versions must have a non-NULL `effective_to`.
- `effective_to` must be later than `effective_from`.

**Indexes:**
- `idx_one_current_version_per_employee`: Unique partial index allowing only one current version per employee.
- `idx_employee_effective_dates`: Supports employee history queries using employee ID and effective date.

### 2.5 rejected_records

**Purpose:** Stores invalid or conflicting source records for auditing and troubleshooting.

| Column | Data Type | Constraint | Description |
|---|---|---|---|
| reject_id | INTEGER | Primary Key, AUTOINCREMENT | Unique rejection record identifier |
| run_id | TEXT | NOT NULL, Foreign Key | Associated pipeline run |
| source_file | TEXT | NOT NULL | Original source file |
| source_row_number | INTEGER | NOT NULL | Original CSV row number |
| raw_payload | TEXT | Nullable | Original rejected record |
| rejection_reason | TEXT | NOT NULL | Reason for rejection |
| rejected_at | TEXT | NOT NULL | Rejection timestamp |

### 2.6 event_processing_log

**Purpose:** Maintains event-level processing activity for traceability and monitoring.

| Column | Data Type | Constraint | Description |
|---|---|---|---|
| log_id | INTEGER | Primary Key, AUTOINCREMENT | Unique log identifier |
| run_id | TEXT | NOT NULL, Foreign Key | Associated pipeline execution |
| event_id | TEXT | NOT NULL | Source event identifier |
| employee_id | TEXT | Nullable | Employee business identifier |
| processing_status | TEXT | NOT NULL | Event processing result |
| details | TEXT | Nullable | Additional processing information |
| processed_at | TEXT | NOT NULL | Event processing timestamp |

## 3. Relationships

- `source_events.department_code` references `ref_department.department_code`.
- `source_events.first_seen_run_id` references `pipeline_runs.run_id`.
- `dim_employee.source_event_id` references `source_events.event_id`.
- `dim_employee.created_run_id` references `pipeline_runs.run_id`.
- `dim_employee.last_updated_run_id` references `pipeline_runs.run_id`.
- `rejected_records.run_id` references `pipeline_runs.run_id`.
- `event_processing_log.run_id` references `pipeline_runs.run_id`.

## 4. Data Management Rules

1. Every accepted source event has a unique event ID.
2. Invalid records are stored separately in the rejection table.
3. Employee history is maintained through SCD Type 2.
4. A new historical version is created when tracked employee attributes change.
5. Historical versions have an effective start and end timestamp.
6. The current version has a NULL effective end timestamp.
7. Only one current version is permitted per employee.
8. Pipeline execution details are recorded for auditing and recovery.

## 5. Conclusion

The database schema provides a structured foundation for historical employee data processing, data validation, auditability, and reliable SCD Type 2 version management.