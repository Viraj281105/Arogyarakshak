"""#107 appeal completeness and #115 hallucination / grounding harnesses.

Hand-computed expectations on tiny inputs, plus the shipped SYNTHETIC datasets. The harnesses
score offline template code, not LLM output (docs/evaluation/phase4-harnesses.md)."""

import pytest

from app.evaluation.appeal_completeness import (
    WEIGHTS,
    evaluate_appeal_completeness,
    run_checks,
    score_checks,
)
from app.evaluation.datasets import DATA_DIR, load_dataset
from app.evaluation.grounding import (
    allowed_claims,
    evaluate_detector,
    evaluate_production,
    extract_claims,
    ground_letter,
)
from app.evaluation.runner import DATASETS, run_all

FACTS = {
    "policy_number": "AB-12",
    "insurer_name": "Acme Insurance",
    "diagnosis": "Dengue",
    "claimed_amount": 1000.0,
    "denied_amount": 400.0,
    "denial_reason": "Not payable",
    "grounds": "Policy is old.",
    "violations": [{"clause_reference": "Clause 16 — Moratorium", "statute_or_circular": "IRDAI Master Circular (May 29, 2024)"}],
}
COMPLETE = (
    "To the GRO, Acme Insurance. Claim No. C-77 under Policy No. AB-12. Diagnosis: Dengue. "
    "Claimed INR 1,000.00, disallowed INR 400.00. Reason: Not payable. Grounds: Policy is old. "
    "Clause 16 — Moratorium, IRDAI Master Circular (May 29, 2024). Pay INR 400.00 within 15 days. "
    "Else Bima Bharosa and the Ombudsman. Signed, Asha Rao."
)


# ---- #107 appeal completeness ------------------------------------------------------------------
def test_weights_sum_to_one_and_match_the_issue():
    assert WEIGHTS == {"patient": 0.15, "policy": 0.20, "clauses": 0.30, "justification": 0.25, "references": 0.10}
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_score_checks_hand_computed_with_a_dropped_category():
    checks = {
        "patient": [("a", True), ("b", True), ("c", False)],  # 2/3
        "policy": [("a", True)],  # 1
        "clauses": [],  # not applicable: weight dropped
        "justification": [("a", True)],  # 1
        "references": [("a", True), ("b", True), ("c", False)],  # 2/3
    }
    r = score_checks(checks)
    expected = (0.15 * 2 / 3 + 0.20 + 0.25 + 0.10 * 2 / 3) / (0.15 + 0.20 + 0.25 + 0.10)
    assert r["score"] == pytest.approx(expected)
    assert r["applicable_weight"] == pytest.approx(0.70)
    assert r["categories"]["clauses"] is None
    assert r["failed"] == ["patient.c", "references.c"]


def test_a_complete_letter_passes_every_check():
    r = score_checks(run_checks(COMPLETE, FACTS))
    assert r["failed"] == [] and r["score"] == pytest.approx(1.0)


def test_each_missing_element_is_caught():
    cases = {
        "Clause 16 — Moratorium, IRDAI Master Circular (May 29, 2024).": "clauses.clause_cited[0]",
        "Policy No. AB-12": "policy.policy_number_stated",
        "Pay INR 400.00 within 15 days.": "justification.resolution_window_demanded",
        "Grounds: Policy is old.": "justification.grounds_stated",
        "Else Bima Bharosa and the Ombudsman.": "references.escalation_path_named",
    }
    for removed, expected_failure in cases.items():
        letter = COMPLETE.replace(removed, "")
        assert expected_failure in score_checks(run_checks(letter, FACTS))["failed"], removed


def test_relief_amount_must_be_restated_not_just_mentioned_once():
    once = COMPLETE.replace("Pay INR 400.00 within 15 days.", "Pay within 15 days.")
    assert COMPLETE.count("INR 400.00") == 2 and once.count("INR 400.00") == 1
    assert "justification.relief_amount_restated" in score_checks(run_checks(once, FACTS))["failed"]
    assert "justification.relief_amount_restated" not in score_checks(run_checks(COMPLETE, FACTS))["failed"]


