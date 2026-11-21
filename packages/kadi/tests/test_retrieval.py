"""kadi.retrieval: chunking, Devanagari-aware tokenisation, deterministic BM25 with query-scaled
floors, resource limits and the per-case in-memory index (BYOD: nothing is written to disk).

Expected scores are hand-computed from BM25 with k1=1.5, b=0.75 and
idf = ln(1 + (N - n + 0.5) / (n + 0.5)). Hindi/Marathi sample text below is engineer-written
test data (NEEDS NATIVE-SPEAKER QA), used only to exercise tokenising and abstention."""

import builtins
import io
import math
import os
import pathlib
import shutil
import sqlite3
import tempfile
import threading
import time

import pytest

from kadi.injection import _matching_view
from kadi.retrieval import (
    DEFAULT_MIN_COVERAGE,
    DEFAULT_MIN_SCORE,
    DEFAULT_MIN_SCORE_RATIO,
    Bm25Index,
    CaseRetrievalIndex,
    Chunk,
    Hit,
    RetrievalLimitError,
    chunk_document,
    fold,
    tokenize,
)

LOOSE = dict(min_score=0.0, min_score_ratio=0.0, min_coverage=0.0)


def _idx(**kw):
    return Bm25Index(**{**LOOSE, **kw})


def test_documented_defaults_are_pinned():
    assert DEFAULT_MIN_SCORE == 0.0
    assert DEFAULT_MIN_SCORE_RATIO == 0.25
    assert DEFAULT_MIN_COVERAGE == 0.5


# ---- tokenisation ------------------------------------------------------------
def test_tokenize_lowercases_and_splits_punctuation():
    assert tokenize("Room-Rent, ICU!") == ["room", "rent", "icu"]


def test_amounts_are_unit_aware_and_grouping_independent():
    for form in ("5 lakh", "5-lakh", "5lakh", "5,00,000", "500000", "५ लाख", "5 Lakhs"):
        assert tokenize(form) == ["500000"], form
    assert tokenize("Rs 2,50,000 and 1.50 lakh") == ["rs", "250000", "and", "150000"]
    assert tokenize("2 crore") == ["20000000"] and tokenize("50 thousand") == ["50000"]


def test_decimals_are_canonical():
    assert tokenize("1.5") == tokenize("1.50") == ["1.5"]
    assert tokenize("2.0") == ["2"]


def test_commas_are_removed_only_for_valid_digit_grouping():
    assert tokenize("60,70") == ["60", "70"]
    assert tokenize("1,23") == ["1", "23"]
    assert tokenize("1,000") == ["1000"]
    assert tokenize("12,34,567") == ["1234567"]


def test_tokenize_normalises_devanagari_digits_and_keeps_matras():
    assert tokenize("आयु ७० वर्ष") == ["आयु", "70", "वर्ष"]


def test_tokenize_folds_nukta_and_chandrabindu():
    assert tokenize("ज़रूरी") == tokenize("जरूरी")
    assert tokenize("आँख") == tokenize("आंख")


def test_zwj_and_zwnj_do_not_split_or_change_conjuncts():
    assert tokenize("क्‍ष") == tokenize("क्ष") == tokenize("क्‌ष")
    assert len(tokenize("क्‍ष वर्ष")) == 2


def test_tokenize_splits_on_danda_and_drops_hidden_characters():
    assert tokenize("पात्र।अपात्र") == ["पात्र", "अपात्र"]
    assert tokenize("पात्र॥अपात्र") == ["पात्र", "अपात्र"]
    assert tokenize("ig​nore") == ["ignore"]


def test_stopwords_english_hindi_marathi_only_when_asked():
    assert tokenize("the claim of the patient") == ["the", "claim", "of", "the", "patient"]
    assert tokenize("the claim of the patient", drop_stopwords=True) == ["claim", "patient"]
    assert tokenize("How does the claim work?", drop_stopwords=True) == ["claim", "work"]
    assert tokenize("मेरा क्या है", drop_stopwords=True) == []  # NEEDS NATIVE-SPEAKER QA
    assert tokenize("आहे काय माझा", drop_stopwords=True) == []  # NEEDS NATIVE-SPEAKER QA
    assert tokenize("पात्रता क्या है", drop_stopwords=True) == ["पात्रता"]


def test_token_length_is_capped():
    assert tokenize("a" * 500) == ["a" * 64]


