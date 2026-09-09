"""
Unit tests for BimaNyay insurance dispute analysis and grievance engine.
"""

import pytest
from bimanyay.models import ClaimDenialInput
from bimanyay import (
    analyze_insurance_denial,
    audit_claim_denial,
    calculate_grievance_timeline,
    draft_gro_appeal_letter,
    draft_bimabharosa_summary,
    draft_ombudsman_statement,
)


def test_5_year_moratorium_protection():
    payload = ClaimDenialInput(
        policy_number="POL-998822",
        insurer_name="Star Health & Allied Insurance",
        policy_age_years=6.0,
        claimed_amount=150000.0,
        denied_or_deducted_amount=150000.0,
        denial_category="PED_NON_DISCLOSURE",
        denial_reason_raw="Claim repudiated due to non-disclosure of hypertension at policy inception.",
        diagnosis="Acute Myocardial Infarction",
    )
    result = analyze_insurance_denial(payload)
    assert result.is_wrongful_denial is True
    assert result.reversal_probability_score >= 0.90
    assert "moratorium" in result.primary_dispute_grounds.lower()
    assert len(result.regulatory_violations) >= 1
    assert any("Moratorium" in v.clause_reference for v in result.regulatory_violations)


def test_room_rent_illegal_deduction():
    payload = ClaimDenialInput(
        policy_number="POL-441122",
        insurer_name="Care Health Insurance",
        policy_age_years=2.0,
        claimed_amount=200000.0,
        denied_or_deducted_amount=75000.0,
        denial_category="ROOM_RENT_CAPPING",
        denial_reason_raw="Proportionate deduction applied across ICU and surgical charges due to higher room category.",
        diagnosis="Cholecystectomy",
    )
    result = analyze_insurance_denial(payload)
    assert result.is_wrongful_denial is True
    assert result.reversal_probability_score >= 0.85
    assert "proportionate deductions" in result.primary_dispute_grounds.lower()


def test_delayed_intimation_denial():
    payload = ClaimDenialInput(
        policy_number="POL-773311",
        insurer_name="HDFC ERGO General Insurance",
        policy_age_years=3.0,
        claimed_amount=95000.0,
        denied_or_deducted_amount=95000.0,
        denial_category="DELAYED_INTIMATION",
        denial_reason_raw="Claim submitted 35 days post discharge, violating the 30-day intimation limit.",
        diagnosis="Dengue Hemorrhagic Fever",
    )
    result = analyze_insurance_denial(payload)
    assert result.is_wrongful_denial is True
    assert result.reversal_probability_score >= 0.80
    assert any("216/09/2011" in v.statute_or_circular for v in result.regulatory_violations)


def test_drafter_output_format():
    payload = ClaimDenialInput(
        policy_number="POL-123456",
        insurer_name="Niva Bupa Health Insurance",
        policy_age_years=5.5,
        claimed_amount=120000.0,
        denied_or_deducted_amount=120000.0,
        denial_category="PED_NON_DISCLOSURE",
        denial_reason_raw="Pre-existing diabetes condition not declared.",
        diagnosis="Diabetic Ketoacidosis",
    )
    is_wrongful, prob, grounds, violations = audit_claim_denial(payload)
    gro_letter = draft_gro_appeal_letter(payload, grounds, violations)
    bima_text = draft_bimabharosa_summary(payload, grounds)
    ombuds_text = draft_ombudsman_statement(payload, grounds)

    assert "The Grievance Redressal Officer (GRO)" in gro_letter
    assert "Niva Bupa Health Insurance" in gro_letter
    assert len(bima_text) <= 2000
    assert "STATEMENT OF FACTS FOR COMPLAINT TO INSURANCE OMBUDSMAN" in ombuds_text


def test_grievance_timeline_deadlines():
    timeline = calculate_grievance_timeline(
        insurer_name="Star Health",
        date_initiated="2026-03-01",
        claim_number="CLM-00123",
        current_tier="LEVEL_1_GRO"
    )
    assert timeline.claim_number == "CLM-00123"
    assert timeline.insurer_name == "Star Health"
    assert len(timeline.timeline_events) == 3
    assert timeline.timeline_events[0].tier == "LEVEL_1_GRO"
    assert timeline.timeline_events[0].deadline_date == "2026-03-16"
    assert timeline.timeline_events[1].tier == "LEVEL_2_BIMA_BHAROSA"
    assert timeline.timeline_events[1].deadline_date == "2026-03-31"
    assert timeline.timeline_events[2].tier == "LEVEL_3_OMBUDSMAN"
    assert timeline.timeline_events[2].deadline_date == "2027-03-01"


def test_drafter_hindi_output():
    payload = ClaimDenialInput(
        policy_number="POL-HI-123456",
        insurer_name="स्टार हेल्थ इंश्योरेंस",
        policy_age_years=6.0,
        claimed_amount=180000.0,
        denied_or_deducted_amount=180000.0,
        denial_category="PED_NON_DISCLOSURE",
        denial_reason_raw="उच्च रक्तचाप का गैर-प्रकटीकरण",
        diagnosis="हार्ट अटैक",
    )
    result = analyze_insurance_denial(payload, language="hi")
    assert "प्रति:" in result.level_1_gro_appeal
    assert "शिकायत निवारण अधिकारी (GRO)" in result.level_1_gro_appeal
    assert "सांविधिक अपील" in result.level_1_gro_appeal
    assert "स्टार हेल्थ इंश्योरेंस" in result.level_1_gro_appeal
    assert len(result.level_2_bimabharosa_text) <= 2000
    assert "बीमा भरोसा" in result.level_2_bimabharosa_text or "IRDAI" in result.level_2_bimabharosa_text
    assert "बीमा लोकपाल के समक्ष शिकायत हेतु तथ्यों का विवरण" in result.level_3_ombudsman_grounds


def test_drafter_marathi_output():
    payload = ClaimDenialInput(
        policy_number="POL-MR-987654",
        insurer_name="केअर हेल्थ इन्शुरन्स",
        policy_age_years=5.5,
        claimed_amount=220000.0,
        denied_or_deducted_amount=220000.0,
        denial_category="PED_NON_DISCLOSURE",
        denial_reason_raw="मधुमेहाची पूर्व माहिती लपविल्याचा आरोप",
        diagnosis="बायपास सर्जरी",
    )
    result = analyze_insurance_denial(payload, language="mr")
    assert "प्रति:" in result.level_1_gro_appeal
    assert "तक्रार निवारण अधिकारी (GRO)" in result.level_1_gro_appeal
    assert "वैधानिक अपील" in result.level_1_gro_appeal
    assert "केअर हेल्थ इन्शुरन्स" in result.level_1_gro_appeal
    assert len(result.level_2_bimabharosa_text) <= 2000
    assert "विमा लोकपाल यांच्याकडे तक्रारीसाठी वस्तुस्थितीचे विवरण" in result.level_3_ombudsman_grounds

