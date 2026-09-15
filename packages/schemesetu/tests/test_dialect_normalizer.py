"""Tests for SchemeSetu's regional state-name normalization (#95)."""

import pytest

from schemesetu.dialect_normalizer import normalize_state_name
from schemesetu.agent import check_eligibility, EligibilityRequest


def test_devanagari_maharashtra_is_normalized():
    result = normalize_state_name("महाराष्ट्र")
    assert result.normalized == "Maharashtra"
    assert result.was_normalized is True
    assert result.normalization_basis == "devanagari_or_spelling_variant"


def test_devanagari_locative_form_is_normalized():
    result = normalize_state_name("महाराष्ट्रात")
    assert result.normalized == "Maharashtra"


def test_common_misspelling_is_normalized():
    result = normalize_state_name("Maharastra")
    assert result.normalized == "Maharashtra"
    assert result.was_normalized is True


def test_city_name_is_inferred_to_state():
    result = normalize_state_name("Mumbai")
    assert result.normalized == "Maharashtra"
    assert result.normalization_basis == "inferred_from_city_name"


def test_canonical_spelling_is_not_flagged_as_normalized():
    result = normalize_state_name("Maharashtra")
    assert result.normalized == "Maharashtra"
    assert result.was_normalized is False
    assert result.normalization_basis is None


def test_unrecognized_state_passes_through_unchanged_never_guessed():
    # Karnataka is a real state but not in the curated variant table (MJPJAY is
    # Maharashtra-only, so there is nothing to normalize it to) — must pass through
    # untouched, not be silently mapped to anything.
    result = normalize_state_name("Karnataka")
    assert result.normalized == "Karnataka"
    assert result.was_normalized is False


def test_empty_state_does_not_crash():
    result = normalize_state_name("")
    assert result.was_normalized is False
    result_none = normalize_state_name(None)
    assert result_none.was_normalized is False


@pytest.mark.parametrize("state_input", ["महाराष्ट्र", "Maharastra", "Mumbai", "pune", "THANE"])
def test_mjpjay_appears_for_every_normalized_variant(state_input):
    # This is the actual bug #95 fixes: before normalization, every one of these
    # inputs made MJPJAY silently vanish from the results with no explanation.
    request = EligibilityRequest(
        income=200000, location_state=state_input, category="General", medical_need="checkup"
    )
    results = check_eligibility(request)
    scheme_names = [r.scheme_name for r in results]
    assert any("MJPJAY" in name for name in scheme_names), (
        f"MJPJAY missing for state input '{state_input}' — normalization regression"
    )


def test_mjpjay_result_discloses_that_normalization_happened():
    request = EligibilityRequest(
        income=200000, location_state="महाराष्ट्र", category="General", medical_need="checkup"
    )
    results = check_eligibility(request)
    mjpjay = next(r for r in results if "MJPJAY" in r.scheme_name)
    assert "महाराष्ट्र" in mjpjay.reason
    assert "Maharashtra" in mjpjay.reason


def test_mjpjay_still_absent_for_a_genuinely_different_state():
    request = EligibilityRequest(
        income=200000, location_state="Karnataka", category="General", medical_need="checkup"
    )
    results = check_eligibility(request)
    scheme_names = [r.scheme_name for r in results]
    assert not any("MJPJAY" in name for name in scheme_names)


def test_exact_canonical_maharashtra_input_still_works_unchanged():
    """Regression guard: normalization must not break the already-working exact-match case."""
    request = EligibilityRequest(
        income=200000, location_state="Maharashtra", category="General", medical_need="checkup"
    )
    results = check_eligibility(request)
    mjpjay = next(r for r in results if "MJPJAY" in r.scheme_name)
    assert "interpreted" not in mjpjay.reason
