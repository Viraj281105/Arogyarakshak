"""BillNyay rate basis: a recurring CGHS rate (per day / visit / session / shift / bottle)
is applied only to a count the bill line states."""

import pytest

from billnyay.rate_basis import benchmark_line, line_quantity


def test_room_rent_for_three_days_is_compared_with_three_days_of_the_rate():
    b = benchmark_line("Room Rent (Private Ward) 3 days", 4500.0, "per_day")
    assert b.benchmark_total == 13500.0
    assert b.basis == "₹4,500 per day × 3 days"
    assert b.reason is None


@pytest.mark.parametrize("name, unit", [("ICU", "per_day"), ("Specialist Consultation", "per_visit"),
                                        ("Paracetamol IV", "per_bottle"), ("Dialysis", "per_session")])
def test_recurring_rate_without_a_count_is_not_compared(name, unit):
    b = benchmark_line(name, 1000.0, unit)
    assert b.benchmark_total is None
    assert "does not say how many" in b.reason


def test_a_count_of_the_wrong_kind_is_not_converted():
    # "2 visits" says nothing about how many days of ICU the line covers.
    assert benchmark_line("ICU 2 visits", 5400.0, "per_day").benchmark_total is None


def test_generic_counts_apply_to_any_unit():
    assert benchmark_line("Dialysis x 3", 1800.0, "per_session").benchmark_total == 5400.0
    assert benchmark_line("Paracetamol IV Qty: 4", 42.0, "per_bottle").benchmark_total == 168.0


def test_one_service_per_line_unless_a_count_is_stated():
    assert benchmark_line("MRI Brain", 3500.0, "per_service").benchmark_total == 3500.0
    assert benchmark_line("MRI Brain x 2", 3500.0, "per_service").benchmark_total == 7000.0
    assert benchmark_line("MRI Brain", 3500.0, None).benchmark_total == 3500.0


def test_a_zero_count_is_refused():
    b = benchmark_line("ICU 0 days", 5400.0, "per_day")
    assert b.benchmark_total is None and "zero" in b.reason


def test_strength_and_dates_are_not_counts():
    assert line_quantity("Paracetamol IV 100ml", "per_bottle") is None
    assert line_quantity("Laparoscopic Appendectomy 2024", "per_service") is None
