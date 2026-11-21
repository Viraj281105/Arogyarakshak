"""kadi.retrieval: chunking, Devanagari-aware tokenisation, deterministic BM25 with a score
floor, and the per-case in-memory index (BYOD: nothing is ever written to disk).

Expected scores are hand-computed from the BM25 formula with k1=1.5, b=0.75 and
idf = ln(1 + (N - n + 0.5) / (n + 0.5))."""

import builtins
import math
import os
import pathlib

import pytest

from kadi.retrieval import Bm25Index, CaseRetrievalIndex, Chunk, Hit, chunk_document, tokenize


# ---- tokenisation ------------------------------------------------------------
def test_tokenize_lowercases_and_splits_punctuation():
    assert tokenize("Room-Rent, ICU!") == ["room", "rent", "icu"]


def test_tokenize_keeps_indian_grouped_and_decimal_numbers_whole():
    assert tokenize("Rs 2,50,000 and 1.50 lakh") == ["rs", "250000", "and", "1.50", "lakh"]


def test_tokenize_normalises_devanagari_digits_and_keeps_matras():
    assert tokenize("आयु ७० वर्ष") == ["आयु", "70", "वर्ष"]


def test_tokenize_folds_nukta_and_chandrabindu_like_the_injection_matching_view():
    assert tokenize("ज़रूरी") == tokenize("जरूरी")
    assert tokenize("आँख") == tokenize("आंख")


def test_tokenize_splits_on_danda_and_drops_hidden_characters():
    assert tokenize("पात्र।अपात्र") == ["पात्र", "अपात्र"]
    assert tokenize("ig​nore") == ["ignore"]


def test_tokenize_drops_english_stopwords_only_when_asked():
    assert tokenize("the claim of the patient") == ["the", "claim", "of", "the", "patient"]
    assert tokenize("the claim of the patient", drop_stopwords=True) == ["claim", "patient"]


# ---- chunking ----------------------------------------------------------------
def test_chunk_document_splits_paragraphs_and_quotes_are_exact_substrings():
    text = "First clause about moratorium.\n\nSecond clause about room rent."
    chunks = chunk_document(text, source="doc", page=3)
    assert [c.text for c in chunks] == ["First clause about moratorium.", "Second clause about room rent."]
    assert all(c.source == "doc" and c.page == 3 for c in chunks)
    assert all(c.text in text for c in chunks)
    assert [c.index for c in chunks] == [0, 1]


def test_chunk_document_packs_long_paragraph_by_sentence_under_the_word_limit():
    sentences = [f"Sentence number {i} has exactly seven words." for i in range(6)]
    text = " ".join(sentences)
    chunks = chunk_document(text, "doc", 1, max_words=16)
    assert len(chunks) == 3  # two 8-word sentences per chunk
    assert all(len(c.text.split()) <= 16 for c in chunks)
    assert all(c.text in text for c in chunks)
    assert " ".join(c.text for c in chunks) == text


def test_chunk_document_never_drops_text_of_an_over_long_sentence():
    text = " ".join(f"w{i}" for i in range(50))  # one 50-word sentence
    chunks = chunk_document(text, "doc", 1, max_words=20)
    assert " ".join(c.text for c in chunks) == text
    assert all(len(c.text.split()) <= 20 for c in chunks)


def test_chunk_document_blank_text_gives_no_chunks():
    assert chunk_document("  \n\n ", "doc", 1) == []


def test_chunk_document_splits_devanagari_sentences_on_danda():
    text = "पहला वाक्य यहाँ है। दूसरा वाक्य वहाँ है।"
    chunks = chunk_document(text, "d", 1, max_words=4)
    assert [c.text for c in chunks] == ["पहला वाक्य यहाँ है।", "दूसरा वाक्य वहाँ है।"]


# ---- BM25 --------------------------------------------------------------------
def _two_docs(**kw):
    idx = Bm25Index(**kw)
    idx.add(Chunk("A", 1, 0, "alpha beta"))
    idx.add(Chunk("B", 1, 0, "gamma delta"))
    return idx


def test_bm25_score_matches_hand_computation():
    # N=2, n=1: idf = ln(1 + 1.5/1.5) = ln 2.  tf=1, dl=avgdl=2 -> tf part = 2.5/2.5 = 1.
    hits = _two_docs(min_score=0.0).search("alpha", k=5)
    assert len(hits) == 1
    assert hits[0].source == "A" and hits[0].page == 1 and hits[0].quote == "alpha beta"
    assert hits[0].score == pytest.approx(math.log(2))


def test_bm25_length_normalisation_matches_hand_computation():
    # N=2, doc A has 1 token, doc B has 3; avgdl = 2. Both contain "x" once -> n=2.
    # idf = ln(1 + 0.5/2.5) = ln 1.2.
    # A: 2.5 / (1 + 1.5*(0.25 + 0.75*1/2)) = 2.5 / (1 + 0.9375) ; B: 2.5 / (1 + 1.5*(0.25 + 0.75*3/2)).
    idx = Bm25Index(min_score=0.0)
    idx.add(Chunk("A", 1, 0, "x"))
    idx.add(Chunk("B", 1, 0, "x y z"))
    hits = {h.source: h.score for h in idx.search("x", k=2)}
    idf = math.log(1.2)
    assert hits["A"] == pytest.approx(idf * 2.5 / (1 + 1.5 * (0.25 + 0.75 * 0.5)))
    assert hits["B"] == pytest.approx(idf * 2.5 / (1 + 1.5 * (0.25 + 0.75 * 1.5)))
    assert hits["A"] > hits["B"]