SHARED_FOLD_SAMPLES = [
    "ज़रूरी दस्तावेज़", "आँख", "क्‍ष", "ig​nore", "ＡＢＣ ｐｍｊａｙ", "५० हजार", "Mixed CASE text",
    "ﬁne", "पात्र​।", "tab\there",
]


def test_fold_matches_the_injection_matching_view_on_shared_samples():
    for sample in SHARED_FOLD_SAMPLES:
        assert " ".join(fold(sample).split()) == _matching_view(sample), sample


# ---- chunking ----------------------------------------------------------------
def test_chunk_document_splits_paragraphs_and_quotes_are_exact_substrings():
    text = "First clause about moratorium.\n\nSecond clause about room rent."
    chunks = chunk_document(text, source="doc", page=3)
    assert [c.text for c in chunks] == ["First clause about moratorium.", "Second clause about room rent."]
    assert all(c.source == "doc" and c.page == 3 and c.text in text for c in chunks)
    assert [c.index for c in chunks] == [0, 1]


def test_paragraph_exactly_at_max_words_stays_whole_and_one_more_word_splits():
    assert len(chunk_document("one two three four", "d", 1, max_words=4)) == 1
    over = chunk_document("one two three four five", "d", 1, max_words=4)  # one 5-word sentence
    assert [c.text for c in over] == ["one two three four", "five"]


def test_sentence_packing_with_one_sentence_overlap():
    sentences = [f"Sentence number {i} has exactly seven words." for i in range(6)]  # 7 words each
    text = " ".join(sentences)
    chunks = chunk_document(text, "doc", 1, max_words=16)
    # 7+7 fits (14), a third (21) does not: each next chunk repeats the previous last sentence.
    assert [c.text for c in chunks] == [f"{sentences[i]} {sentences[i + 1]}" for i in range(5)]
    assert all(len(c.text.split()) <= 16 and c.text in text for c in chunks)
    assert all(any(s in c.text for c in chunks) for s in sentences)  # no sentence dropped


def test_no_overlap_when_it_would_not_fit():
    chunks = chunk_document("aa bb cc. dd ee ff gg.", "d", 1, max_words=6)  # 3 + 4 words: 7 > 6
    assert [c.text for c in chunks] == ["aa bb cc.", "dd ee ff gg."]


def test_over_long_sentence_is_windowed_without_dropping_text():
    text = " ".join(f"w{i}" for i in range(50))
    chunks = chunk_document(text, "doc", 1, max_words=20)
    assert " ".join(c.text for c in chunks) == text
    assert [len(c.text.split()) for c in chunks] == [20, 20, 10]


def test_over_long_word_is_split_by_characters_and_limits_hold():
    text = "x" * 2500
    chunks = chunk_document(text, "d", 1, max_chars=1000)
    assert [len(c.text) for c in chunks] == [1000, 1000, 500]
    assert "".join(c.text for c in chunks) == text


def test_chunks_respect_max_chars_for_many_normal_words():
    text = " ".join(["word"] * 400)
    chunks = chunk_document(text, "d", 1, max_words=200, max_chars=100)
    assert all(len(c.text) <= 100 for c in chunks)
    assert " ".join(c.text for c in chunks) == text


def test_document_larger_than_the_limit_is_rejected_loudly():
    with pytest.raises(RetrievalLimitError):
        chunk_document("x" * 101, "d", 1, max_doc_chars=100)
    assert chunk_document("x" * 100, "d", 1, max_doc_chars=100)


def test_chunk_document_blank_text_gives_no_chunks_and_rejects_bad_limits():
    assert chunk_document("  \n\n ", "doc", 1) == []
    with pytest.raises(ValueError):
        chunk_document("a", "d", 1, max_words=0)


def test_danda_and_double_danda_end_sentences():
    assert [c.text for c in chunk_document("पहला वाक्य यहाँ है। दूसरा वाक्य वहाँ है।", "d", 1, max_words=4)] == [
        "पहला वाक्य यहाँ है।",
        "दूसरा वाक्य वहाँ है।",
    ]
    assert [c.text for c in chunk_document("एक दो॥ तीन चार॥", "d", 1, max_words=2)] == ["एक दो॥", "तीन चार॥"]