def test_placeholders_are_unfilled_not_missing():
    letter = COMPLETE.replace("Signed, Asha Rao.", "Signed, [POLICYHOLDER NAME].").replace("C-77", "[CLAIM_NO]")
    failed = score_checks(run_checks(letter, FACTS))["failed"]
    assert "patient.policyholder_name_filled" in failed and "policy.claim_reference_filled" in failed
    # no claim-number label at all is also a failure (hi/mr templates have none)
    assert "policy.claim_reference_filled" in score_checks(run_checks("Policy No. AB-12", FACTS))["failed"]


def test_devanagari_digits_count_for_the_resolution_window():
    letter = COMPLETE.replace("15 days", "१५ दिनों")
    assert "justification.resolution_window_demanded" not in score_checks(run_checks(letter, FACTS))["failed"]


def test_no_violations_makes_clauses_not_applicable():
    r = score_checks(run_checks(COMPLETE, {**FACTS, "violations": []}))
    assert r["categories"]["clauses"] is None and r["applicable_weight"] == pytest.approx(0.70)


def test_evaluate_appeal_completeness_hand_computed():
    rows = [{"id": "r1", "input": {}}, {"id": "r2", "input": {}}]
    letters = iter([COMPLETE, COMPLETE.replace("Policy is old.", "")])

    r = evaluate_appeal_completeness(rows, lambda payload, lang: (next(letters), FACTS), languages=("en",))
    assert r["letters"] == 2 and r["fully_complete_share"] == pytest.approx(0.5)
    # the second letter misses only justification.grounds_stated: 1 of 3 checks, 0.25 weight
    assert r["mean_score"] == pytest.approx((1.0 + (1 - 0.25 / 3)) / 2)
    assert r["failed_check_counts"] == {"justification.grounds_stated": 1}


def test_unverified_citations_are_counted_not_hidden():
    facts = {**FACTS, "violations": [{"clause_reference": "UNVERIFIED — no primary-source citation",
                                      "statute_or_circular": "IRDAI provision not verified"}]}
    r = evaluate_appeal_completeness([{"id": "x", "input": {}}], lambda p, l: (COMPLETE, facts), languages=("en",))
    assert r["unverified_clause_citations"] == 1


# ---- #115 grounding ---------------------------------------------------------------------------
def test_extract_claims_hand_checked_across_scripts():
    text = ("Policy No. AB-12. INR 1,000.00 and ₹२५० and Rs. 3000. Within १५ दिनों "
            "at २% on 29 मई 2024 / May 29, 2024. Clause 16 and नियम 14(1)(बी). Dr. Rao agreed.")
    got = sorted(extract_claims(text), key=repr)
    assert got == sorted([
        ("amount", 1000.0), ("amount", 250.0), ("amount", 3000.0),
        ("policy_no", "AB-12"), ("days", 15), ("percent", 2.0),
        ("date", "2024-05-29"), ("date", "2024-05-29"),
        ("clause", "clause16"), ("clause", "rule14(1)(b)"), ("clinician", "dr. rao"),
    ], key=repr)


def test_rs_inside_a_word_is_not_an_amount():
    assert ("amount", 5.0) not in extract_claims("after 3 hours 5 more")


def test_clinician_claims_are_never_grounded_but_doctor_notes_are_not_claims():
    assert ("clinician", "dr. rao") in ground_letter("Dr. Rao reviewed it.", FACTS)["ungrounded"]
    assert extract_claims("without diagnostic reports or doctor notes") == []
    assert all(kind != "clinician" for kind, _ in allowed_claims({**FACTS, "grounds": "Dr. Rao says so"}))


