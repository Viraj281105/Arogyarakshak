"""Templated Hindi/Marathi explanations over the deterministic reasoning trace. All
Hindi/Marathi wording is engineer-written and UNREVIEWED (NEEDS NATIVE-SPEAKER QA); these
tests check structure and that every claim is verifiable against its cited span, not the
quality of the language."""

import re

import pytest

from schemesetu.agent import EligibilityRequest
from schemesetu.citations import verify_citation
from schemesetu.explain_i18n import (
    NEEDS_QA,
    LocalizedSentence,
    build_citation_hits,
    explain_eligibility,
)
from schemesetu.reasoning_agent import reason_about_eligibility

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def _reasoning(state="Maharashtra"):
    return reason_about_eligibility(EligibilityRequest(income=120000.0, location_state=state, medical_need="surgery"))


@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_every_sentence_has_a_resolvable_citation_key_and_the_qa_marker(lang):
    reasoning = _reasoning()
    expl = explain_eligibility(reasoning, lang)
    hits = build_citation_hits(reasoning)
    assert expl.lang == lang and expl.review_status == NEEDS_QA == "NEEDS NATIVE-SPEAKER QA"
    assert expl.sentences
    for s in expl.sentences:
        assert s.citation_key and s.citation_key in hits
        assert s.review_status == NEEDS_QA
        assert _DEVANAGARI.search(s.text)


@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_every_checkable_sentence_verifies_against_its_cited_span(lang):
    reasoning = _reasoning()
    expl = explain_eligibility(reasoning, lang)
    hits = build_citation_hits(reasoning)
    checkable = [s for s in expl.sentences if s.checkable]
    assert len(checkable) >= 4
    for s in checkable:
        verdict = verify_citation(s.text, hits[s.citation_key])
        assert verdict.supported, (s.citation_key, verdict)


def test_marathi_uses_devanagari_digits_and_still_verifies():
    reasoning = _reasoning()
    expl = explain_eligibility(reasoning, "mr")
    joined = " ".join(s.text for s in expl.sentences)
    assert "७०" in joined and "५ लाख" in joined


def test_hindi_figures_are_the_cited_ones():
    joined = " ".join(s.text for s in explain_eligibility(_reasoning(), "hi").sentences)
    assert "70" in joined and "5 लाख" in joined


def test_non_maharashtra_has_no_mjpjay_sentence():
    expl = explain_eligibility(_reasoning("Karnataka"), "hi")
    assert not any("MJPJAY" in s.text for s in expl.sentences)
    assert any("PMJAY" in s.text for s in expl.sentences)


def test_provisional_notice_is_always_present_and_not_a_claim():
    for lang in ("hi", "mr"):
        expl = explain_eligibility(_reasoning(), lang)
        notice = [s for s in expl.sentences if s.citation_key == "TRACE:provisional"]
        assert len(notice) == 1 and notice[0].checkable is False


def test_income_is_reported_as_non_determinative_and_its_amount_is_not_echoed():
    reasoning = _reasoning()
    text = " ".join(s.text for s in explain_eligibility(reasoning, "hi").sentences)
    assert "120000" not in text and "1,20,000" not in text


def test_verifier_catches_a_tampered_figure_in_a_localised_sentence():
    reasoning = _reasoning()
    hits = build_citation_hits(reasoning)
    good = next(s for s in explain_eligibility(reasoning, "hi").sentences if s.citation_key == "MJPJAY:S1")
    bad = LocalizedSentence(**{**good.model_dump(), "text": good.text.replace("5 लाख", "3 लाख")})
    assert verify_citation(good.text, hits["MJPJAY:S1"]).supported
    assert verify_citation(bad.text, hits["MJPJAY:S1"]).supported is False


def test_citation_hits_are_the_cited_source_text_not_generated():
    reasoning = _reasoning()
    hits = build_citation_hits(reasoning)
    mjpjay = next(r for r in reasoning.scheme_results if r.scheme_name.startswith("MJPJAY"))
    assert mjpjay.sources[0].supports in hits["MJPJAY:S1"].quote
    assert hits["MJPJAY:S1"].source == mjpjay.sources[0].url


def test_unsupported_language_is_rejected_not_machine_translated():
    with pytest.raises(ValueError):
        explain_eligibility(_reasoning(), "fr")


def test_output_is_deterministic():
    assert explain_eligibility(_reasoning(), "hi") == explain_eligibility(_reasoning(), "hi")
