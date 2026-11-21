"""
CI evaluation regression gate (WS2, ADR-024).

    python scripts/check_eval_regression.py                      # run harnesses, compare to baseline
    python scripts/check_eval_regression.py --current out.json   # compare a saved --json report
    python scripts/check_eval_regression.py --write-baseline PATH  # (re)generate a baseline

Exit codes: 0 no regression · 1 regression (a metric dropped beyond its tolerance or a
dataset size changed) · 2 structural problem (bad/missing baseline, missing metric,
non-synthetic dataset).

Measures the OFFLINE heuristic/rule paths on SYNTHETIC datasets — not LLM accuracy and not
real-world accuracy (docs/evaluation/phase4-harnesses.md). No Groq key, no network.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "apps" / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.evaluation.regression import BASELINE_PATH, build_baseline, compare, load_baseline  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    parser.add_argument("--current", type=Path, help="a saved `evaluate_phase4.py --json` report")
    parser.add_argument("--write-baseline", type=Path, metavar="PATH",
                        help="write a baseline built from the current report and exit")
    args = parser.parse_args(argv)

    if args.current:
        reports = json.loads(args.current.read_text(encoding="utf-8"))
    else:
        # The harnesses log every failure row at INFO/WARNING; the gate prints its own table.
        logging.disable(logging.WARNING)
        try:
            from app.evaluation.runner import run_all

            reports = run_all()
        finally:
            logging.disable(logging.NOTSET)

    if args.write_baseline:
        args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
        args.write_baseline.write_text(json.dumps(build_baseline(reports), indent=2) + "\n",
                                       encoding="utf-8", newline="\n")
        print(f"Baseline written to {args.write_baseline}")
        return 0

    try:
        baseline = load_baseline(args.baseline)
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot read baseline {args.baseline}: {exc}")
        return 2

    result = compare(baseline, reports)
    print("Phase-4 evaluation regression gate — offline paths on SYNTHETIC data (not LLM accuracy)")
    print(f"baseline: {args.baseline}")
    print(result.format_table())
    for err in result.errors:
        print(f"ERROR: {err}")
    if result.errors:
        return 2
    if not result.ok:
        print("RESULT: REGRESSION — a metric dropped beyond its tolerance or a dataset size changed.")
        return 1
    if any(r.status == "improved" for r in result.rows):
        print("RESULT: PASS (improvements found — raise the baseline in a reviewed commit with --write-baseline)")
    else:
        print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