def test_abbreviations_and_decimals_do_not_split_a_sentence():
    text = "The limit is Rs. 5,00,000 per family. Another sentence."
    chunks = chunk_document(text, "d", 1, max_words=8)
    assert chunks[0].text == "The limit is Rs. 5,00,000 per family."
    text2 = "Cover was 1.50 lakh per family. Next one here."
    assert chunk_document(text2, "d", 1, max_words=6)[0].text == "Cover was 1.50 lakh per family."


def test_chunk_repr_never_shows_the_text():
    assert "SECRETTEXT" not in repr(Chunk("s", 1, 0, "SECRETTEXT"))


ADVERSARIAL = {
    "dot_run": "word " * 81 + "." * 100_000 + "x",
    "mixed_terminators": "ab" + ".!?।॥" * 20_000,
    "terminator_then_word": "word " * 81 + "!?" * 50_000 + "x",
    "one_huge_word": "x" * 100_000,
    "blank_paragraphs": "a\n\n" * 33_333,
    "one_long_paragraph": "word " * 20_000,
    "whitespace": " \n" * 50_000,
    "digit_commas": "1," * 50_000,
    "unit_spaces": "5" + " " * 100_000 + "x",
    "abbreviation_dots": "Rs. " * 25_000,
}


@pytest.mark.parametrize("name", sorted(ADVERSARIAL))
def test_adversarial_inputs_chunk_and_tokenize_in_linear_time(name):
    text = ADVERSARIAL[name]
    start = time.perf_counter()
    chunk_document(text, "d", 1)
    tokenize(text)
    assert time.perf_counter() - start < 0.5, name


# ---- BM25 --------------------------------------------------------------------
def _two_docs(**kw):
    idx = _idx(**kw)
    idx.add(Chunk("A", 1, 0, "alpha beta"))
    idx.add(Chunk("B", 1, 0, "gamma delta"))
    return idx


def test_bm25_score_matches_hand_computation():
    # N=2, n=1: idf = ln(1 + 1.5/1.5) = ln 2.  tf=1, dl=avgdl=2 -> tf part = 2.5/2.5 = 1.
    hits = _two_docs().search("alpha", k=5)
    assert len(hits) == 1
    assert (hits[0].source, hits[0].page, hits[0].quote) == ("A", 1, "alpha beta")
    assert hits[0].score == pytest.approx(math.log(2))


def test_bm25_term_frequency_matches_hand_computation():
    # A = "alpha alpha beta" (dl 3), B = "gamma" (dl 1), avgdl 2, n=1 -> idf ln 2.
    # tf=2: 2 * 2.5 / (2 + 1.5 * (0.25 + 0.75 * 3/2)) = 5 / 4.0625
    idx = _idx()
    idx.add(Chunk("A", 1, 0, "alpha alpha beta"))
    idx.add(Chunk("B", 1, 0, "gamma"))
    assert idx.search("alpha", k=1)[0].score == pytest.approx(math.log(2) * 5 / 4.0625)


def test_bm25_length_normalisation_matches_hand_computation():
    idx = _idx()
    idx.add(Chunk("A", 1, 0, "x"))
    idx.add(Chunk("B", 1, 0, "x y z"))
    hits = {h.source: h.score for h in idx.search("x", k=2)}
    idf = math.log(1.2)  # N=2, n=2
    assert hits["A"] == pytest.approx(idf * 2.5 / (1 + 1.5 * (0.25 + 0.75 * 0.5)))
    assert hits["B"] == pytest.approx(idf * 2.5 / (1 + 1.5 * (0.25 + 0.75 * 1.5)))


def test_ranks_the_chunk_with_more_query_terms_first():
    idx = _idx()
    idx.add(Chunk("A", 1, 0, "claim moratorium five years"))
    idx.add(Chunk("B", 1, 0, "claim room rent cap"))
    idx.add(Chunk("C", 1, 0, "unrelated hospital name"))
    hits = idx.search("claim moratorium", k=3)
    assert [h.source for h in hits] == ["A", "B"]
    assert hits[0].score > hits[1].score > 0


def test_k_truncates_to_the_best_hits():
    idx = _idx()
    for i in range(6):
        idx.add(Chunk(f"S{i}", 1, 0, "claim " + "pad " * i))  # longer chunks score lower
    hits = idx.search("claim", k=2)
    assert [h.source for h in hits] == ["S0", "S1"]
    assert len(idx.search("claim", k=100)) == 6


