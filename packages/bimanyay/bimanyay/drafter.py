"""
BimaNyay Appeal & Grievance Package Drafter.

Generates structured, legally cited appeal documents across the 3 statutory tiers:
1. Insurer Grievance Redressal Officer (GRO)
2. IRDAI Bima Bharosa Portal (IGMS)
3. Council for Insurance Ombudsmen (CIO) Form VI
"""

from typing import List
from bimanyay.models import ClaimDenialInput, RegulatoryViolation


def draft_gro_appeal_letter(
    input_data: ClaimDenialInput,
    grounds: str,
    violations: List[RegulatoryViolation],
    language: str = "en",
) -> str:
    """Drafts formal representation letter addressed to the Insurer's Grievance Redressal Officer in English, Hindi, or Marathi."""
    lang = language.lower()

    if lang == "hi":
        violations_text = "\n".join([f"- {v.clause_reference} ({v.statute_or_circular}): {v.violation_summary}" for v in violations])
        return f"""प्रति:
शिकायत निवारण अधिकारी (GRO)
{input_data.insurer_name}

विषय: पॉलिसी संख्या {input_data.policy_number} के अंतर्गत दावा निरस्तीकरण के विरुद्ध औपचारिक सांविधिक अपील

महोदय / महोदया,

मैं {input_data.diagnosis} के उपचार हेतु कुल दावा राशि ₹{input_data.claimed_amount:,.2f} में से अस्वीकृत / काटी गई राशि ₹{input_data.denied_or_deducted_amount:,.2f} के मनमाने और विधि-विरुद्ध निरस्तीकरण के विरुद्ध यह औपचारिक सांविधिक अपील दर्ज कर रहा हूँ।

बीमाकर्ता द्वारा दिया गया निरस्तीकरण कारण:
"{input_data.denial_reason_raw}"

अपील के सांविधिक आधार:
{grounds}

उल्लंघन किए गए IRDAI विनियामक प्रावधान:
{violations_text}

IRDAI स्वास्थ्य बीमा मास्टर परिपत्र (२९ मई २०२४) के अनुसार, ३-सदस्यीय दावा समीक्षा समिति (CRC) के पूर्व लिखित अनुमोदन के बिना कोई भी स्वास्थ्य बीमा दावा निरस्त नहीं किया जा सकता। इसके अतिरिक्त, सांविधिक समय-सीमा के भीतर दावा निपटान न करने पर बीमाकर्ता बैंक दर + २% की दर से दंडात्मक ब्याज देने हेतु उत्तरदायी है।

अतः आपसे अनुरोध है कि मेरे दावे की निष्पक्ष पुनर्परीक्षा कर १५ दिनों की सांविधिक समय-सीमा के भीतर स्वीकार्य दावा राशि ₹{input_data.denied_or_deducted_amount:,.2f} जारी करने की कृपा करें। समाधान न होने पर यह प्रकरण IRDAI बीमा भरोसा पोर्टल एवं बीमा लोकपाल के समक्ष प्रस्तुत किया जाएगा।

भवदीय,
[पॉलिसीधारक का नाम]
पॉलिसी संख्या: {input_data.policy_number}
"""
    elif lang == "mr":
        violations_text = "\n".join([f"- {v.clause_reference} ({v.statute_or_circular}): {v.violation_summary}" for v in violations])
        return f"""प्रति:
तक्रार निवारण अधिकारी (GRO)
{input_data.insurer_name}

विषय: पॉलिसी क्र. {input_data.policy_number} अंतर्गत दावा नाकारल्याबाबत कायदेशीर वैधानिक अपील

महोदय / महोदया,

मी {input_data.diagnosis} च्या उपचारासाठी एकूण दावा रक्कम ₹{input_data.claimed_amount:,.2f} पैकी नाकारण्यात आलेली ₹{input_data.denied_or_deducted_amount:,.2f} या रकमेच्या अवाजवी व एकतर्फी नकाराविरुद्ध ही औपचारिक वैधानिक तक्रार नोंदवत आहे.

विमा कंपनीने दिलेले नकाराचे कारण:
"{input_data.denial_reason_raw}"

अपीलचे कायदेशीर आधार:
{grounds}

उल्लंघन केलेले IRDAI वैधानिक नियम:
{violations_text}

IRDAI आरोग्य विमा मास्टर परिपत्रक (२९ मे २०२४) नुसार, ३-सदस्यीय दावा पुनरावलोकन समितीच्या (CRC) पूर्व लेखी मंजुरीशिवाय कोणताही आरोग्य विमा दावा नाकारता येत नाही. तसेच, विहित मुदतीत दाव्याचा निपटारा न केल्यास बँक दरापेक्षा २% अधिक दंडात्मक व्याज देणे बंधनकारक आहे.

तरी माझ्या दाव्याची फेरतपासणी करून १५ दिवसांच्या वैधानिक मुदतीत पात्र रक्कम ₹{input_data.denied_or_deducted_amount:,.2f} मंजूर करावी. अन्यथा सदर प्रकरण IRDAI विमा भरोसा पोर्टल व विमा लोकपाल यांच्याकडे वर्ग केले जाईल.

आपला नम्र,
[पॉलिसीधारकाचे नाव]
पॉलिसी क्र: {input_data.policy_number}
"""

    violations_text = "\n".join([f"- {v.clause_reference} ({v.statute_or_circular}): {v.violation_summary}" for v in violations])

    return f"""TO:
The Grievance Redressal Officer (GRO)
{input_data.insurer_name}

SUBJECT: Formal Appeal Against Wrongful Repudiation of Claim No. [CLAIM_NO] Under Policy No. {input_data.policy_number}

Dear Sir / Madam,

I am writing to register an urgent grievance against the arbitrary and wrongful repudiation / disallowance of my health insurance claim amounting to INR {input_data.denied_or_deducted_amount:,.2f} out of total claimed expenses of INR {input_data.claimed_amount:,.2f} for treatment of {input_data.diagnosis}.

REASON CITED BY INSURER:
"{input_data.denial_reason_raw}"

GROUNDS OF APPEAL:
{grounds}

STATUTORY IRDAI PROVISIONS VIOLATED:
{violations_text}

Under the IRDAI Master Circular on Health Insurance Business (May 29, 2024), health insurance claims cannot be repudiated without documented prior approval of the Claims Review Committee (CRC). Furthermore, insurers failing to settle claims within statutory timelines are liable to pay penal interest at Bank Rate + 2%.

I request you to re-examine my claim dossier and release the admissible settlement amount of INR {input_data.denied_or_deducted_amount:,.2f} within the statutory 15-day resolution window. Failing this, I will escalate this matter to the IRDAI Bima Bharosa portal and the Insurance Ombudsman.

Yours faithfully,
[POLICYHOLDER NAME]
Policy No: {input_data.policy_number}
"""


