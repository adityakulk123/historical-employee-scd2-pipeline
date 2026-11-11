
from src.scd2_processor import build_employee_timeline


def make_event(event_id, employee_id, department, salary, effective_at, sequence):
    return {
        "event_id": event_id,
        "employee_id": employee_id,
        "employee_name": "Kiran",
        "department_code": department,
        "salary": salary,
        "effective_at": effective_at,
        "source_sequence": sequence,
    }


def test_first_employee_event_creates_one_current_version():
    events = [
        make_event("E1", "101", "IT", 40000,
                   "2026-01-01T09:00:00+00:00", 1)
    ]

    result = build_employee_timeline(events)

    assert len(result) == 1
    assert result[0]["is_current"] == 1
    assert result[0]["effective_to"] is None


def test_department_change_creates_two_versions():
    events = [
        make_event("E1", "101", "IT", 40000,
                   "2026-01-01T09:00:00+00:00", 1),
        make_event("E2", "101", "FIN", 45000,
                   "2026-03-01T09:00:00+00:00", 2),
    ]

    result = build_employee_timeline(events)

    assert len(result) == 2
    assert result[0]["department_code"] == "IT"
    assert result[0]["is_current"] == 0
    assert result[1]["department_code"] == "FIN"
    assert result[1]["is_current"] == 1


def test_late_arriving_event_is_inserted_in_correct_order():
    events = [
        make_event("E1", "101", "IT", 40000,
                   "2026-01-01T09:00:00+00:00", 1),
        make_event("E2", "101", "FIN", 50000,
                   "2026-03-01T09:00:00+00:00", 2),
        make_event("E3", "101", "HR", 45000,
                   "2026-02-01T09:00:00+00:00", 3),
    ]

    result = build_employee_timeline(events)

    assert len(result) == 3
    assert [r["department_code"] for r in result] == ["IT", "HR", "FIN"]
    assert result[0]["effective_to"] == "2026-02-01T09:00:00+00:00"
    assert result[1]["effective_to"] == "2026-03-01T09:00:00+00:00"
    assert result[2]["is_current"] == 1


def test_identical_snapshots_do_not_create_extra_version():
    events = [
        make_event("E1", "101", "IT", 40000,
                   "2026-01-01T09:00:00+00:00", 1),
        make_event("E2", "101", "IT", 40000,
                   "2026-02-01T09:00:00+00:00", 2),
    ]

    result = build_employee_timeline(events)

    assert len(result) == 1
    assert result[0]["is_current"] == 1
