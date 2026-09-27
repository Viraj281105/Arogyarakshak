"""
BillNyay — what a CGHS reference rate is *per*, and what a bill line covers.

CGHS reference rates are per day (room, ICU), per visit (consultation), per session
(dialysis), per shift (PPE kit), per bottle (an IV infusion) or per service (a scan, a
surgical package). A bill line is usually a TOTAL. Comparing "Room Rent (Private Ward)
3 days ₹13,500" with a ₹4,500-per-day rate as if it were one day reports a false +200%.

Rules (no rule guesses):
  * per-service rates (a scan, a test, a surgical package) compare a line as one service,
    unless the line states a count ("x 2", "Qty 2"), which multiplies the reference;
  * recurring rates (per day / visit / session / shift / bottle) need the line to state how
    many — "3 days", "2 visits", "Qty 3" — otherwise the line is NOT benchmarked, with the
    reason, rather than compared as if it were one unit;
  * an explicit count of the wrong kind (e.g. "3 visits" against a per-day rate) is not
    converted.
"""

import re
from dataclasses import dataclass
from typing import Optional

PER_SERVICE = "per_service"
RECURRING_UNITS = {
    "per_day": ("day", "days", r"days?|nights?"),
    "per_visit": ("visit", "visits", r"visits?"),
    "per_session": ("session", "sessions", r"sessions?|sittings?"),
    "per_shift": ("shift", "shifts", r"shifts?"),
    "per_bottle": ("bottle", "bottles", r"bottles?|vials?|bags?|units?|nos?"),
}
_GENERIC_COUNT = re.compile(r"(?:\bqty\.?\s*[:=\-]?\s*|\bquantity\s*[:=\-]?\s*|(?<![\w.])[x×]\s*)(\d{1,3})\b")


@dataclass(frozen=True)
class LineBenchmark:
    benchmark_total: Optional[float]
    quantity: Optional[float]
    basis: str  # human-readable: "₹4,500 per day × 3 days"
    reason: Optional[str] = None  # set when not benchmarked


def _rupees(n: float) -> str:
    return f"₹{n:,.0f}" if float(n).is_integer() else f"₹{n:,.2f}"


def line_quantity(item_name: str, billing_unit: str) -> Optional[float]:
    """The count a bill line states for the rate's unit, or None when it states none.
    Returns 0 for an explicit zero (the caller treats it as invalid)."""
    text = (item_name or "").lower()
    if billing_unit in RECURRING_UNITS:
        words = RECURRING_UNITS[billing_unit][2]
        m = re.search(rf"(?<![\w.])(\d{{1,3}})\s*(?:{words})\b", text)
        if m:
            return float(m.group(1))
    m = _GENERIC_COUNT.search(text)
    if m:
        return float(m.group(1))
    return None


def benchmark_line(item_name: str, rate: float, billing_unit: Optional[str]) -> LineBenchmark:
    """The reference total for this bill line, or a reason it cannot be compared."""
    unit = billing_unit or PER_SERVICE
    qty = line_quantity(item_name, unit)
    if qty is not None and qty <= 0:
        return LineBenchmark(None, qty, "", "The bill line states a zero quantity.")

    if unit == PER_SERVICE:
        n = qty or 1.0
        basis = f"{_rupees(rate)} per service" + (f" × {n:g}" if qty else "")
        return LineBenchmark(round(rate * n, 2), n, basis)

    singular, plural, _ = RECURRING_UNITS.get(unit, ("unit", "units", ""))
    if qty is None:
        return LineBenchmark(
            None,
            None,
            f"{_rupees(rate)} per {singular}",
            f"The reference rate is per {singular}, and this bill line does not say how many {plural} it covers, "
            "so it was not compared.",
        )
    return LineBenchmark(round(rate * qty, 2), qty, f"{_rupees(rate)} per {singular} × {qty:g} {singular if qty == 1 else plural}")