def draft_bimabharosa_summary(
    input_data: ClaimDenialInput,
    grounds: str,
    language: str = "en",
) -> str:
    """Generates concise text strictly within the 2,000-character limit of the IRDAI Bima Bharosa web form."""
    lang = language.lower()

    if lang == "hi":
        summary = (
            f"{input_data.insurer_name} द्वारा अनुचित दावा निरस्तीकरण के विरुद्ध शिकायत। "
            f"पॉलिसी संख्या: {input_data.policy_number}। अस्वीकृत राशि: ₹{input_data.denied_or_deducted_amount:,.2f}। "
            f"कंपनी का कारण: '{input_data.denial_reason_raw}'। "
            f"आधार: {grounds} "
            "कंपनी IRDAI मास्टर परिपत्र २०२४ के अनुसार १५ दिवसीय सांविधिक सीमा में समाधान देने में विफल रही। "
            "IRDAI से २% अतिरिक्त बैंक दर दंडात्मक ब्याज सहित दावा निपटान का निर्देश देने का अनुरोध है।"
        )
        return summary[:2000]
    elif lang == "mr":
        summary = (
            f"{input_data.insurer_name} विरुद्ध दावा अवाजवीपणे नाकारल्याबाबत तक्रार. "
            f"पॉलिसी क्र: {input_data.policy_number}. नाकारलेली रक्कम: ₹{input_data.denied_or_deducted_amount:,.2f}. "
            f"विमा कंपनीचे कारण: '{input_data.denial_reason_raw}'. "
            f"आधार: {grounds} "
            "कंपनी १५ दिवसांच्या IRDAI कायदेशीर मुदतीत तक्रार निवारण करण्यात अपयशी ठरली. "
            "IRDAI ने कंपनीस २% दंडात्मक व्याजासह तत्काळ भरपाई देण्याचे निर्देश द्यावेत ही नम्र विनंती."
        )
        return summary[:2000]

    summary = (
        f"Grievance against {input_data.insurer_name} for wrongful claim repudiation. "
        f"Policy No: {input_data.policy_number}. Disallowed Amount: INR {input_data.denied_or_deducted_amount:,.2f}. "
        f"Insurer Rejection Reason: '{input_data.denial_reason_raw}'. "
        f"Grounds: {grounds} "
        "Insurer failed to resolve dispute within 15-day statutory window under IRDAI Master Circular 2024. "
        "Requesting IRDAI regulatory intervention to direct settlement with statutory penal interest."
    )
    return summary[:2000]


