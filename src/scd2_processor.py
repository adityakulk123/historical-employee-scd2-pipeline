
import hashlib
import json

from datetime import datetime, timezone


def normalize_timestamp(value):
    """Convert an ISO-8601 timestamp to UTC."""

    timestamp = datetime.fromisoformat(value)

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Timestamp must contain timezone information")

    return timestamp.astimezone(timezone.utc).isoformat()


def calculate_attribute_hash(event):
    """Create a hash from tracked employee attributes."""

    attributes = {
        "employee_name": event["employee_name"],
        "department_code": event["department_code"],
        "salary": event["salary"],
    }

    canonical_data = json.dumps(
        attributes,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(canonical_data.encode("utf-8")).hexdigest()


def generate_version_id(employee_id, effective_from, attribute_hash):
    """Generate a deterministic ID for an employee version."""

    value = f"{employee_id}|{effective_from}|{attribute_hash}"

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_employee_timeline(events):
    """
    Build an SCD Type 2 timeline for one employee.

    Events are sorted by effective date and source sequence.
    Consecutive identical employee states are collapsed.
    """

    if not events:
        return []

    normalized_events = []

    for event in events:
        item = event.copy()
        item["effective_at"] = normalize_timestamp(
            item["effective_at"]
        )
        normalized_events.append(item)

    # Sort by effective date, sequence and event ID.
    normalized_events.sort(
        key=lambda event: (
            event["effective_at"],
            event["source_sequence"],
            event["event_id"]
        )
    )

    # If multiple events have the same effective timestamp,
    # the highest source sequence determines the state at that time.
    latest_at_timestamp = {}

    for event in normalized_events:
        latest_at_timestamp[event["effective_at"]] = event

    ordered_events = sorted(
        latest_at_timestamp.values(),
        key=lambda event: event["effective_at"]
    )

    # Keep only actual changes in employee attributes.
    versions = []

    for event in ordered_events:
        attribute_hash = calculate_attribute_hash(event)

        if versions and versions[-1]["attribute_hash"] == attribute_hash:
            continue

        versions.append({
            "employee_id": event["employee_id"],
            "employee_name": event["employee_name"],
            "department_code": event["department_code"],
            "salary": event["salary"],
            "effective_from": event["effective_at"],
            "attribute_hash": attribute_hash,
            "source_event_id": event["event_id"],
        })

    # Calculate effective_to and current-row status.
    timeline = []

    for index, version in enumerate(versions):
        effective_to = (
            versions[index + 1]["effective_from"]
            if index + 1 < len(versions)
            else None
        )

        timeline.append({
            **version,
            "employee_version_id": generate_version_id(
                version["employee_id"],
                version["effective_from"],
                version["attribute_hash"]
            ),
            "effective_to": effective_to,
            "is_current": 1 if effective_to is None else 0,
        })

    return timeline


if __name__ == "__main__":
    print("SCD Type 2 processing module is ready.")
