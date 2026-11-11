
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "output"
DB_PATH = DATA_DIR / "scd2_pipeline.db"


def get_connection():
    """Create a database connection with foreign keys enabled."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """Create all tables and indexes required by the pipeline."""

    schema = """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
        run_id TEXT PRIMARY KEY,
        source_file TEXT NOT NULL,
        status TEXT NOT NULL
            CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED')),
        started_at TEXT NOT NULL,
        completed_at TEXT,
        input_count INTEGER DEFAULT 0,
        accepted_count INTEGER DEFAULT 0,
        rejected_count INTEGER DEFAULT 0,
        inserted_count INTEGER DEFAULT 0,
        updated_count INTEGER DEFAULT 0,
        error_message TEXT
    );

    CREATE TABLE IF NOT EXISTS ref_department (
        department_code TEXT PRIMARY KEY,
        department_name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS source_events (
        event_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        employee_name TEXT NOT NULL,
        department_code TEXT NOT NULL,
        salary INTEGER NOT NULL CHECK (salary >= 0),
        effective_at TEXT NOT NULL,
        source_sequence INTEGER NOT NULL CHECK (source_sequence >= 1),
        payload_hash TEXT NOT NULL,
        source_file TEXT NOT NULL,
        source_row_number INTEGER NOT NULL,
        first_seen_run_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (department_code)
            REFERENCES ref_department(department_code),
        FOREIGN KEY (first_seen_run_id)
            REFERENCES pipeline_runs(run_id)
    );

    CREATE INDEX IF NOT EXISTS
        idx_source_events_employee_timeline
    ON source_events(
        employee_id,
        effective_at,
        source_sequence
    );

    CREATE TABLE IF NOT EXISTS dim_employee (
        employee_version_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        employee_name TEXT NOT NULL,
        department_code TEXT NOT NULL,
        salary INTEGER NOT NULL CHECK (salary >= 0),
        effective_from TEXT NOT NULL,
        effective_to TEXT,
        is_current INTEGER NOT NULL CHECK (is_current IN (0, 1)),
        attribute_hash TEXT NOT NULL,
        source_event_id TEXT NOT NULL,
        created_run_id TEXT NOT NULL,
        last_updated_run_id TEXT NOT NULL,
        CHECK (
            effective_to IS NULL
            OR effective_to > effective_from
        ),
        CHECK (
            (is_current = 1 AND effective_to IS NULL)
            OR
            (is_current = 0 AND effective_to IS NOT NULL)
        ),
        FOREIGN KEY (source_event_id)
            REFERENCES source_events(event_id),
        FOREIGN KEY (created_run_id)
            REFERENCES pipeline_runs(run_id),
        FOREIGN KEY (last_updated_run_id)
            REFERENCES pipeline_runs(run_id)
    );

    CREATE UNIQUE INDEX IF NOT EXISTS
        idx_one_current_version_per_employee
    ON dim_employee(employee_id)
    WHERE is_current = 1;

    CREATE INDEX IF NOT EXISTS
        idx_employee_effective_dates
    ON dim_employee(employee_id, effective_from);

    CREATE TABLE IF NOT EXISTS rejected_records (
        reject_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        source_file TEXT NOT NULL,
        source_row_number INTEGER NOT NULL,
        raw_payload TEXT,
        rejection_reason TEXT NOT NULL,
        rejected_at TEXT NOT NULL,
        FOREIGN KEY (run_id)
            REFERENCES pipeline_runs(run_id)
    );

    CREATE TABLE IF NOT EXISTS event_processing_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        event_id TEXT NOT NULL,
        employee_id TEXT,
        processing_status TEXT NOT NULL,
        details TEXT,
        processed_at TEXT NOT NULL,
        FOREIGN KEY (run_id)
            REFERENCES pipeline_runs(run_id)
    );
    """

    with get_connection() as connection:
        connection.executescript(schema)

        departments = [
            ("IT", "Information Technology"),
            ("FIN", "Finance"),
            ("HR", "Human Resources"),
            ("OPS", "Operations"),
            ("SALES", "Sales"),
            ("ENG", "Engineering"),
        ]

        connection.executemany(
            """
            INSERT OR IGNORE INTO ref_department
            (department_code, department_name)
            VALUES (?, ?)
            """,
            departments
        )

    print(f"Database initialized successfully: {DB_PATH}")


if __name__ == "__main__":
    initialize_database()
