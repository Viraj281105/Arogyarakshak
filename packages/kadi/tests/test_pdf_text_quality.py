"""Tests for the PDF text-layer quality gate (Wave 2, stream A).

The corrupted samples below are short quotations from public Government of India /
Maharashtra documents (see data/raw/devanagari_public_docs/README.md); the "clean" samples are
written for this test and are UNREVIEWED Hindi/Marathi (NEEDS NATIVE-SPEAKER QA). They only need
to be well-formed text, not good prose.
"""

from kadi.pdf_text_quality import TextLayerAssessment, assess_text_layer

# Legacy (Kruti/Chanakya style) font: Hindi stored as Latin look-alike glyph codes.
LEGACY_FONT = (
    "jftLVªh laö Mhö ,yö&33004@99 REGD. NO. D. L.-33004/99\n"
    "vlk/kj.k EXTRAORDINARY Hkkx II—[k.M 3—mi&[k.M (i)\n"
    "izkf/dkj ls izdkf'kr PUBLISHED BY AUTHORITY\n"
    "ubZ fnYyh] c`gLifrokj] vizSy 27] 2017\n"
)

# Hindi stored through a font whose glyph map lands in unrelated Unicode blocks.
STRAY_SCRIPT_HINDI = (
    "िव᭜ त मंᮢालय (िव᭜ तीय सेवाएं िवभाग) (बीमा ᮧभाग) अिधसूचना "
    "कितपय िनयमᲂ का ᮧाᱨप अथाᭅत् बीमा लोकपाल िनयम 2017 "
    "पᳯरभाषाएं इन िनयमᲂ से जब तक संदभᭅ से अ᭠ यथा अपेिᭃत न हो"
)

# Marathi with wrong glyph mapping: stray "ि" and "ऄ", doubled vowel signs.
MARATHI_GLYPH_SWAP = (
    "विस्तावरत महात्मा ज्योवतराि फुले जन अरोग्य योजना ि अयुष्मान भारत "
    "ऄंमलबजािणी सहाय्य संस्थेच्या वनयुक्तीस प्रशासकीय मानयता देण्याबाबत "
    "राखीि ठेिण्यात अलेल्या सािगजवनक अरोग्य विभाग िैद्यकीय वशक्षण"
)

# Hindi with punctuation / Latin letters substituted for Devanagari glyphs.
HINDI_PUNCT_SUBST = (
    "साव$भौ'मक +वा+,य कवरेज आयु$मान भरत -धान मं0ी जन आरो4य योजना "
    "मु#य &ब(दु आयु$मान भारत--धानमं0ी जन आरो4य योजना दु#नया क) सबसे बड़ी "
    "लाभाOथPयQ के Rलए गुणवMापूण0 2वा23य सेवा"
)

CLEAN_MARATHI = (
    "महाराष्ट्र शासन\n"
    "सार्वजनिक आरोग्य विभाग\n"
    "शासन निर्णय क्रमांक: मफुयो-2025\n"
    "दिनांक: ०६ जानेवारी, २०२६\n"
    "या योजनेअंतर्गत रुग्णालयांना रुग्णांच्या उपचारांसाठी मिळणारी रक्कम राज्य आरोग्य हमी "
    "सोसायटीकडून देण्यात येईल. सदर आदेश सर्व रुग्णालयांना लागू आहेत आणि त्याची अंमलबजावणी "
    "तात्काळ करण्यात यावी. या बाबतीत कोणतीही तक्रार असल्यास ती विभागाकडे नोंदवावी.\n"
)

CLEAN_HINDI = (
    "भारतीय बीमा विनियामक और विकास प्राधिकरण\n"
    "पॉलिसी धारक शिकायत पंजीकरण फॉर्म\n"
    "यदि कंपनी की ओर से शिकायत दर्ज की जा रही है तो उसका नाम लिखें। दावा संख्या के साथ दावे का "
    "विवरण भी संलग्न करें। यह फॉर्म सभी शिकायतों के लिए है और इसमें दी गई जानकारी सही होनी चाहिए। "
    "आयुष्मान भारत योजना के अंतर्गत परिवार को स्वास्थ्य बीमा का लाभ मिलता है।\n"
)

CLEAN_ENGLISH = (
    "Tax invoice for room rent and nursing charges. The patient was admitted on 12 March "
    "and discharged on 15 March. Total payable by the insurer is as per the policy schedule. "
    "Please attach the original bills with the claim form. iPhone and eBay are brand names."
)