def test_duplicate_query_terms_count_once_for_coverage():
    idx = Bm25Index(min_score=0.0, min_score_ratio=0.0, min_coverage=0.5)
    idx.add(Chunk("A", 1, 0, "xa xb"))
    idx.add(Chunk("B", 1, 0, "xc xd"))
    # distinct terms {xa, xb, xc}: need ceil(0.5 * 3) = 2. Counting duplicates (5 terms) would need 3.
    assert [h.source for h in idx.search("xa xa xa xb xc", k=3)] == ["A"]


def test_tie_break_is_source_page_then_chunk_index():
    idx = _idx()
    idx.add(Chunk("A", 1, 1, "same one"))
    idx.add(Chunk("A", 1, 0, "same two"))
    assert [h.quote for h in idx.search("same", k=2)] == ["same two", "same one"]
    idx2 = _idx()
    for src, page in [("B", 2), ("A", 9), ("A", 1), ("B", 1)]:
        idx2.add(Chunk(src, page, 0, "same text here"))
    first = idx2.search("same text", k=4)
    assert [(h.source, h.page) for h in first] == [("A", 1), ("A", 9), ("B", 1), ("B", 2)]
    assert first == idx2.search("same text", k=4)


def test_absolute_floor_drops_hits_below_it():
    idx = _two_docs(min_score=1.0)  # best possible score is ln 2 = 0.693
    assert idx.search("alpha", k=5) == []
    assert _two_docs(min_score=0.69).search("alpha", k=5)


def test_ratio_floor_scales_with_the_query_hand_computed():
    # "alpha zzz": idf(alpha)=ln2=0.693; zzz is absent (n=0): ln(1 + 2.5/0.5) = ln 6 = 1.792.
    # reference = 2.485; the alpha chunk scores 0.693.  0.25*2.485 = 0.621 -> kept; 0.3*2.485 = 0.746 -> dropped.
    assert _two_docs(min_score_ratio=0.25).search("alpha zzz", k=3)
    assert _two_docs(min_score_ratio=0.3).search("alpha zzz", k=3) == []


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_default_floors_answer_a_single_term_query_in_a_tiny_index(n):
    """A single rejection letter is the typical BYOD case: a present term must not abstain."""
    idx = Bm25Index()
    for i in range(n):
        idx.add(Chunk("S", i, 0, f"term{i} common"))
    hits = idx.search("term0")
    assert [h.page for h in hits] == [0]
    assert idx.search("absentterm") == []


def test_default_floors_on_short_realistic_chunks():
    idx = Bm25Index()
    idx.add_document("Claim denied for late intimation.", source="letter", page=1)
    assert idx.search("late intimation")[0].page == 1
    assert idx.search("moratorium") == []


def test_coverage_floor_requires_all_terms_for_short_queries():
    idx = Bm25Index(min_score=0.0, min_score_ratio=0.0)
    idx.add(Chunk("ration", 1, 0, "ration card holders qualify"))
    assert idx.search("pan card") == []  # 1 of 2 terms: not enough
    assert idx.search("ration card")[0].source == "ration"
    assert idx.search("card")[0].source == "ration"


def test_coverage_floor_for_longer_queries_is_a_share():
    idx = Bm25Index(min_score=0.0, min_score_ratio=0.0, min_coverage=0.5)
    idx.add(Chunk("A", 1, 0, "alpha beta"))
    assert idx.search("alpha zzz yyy") == []  # 1 of 3 < ceil(1.5) = 2
    assert idx.search("alpha beta yyy")  # 2 of 3
    loose = _idx()
    loose.add(Chunk("A", 1, 0, "alpha beta"))
    assert loose.search("alpha zzz yyy")


def test_search_on_empty_index_or_empty_query_or_nonpositive_k_is_empty():
    assert Bm25Index().search("anything", k=3) == []
    assert _two_docs().search("", k=3) == []
    assert _two_docs().search("alpha", k=0) == []
    assert _two_docs().search(None, k=3) == []  # type: ignore[arg-type]


def test_stopword_only_query_returns_nothing():
    idx = _idx()
    idx.add(Chunk("A", 1, 0, "the of and the"))
    assert idx.search("the of and", k=3) == []


