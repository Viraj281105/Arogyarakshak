from dawacheck.metaphone import double_metaphone, phonetic_codes_match


def test_identical_words_match():
    assert phonetic_codes_match("amoxicillin", "amoxicillin") is True


def test_spelling_variant_matches():
    # Common OCR/spelling variants seen in scanned pharmacy bills.
    assert phonetic_codes_match("amoxicillin", "amoxycillin") is True
    assert phonetic_codes_match("azithromycin", "azithromicin") is True


def test_unrelated_words_do_not_match():
    assert phonetic_codes_match("paracetamol", "hospital") is False
    assert phonetic_codes_match("metformin", "unrelated") is False


def test_double_metaphone_returns_two_codes():
    primary, secondary = double_metaphone("Paracetamol")
    assert isinstance(primary, str) and primary
    assert isinstance(secondary, str) and secondary


def test_empty_string_returns_empty_codes():
    assert double_metaphone("") == ("", "")
    assert double_metaphone("123") == ("", "")
