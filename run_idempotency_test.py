
from pathlib import Path
import sqlite3
import time

from src import database, publisher

ROOT = Path(__file__).resolve().parent

INPUT_FILE = ROOT / "data" / "input" / "employees_100k.csv"

DB_PATH = (
    ROOT / "data" / "output"
    / "performance_100k_optimized_20261111.db"
)


def get_snapshot():
    with sqlite3.connect(DB_PATH) as conn:
        source_count = conn.execute(
            "SELECT COUNT(*) FROM source_events"
        ).fetchone()[0]

        version_count = conn.execute(
            "SELECT COUNT(*) FROM dim_employee"
        ).fetchone()[0]

        current_count = conn.execute(
            "SELECT COUNT(*) FROM dim_employee WHERE is_current = 1"
        ).fetchone()[0]

        # Compare business and historical attributes,
        # excluding last_updated_run_id.
        versions = conn.execute("""
            SELECT employee_version_id, employee_id,
                   employee_name, department_code, salary,
                   effective_from, effective_to, is_current,
                   attribute_hash, source_event_id, created_run_id
            FROM dim_employee
            ORDER BY employee_version_id
        """).fetchall()

        return source_count, version_count, current_count, versions


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    database.DB_PATH = DB_PATH

    print("Capturing database state before rerun...")
    before = get_snapshot()

    print("Processing the same 100K input again...")
    start = time.perf_counter()

    report = publisher.process_employee_csv(str(INPUT_FILE))

    elapsed = time.perf_counter() - start

    after = get_snapshot()

    print("\n========== IDEMPOTENCY RESULTS ==========")
    print("Run status:", report["status"])
    print("Input records:", report["input_count"])
    print("Accepted records:", report["accepted_count"])
    print("Rejected records:", report["rejected_count"])
    print(f"Rerun time: {elapsed:.2f} seconds")

    print("\nBefore:", before[:3])
    print("After: ", after[:3])

    print("\nSource event count unchanged:", before[0] == after[0])
    print("Dimension version count unchanged:", before[1] == after[1])
    print("Current version count unchanged:", before[2] == after[2])
    print("Historical data unchanged:", before[3] == after[3])

    success = (
        report["status"] == "COMPLETED"
        and before == after
    )

    print("\nIDEMPOTENCY TEST:", "PASSED" if success else "FAILED")


if __name__ == "__main__":
    main()