def test_hit_quote_is_always_the_indexed_text_not_generated():
    idx = _idx()
    texts = {"x": "Moratorium period is 5 years.", "y": "Room rent cap applies."}
    for i, (s, t) in enumerate(texts.items()):
        idx.add(Chunk(s, i + 1, 0, t))
    for h in idx.search("moratorium rent", k=5):
        assert h.quote == texts[h.source]


def test_devanagari_variants_and_digits_match_after_folding():
    idx = Bm25Index()
    idx.add(Chunk("hi", 1, 0, "ज़रूरी दस्तावेज़ जमा करें"))
    idx.add(Chunk("age", 2, 0, "आयु 70 वर्ष या अधिक"))
    assert idx.search("जरूरी दस्तावेज", k=1)[0].source == "hi"
    assert idx.search("७०", k=1)[0].source == "age"  # Devanagari digits vs ASCII digits in the document


def test_mixed_script_query_matches_an_english_clause():
    idx = Bm25Index()
    idx.add(Chunk("en", 1, 0, "PMJAY covers every senior citizen aged 70 and above"))
    idx.add(Chunk("other", 1, 0, "room rent proportionate deduction"))
    hits = idx.search("PMJAY में 70 साल")  # 'में' is a stop-word; pmjay + 70 match, साल does not
    assert [h.source for h in hits] == ["en"]


def test_amount_forms_match_across_spellings_in_retrieval():
    idx = Bm25Index()
    idx.add(Chunk("a", 1, 0, "cover of Rs 5,00,000 per family"))
    idx.add(Chunk("b", 1, 0, "unrelated hospital note"))
    for q in ("5 lakh cover", "500000 cover", "५ लाख cover"):
        assert [h.source for h in idx.search(q)] == ["a"], q


def test_hindi_out_of_corpus_queries_return_nothing_never_a_guess():
    """NEEDS NATIVE-SPEAKER QA: engineer-written Hindi sample corpus."""
    idx = Bm25Index()
    idx.add_document("आयुष्मान कार्ड बनवाने के लिए आधार दिखाएं", source="hi", page=1)
    idx.add_document("पात्र परिवारों को पांच लाख रुपये का कवर मिलता है", source="hi", page=2)
    idx.add_document("अस्पताल में नकद रहित इलाज उपलब्ध है", source="hi", page=3)
    assert idx.search("मौसम का हाल क्या है") == []
    assert idx.search("पैन कार्ड कैसे बनवाएं") == []  # shares only 'कार्ड'
    assert idx.search("आयुष्मान कार्ड")[0].page == 1  # sanity: the corpus is searchable


def test_add_document_chunks_and_indexes_in_one_call():
    idx = _idx()
    n = idx.add_document("Para one about alpha.\n\nPara two about beta.", source="S", page=2)
    assert n == 2 and len(idx) == 2
    assert idx.search("beta", k=1)[0].quote == "Para two about beta."


def test_hit_is_frozen_and_repr_hides_untrusted_text():
    h = Hit("SECRETSOURCE", 1, "SECRETQUOTE", 1.0)
    with pytest.raises(Exception):
        h.score = 2.0  # type: ignore[misc]
    assert "SECRET" not in repr(h)
    idx = _idx()
    idx.add(Chunk("s", 1, 0, "SECRETQUOTE"))
    assert "SECRET" not in repr(idx)


# ---- limits ------------------------------------------------------------------
def test_max_chunks_is_enforced_loudly_and_atomically():
    idx = _idx(max_chunks=2)
    idx.add(Chunk("A", 1, 0, "one"))
    idx.add(Chunk("A", 2, 0, "two"))
    with pytest.raises(RetrievalLimitError):
        idx.add(Chunk("A", 3, 0, "three"))
    idx2 = _idx(max_chunks=2)
    with pytest.raises(RetrievalLimitError):
        idx2.add_document("p one\n\np two\n\np three", source="S", page=1)
    assert len(idx2) == 0  # nothing was added


def test_oversized_document_is_rejected_by_the_index():
    idx = _idx()
    with pytest.raises(RetrievalLimitError):
        idx.add_document("x" * 1_000_001, source="S", page=1)
    assert len(idx) == 0


def test_query_length_and_term_count_are_capped_not_crashing():
    idx = _idx()
    idx.add(Chunk("A", 1, 0, "t0"))
    idx.add(Chunk("B", 1, 0, "t99"))
    assert [h.source for h in idx.search(" ".join(f"t{i}" for i in range(100)), k=5)] == ["A"]  # 32-term cap
    idx.add(Chunk("C", 1, 0, "alpha"))
    assert idx.search("zzz " * 10_000 + "alpha") == []  # cut at 1000 characters before 'alpha'