def draft_ombudsman_statement(
    input_data: ClaimDenialInput,
    grounds: str,
    language: str = "en",
) -> str:
    """Drafts Statement of Facts for Insurance Ombudsman Form VI under Rule 14(1)(b)."""
    lang = language.lower()

    if lang == "hi":
        return f"""बीमा लोकपाल के समक्ष शिकायत हेतु तथ्यों का विवरण
(बीमा लोकपाल नियम, २०१७ के नियम १४(१)(बी) के अंतर्गत)

१. शिकायतकर्ता का नाम एवं विवरण: [पॉलिसीधारक का नाम]
२. बीमाकर्ता कंपनी का नाम: {input_data.insurer_name}
३. पॉलिसी संख्या: {input_data.policy_number} (सक्रियता अवधि: {input_data.policy_age_years} वर्ष)
४. कुल दावा राशि: ₹{input_data.claimed_amount:,.2f}
५. अस्वीकृत / विवादित राशि: ₹{input_data.denied_or_deducted_amount:,.2f}
६. बीमारी / उपचार का विवरण: {input_data.diagnosis}
७. विधिक अनुतोष के आधार:
{grounds}
८. प्रार्थित अनुतोष:
{input_data.insurer_name} को अस्वीकृत राशि ₹{input_data.denied_or_deducted_amount:,.2f} का भुगतान IRDAI नियमों के अंतर्गत विलंबित निपटान हेतु बैंक दर से २% अतिरिक्त सांविधिक दंडात्मक ब्याज सहित करने का आदेश जारी किया जाए।
"""
    elif lang == "mr":
        return f"""विमा लोकपाल यांच्याकडे तक्रारीसाठी वस्तुस्थितीचे विवरण
(विमा लोकपाल नियम, २०१७ च्या नियम १४(१)(बी) अन्वये)

१. तक्रारदाराचे नाव व तपशील: [पॉलिसीधारकाचे नाव]
२. विमा कंपनीचे नाव: {input_data.insurer_name}
३. पॉलिसी क्रमांक: {input_data.policy_number} (सलग कालावधी: {input_data.policy_age_years} वर्षे)
४. एकूण दावा रक्कम: ₹{input_data.claimed_amount:,.2f}
५. नाकारलेली / कपात रक्कम: ₹{input_data.denied_or_deducted_amount:,.2f}
६. आजार / उपचाराचे स्वरूप: {input_data.diagnosis}
७. कायदेशीर दाव्याचे आधार:
{grounds}
८. मागितलेले कायदेशीर निवारण:
{input_data.insurer_name} विमा कंपनीस नाकारलेली रक्कम ₹{input_data.denied_or_deducted_amount:,.2f} ही बँक दरापेक्षा २% अधिक दंडात्मक व्याजासह देण्याचे निर्देश देण्यात यावेत.
"""

    return f"""STATEMENT OF FACTS FOR COMPLAINT TO INSURANCE OMBUDSMAN
(Under Rule 14(1)(b) of Insurance Ombudsman Rules, 2017)

1. Complainant Name & Details: [POLICYHOLDER NAME]
2. Insurer Name: {input_data.insurer_name}
3. Policy Number: {input_data.policy_number}
4. Policy Inception Date: Active continuously for {input_data.policy_age_years} years
5. Total Claim Amount: INR {input_data.claimed_amount:,.2f}
6. Disallowed / Repudiated Amount: INR {input_data.denied_or_deducted_amount:,.2f}
7. Nature of Disease / Treatment: {input_data.diagnosis}
8. Grounds for Relief:
{grounds}
9. Relief Sought:
Direction to {input_data.insurer_name} to pay INR {input_data.denied_or_deducted_amount:,.2f} along with 2% above bank rate penal interest for delayed settlement as mandated by IRDAI regulations.
"""
