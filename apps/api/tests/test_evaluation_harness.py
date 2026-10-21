"""Tests for the Phase-4 evaluation harnesses. Expected values are hand-computed from tiny
inputs; the dataset checks assert structure (synthetic flag, unique ids), never accuracy."""

import json
from types import SimpleNamespace

import pytest

from app.evaluation import metrics as m
from app.evaluation.anomaly import evaluate_anomaly
from app.evaluation.bma import classify as bma_classify, evaluate_bma
from app.evaluation.crma import evaluate_crma
from app.evaluation.datasets import DATA_DIR, DatasetError, load_dataset
from app.evaluation.dawacheck_mapping import classify as dawa_classify, evaluate_dawacheck_mapping
from app.evaluation.ocr_wer import evaluate_ocr
from app.evaluation.pea import evaluate_pea
from app.evaluation.runner import DATASETS, run_all


# ---- metrics ---------------------------------------------------------------
def test_precision_recall_f1_hand_computed():
    r = m.precision_recall_f1(tp=3, fp=1, fn=2)
    assert r["precision"] == pytest.approx(0.75)
    assert r["recall"] == pytest.approx(0.6)
    assert r["f1"] == pytest.approx(2 * 0.75 * 0.6 / 1.35)  # 0.6667


def test_undefined_metrics_are_none_not_zero():
    assert m.precision_recall_f1(0, 0, 0) == {"precision": None, "recall": None, "f1": None}
    r = m.precision_recall_f1(0, 2, 0)  # predicted something, no gold positives
    assert r["precision"] == 0.0 and r["recall"] is None and r["f1"] is None
    assert m.precision_recall_f1(0, 1, 1)["f1"] == 0.0
    assert m.accuracy(1, 0) is None


def test_binary_counts():
    assert m.binary_counts([(True, True), (True, False), (False, True), (False, False), (False, False)]) == {
        "tp": 1, "fp": 1, "fn": 1, "tn": 2,
    }


def test_multiset_match_counts_duplicates_must_match_twice():
    assert m.multiset_match_counts(["a", "a", "b"], ["a", "b", "b"]) == {"tp": 2, "fp": 1, "fn": 1}
    assert m.multiset_match_counts([], []) == {"tp": 0, "fp": 0, "fn": 0}


def test_edit_distance_known_values():
    assert m.edit_distance("kitten", "sitting") == 3
    assert m.edit_distance("", "abc") == 3
    assert m.edit_distance("abc", "") == 3
    assert m.edit_distance(["a", "b"], ["a", "c"]) == 1


def test_wer_cer_hand_computed():
    assert m.wer("the cat sat", "the cat sit") == pytest.approx(1 / 3)
    assert m.wer("a b c d", "a d") == pytest.approx(0.5)  # two deletions / 4 words
    assert m.wer("a", "a b c") == pytest.approx(2.0)  # insertions can push WER above 1
    assert m.wer("", "x") is None
    assert m.cer("abc", "axc") == pytest.approx(1 / 3)
    assert m.cer("ab  cd", "ab cd") == 0.0  # whitespace runs collapsed
    assert m.cer("", "") is None


def test_corpus_error_rate_is_total_edits_over_total_reference():
    pairs = [("a b", "a c"), ("x y z w", "x y z w")]
    assert m.corpus_error_rate(pairs, "word") == pytest.approx(1 / 6)  # not mean(0.5, 0.0)
    assert m.corpus_error_rate([("abcd", "abxd")], "char") == pytest.approx(0.25)


