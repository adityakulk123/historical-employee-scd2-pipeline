
import argparse
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

FIELDNAMES = [
    "event_id",
    "employee_id",
    "employee_name",
    "department_code",
    "salary",
    "effective_at",
    "source_sequence",
]

DEPARTMENTS = ["IT", "FIN", "HR", "OPS", "SALES", "ENG"]

FIRST_NAMES = [
    "Aarav", "Aditya", "Rahul", "Priya", "Sneha",
    "Kiran", "Rohan", "Ananya", "Vikram", "Meera",
]

LAST_NAMES = [
    "Sharma", "Reddy", "Kumar", "Patel", "Rao",
    "Verma", "Gupta", "Naidu", "Singh", "Das",
]


def generate_events(
    employee_count=1000,
    events_per_employee=100,
    seed=42,
):
    """Generate reproducible synthetic employee events."""

    if employee_count < 1:
        raise ValueError("Employee count must be at least 1.")

    if events_per_employee < 1:
        raise ValueError("Events per employee must be at least 1.")

    rng = random.Random(seed)
    all_events = []

    base_date = datetime(
        2025, 1, 1, tzinfo=timezone.utc
    )

    for employee_number in range(1, employee_count + 1):

        employee_id = f"EMP-{employee_number:06d}"

        employee_name = (
            f"{rng.choice(FIRST_NAMES)} "
            f"{rng.choice(LAST_NAMES)}"
        )

        department = rng.choice(DEPARTMENTS)
        salary = rng.randint(25000, 90000)

        effective_date = base_date

        for event_number in range(1, events_per_employee + 1):

            if event_number > 1:

                effective_date += timedelta(
                    days=rng.randint(1, 30)
                )

                # Occasionally change department.
                if rng.random() < 0.08:
                    department = rng.choice(
                        [d for d in DEPARTMENTS if d != department]
                    )

                # Occasionally change salary.
                if rng.random() < 0.35:
                    salary_change = rng.randint(-5000, 10000)
                    salary = max(15000, salary + salary_change)

            event = {
                "event_id": (
                    f"EVT-{employee_number:06d}-"
                    f"{event_number:04d}"
                ),
                "employee_id": employee_id,
                "employee_name": employee_name,
                "department_code": department,
                "salary": salary,
                "effective_at": effective_date.isoformat(),
                "source_sequence": event_number,
            }

            all_events.append(event)

    # Shuffle records to simulate out-of-order arrival.
    rng.shuffle(all_events)

    return all_events


def write_events(events, output_path):
    """Write generated events to a CSV file."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
        )

        writer.writeheader()
        writer.writerows(events)


def main():

    parser = argparse.ArgumentParser(
        description="Generate synthetic SCD2 employee events."
    )

    parser.add_argument(
        "--employees",
        type=int,
        default=1000,
        help="Number of employees.",
    )

    parser.add_argument(
        "--events-per-employee",
        type=int,
        default=100,
        help="Number of events per employee.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/input/employees_100k.csv",
        help="Output CSV path relative to project root.",
    )

    args = parser.parse_args()

    output_path = Path(args.output)

    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    events = generate_events(
        employee_count=args.employees,
        events_per_employee=args.events_per_employee,
        seed=args.seed,
    )

    write_events(events, output_path)

    print("\n========== DATA GENERATION REPORT ==========")
    print(f"Employees             : {args.employees}")
    print(f"Events per employee   : {args.events_per_employee}")
    print(f"Total events generated: {len(events)}")
    print(f"Random seed           : {args.seed}")
    print(f"Output file           : {output_path}")
    print("Status                : SUCCESS")
    print("============================================")


if __name__ == "__main__":
    main()
