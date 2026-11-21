"""Templated Hindi/Marathi explanations over the deterministic reasoning trace. All
Hindi/Marathi wording is engineer-written and UNREVIEWED (NEEDS NATIVE-SPEAKER QA); these
tests check structure and that every claim is verifiable against its cited span, not the
quality of the language."""

import re

import pytest

from schemesetu import explain_i18n
from schemesetu.agent import EligibilityRequest
from schemesetu.citations import verify_citation
from schemesetu.explain_i18n import (
    NEEDS_QA,
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
def test_figure_sentences_are_supported_and_trace_sentences_are_scheme_only(lang):
    """TRACE sentences carry no figure, so only their scheme attribution is checked (scheme_only);
    the figures in the source-keyed sentences are the ones really verified."""
    reasoning = _reasoning()
    expl = explain_eligibility(reasoning, lang)
    hits = build_citation_hits(reasoning)
    checkable = [s for s in expl.sentences if s.checkable]
    assert len(checkable) >= 5 and expl.dropped_citation_keys == []
    for s in checkable:
        status = verify_citation(s.text, hits[s.citation_key]).status
        assert status == ("supported" if ":S" in s.citation_key else "scheme_only"), (s.citation_key, status)
    assert {s.citation_key for s in checkable if ":S" in s.citation_key} == {"PMJAY:S2", "MJPJAY:S1"}


def test_marathi_uses_devanagari_digits_and_still_verifies():
    joined = " ".join(s.text for s in explain_eligibility(_reasoning(), "mr").sentences)
    assert "७०" in joined and "५ लाख" in joined


def test_hindi_figures_are_the_cited_ones():
    joined = " ".join(s.text for s in explain_eligibility(_reasoning(), "hi").sentences)
    assert "70" in joined and "5 लाख" in joined


def test_non_maharashtra_has_no_mjpjay_sentence_and_nothing_omitted():
    expl = explain_eligibility(_reasoning("Karnataka"), "hi")
    assert not any("MJPJAY" in s.text for s in expl.sentences)
    assert any("PMJAY" in s.text for s in expl.sentences)
    keys = {s.citation_key for s in expl.sentences}
    assert "PMJAY:TRACE:annual_income" in keys and "MJPJAY:TRACE:annual_income" not in keys
    assert expl.omitted_schemes == []


def test_income_trace_sentence_exists_for_each_applicable_scheme():
    keys = {s.citation_key for s in explain_eligibility(_reasoning(), "mr").sentences}
    assert {"PMJAY:TRACE:annual_income", "MJPJAY:TRACE:annual_income"} <= keys


def test_provisional_notice_is_always_present_and_not_a_claim():
    for lang in ("hi", "mr"):
        expl = explain_eligibility(_reasoning(), lang)
        notice = [s for s in expl.sentences if s.citation_key == "TRACE:provisional"]
        assert len(notice) == 1 and notice[0].checkable is False


def test_income_amount_is_not_echoed():
    text = " ".join(s.text for s in explain_eligibility(_reasoning(), "hi").sentences)
    assert "120000" not in text and "1,20,000" not in text


def test_omitted_schemes_is_empty_for_the_normal_flows_and_lists_unknown_schemes():
    assert explain_eligibility(_reasoning(), "hi").omitted_schemes == []
    reasoning = _reasoning()
    other = reasoning.scheme_results[0].model_copy(update={"scheme_name": "Some Other Scheme"})
    changed = reasoning.model_copy(update={"scheme_results": [other, *reasoning.scheme_results[1:]]})
    expl = explain_eligibility(changed, "hi")
    assert expl.omitted_schemes == ["Some Other Scheme"]
    assert not any(s.citation_key.startswith("PMJAY") for s in expl.sentences)


def test_unexpected_verdict_for_a_known_scheme_is_omitted_not_invented():
    reasoning = _reasoning()
    flipped = reasoning.scheme_results[0].model_copy(update={"estimated_eligibility": "ineligible"})
    expl = explain_eligibility(reasoning.model_copy(update={"scheme_results": [flipped]}), "hi")
    assert expl.omitted_schemes == [flipped.scheme_name]


def test_missing_cited_sources_degrade_to_omitted_instead_of_raising():
    reasoning = _reasoning()
    stripped = reasoning.scheme_results[0].model_copy(update={"sources": []})
    expl = explain_eligibility(reasoning.model_copy(update={"scheme_results": [stripped, *reasoning.scheme_results[1:]]}), "hi")
    assert expl.omitted_schemes == [stripped.scheme_name]
    assert any(s.citation_key.startswith("MJPJAY") for s in expl.sentences)


def test_a_changed_trace_degrades_to_omitted():
    reasoning = _reasoning()
    trace = [s for s in reasoning.reasoning_trace if s.criterion != "state_of_residence"]
    expl = explain_eligibility(reasoning.model_copy(update={"reasoning_trace": trace}), "hi")
    assert any("MJPJAY" in name for name in expl.omitted_schemes)


def test_an_unsupported_sentence_is_dropped_and_reported(monkeypatch):
    patched = dict(explain_i18n._TEMPLATES["hi"])
    patched["MJPJAY:S1"] = patched["MJPJAY:S1"].replace("5 लाख", "3 लाख")
    monkeypatch.setitem(explain_i18n._TEMPLATES, "hi", patched)
    expl = explain_eligibility(_reasoning(), "hi")
    assert expl.dropped_citation_keys == ["MJPJAY:S1"]
    assert "MJPJAY:S1" not in {s.citation_key for s in expl.sentences}
    assert "MJPJAY:TRACE:state_of_residence" in {s.citation_key for s in expl.sentences}


def test_verifier_catches_tampered_figures_in_hindi_and_marathi():
    reasoning = _reasoning()
    hits = build_citation_hits(reasoning)
    hi = next(s for s in explain_eligibility(reasoning, "hi").sentences if s.citation_key == "MJPJAY:S1")
    mr = next(s for s in explain_eligibility(reasoning, "mr").sentences if s.citation_key == "PMJAY:S2")
    mr_amount = next(s for s in explain_eligibility(reasoning, "mr").sentences if s.citation_key == "MJPJAY:S1")
    assert verify_citation(hi.text, hits["MJPJAY:S1"]).supported
    assert verify_citation(hi.text.replace("5 लाख", "3 लाख"), hits["MJPJAY:S1"]).supported is False
    assert verify_citation(mr.text, hits["PMJAY:S2"]).supported
    assert verify_citation(mr.text.replace("७०", "६०"), hits["PMJAY:S2"]).supported is False
    assert verify_citation(mr_amount.text.replace("५ लाख", "३ लाख"), hits["MJPJAY:S1"]).supported is False


def test_a_pmjay_sentence_cannot_pass_against_the_mjpjay_source():
    hits = build_citation_hits(_reasoning())
    hi = next(s for s in explain_eligibility(_reasoning(), "hi").sentences if s.citation_key == "MJPJAY:S1")
    assert verify_citation(hi.text.replace("MJPJAY", "PMJAY"), hits["MJPJAY:S1"]).supported is False


def test_citation_hits_are_the_cited_source_text_not_generated():
    reasoning = _reasoning()
    hits = build_citation_hits(reasoning)
    mjpjay = next(r for r in reasoning.scheme_results if r.scheme_name.startswith("MJPJAY"))
    assert hits["MJPJAY:S1"].quote == mjpjay.sources[0].supports
    assert hits["MJPJAY:S1"].title == mjpjay.sources[0].document and hits["MJPJAY:S1"].scheme == "MJPJAY"
    assert hits["MJPJAY:S1"].source == mjpjay.sources[0].url


@pytest.mark.parametrize("lang", [None, "", "HI", "en", "fr", "hindi"])
def test_unsupported_language_is_rejected_not_machine_translated(lang):
    with pytest.raises(ValueError):
        explain_eligibility(_reasoning(), lang)  # type: ignore[arg-type]


def test_output_is_deterministic():
    assert explain_eligibility(_reasoning(), "hi") == explain_eligibility(_reasoning(), "hi")