# ---- dataset loader --------------------------------------------------------
def test_loader_rejects_non_synthetic_and_duplicate_ids(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(json.dumps({"_meta": {"name": "x", "synthetic": False}}) + "\n", encoding="utf-8")
    with pytest.raises(DatasetError):
        load_dataset(p)
    p.write_text(json.dumps({"name": "no meta"}) + "\n", encoding="utf-8")
    with pytest.raises(DatasetError):
        load_dataset(p)
    p.write_text(
        json.dumps({"_meta": {"synthetic": True}}) + "\n" + json.dumps({"id": "1"}) + "\n" + json.dumps({"id": "1"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(DatasetError):
        load_dataset(p)


@pytest.mark.parametrize("name,filename", sorted(DATASETS.items()))
def test_every_shipped_dataset_is_marked_synthetic(name, filename):
    meta, rows = load_dataset(DATA_DIR / filename)
    assert meta["synthetic"] is True
    assert "provenance" in meta and rows


def test_crma_dataset_has_25_scenarios():
    _, rows = load_dataset(DATA_DIR / DATASETS["crma"])
    assert len(rows) == 25


# ---- BMA -------------------------------------------------------------------
def test_bma_classify_outcomes():
    assert bma_classify(["icu"], "icu") == "correct"
    assert bma_classify([], None) == "correct"
    assert bma_classify(["icu"], "ppe") == "wrong_key"
    assert bma_classify(["icu"], None) == "missed"
    assert bma_classify([], "icu") == "false_match"


def test_evaluate_bma_hand_computed():
    rows = [
        {"id": "1", "hospital_line": "ICU", "category": "a", "expected_keys": ["icu"]},          # correct
        {"id": "2", "hospital_line": "MRI", "category": "a", "expected_keys": ["mri"]},          # wrong_key
        {"id": "3", "hospital_line": "Scan", "category": "b", "expected_keys": ["ct scan"]},     # missed
        {"id": "4", "hospital_line": "Fee", "category": "b", "expected_keys": []},              # correct (rejected)
        {"id": "5", "hospital_line": "Ward Boy", "category": "b", "expected_keys": []},         # false_match
    ]
    table = {"icu": "icu", "mri": "ppe", "ward boy": "ward stay"}
    r = evaluate_bma(rows, lambda line: table.get(line))
    assert r["outcomes"] == {"correct": 2, "wrong_key": 1, "missed": 1, "false_match": 1}
    assert r["accuracy"] == pytest.approx(0.4)
    # predicted keys on rows 1,2,5 -> tp 1, fp 2; gold-positive rows not correctly mapped: 2,3 -> fn 2
    assert r["mapping"]["precision"] == pytest.approx(1 / 3)
    assert r["mapping"]["recall"] == pytest.approx(1 / 3)
    assert r["per_category"]["b"]["n"] == 3
    assert {f["id"] for f in r["failures"]} == {"2", "3", "5"}


# ---- PEA -------------------------------------------------------------------
def test_evaluate_pea_hand_computed():
    rows = [
        {"id": "1", "category": "c", "text": "t1", "procedures": [["Consultation", 500], ["MRI", 3500]],
         "medicines": [["Tab Dolo 650", 33]], "total_amount": 4033},
    ]
    extracted = SimpleNamespace(
        procedures=[{"name": "consultation", "amount": 500.0}, {"name": "X-Ray", "amount": 350.0}],  # 1 tp, 1 fp, 1 fn
        medicines=[{"name": "Tab Dolo 650", "cost": 33.0}],                                           # 1 tp
        total_amount=4000.0,                                                                          # wrong
    )
    r = evaluate_pea(rows, lambda text: extracted)
    assert (r["procedures"]["tp"], r["procedures"]["fp"], r["procedures"]["fn"]) == (1, 1, 1)
    assert r["procedures"]["precision"] == pytest.approx(0.5) and r["procedures"]["recall"] == pytest.approx(0.5)
    assert r["medicines"]["f1"] == pytest.approx(1.0)
    assert (r["all_items"]["tp"], r["all_items"]["fp"], r["all_items"]["fn"]) == (2, 1, 1)
    assert r["total_amount_accuracy"] == 0.0
    assert r["split_errors"] == 0
    assert r["bills_with_errors"] == 1


def test_evaluate_pea_counts_split_errors():
    rows = [{"id": "1", "category": "c", "text": "", "procedures": [["Dressing", 100]], "medicines": [], "total_amount": 100}]
    extracted = SimpleNamespace(procedures=[], medicines=[{"name": "dressing", "cost": 100.0}], total_amount=100.0)
    r = evaluate_pea(rows, lambda t: extracted)
    assert r["split_errors"] == 1  # right name+amount, filed under medicines
    assert r["all_items"]["tp"] == 1 and r["procedures"]["fn"] == 1 and r["medicines"]["fp"] == 1


# ---- anomaly ---------------------------------------------------------------
def test_evaluate_anomaly_hand_computed():
    rows = [
        {"id": "B1", "category": "x", "lines": [
            {"name": "a", "charged": 10, "anomalous": True},    # pred True  -> tp
            {"name": "b", "charged": 10, "anomalous": False},   # pred True  -> fp
        ]},
        {"id": "B2", "category": "x", "lines": [
            {"name": "c", "charged": 10, "anomalous": True},    # abstained -> fn (abstained)
            {"name": "d", "charged": 10, "anomalous": True},    # judged fair -> fn (judged_fair)
            {"name": "e", "charged": 10, "anomalous": False},   # tn
        ]},
    ]
    verdicts = {
        "B1": [("overcharged", True), ("overcharged", True)],
        "B2": [("not_benchmarked", False), ("within_benchmark", False), ("within_benchmark", False)],
    }

    def auditor(case_id, items):
        assert [i.name for i in items] == [l["name"] for l in next(r for r in rows if r["id"] == case_id)["lines"]]
        return SimpleNamespace(audit_items=[
            SimpleNamespace(status=s, is_deviation=d, cghs_benchmark=None) for s, d in verdicts[case_id]
        ])

    r = evaluate_anomaly(rows, auditor)
    lv = r["line_level"]
    assert (lv["tp"], lv["fp"], lv["fn"], lv["tn"]) == (1, 1, 2, 1)
    assert lv["precision"] == pytest.approx(0.5) and lv["recall"] == pytest.approx(1 / 3)
    assert lv["f1"] == pytest.approx(0.4)
    assert (r["false_negatives_abstained"], r["false_negatives_judged_fair"]) == (1, 1)
    bl = r["bill_level"]  # B1 gold+pred anomalous (tp); B2 gold anomalous, pred clean (fn)
    assert (bl["tp"], bl["fp"], bl["fn"], bl["tn"]) == (1, 0, 1, 0)


# ---- CRMA ------------------------------------------------------------------
def test_evaluate_crma_hand_computed():
    base = {"policy_number": "p", "insurer_name": "i", "policy_age_years": 1, "claimed_amount": 1,
            "denied_or_deducted_amount": 1, "denial_reason_raw": "r", "diagnosis": "d"}
    rows = [
        {"id": "1", "group": "g", "input": {**base, "denial_category": "A"}, "expected_is_wrongful": True,
         "expected_clause": "moratorium", "expected_clinical_review": True},    # all correct
        {"id": "2", "group": "g", "input": {**base, "denial_category": "B"}, "expected_is_wrongful": False,
         "expected_clause": None, "expected_clinical_review": False},           # wrongful wrong
        {"id": "3", "group": "h", "input": {**base, "denial_category": "C"}, "expected_is_wrongful": True,
         "expected_clause": "moratorium", "expected_clinical_review": False},   # clause wrong
    ]
    answers = {
        "A": {"is_wrongful": True, "citations": ["IRDAI Clause 16 — Moratorium Period"], "clinical": True},
        "B": {"is_wrongful": True, "citations": [], "clinical": False},
        "C": {"is_wrongful": True, "citations": ["other"], "clinical": False},
    }
    r = evaluate_crma(rows, lambda payload: answers[payload["denial_category"]])
    assert r["crma"] == pytest.approx(1 / 3)
    assert r["wrongful_accuracy"] == pytest.approx(2 / 3)
    assert (r["wrongful"]["tp"], r["wrongful"]["fp"]) == (2, 1)
    assert r["clause_checks"] == 2 and r["clause_accuracy"] == pytest.approx(0.5)
    assert r["clinical_accuracy"] == 1.0
    assert r["per_group"]["g"] == {"n": 2, "correct": 1}


# ---- OCR -------------------------------------------------------------------
def test_evaluate_ocr_hand_computed_and_external_hypotheses():
    rows = [
        {"id": "1", "error_kind": "k", "reference": "a b c d", "hypothesis": "a b c x"},  # 1 word edit / 4
        {"id": "2", "error_kind": "k", "reference": "ab", "hypothesis": "ab"},
    ]
    r = evaluate_ocr(rows)
    assert r["corpus_wer"] == pytest.approx(1 / 5)       # 1 edit over 5 reference words
    assert r["corpus_cer"] == pytest.approx(1 / 9)       # "a b c d"(7)+"ab"(2) = 9 chars, 1 edit
    r2 = evaluate_ocr(rows, hypotheses={"2": "ax"})
    assert r2["rows_scored"] == 1 and r2["corpus_wer"] == pytest.approx(1.0)


# ---- DawaCheck -------------------------------------------------------------
def test_dawacheck_classify_and_evaluate():
    assert dawa_classify("X", "X") == "correct"
    assert dawa_classify(None, None) == "correct"
    assert dawa_classify("X", "Y") == "wrong_drug"
    assert dawa_classify("X", None) == "missed"
    assert dawa_classify(None, "Y") == "false_match"
    rows = [
        {"id": "1", "category": "a", "query": "q1", "expected_active_ingredient": "X", "expected_ceiling": 2.0},
        {"id": "2", "category": "a", "query": "q2", "expected_active_ingredient": "X", "expected_ceiling": 2.0},
        {"id": "3", "category": "b", "query": "q3", "expected_active_ingredient": None, "expected_ceiling": None},
        {"id": "4", "category": "b", "query": "q4", "expected_active_ingredient": "Z", "expected_ceiling": 1.0},
    ]
    got = {
        "q1": SimpleNamespace(active_ingredient="X", nppa_ceiling_price=2.0, match_method="exact_or_alias"),
        "q2": SimpleNamespace(active_ingredient="X", nppa_ceiling_price=2.5, match_method="fuzzy_phonetic"),  # ceiling off
        "q3": SimpleNamespace(active_ingredient="Y", nppa_ceiling_price=1.0, match_method="fuzzy_phonetic"),  # false match
    }
    r = evaluate_dawacheck_mapping(rows, lambda q: got.get(q))
    assert r["outcomes"] == {"correct": 2, "wrong_drug": 0, "false_match": 1, "missed": 1}
    assert r["accuracy"] == pytest.approx(0.5)
    assert r["ceiling_checked"] == 2 and r["ceiling_accuracy"] == pytest.approx(0.5)
    assert r["mapping"]["precision"] == pytest.approx(2 / 3) and r["mapping"]["recall"] == pytest.approx(2 / 3)
    assert r["match_methods_returned"] == {"exact_or_alias": 1, "fuzzy_phonetic": 2}


# ---- end to end (structure only) -------------------------------------------
def test_run_all_is_offline_deterministic_and_complete(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    first = run_all()
    second = run_all()
    assert set(first) == set(DATASETS)
    assert first == second
    for name, report in first.items():
        assert report["dataset"]["synthetic"] is True, name