def test_real_legacy_font_text_is_corrupted():
    a = assess_text_layer(LEGACY_FONT)
    assert isinstance(a, TextLayerAssessment)
    assert a.legacy_font_signature is True
    assert a.verdict == "corrupted"


def test_stray_script_glyph_mapping_is_corrupted():
    a = assess_text_layer(STRAY_SCRIPT_HINDI)
    assert a.legacy_font_signature is True
    assert a.verdict == "corrupted"


def test_marathi_glyph_swap_is_corrupted():
    assert assess_text_layer(MARATHI_GLYPH_SWAP).verdict == "corrupted"


def test_hindi_with_punctuation_substitution_is_corrupted():
    assert assess_text_layer(HINDI_PUNCT_SUBST).verdict == "corrupted"


def test_clean_marathi_is_not_corrupted():
    a = assess_text_layer(CLEAN_MARATHI)
    assert a.verdict == "clean"
    assert a.devanagari_ratio > 0.9
    assert a.legacy_font_signature is False
    assert a.known_word_ratio >= 0.12


def test_clean_hindi_is_not_corrupted():
    a = assess_text_layer(CLEAN_HINDI)
    assert a.verdict == "clean"
    assert a.known_word_ratio >= 0.12


def test_clean_english_is_not_devanagari_and_keeps_the_text_path():
    a = assess_text_layer(CLEAN_ENGLISH)
    assert a.verdict == "not_devanagari"
    assert a.devanagari_ratio == 0.0
    assert a.legacy_font_signature is False


def test_empty_and_whitespace_text_is_not_devanagari():
    assert assess_text_layer("").verdict == "not_devanagari"
    assert assess_text_layer("   \n \n").verdict == "not_devanagari"
    assert assess_text_layer(None).verdict == "not_devanagari"  # type: ignore[arg-type]


def test_a_few_devanagari_words_inside_english_stay_not_devanagari():
    text = CLEAN_ENGLISH + " Amount in words: रुपये."
    assert assess_text_layer(text).verdict == "not_devanagari"


def test_clean_bilingual_page_is_clean():
    assert assess_text_layer(CLEAN_HINDI + "\n" + CLEAN_ENGLISH).verdict == "clean"


def test_ratios_are_bounded_and_deterministic():
    for text in (LEGACY_FONT, CLEAN_MARATHI, CLEAN_ENGLISH, ""):
        a = assess_text_layer(text)
        assert 0.0 <= a.devanagari_ratio <= 1.0
        assert 0.0 <= a.known_word_ratio <= 1.0
        assert a == assess_text_layer(text)


def test_assessment_carries_no_document_text():
    a = assess_text_layer(CLEAN_MARATHI)
    blob = repr(a)
    assert "महाराष्ट्र" not in blob and "रुग्ण" not in blob


# --- Wave 2 review round 1: English and other-script false positives -------------------

import pytest  # noqa: E402

ENGLISH_PAGES = {
    "slashes": "Room charges bed/day 3000 and/or ICU 5000. Pay by cash/card. Discount/waiver nil.",
    "mixed_case_names": (
        "Patient uses iPhone and eBay app, email aBc@mail.com, ID XyZ12, McDonald Road"
    ),
    "greek_mu": "Vitamin B12 500 μg daily after food. Dose 10 μg/kg twice a day. Take with water.",
    "accents": "Café receipt: crème, naïve, fiancé, résumé and the total amount is nil.",
    "invoice": (
        "TAX INVOICE No. 4471  Date 12/03/2026\nPatient name: A Kumar  Age 54  Sex M\n"
        "Room rent 3 days @ 1500 = 4500\nNursing charges 3 days @ 400 = 1200\n"
        "ICU charges 1 day @ 5000 = 5000\nPharmacy as per bill attached\n"
        "Total payable 10700  Discount nil  Net amount 10700\nAuthorised signature and hospital stamp"
    ),
    "prescription": (
        "Dr R Sharma MBBS  Date 12/03/2026\nName: A Kumar Age 54 Sex M\n"
        "Tab Paracetamol 500 mg twice daily after food for 5 days\n"
        "Syrup Cough 5 ml thrice daily  Cap Omeprazole 20 mg once daily before food\n"
        "BP 130/80 mmHg  Follow up after 7 days. Review with reports."
    ),
    "ligatures_nfd": "The ﬁnal ﬂow of résumé files é is on the oﬃce form and the bill.",
}


@pytest.mark.parametrize("name", sorted(ENGLISH_PAGES))
def test_realistic_english_is_not_devanagari(name):
    a = assess_text_layer(ENGLISH_PAGES[name])
    assert a.verdict == "not_devanagari", (name, a)
    assert a.legacy_font_signature is False