def test_bm25_ranks_the_chunk_with_more_query_terms_first():
    idx = Bm25Index(min_score=0.0)
    idx.add(Chunk("A", 1, 0, "claim moratorium five years"))
    idx.add(Chunk("B", 1, 0, "claim room rent cap"))
    idx.add(Chunk("C", 1, 0, "unrelated hospital name"))
    hits = idx.search("claim moratorium", k=3)
    assert [h.source for h in hits] == ["A", "B"]
    assert hits[0].score > hits[1].score > 0


def test_search_returns_empty_below_the_floor_never_a_guess():
    idx = _two_docs(min_score=1.0)  # best possible score is ln 2 = 0.693 < 1.0
    assert idx.search("alpha", k=5) == []
    assert idx.search("zzz nothing matches", k=5) == []


def test_search_on_empty_index_or_empty_query_or_nonpositive_k_is_empty():
    assert Bm25Index().search("anything", k=3) == []
    assert _two_docs(min_score=0.0).search("", k=3) == []
    assert _two_docs(min_score=0.0).search("alpha", k=0) == []


def test_stopword_only_query_returns_nothing():
    idx = Bm25Index(min_score=0.0)
    idx.add(Chunk("A", 1, 0, "the of and the"))
    assert idx.search("the of and", k=3) == []


def test_search_is_deterministic_and_ties_break_by_source_page_index():
    idx = Bm25Index(min_score=0.0)
    for src, page in [("B", 2), ("A", 9), ("A", 1), ("B", 1)]:
        idx.add(Chunk(src, page, 0, "same text here"))
    first = idx.search("same text", k=4)
    assert [(h.source, h.page) for h in first] == [("A", 1), ("A", 9), ("B", 1), ("B", 2)]
    assert first == idx.search("same text", k=4)


def test_hit_quote_is_always_the_indexed_text_not_generated():
    idx = Bm25Index(min_score=0.0)
    texts = {"x": "Moratorium period is 5 years.", "y": "Room rent cap applies."}
    for i, (s, t) in enumerate(texts.items()):
        idx.add(Chunk(s, i + 1, 0, t))
    for h in idx.search("moratorium rent", k=5):
        assert h.quote == texts[h.source]


def test_devanagari_variants_match_after_folding():
    idx = Bm25Index(min_score=0.0)
    idx.add(Chunk("hi", 1, 0, "ज़रूरी दस्तावेज़ जमा करें"))
    assert idx.search("जरूरी दस्तावेज", k=1)[0].source == "hi"


def test_add_document_chunks_and_indexes_in_one_call():
    idx = Bm25Index(min_score=0.0)
    n = idx.add_document("Para one about alpha.\n\nPara two about beta.", source="S", page=2)
    assert n == 2 and len(idx) == 2
    assert idx.search("beta", k=1)[0].quote == "Para two about beta."


def test_hit_is_a_frozen_value():
    h = Hit("s", 1, "q", 1.0)
    with pytest.raises(Exception):
        h.score = 2.0  # type: ignore[misc]


# ---- per-case in-memory index (BYOD) -----------------------------------------
def test_purge_empties_the_index():
    idx = CaseRetrievalIndex("case-1", min_score=0.0)
    idx.add_document("alpha beta gamma", source="S", page=1)
    assert len(idx) == 1 and idx.search("alpha", k=1)
    idx.purge()
    assert len(idx) == 0 and idx.search("alpha", k=1) == []
    assert idx.purged is True


def test_purged_index_refuses_new_documents():
    idx = CaseRetrievalIndex("case-1")
    idx.purge()
    with pytest.raises(RuntimeError):
        idx.add_document("alpha", source="S", page=1)


def test_index_works_as_context_manager_and_purges_on_exit():
    with CaseRetrievalIndex("c", min_score=0.0) as idx:
        idx.add_document("alpha beta", source="S", page=1)
        assert idx.search("alpha", k=1)
    assert idx.purged and len(idx) == 0


def test_index_never_touches_the_disk(monkeypatch, tmp_path):
    """Zero retention: indexing, searching and purging must not open, create or write any file."""
    monkeypatch.chdir(tmp_path)
    before = set(os.listdir(tmp_path))

    def forbidden(*a, **k):
        raise AssertionError("retrieval touched the filesystem")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(os, "open", forbidden)
    monkeypatch.setattr(pathlib.Path, "open", forbidden)
    monkeypatch.setattr(pathlib.Path, "write_text", forbidden)
    monkeypatch.setattr(pathlib.Path, "write_bytes", forbidden)
    monkeypatch.setattr(pathlib.Path, "mkdir", forbidden)
    import tempfile

    monkeypatch.setattr(tempfile, "mkstemp", forbidden)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", forbidden)

    idx = CaseRetrievalIndex("case-2", min_score=0.0)
    idx.add_document("Patient bill for knee surgery.\n\nDischarge summary text.", source="bill", page=1)
    assert idx.search("knee surgery", k=2)
    idx.purge()
    assert set(os.listdir(tmp_path)) == before


def test_index_does_not_log_document_text(caplog):
    caplog.set_level("DEBUG")
    idx = CaseRetrievalIndex("case-3", min_score=0.0)
    idx.add_document("SECRETPATIENTNAME had surgery", source="S", page=1)
    idx.search("SECRETPATIENTNAME", k=1)
    idx.purge()
    assert "secretpatientname" not in caplog.text.lower()
