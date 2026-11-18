"""The CI evaluation regression gate (WS2): the comparator, the committed baseline, and the
``scripts/check_eval_regression.py`` entry point. The gate measures the OFFLINE harness
paths on SYNTHETIC datasets (docs/evaluation/phase4-harnesses.md), not LLM accuracy."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from app.evaluation.regression import (
    BASELINE_PATH,
    COUNT_METRICS,
    HEADLINE_METRICS,
    build_baseline,
    compare,
    extract_metrics,
    load_baseline,
)

ROOT = Path(__file__).resolve().parents[3]


def _reports():
    """A minimal report set shaped like run_all()'s output."""
    ds = {"name": "x", "synthetic": True}
    return {
        "bma": {"dataset": ds, "rows": 78, "accuracy": 0.7, "mapping": {"f1": 0.77}},
        "pea": {"dataset": ds, "bills": 28, "procedures": {"f1": 0.94}, "medicines": {"f1": 1.0},
                "all_items": {"f1": 0.95}, "total_amount_accuracy": 1.0},
        "anomaly": {"dataset": ds, "bills": 39, "lines": 70, "line_level": {"f1": 0.81},
                    "bill_level": {"f1": 0.78}},
        "crma": {"dataset": ds, "scenarios": 25, "crma": 0.56, "wrongful": {"f1": 0.69},
                 "clause_accuracy": 0.83, "clinical_accuracy": 1.0},
        "ocr": {"dataset": ds, "rows_total": 15, "corpus_wer": 0.38, "corpus_cer": 0.09},
        "dawacheck": {"dataset": ds, "rows": 52, "accuracy": 0.86, "mapping": {"f1": 0.88},
                      "ceiling_accuracy": 0.97},
    }


def test_every_headline_and_count_metric_is_extracted():
    metrics = extract_metrics(_reports())
    assert set(metrics) == {m.path for m in HEADLINE_METRICS} | set(COUNT_METRICS)
    assert metrics["ocr.corpus_wer"] == 0.38 and metrics["bma.rows"] == 78


def test_identical_reports_pass():
    base = build_baseline(_reports())
    result = compare(base, _reports())
    assert result.ok and not result.errors
    assert {r.status for r in result.rows} == {"ok"}


def test_a_drop_in_a_higher_is_better_metric_fails():
    base = build_baseline(_reports())
    cur = _reports()
    cur["pea"]["procedures"]["f1"] = 0.93
    result = compare(base, cur)
    assert not result.ok
    bad = [r for r in result.rows if r.status == "regressed"]
    assert [r.name for r in bad] == ["pea.procedures.f1"]
    assert bad[0].delta == pytest.approx(-0.01)


def test_a_rise_in_a_lower_is_better_metric_fails():
    base = build_baseline(_reports())
    cur = _reports()
    cur["ocr"]["corpus_wer"] = 0.40
    assert not compare(base, cur).ok


def test_improvements_pass_and_are_reported():
    base = build_baseline(_reports())
    cur = _reports()
    cur["bma"]["accuracy"] = 0.8
    cur["ocr"]["corpus_cer"] = 0.05
    result = compare(base, cur)
    assert result.ok
    assert {r.name for r in result.rows if r.status == "improved"} == {"bma.accuracy", "ocr.corpus_cer"}


def test_tolerance_absorbs_a_drop_within_it():
    base = build_baseline(_reports())
    base["metrics"]["crma.crma"]["tolerance"] = 0.05
    cur = _reports()
    cur["crma"]["crma"] = 0.52
    assert compare(base, cur).ok
    cur["crma"]["crma"] = 0.50
    assert not compare(base, cur).ok


def test_float_noise_is_not_a_regression():
    base = build_baseline(_reports())
    cur = _reports()
    cur["bma"]["accuracy"] = 0.7 - 1e-12
    assert compare(base, cur).ok


def test_a_changed_dataset_size_fails():
    base = build_baseline(_reports())
    cur = _reports()
    cur["bma"]["rows"] = 77
    result = compare(base, cur)
    assert not result.ok
    assert [r.name for r in result.rows if r.status == "count_changed"] == ["bma.rows"]


