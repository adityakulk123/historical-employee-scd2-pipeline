
import pytest

from src.validation import validate_employee_record


def make_record(**overrides):
    data = {
        "event_id": "EVT001",
        "employee_id": "101",
        "employee_name": "Kiran",
        "department_code": "IT",
        "salary": "40000",
        "effective_at": "2026-01-01T09:00:00+00:00",
        "source_sequence": "1",
    }

    data.update(overrides)

    return {
        "row_number": 2,
        "data": data
    }


def test_valid_employee_record():
    valid, cleaned, error = validate_employee_record(make_record())

    assert valid is True
    assert cleaned["employee_id"] == "101"
    assert cleaned["salary"] == 40000
    assert cleaned["source_sequence"] == 1
    assert error is None


def test_missing_employee_name_is_rejected():
    valid, cleaned, error = validate_employee_record(
        make_record(employee_name="")
    )

    assert valid is False
    assert cleaned is None
    assert error == "Missing required field: employee_name"


def test_invalid_department_is_rejected():
    valid, cleaned, error = validate_employee_record(
        make_record(department_code="MARKETING")
    )

    assert valid is False
    assert error == "Invalid department code"


def test_non_integer_salary_is_rejected():
    valid, cleaned, error = validate_employee_record(
        make_record(salary="forty thousand")
    )

    assert valid is False
    assert error == "Salary must be an integer"


def test_negative_salary_is_rejected():
    valid, cleaned, error = validate_employee_record(
        make_record(salary="-500")
    )

    assert valid is False
    assert error == "Salary cannot be negative"


def test_timestamp_without_timezone_is_rejected():
    valid, cleaned, error = validate_employee_record(
        make_record(effective_at="2026-01-01T09:00:00")
    )

    assert valid is False
    assert error == "Timestamp must include timezone information"


def test_malformed_timestamp_is_rejected():
    valid, cleaned, error = validate_employee_record(
        make_record(effective_at="not-a-date")
    )

    assert valid is False
    assert error == "Invalid ISO-8601 timestamp"


def test_zero_source_sequence_is_rejected():
    valid, cleaned, error = validate_employee_record(
        make_record(source_sequence="0")
    )

    assert valid is False
    assert error == "Source sequence must be positive"


def test_employee_fields_are_normalized():
    valid, cleaned, error = validate_employee_record(
        make_record(
            employee_id=" 101 ",
            employee_name=" Kiran ",
            department_code=" it "
        )
    )

    assert valid is True
    assert cleaned["employee_id"] == "101"
    assert cleaned["employee_name"] == "Kiran"
    assert cleaned["department_code"] == "IT"
    assert error is None