def test_grounding_uses_the_case_facts_and_the_static_reference():
    ok = "Policy No. AB-12, INR 1,000.00, INR 400.00, Clause 16, 15 days, 2%, May 29, 2024, Rule 14(1)(b)."
    assert ground_letter(ok, FACTS)["ungrounded"] == []
    bad = ground_letter("Policy No. ZZ-9, INR 401.00, Section 45, 7 days, 5%, June 3, 2023.", FACTS)["ungrounded"]
    assert sorted(bad, key=repr) == sorted(
        [("policy_no", "ZZ-9"), ("amount", 401.0), ("clause", "section45"), ("days", 7),
         ("percent", 5.0), ("date", "2023-06-03")], key=repr)


def test_evaluate_detector_hand_computed():
    rows = [
        {"id": "a", "letter": "INR 401.00 and INR 401.00", "facts": FACTS, "gold_ungrounded": [["amount", 401.0], ["amount", 401.0]]},
        {"id": "b", "letter": "7 days", "facts": FACTS, "gold_ungrounded": []},  # detector says 1: a false positive
        {"id": "c", "letter": "sixty rupees", "facts": FACTS, "gold_ungrounded": [["amount_in_words", "sixty"]]},  # miss
    ]
    r = evaluate_detector(rows)
    assert (r["tp"], r["fp"], r["fn"]) == (2, 1, 1)
    assert r["precision"] == pytest.approx(2 / 3) and r["recall"] == pytest.approx(2 / 3)
    assert r["spurious"][0]["id"] == "b" and r["missed"][0]["id"] == "c"


def test_evaluate_production_hand_computed_and_catches_a_drifted_template():
    rows = [{"id": "s1", "input": {}}]
    clean = "Policy No. AB-12, INR 400.00, 15 days."
    drifted = "Policy No. AB-12, INR 499.00, 15 days."

    r = evaluate_production(rows, lambda p, l: [("gro", clean, FACTS)], languages=("en",))
    assert (r["claims"], r["ungrounded_claims"], r["hallucination_rate"], r["grounding_score"]) == (3, 0, 0.0, 1.0)

    r = evaluate_production(rows, lambda p, l: [("gro", drifted, FACTS)], languages=("en",))
    assert r["ungrounded_claims"] == 1 and r["hallucination_rate"] == pytest.approx(1 / 3)
    assert r["grounding_score"] == pytest.approx(2 / 3) and r["letters_with_ungrounded"] == 1.0
    assert r["by_kind"]["amount"] == {"claims": 1, "ungrounded": 1}


# ---- shipped datasets and the real production path -------------------------------------------
def test_shipped_grounding_dataset_known_results():
    _, rows = load_dataset(DATA_DIR / DATASETS["grounding"])
    assert len(rows) == 18
    r = evaluate_detector(rows)
    # every injected hallucination of a supported kind is found, nothing clean is flagged,
    # and the two documented limits (amounts in words, case law) are the only misses
    assert r["fp"] == 0
    assert sorted(m["category"] for m in r["missed"]) == ["KNOWN_MISS_amount_in_words", "KNOWN_MISS_case_law"]
    assert (r["tp"], r["fn"]) == (15, 2)
    clean = [row for row in rows if not row["gold_ungrounded"]]
    assert len(clean) == 4 and all(not ground_letter(c["letter"], c["facts"])["ungrounded"] for c in clean)


def test_appeal_and_grounding_run_on_the_real_bimanyay_drafts(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    out = run_all("appeal")["appeal"]
    assert out["scenarios"] == 25 and out["letters"] == 75
    # templates leave the policyholder name and the claim number to the patient: a disclosed gap
    assert set(out["failed_check_counts"]) == {"patient.policyholder_name_filled", "policy.claim_reference_filled"}
    assert out["per_category"]["clauses"] == 1.0 and out["per_category"]["references"] == 1.0
    g = run_all("grounding")["grounding"]["production"]
    assert g["letters"] == 225 and g["claims"] > 0
    assert g["ungrounded_claims"] == 0 and g["hallucination_rate"] == 0.0
