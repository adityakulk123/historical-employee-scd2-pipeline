
from pathlib import Path
import sqlite3
import time

from src import database, publisher

PROJECT_ROOT = Path(__file__).resolve().parent

INPUT_FILE = PROJECT_ROOT / "data" / "input" / "employees_100k.csv"

# Use a completely separate database for this test.
DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "performance_100k_optimized_20261111.db"
)


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    if DB_PATH.exists():
        raise FileExistsError(
            f"Test database already exists: {DB_PATH}. "
            "Choose a new database filename before testing."
        )

    # Redirect database operations to the performance database.
    database.DB_PATH = DB_PATH

    print("Initializing performance test database...")
    database.initialize_database()

    print("Starting 100K record processing...")
    start_time = time.perf_counter()

    report = publisher.process_employee_csv(str(INPUT_FILE))

    elapsed = time.perf_counter() - start_time

    # Verify actual database counts.
    with sqlite3.connect(DB_PATH) as connection:
        source_events = connection.execute(
            "SELECT COUNT(*) FROM source_events"
        ).fetchone()[0]

        employee_versions = connection.execute(
            "SELECT COUNT(*) FROM dim_employee"
        ).fetchone()[0]

        rejected_records = connection.execute(
            "SELECT COUNT(*) FROM rejected_records"
        ).fetchone()[0]

        employee_count = connection.execute(
            "SELECT COUNT(DISTINCT employee_id) FROM source_events"
        ).fetchone()[0]

    throughput = (
        report["input_count"] / elapsed if elapsed > 0 else 0
    )

    print("\n========== PERFORMANCE RESULTS ==========")
    print(f"Run ID: {report['run_id']}")
    print(f"Status: {report['status']}")
    print(f"Input records: {report['input_count']}")
    print(f"Accepted records: {report['accepted_count']}")
    print(f"Rejected records: {report['rejected_count']}")
    print(f"Source events in DB: {source_events}")
    print(f"Employee versions in DB: {employee_versions}")
    print(f"Distinct employees: {employee_count}")
    print(f"Rejected records in DB: {rejected_records}")
    print(f"Employees rebuilt: {report['employees_rebuilt']}")
    print(f"Elapsed time: {elapsed:.2f} seconds")
    print(f"Throughput: {throughput:.2f} records/second")
    print(f"Database: {DB_PATH}")
    print("==========================================")


if __name__ == "__main__":
    main()
