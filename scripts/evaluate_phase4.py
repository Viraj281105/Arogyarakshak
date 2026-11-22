"""
Run the Phase-4 evaluation harnesses (BMA, PEA, billing-anomaly P/R/F1, CRMA, OCR WER/CER,
DawaCheck price mapping, appeal completeness, letter grounding / hallucination rate).

    python scripts/evaluate_phase4.py                  # all harnesses, summary tables
    python scripts/evaluate_phase4.py --only bma       # one harness
    python scripts/evaluate_phase4.py --json out.json  # full reports (incl. every failure)
    python scripts/evaluate_phase4.py --check-baseline # also gate against the committed
                                                       # baseline (exit 1 on regression)

Offline and deterministic: no Groq key and no network needed. Every dataset in
data/evaluation/ is SYNTHETIC and hand-written; the numbers describe behaviour on those
known cases and are NOT real-world accuracy. See docs/evaluation/phase4-harnesses.md.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.evaluation.regression import BASELINE_PATH, compare, load_baseline  # noqa: E402
from app.evaluation.runner import DATASETS, run_all  # noqa: E402


def _f(v):
    return "n/a" if v is None else f"{v:.3f}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", choices=sorted(DATASETS))
    parser.add_argument("--json", type=Path)
    parser.add_argument("--check-baseline", nargs="?", const=BASELINE_PATH, type=Path, metavar="PATH",
                        help="compare with a regression baseline (default: the committed one); "
                             "exit 1 on regression, 2 on a structural problem")
    args = parser.parse_args(argv)

    reports = run_all(args.only)
    for name, r in reports.items():
        print(f"\n## {name}  (dataset {r['dataset']['name']}, synthetic={r['dataset']['synthetic']})")
        if name == "bma":
            o = r["outcomes"]
            print(f"rows {r['rows']}  accuracy {_f(r['accuracy'])}  outcomes {o}  mapping P/R/F1 "
                  f"{_f(r['mapping']['precision'])}/{_f(r['mapping']['recall'])}/{_f(r['mapping']['f1'])}")
        elif name == "pea":
            for k in ("procedures", "medicines", "all_items"):
                m = r[k]
                print(f"{k}: tp {m['tp']} fp {m['fp']} fn {m['fn']}  P/R/F1 {_f(m['precision'])}/{_f(m['recall'])}/{_f(m['f1'])}")
            print(f"split_errors {r['split_errors']}  total_amount_accuracy {_f(r['total_amount_accuracy'])}  "
                  f"bills_with_errors {r['bills_with_errors']}/{r['bills']}")
        elif name == "anomaly":
            for k in ("line_level", "bill_level"):
                m = r[k]
                print(f"{k}: tp {m['tp']} fp {m['fp']} fn {m['fn']} tn {m['tn']}  P/R/F1 "
                      f"{_f(m['precision'])}/{_f(m['recall'])}/{_f(m['f1'])}")
            print(f"FN abstained {r['false_negatives_abstained']}  FN judged fair {r['false_negatives_judged_fair']}")
        elif name == "crma":
            w = r["wrongful"]
            print(f"scenarios {r['scenarios']}  CRMA {_f(r['crma'])}  wrongful acc {_f(r['wrongful_accuracy'])} "
                  f"(P/R/F1 {_f(w['precision'])}/{_f(w['recall'])}/{_f(w['f1'])})  clause acc {_f(r['clause_accuracy'])} "
                  f"({r['clause_checks']} checks)  clinical acc {_f(r['clinical_accuracy'])}")
        elif name == "ocr":
            print(f"rows {r['rows_scored']}  corpus WER {_f(r['corpus_wer'])}  corpus CER {_f(r['corpus_cer'])}")
            for k, v in r["per_error_kind"].items():
                print(f"  {k}: WER {_f(v['wer'])} CER {_f(v['cer'])}")
        elif name == "dawacheck":
            print(f"rows {r['rows']}  accuracy {_f(r['accuracy'])}  outcomes {r['outcomes']}  ceiling acc "
                  f"{_f(r['ceiling_accuracy'])} ({r['ceiling_checked']} checked)  methods {r['match_methods_returned']}")
        elif name == "appeal":
            print(f"scenarios {r['scenarios']}  letters {r['letters']}  mean score {_f(r['mean_score'])}  "
                  f"fully complete {_f(r['fully_complete_share'])}  unverified clause citations "
                  f"{r['unverified_clause_citations']}")
            print(f"  per category {{{', '.join(f'{k}: {_f(v)}' for k, v in r['per_category'].items())}}}")
            print(f"  per language {{{', '.join(f'{k}: {_f(v)}' for k, v in r['per_language'].items())}}}")
            print(f"  failed checks {r['failed_check_counts']}")
        elif name == "grounding":
            d, p = r["detector"], r["production"]
            print(f"detector: {d['rows']} labelled letters  tp {d['tp']} fp {d['fp']} fn {d['fn']}  "
                  f"P/R/F1 {_f(d['precision'])}/{_f(d['recall'])}/{_f(d['f1'])}")
            for m in d["missed"]:
                print("  MISSED", json.dumps(m, ensure_ascii=False))
            for m in d["spurious"]:
                print("  SPURIOUS", json.dumps(m, ensure_ascii=False))
            print(f"production: {p['letters']} letters, {p['claims']} claims, ungrounded {p['ungrounded_claims']}  "
                  f"grounding {_f(p['grounding_score'])}  hallucination {_f(p['hallucination_rate'])}  "
                  f"letters with an ungrounded claim {_f(p['letters_with_ungrounded'])}")
            for k, v in p["by_kind"].items():
                print(f"  - {k}: {v}")
        elif name == "retrieval":
            print(f"queries {r['queries']} (answerable {r['answerable']})  MRR {_f(r['mrr'])}  recall@k {_f(r['recall_at_k'])}  "
                  f"PCRA {_f(r['pcra'])}  precision {_f(r['precision'])}  abstention {_f(r['abstention_rate'])}")
            print("  SYNTHETIC tuning set written by the retriever's author: optimistic, not accuracy.")
        elif name == "context_reuse":
            print(f"scenarios {r['n_scenarios']}  requests {r['n_requests']}  DPR {_f(r['dpr'])} (modelled baseline)  "
                  f"hit rate {_f(r.get('hit_rate'))} (non-emptiness, ~1 by construction; not gated)")
        if "per_category" in r and name != "appeal":
            for c, v in r["per_category"].items():
                print(f"  - {c}: {v}")
        for fail in r.get("failures", []):
            print("  FAIL", json.dumps(fail, ensure_ascii=False))

    if args.json:
        args.json.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.check_baseline:
        # With --only, gate just the harness that was run (the others are not required).
        result = compare(load_baseline(args.check_baseline), reports,
                         only=[args.only] if args.only else None)
        scope = f" — harness {args.only} only" if args.only else ""
        print(f"\n## regression gate (offline paths, SYNTHETIC data — not LLM accuracy){scope}")
        print(result.format_table())
        for err in result.errors:
            print(f"ERROR: {err}")
        if result.errors:
            return 2
        return 0 if result.ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
