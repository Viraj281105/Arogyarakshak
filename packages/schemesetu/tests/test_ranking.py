"""rank_schemes orders already-computed eligibility results: eligibility status first,
relevance second. It never changes a verdict and every row stays provisional."""

from schemesetu.agent import EligibilityRequest, check_eligibility
from schemesetu.ranking import RankedScheme, rank_schemes


def _req(state="Maharashtra", need="knee surgery", income=100000.0):
    return EligibilityRequest(income=income, location_state=state, medical_need=need)


def _with_status(result, status):
    return result.model_copy(update={"estimated_eligibility": status})


def test_eligible_ranks_above_ambiguous():
    req = _req()
    ranked = rank_schemes(req, check_eligibility(req))
    assert [r.estimated_eligibility for r in ranked] == ["eligible", "ambiguous"]
    assert ranked[0].scheme_name.startswith("MJPJAY")
    assert [r.rank for r in ranked] == [1, 2]


def test_status_beats_relevance():
    """PMJAY is made far more relevant to the stated need, but a worse status still sorts last."""
    req = _req(need="senior citizen aged 70 ASHA Anganwadi SECC-2011 family")
    pmjay, mjpjay = check_eligibility(req)
    ranked = rank_schemes(req, [_with_status(pmjay, "ineligible"), _with_status(mjpjay, "ambiguous")])
    assert [r.scheme_name[:5] for r in ranked] == ["MJPJA", "PMJAY"]
    by_name = {r.scheme_name[:5]: r for r in ranked}
    assert by_name["PMJAY"].relevance > by_name["MJPJA"].relevance


def test_relevance_breaks_ties_within_a_status():
    pmjay, mjpjay = check_eligibility(_req())
    both_ambiguous = [_with_status(pmjay, "ambiguous"), _with_status(mjpjay, "ambiguous")]

    # No need text: the scheme specific to the stated state is the more relevant one.
    ranked = rank_schemes(_req(need=""), both_ambiguous)
    assert ranked[0].scheme_name.startswith("MJPJAY")

    # A need that only the national scheme text talks about outweighs state specificity.
    ranked = rank_schemes(
        _req(need="senior citizen aged 70 ASHA Anganwadi Worker SECC-2011 deprivation occupational family"),
        both_ambiguous,
    )
    assert ranked[0].scheme_name.startswith("PMJAY")


def test_ranking_never_changes_a_verdict_or_mutates_inputs():
    req = _req()
    results = check_eligibility(req)
    snapshot = [r.model_dump() for r in results]
    ranked = rank_schemes(req, results)
    assert [r.model_dump() for r in results] == snapshot
    for row in ranked:
        original = next(r for r in results if r.scheme_name == row.scheme_name)
        assert row.estimated_eligibility == original.estimated_eligibility
        assert row.result == original


def test_every_row_is_provisional_even_if_the_input_says_otherwise():
    req = _req()
    results = [r.model_copy(update={"is_provisional": False}) for r in check_eligibility(req)]
    ranked = rank_schemes(req, results)
    assert ranked and all(r.provisional is True for r in ranked)
    assert RankedScheme.model_fields["provisional"].default is True


def test_non_maharashtra_profile_ranks_only_pmjay():
    req = _req(state="Karnataka")
    ranked = rank_schemes(req, check_eligibility(req))
    assert len(ranked) == 1 and ranked[0].scheme_name.startswith("PMJAY")


def test_relevance_is_bounded_explained_and_deterministic():
    req = _req()
    results = check_eligibility(req)
    a, b = rank_schemes(req, results), rank_schemes(req, list(reversed(results)))
    assert [r.model_dump() for r in a] == [r.model_dump() for r in b]
    for row in a:
        assert 0.0 <= row.relevance <= 1.0
        assert row.relevance_basis  # says why, in words


def test_income_does_not_affect_order_or_relevance():
    low = rank_schemes(_req(income=1.0), check_eligibility(_req(income=1.0)))
    high = rank_schemes(_req(income=9e9), check_eligibility(_req(income=9e9)))
    assert [(r.scheme_name, r.relevance) for r in low] == [(r.scheme_name, r.relevance) for r in high]


def test_empty_results_rank_to_empty():
    assert rank_schemes(_req(), []) == []


def test_unknown_scheme_is_kept_with_zero_relevance_and_sorted_by_status():
    req = _req()
    pmjay, _ = check_eligibility(req)
    other = pmjay.model_copy(update={"scheme_name": "Some Other Scheme", "estimated_eligibility": "eligible"})
    ranked = rank_schemes(req, [pmjay, other])
    assert ranked[0].scheme_name == "Some Other Scheme" and ranked[0].relevance == 0.0