def test_a_metric_becoming_undefined_fails():
    base = build_baseline(_reports())
    cur = _reports()
    cur["anomaly"]["line_level"]["f1"] = None
    assert not compare(base, cur).ok


def test_structural_problems_are_errors():
    base = build_baseline(_reports())
    cur = _reports()
    del cur["dawacheck"]
    result = compare(base, cur)
    assert not result.ok and any("dawacheck" in e for e in result.errors)

    cur = _reports()
    cur["pea"]["dataset"] = {"name": "x", "synthetic": False}
    result = compare(base, cur)
    assert not result.ok and any("synthetic" in e for e in result.errors)

    broken = copy.deepcopy(base)
    del broken["metrics"]["bma.accuracy"]
    assert any("bma.accuracy" in e for e in compare(broken, _reports()).errors)


def test_baseline_records_direction_and_the_honesty_note():
    base = build_baseline(_reports())
    assert base["metrics"]["ocr.corpus_wer"]["direction"] == "lower"
    assert base["metrics"]["bma.accuracy"]["direction"] == "higher"
    assert all(m["tolerance"] == 0.0 for m in base["metrics"].values())
    assert base["_meta"]["synthetic"] is True
    assert "not llm accuracy" in base["_meta"]["note"].lower()


def test_report_table_prints_every_metric_and_its_delta():
    base = build_baseline(_reports())
    cur = _reports()
    cur["pea"]["procedures"]["f1"] = 0.90
    table = compare(base, cur).format_table()
    assert "pea.procedures.f1" in table and "-0.0400" in table and "REGRESSED" in table


# ---- the committed baseline and the CLI ------------------------------------------------------
def test_committed_baseline_matches_the_current_harnesses():
    """The real gate, also run by the eval-regression-gate CI job."""
    from app.evaluation.runner import run_all

    result = compare(load_baseline(BASELINE_PATH), run_all())
    assert result.ok, result.format_table() + "\n" + "\n".join(result.errors)


def _cli():
    spec = importlib.util.spec_from_file_location("check_eval_regression", ROOT / "scripts" / "check_eval_regression.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cli_exit_codes(tmp_path, capsys):
    cli = _cli()
    current = tmp_path / "current.json"
    current.write_text(json.dumps(_reports()), encoding="utf-8")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(build_baseline(_reports())), encoding="utf-8")
    assert cli.main(["--baseline", str(baseline), "--current", str(current)]) == 0

    degraded = _reports()
    degraded["anomaly"]["line_level"]["f1"] = 0.5
    current.write_text(json.dumps(degraded), encoding="utf-8")
    assert cli.main(["--baseline", str(baseline), "--current", str(current)]) == 1
    out = capsys.readouterr().out
    assert "anomaly.line_level.f1" in out and "REGRESSED" in out

    baseline.write_text("{}", encoding="utf-8")
    assert cli.main(["--baseline", str(baseline), "--current", str(current)]) == 2


def test_cli_write_baseline_round_trips(tmp_path):
    cli = _cli()
    current = tmp_path / "current.json"
    current.write_text(json.dumps(_reports()), encoding="utf-8")
    out = tmp_path / "new_baseline.json"
    assert cli.main(["--current", str(current), "--write-baseline", str(out)]) == 0
    assert compare(load_baseline(out), _reports()).ok


def test_evaluate_phase4_check_baseline_flag(tmp_path):
    spec = importlib.util.spec_from_file_location("evaluate_phase4", ROOT / "scripts" / "evaluate_phase4.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--only", "ocr", "--check-baseline"]) == 2  # one harness: the others are missing
    from app.evaluation.runner import run_all

    full = build_baseline(run_all())
    full["metrics"]["ocr.corpus_wer"]["value"] = 0.1  # pretend WER used to be much lower
    path = tmp_path / "b.json"
    path.write_text(json.dumps(full), encoding="utf-8")
    assert mod.main(["--check-baseline", str(path)]) == 1
    assert mod.main(["--check-baseline"]) == 0