OTHER_INDIC = {
    "tamil": "தமிழ் நாடு அரசு மருத்துவமனை கட்டணம் ",
    "gujarati": "ગુજરાત સરકાર હોસ્પિટલ બિલ રકમ ",
    "bengali": "পশ্চিমবঙ্গ সরকার হাসপাতাল বিল ",
    "telugu": "తెలంగాణ ప్రభుత్వ ఆసుపత్రి బిల్లు ",
    "kannada": "ಕರ್ನಾಟಕ ಸರ್ಕಾರ ಆಸ್ಪತ್ರೆ ಬಿಲ್ಲು ",
    "malayalam": "കേരള സർക്കാർ ആശുപത്രി ബിൽ ",
    "gurmukhi": "ਪੰਜਾਬ ਸਰਕਾਰ ਹਸਪਤਾਲ ਬਿੱਲ ",
}


@pytest.mark.parametrize("script", sorted(OTHER_INDIC))
def test_other_indic_scripts_are_not_judged_corrupted(script):
    text = (OTHER_INDIC[script] + "\n") * 6
    a = assess_text_layer(text)
    assert a.verdict != "corrupted", (script, a)
    assert a.legacy_font_signature is False


def test_stray_script_only_page_is_corrupted():
    page = "᭜ᮢᮧᱨᳯ ᭅᭃᲂ᭠ " * 6
    a = assess_text_layer(page)
    assert a.legacy_font_signature is True and a.verdict == "corrupted"


# --- boundaries ------------------------------------------------------------------------

_FILLER = " ".join(["banara", "kolita", "mepana", "satuka"] * 10)


def test_two_garbled_looking_tokens_are_not_enough_but_three_are():
    two = _FILLER + " jftLVh fnYyh"
    three = _FILLER + " jftLVh fnYyh c`gLifrokj"
    assert assess_text_layer(two).verdict == "not_devanagari"
    assert assess_text_layer(three).verdict == "corrupted"


def test_plain_lowercase_legacy_codes_are_caught_without_devanagari():
    legacy = "dk;kZy; foHkkx jkT; ljdkj ;kstuk fo|kFkhZ ukxfjd dk;Zky;] jkT; foHkkx ljdkj " * 2
    a = assess_text_layer(legacy)
    assert a.devanagari_ratio == 0.0
    assert a.verdict == "corrupted"


def _dev_page(n_tokens: int, per_line: int, words: str) -> str:
    vocabulary = words.split()
    tokens = [vocabulary[i % len(vocabulary)] for i in range(n_tokens)]
    return "\n".join(" ".join(tokens[i : i + per_line]) for i in range(0, n_tokens, per_line))


_NON_FUNCTION = "कमल जल फल नगर घर पथ वन रथ मन धन तन गगन सागर पर्वत नदी किला मंदिर"


def test_known_word_ratio_alone_marks_long_prose_pages_corrupted():
    a = assess_text_layer(_dev_page(120, 12, _NON_FUNCTION))
    assert a.malformed_token_ratio == 0.0 and a.mixed_token_ratio == 0.0
    assert a.legacy_font_signature is False
    assert a.known_word_ratio < 0.10
    assert a.verdict == "corrupted"


def test_known_word_ratio_alone_never_condemns_short_or_table_like_pages():
    assert assess_text_layer(_dev_page(60, 12, _NON_FUNCTION)).verdict == "clean"  # short
    assert assess_text_layer(_dev_page(120, 2, _NON_FUNCTION)).verdict == "clean"  # table-like


def test_one_malformed_token_among_forty_is_clean():
    words = "योजना शासन विभाग रुग्णालय कमल जल फल नगर".split()
    tokens = [words[i % len(words)] for i in range(39)] + ["ठेिण्यात"]
    a = assess_text_layer(" ".join(tokens))
    assert a.malformed_token_ratio > 0
    assert a.verdict == "clean"


def test_four_devanagari_tokens_are_ignored_but_five_are_judged():
    bad = "ठेिण्यात राखीि"
    assert assess_text_layer(bad + " कमल जल").verdict == "not_devanagari"  # 4 tokens
    assert assess_text_layer(bad + " कमल जल फल").verdict == "corrupted"  # 5 tokens


def test_matching_is_suffix_aware():
    from kadi.pdf_text_quality import _is_known

    assert _is_known("शासन") and _is_known("शासनाचे")
    assert not _is_known("कमलाचे")
