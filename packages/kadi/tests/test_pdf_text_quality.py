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
