"""
Run the Phase-4 evaluation harnesses (BMA, PEA, billing-anomaly P/R/F1, CRMA, OCR WER/CER,
DawaCheck price mapping).

    python scripts/evaluate_phase4.py                  # all harnesses, summary tables
    python scripts/evaluate_phase4.py --only bma       # one harness
    python scripts/evaluate_phase4.py --json out.json  # full reports (incl. every failure)

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

from app.evaluation.runner import DATASETS, run_all  # noqa: E402


def _f(v):
    return "n/a" if v is None else f"{v:.3f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", choices=sorted(DATASETS))
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

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
        if "per_category" in r:
            for c, v in r["per_category"].items():
                print(f"  - {c}: {v}")
        for fail in r.get("failures", []):
            print("  FAIL", json.dumps(fail, ensure_ascii=False))

    if args.json:
        args.json.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
