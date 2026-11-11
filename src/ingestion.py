
import csv
from pathlib import Path


REQUIRED_COLUMNS = [
    "event_id",
    "employee_id",
    "employee_name",
    "department_code",
    "salary",
    "effective_at",
    "source_sequence",
]


def read_employee_csv(file_path):
    """
    Read employee events from a CSV file.

    Returns:
        records: List of dictionaries containing employee events.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    records = []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(
    (line for line in file if line.strip())
        )

        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or missing its header.")

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in reader.fieldnames
        ]

        if missing_columns:
            raise ValueError(
                f"Missing required CSV columns: {missing_columns}"
            )

        for row_number, row in enumerate(reader, start=2):
            records.append({
                "row_number": row_number,
                "data": row
            })

    return records


if __name__ == "__main__":
    print("CSV ingestion module is ready.")
