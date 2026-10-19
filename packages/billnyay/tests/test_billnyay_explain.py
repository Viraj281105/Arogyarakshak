"""BillNyay explanation for an audited line (ADR-015)."""

from billnyay.explain import explain_audit_line

ROW = {"name": "OPD Consultation", "benchmark_rate": 350.0, "category": "Consultation",
       "bundled": False, "notes": "ceiling", "billing_unit": "per_visit"}


def _line(**kw):
    base = dict(
        item_name="Consultation (1 visit)", charged=500.0, status="overcharged", source_file="bill.pdf",
        matched_key="consultation", matched_entry=ROW, exact_match=False, rates_version="CGHS-2024-REVISED",
        benchmark_total=350.0, deviation_percentage=42.86, benchmark_basis="₹350 per visit × 1 visit",
        not_benchmarked_reason=None,
    )
    base.update(kw)
    return explain_audit_line(**base)


def test_overcharge_cites_the_row_version_and_arithmetic():
    exp = _line()
    row = next(r for r in exp.rules if r.kind == "REFERENCE_TABLE_ROW")
    assert row.source == "CGHS rate schedule CGHS-2024-REVISED"
    facts = {f.label: f.value for f in row.facts}
    assert facts["Reference rate"] == "₹350" and facts["Rate covers"] == "per visit"
    assert facts["How the line was matched"].startswith("the longest reference name")
    comp = next(r for r in exp.rules if r.kind == "COMPUTATION")
    assert {f.label: f.value for f in comp.facts}["How it was worked out"] == "₹350 per visit × 1 visit"
    assert exp.evidence[0].document == "bill.pdf"


def test_cghs_code_is_reported_as_not_recorded():
    exp = _line()
    assert "CGHS reference rate: OPD Consultation: CGHS procedure code" in exp.not_recorded


def test_unmatched_line_says_it_was_not_checked():
    exp = _line(status="not_benchmarked", matched_key=None, matched_entry=None, benchmark_total=None,
                benchmark_basis=None, deviation_percentage=0.0)
    assert exp.rules == []
    assert exp.undetermined[0].code == "NO_REFERENCE_MATCH"
    assert "was not checked" in exp.undetermined[0].reason


def test_recurring_rate_without_count_carries_the_recorded_reason():
    exp = _line(status="not_benchmarked", benchmark_total=None, not_benchmarked_reason="rate is per day, count not stated")
    assert exp.undetermined[0].code == "CANNOT_COMPARE_BASIS"
    assert exp.undetermined[0].reason == "rate is per day, count not stated"


def test_missing_source_file_is_not_recorded():
    exp = _line(source_file=None)
    assert "Bill line: source document" in exp.not_recorded
