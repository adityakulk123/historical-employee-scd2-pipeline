
import csv

import pytest

import src.database as database
import src.publisher as publisher


FIELDNAMES = [
    "event_id",
    "employee_id",
    "employee_name",
    "department_code",
    "salary",
    "effective_at",
    "source_sequence",
]


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    """Give every test its own temporary database."""
    test_db_path = tmp_path / "publisher_test.db"

    monkeypatch.setattr(database, "DB_PATH", test_db_path)
    database.initialize_database()

    return test_db_path


def write_csv(tmp_path, filename, rows, fieldnames=FIELDNAMES):
    """Create a CSV file for a publisher test."""
    file_path = tmp_path / filename

    with file_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return file_path


def sample_event(
    event_id="EVT-001",
    employee_id="EMP-9001",
    employee_name="Test Employee",
    department_code="IT",
    salary=40000,
    effective_at="2026-01-01T00:00:00+00:00",
    source_sequence=1,
):
    return {
        "event_id": event_id,
        "employee_id": employee_id,
        "employee_name": employee_name,
        "department_code": department_code,
        "salary": salary,
        "effective_at": effective_at,
        "source_sequence": source_sequence,
    }


def get_table_count(table_name):
    """Return a row count from the isolated database."""
    allowed_tables = {
        "source_events",
        "dim_employee",
        "rejected_records",
        "pipeline_runs",
    }
    assert table_name in allowed_tables

    connection = database.get_connection()
    try:
        result = connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()
        return result[0]
    finally:
        connection.close()


def get_run_statuses():
    connection = database.get_connection()
    try:
        rows = connection.execute(
            "SELECT status FROM pipeline_runs ORDER BY started_at"
        ).fetchall()
        return [row["status"] for row in rows]
    finally:
        connection.close()


def test_same_input_rerun_is_idempotent(
    isolated_database, tmp_path
):
    rows = [sample_event()]
    file_path = write_csv(tmp_path, "employees.csv", rows)

    first_report = publisher.process_employee_csv(str(file_path))
    second_report = publisher.process_employee_csv(str(file_path))

    assert first_report["status"] == "COMPLETED"
    assert first_report["accepted_count"] == 1

    assert second_report["status"] == "COMPLETED"
    assert second_report["accepted_count"] == 0
    assert second_report["inserted_versions"] == 0
    assert second_report["rejected_count"] == 0

    assert get_table_count("source_events") == 1
    assert get_table_count("dim_employee") == 1
    assert get_table_count("pipeline_runs") == 2


def test_conflicting_event_id_is_rejected(
    isolated_database, tmp_path
):
    original_event = sample_event()
    file_path = write_csv(
        tmp_path, "original.csv", [original_event]
    )

    publisher.process_employee_csv(str(file_path))

    conflicting_event = sample_event(salary=45000)
    conflict_file = write_csv(
        tmp_path, "conflict.csv", [conflicting_event]
    )

    report = publisher.process_employee_csv(str(conflict_file))

    assert report["status"] == "COMPLETED"
    assert report["accepted_count"] == 0
    assert report["rejected_count"] == 1

    assert get_table_count("source_events") == 1
    assert get_table_count("rejected_records") == 1
    assert get_table_count("dim_employee") == 1


def test_invalid_department_is_quarantined(
    isolated_database, tmp_path
):
    invalid_event = sample_event(department_code="UNKNOWN")
    file_path = write_csv(
        tmp_path, "invalid_department.csv", [invalid_event]
    )

    report = publisher.process_employee_csv(str(file_path))

    assert report["status"] == "COMPLETED"
    assert report["accepted_count"] == 0
    assert report["rejected_count"] == 1

    assert get_table_count("source_events") == 0
    assert get_table_count("rejected_records") == 1
    assert get_table_count("dim_employee") == 0


def test_empty_input_completes_successfully(
    isolated_database, tmp_path
):
    file_path = write_csv(tmp_path, "empty.csv", [])

    report = publisher.process_employee_csv(str(file_path))

    assert report["status"] == "COMPLETED"
    assert report["input_count"] == 0
    assert report["accepted_count"] == 0
    assert report["rejected_count"] == 0

    assert get_table_count("source_events") == 0
    assert get_table_count("dim_employee") == 0
    assert get_table_count("pipeline_runs") == 1


def test_invalid_csv_schema_marks_run_failed(
    isolated_database, tmp_path
):
    incomplete_fields = [
        "event_id",
        "employee_id",
        "employee_name",
        "department_code",
        "salary",
        "effective_at",
    ]

    file_path = write_csv(
        tmp_path,
        "invalid_schema.csv",
        [],
        fieldnames=incomplete_fields,
    )

    with pytest.raises(ValueError):
        publisher.process_employee_csv(str(file_path))

    assert get_table_count("pipeline_runs") == 1
    assert get_run_statuses() == ["FAILED"]

    assert get_table_count("source_events") == 0
    assert get_table_count("dim_employee") == 0


def test_failed_publish_can_be_restarted_safely(
    isolated_database, tmp_path, monkeypatch
):
    rows = [sample_event()]
    file_path = write_csv(tmp_path, "restart.csv", rows)

    real_rebuild = publisher.rebuild_employee
    call_count = {"value": 0}

    def fail_once(connection, employee_id, run_id):
        call_count["value"] += 1

        if call_count["value"] == 1:
            raise RuntimeError("Simulated publishing failure")

        return real_rebuild(connection, employee_id, run_id)

    monkeypatch.setattr(
        publisher, "rebuild_employee", fail_once
    )

    # First execution: source event is accepted,
    # but publishing fails.
    with pytest.raises(
        RuntimeError,
        match="Simulated publishing failure",
    ):
        publisher.process_employee_csv(str(file_path))

    assert get_table_count("source_events") == 1
    assert get_table_count("dim_employee") == 0
    assert get_run_statuses() == ["FAILED"]

    # Second execution: duplicate event is recognized,
    # and the employee timeline is rebuilt.
    retry_report = publisher.process_employee_csv(str(file_path))

    assert retry_report["status"] == "COMPLETED"
    assert retry_report["accepted_count"] == 0
    assert retry_report["inserted_versions"] == 1

    assert get_table_count("source_events") == 1
    assert get_table_count("dim_employee") == 1
    assert get_table_count("pipeline_runs") == 2
    assert get_run_statuses() == ["FAILED", "COMPLETED"]
