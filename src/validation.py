
from datetime import datetime


REQUIRED_FIELDS = [
    "event_id",
    "employee_id",
    "employee_name",
    "department_code",
    "salary",
    "effective_at",
    "source_sequence",
]

VALID_DEPARTMENTS = {
    "IT", "FIN", "HR", "OPS", "SALES", "ENG"
}


def validate_employee_record(record):
    """
    Validate one employee event.

    Returns:
        (True, cleaned_record, None) for valid records.
        (False, None, error_message) for invalid records.
    """

    data = record["data"].copy()

    # 1. Check required fields
    for field in REQUIRED_FIELDS:
        if not data.get(field) or not data[field].strip():
            return False, None, f"Missing required field: {field}"

    # 2. Validate employee ID
    data["employee_id"] = data["employee_id"].strip()

    # 3. Validate employee name
    data["employee_name"] = data["employee_name"].strip()

    # 4. Validate department
    data["department_code"] = data["department_code"].strip().upper()

    if data["department_code"] not in VALID_DEPARTMENTS:
        return False, None, "Invalid department code"

    # 5. Validate salary
    try:
        data["salary"] = int(data["salary"])
    except ValueError:
        return False, None, "Salary must be an integer"

    if data["salary"] < 0:
        return False, None, "Salary cannot be negative"

    # 6. Validate effective date
    try:
        effective_at = datetime.fromisoformat(data["effective_at"])
        if effective_at.tzinfo is None or effective_at.utcoffset() is None:
            return False, None, "Timestamp must include timezone information"
    except ValueError:
        return False, None, "Invalid ISO-8601 timestamp"

    # 7. Validate source sequence
    try:
        data["source_sequence"] = int(data["source_sequence"])
    except ValueError:
        return False, None, "Source sequence must be an integer"

    if data["source_sequence"] < 1:
        return False, None, "Source sequence must be positive"

    data["effective_at"] = effective_at.isoformat()

    return True, data, None


if __name__ == "__main__":
    print("Employee validation module is ready.")