def test_hit_quote_is_truncated_to_the_configured_length():
    idx = _idx(max_quote_chars=10)
    idx.add(Chunk("A", 1, 0, "alpha beta gamma delta"))
    assert idx.search("alpha")[0].quote == "alpha beta"


def test_k_is_capped():
    idx = _idx()
    for i in range(150):
        idx.add(Chunk("S", i, 0, "claim"))
    assert len(idx.search("claim", k=10**9)) == 100


def test_concurrent_add_and_search_are_safe():
    idx = _idx()
    errors = []

    def work(n):
        try:
            for i in range(30):
                idx.add_document(f"claim number {n} {i}", source=f"S{n}", page=i)
                idx.search("claim", k=5)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(n,)) for n in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors and len(idx) == 180


# ---- per-case in-memory index (BYOD) -----------------------------------------
def test_purge_empties_every_internal_structure():
    idx = CaseRetrievalIndex("case-1", **LOOSE)
    idx.add_document("alpha beta gamma", source="S", page=1)
    assert len(idx) == 1 and idx.search("alpha", k=1)
    idx.purge()
    assert len(idx) == 0 and idx.search("alpha", k=1) == []
    assert idx._chunks == [] and idx._tf == [] and idx._len == [] and idx._df == {}
    assert idx._postings == {} and idx._total_len == 0
    assert idx.purged is True


def test_purged_flag_is_read_only_and_purged_index_refuses_documents():
    idx = CaseRetrievalIndex("case-1")
    idx.purge()
    with pytest.raises(AttributeError):
        idx.purged = False  # type: ignore[misc]
    with pytest.raises(RuntimeError):
        idx.add_document("alpha", source="S", page=1)
    with pytest.raises(RuntimeError):
        idx.add(Chunk("S", 1, 0, "alpha"))
    with pytest.raises(RuntimeError):  # the purge check comes before any size check
        idx.add_document("x" * 2_000_000, source="S", page=1)


def test_context_manager_purges_on_normal_and_on_exception_exit():
    with CaseRetrievalIndex("c", **LOOSE) as idx:
        idx.add_document("alpha beta", source="S", page=1)
        assert idx.search("alpha", k=1)
    assert idx.purged and len(idx) == 0
    with pytest.raises(ValueError):
        with CaseRetrievalIndex("c2", **LOOSE) as idx2:
            idx2.add_document("alpha beta", source="S", page=1)
            raise ValueError("boom")
    assert idx2.purged and len(idx2) == 0 and idx2._tf == []


def test_index_does_not_touch_the_filesystem_through_the_common_entry_points(monkeypatch, tmp_path):
    """Zero retention. The common file-creating entry points are patched to fail; this is a
    tripwire for accidental persistence, not a proof that no other path could write."""
    monkeypatch.chdir(tmp_path)
    before = set(os.listdir(tmp_path))

    def forbidden(*a, **k):
        raise AssertionError("retrieval touched the filesystem")

    for owner, names in [
        (builtins, ["open"]),
        (io, ["open"]),
        (os, ["open", "fdopen", "mkdir", "makedirs", "rename", "replace"]),
        (pathlib.Path, ["open", "write_text", "write_bytes", "touch", "mkdir"]),
        (tempfile, ["mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryFile", "SpooledTemporaryFile"]),
        (sqlite3, ["connect"]),
        (shutil, ["copyfile", "copy", "copy2", "move", "copyfileobj"]),
    ]:
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)

    idx = CaseRetrievalIndex("case-2", **LOOSE)
    idx.add_document("Patient bill for knee surgery.\n\nDischarge summary text.", source="bill", page=1)
    assert idx.search("knee surgery", k=2)
    idx.purge()
    assert set(os.listdir(tmp_path)) == before


def test_index_does_not_log_document_text(caplog):
    caplog.set_level("DEBUG")
    idx = CaseRetrievalIndex("case-3", **LOOSE)
    idx.add_document("SECRETPATIENTNAME had surgery", source="S", page=1)
    idx.search("SECRETPATIENTNAME", k=1)
    idx.purge()
    assert "secretpatientname" not in caplog.text.lower()
