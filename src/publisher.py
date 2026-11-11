
import hashlib
import json
import uuid

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from src.database import get_connection
from src.ingestion import read_employee_csv
from src.validation import validate_employee_record
from src.scd2_processor import (
    build_employee_timeline,
    normalize_timestamp,
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def database_session():
    """Open a database connection and always close it."""

    connection = get_connection()

    try:
        with connection:
            yield connection
    finally:
        connection.close()


def calculate_payload_hash(event):
    """Hash the complete normalized source event."""

    payload = json.dumps(
        event,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_rejection(connection, run_id, source_file, record, reason):
    """Store a rejected source record."""

    data = record.get("data", {})
    event_id = data.get("event_id") or f"ROW_{record['row_number']}"

    connection.execute(
        """
        INSERT INTO rejected_records (
            run_id, source_file, source_row_number,
            raw_payload, rejection_reason, rejected_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            source_file,
            record["row_number"],
            json.dumps(data),
            reason,
            utc_now()
        )
    )

    connection.execute(
        """
        INSERT INTO event_processing_log (
            run_id, event_id, employee_id,
            processing_status, details, processed_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            event_id,
            data.get("employee_id"),
            "REJECTED",
            reason,
            utc_now()
        )
    )


def rebuild_employee(connection, employee_id, run_id):
    """Rebuild and atomically publish one employee's complete history."""

    old_rows = connection.execute(
        """
        SELECT *
        FROM dim_employee
        WHERE employee_id = ?
        """,
        (employee_id,)
    ).fetchall()

    old_by_id = {
        row["employee_version_id"]: dict(row)
        for row in old_rows
    }

    source_rows = connection.execute(
        """
        SELECT *
        FROM source_events
        WHERE employee_id = ?
        """,
        (employee_id,)
    ).fetchall()

    events = [
        {
            "event_id": row["event_id"],
            "employee_id": row["employee_id"],
            "employee_name": row["employee_name"],
            "department_code": row["department_code"],
            "salary": row["salary"],
            "effective_at": row["effective_at"],
            "source_sequence": row["source_sequence"],
        }
        for row in source_rows
    ]

    timeline = build_employee_timeline(events)

    new_by_id = {
        row["employee_version_id"]: row
        for row in timeline
    }

    inserted_count = len(
        set(new_by_id) - set(old_by_id)
    )

    updated_count = sum(
        1
        for version_id in set(new_by_id) & set(old_by_id)
        if any(
            new_by_id[version_id][field] != old_by_id[version_id][field]
            for field in [
                "effective_to",
                "is_current",
                "source_event_id",
            ]
        )
    )

    # This entire replacement is one transaction.
    connection.execute(
        "DELETE FROM dim_employee WHERE employee_id = ?",
        (employee_id,)
    )

    for version in timeline:
        previous = old_by_id.get(version["employee_version_id"])

        created_run_id = (
            previous["created_run_id"]
            if previous
            else run_id
        )

        connection.execute(
            """
            INSERT INTO dim_employee (
                employee_version_id,
                employee_id,
                employee_name,
                department_code,
                salary,
                effective_from,
                effective_to,
                is_current,
                attribute_hash,
                source_event_id,
                created_run_id,
                last_updated_run_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version["employee_version_id"],
                version["employee_id"],
                version["employee_name"],
                version["department_code"],
                version["salary"],
                version["effective_from"],
                version["effective_to"],
                version["is_current"],
                version["attribute_hash"],
                version["source_event_id"],
                created_run_id,
                run_id,
            )
        )

    connection.execute(
        """
        INSERT INTO event_processing_log (
            run_id, event_id, employee_id,
            processing_status, details, processed_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            "TIMELINE_REBUILD",
            employee_id,
            "COMPLETED",
            json.dumps({
                "versions": len(timeline),
                "inserted": inserted_count,
                "updated": updated_count,
            }),
            utc_now()
        )
    )

    return inserted_count, updated_count


def process_employee_csv(file_path):
    """Ingest, validate, deduplicate and publish employee events."""

    path = Path(file_path)
    source_file = str(path)

    run_id = str(uuid.uuid4())
    started_at = utc_now()

    input_count = 0
    accepted_count = 0
    rejected_count = 0
    inserted_count = 0
    updated_count = 0

    # Create the run before processing source events.
    with database_session() as connection:
        connection.execute(
            """
            INSERT INTO pipeline_runs (
                run_id, source_file, status, started_at
            )
            VALUES (?, ?, 'RUNNING', ?)
            """,
            (run_id, source_file, started_at)
        )

    try:
        records = read_employee_csv(file_path)
        input_count = len(records)

        impacted_employees = set()

        # Ingestion and event acceptance are one transaction.
        with database_session() as connection:

            for record in records:

                valid, event, reason = validate_employee_record(record)

                if not valid:
                    record_rejection(
                        connection, run_id, source_file,
                        record, reason
                    )
                    rejected_count += 1
                    continue

                event["effective_at"] = normalize_timestamp(
                    event["effective_at"]
                )

                payload_hash = calculate_payload_hash(event)

                existing = connection.execute(
                    """
                    SELECT payload_hash, employee_id
                    FROM source_events
                    WHERE event_id = ?
                    """,
                    (event["event_id"],)
                ).fetchone()

                # Identical event: safe idempotent no-op.
                if existing:
                    if existing["payload_hash"] == payload_hash:

                        impacted_employees.add(event["employee_id"])

                        connection.execute(
                            """
                            INSERT INTO event_processing_log (
                                run_id, event_id, employee_id,
                                processing_status, details, processed_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                run_id,
                                event["event_id"],
                                event["employee_id"],
                                "DUPLICATE_IGNORED",
                                "Identical event already exists",
                                utc_now()
                            )
                        )
                    else:
                        record_rejection(
                            connection, run_id, source_file,
                            record,
                            "Event ID already exists with different content"
                        )
                        rejected_count += 1

                    continue

                # Prevent ambiguous events at the same employee,
                # effective timestamp and source sequence.
                conflicting_sequence = connection.execute(
                    """
                    SELECT event_id
                    FROM source_events
                    WHERE employee_id = ?
                      AND effective_at = ?
                      AND source_sequence = ?
                    """,
                    (
                        event["employee_id"],
                        event["effective_at"],
                        event["source_sequence"]
                    )
                ).fetchone()

                if conflicting_sequence:
                    record_rejection(
                        connection, run_id, source_file,
                        record,
                        "Conflicting event for employee, effective timestamp and source sequence"
                    )
                    rejected_count += 1
                    continue

                connection.execute(
                    """
                    INSERT INTO source_events (
                        event_id,
                        employee_id,
                        employee_name,
                        department_code,
                        salary,
                        effective_at,
                        source_sequence,
                        payload_hash,
                        source_file,
                        source_row_number,
                        first_seen_run_id,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["event_id"],
                        event["employee_id"],
                        event["employee_name"],
                        event["department_code"],
                        event["salary"],
                        event["effective_at"],
                        event["source_sequence"],
                        payload_hash,
                        source_file,
                        record["row_number"],
                        run_id,
                        utc_now()
                    )
                )

                accepted_count += 1
                impacted_employees.add(event["employee_id"])

                connection.execute(
                    """
                    INSERT INTO event_processing_log (
                        run_id, event_id, employee_id,
                        processing_status, details, processed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        event["event_id"],
                        event["employee_id"],
                        "ACCEPTED",
                        "Source event stored successfully",
                        utc_now()
                    )
                )

        # Rebuild each affected employee separately.
        # A failure for one employee does not undo another
        # employee's already committed timeline.
        for employee_id in sorted(impacted_employees):

            with database_session() as connection:
                inserted, updated = rebuild_employee(
                    connection, employee_id, run_id
                )

                inserted_count += inserted
                updated_count += updated

        completed_at = utc_now()

        with database_session() as connection:
            connection.execute(
                """
                UPDATE pipeline_runs
                SET status = 'COMPLETED',
                    completed_at = ?,
                    input_count = ?,
                    accepted_count = ?,
                    rejected_count = ?,
                    inserted_count = ?,
                    updated_count = ?
                WHERE run_id = ?
                """,
                (
                    completed_at,
                    input_count,
                    accepted_count,
                    rejected_count,
                    inserted_count,
                    updated_count,
                    run_id
                )
            )

        report = {
            "run_id": run_id,
            "status": "COMPLETED",
            "input_count": input_count,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "inserted_versions": inserted_count,
            "updated_versions": updated_count,
            "employees_rebuilt": len(impacted_employees),
            "source_file": source_file,
        }

        return report

    except Exception as error:

        with database_session() as connection:
            connection.execute(
                """
                UPDATE pipeline_runs
                SET status = 'FAILED',
                    completed_at = ?,
                    input_count = ?,
                    accepted_count = ?,
                    rejected_count = ?,
                    inserted_count = ?,
                    updated_count = ?,
                    error_message = ?
                WHERE run_id = ?
                """,
                (
                    utc_now(),
                    input_count,
                    accepted_count,
                    rejected_count,
                    inserted_count,
                    updated_count,
                    str(error),
                    run_id
                )
            )

        raise


if __name__ == "__main__":
    result = process_employee_csv("data/input/employees.csv")
    print(json.dumps(result, indent=4))
