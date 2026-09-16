"""
Evaluate Kadi entity resolution against a labeled pair dataset.

    python scripts/evaluate_entity_resolution.py                 # lexical, +phonetic, Soundex baseline
    python scripts/evaluate_entity_resolution.py --semantic      # also +semantic (IndicSBERT)
    python scripts/evaluate_entity_resolution.py --json out.json # full report as JSON

--semantic loads l3cube-pune/indic-sentence-similarity-sbert (needs packages/kadi[semantic],
torch >= 2.6 and the model in the Hugging Face cache or network access). If it cannot load,
the report says so; it never substitutes a different model.

The default dataset is the hand-curated synthetic fixture. Its metrics describe behaviour on
known hard cases, not real-world accuracy.
"""

import argparse
import json
import sys
from pathlib import Path

from kadi.resolution.evaluation import evaluate_pairs, evaluate_soundex_baseline, load_labeled_pairs
from kadi.resolution.semantic import IndicSBERTEncoder

DEFAULT_DATASET = (
    Path(__file__).resolve().parent.parent
    / "packages" / "kadi" / "tests" / "fixtures" / "entity_pairs_curated_synthetic.jsonl"
)


def _fmt(value):
    return "n/a" if value is None else f"{value:.3f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--semantic", action="store_true", help="include the IndicSBERT signal")
    parser.add_argument("--json", type=Path, help="write the full reports to this file")
    args = parser.parse_args()

    meta, pairs = load_labeled_pairs(args.dataset)
    configurations = [
        ("lexical only", frozenset({"lexical"}), None),
        ("lexical + phonetic", frozenset({"lexical", "phonetic"}), None),
    ]
    if args.semantic:
        configurations.append(
            ("lexical + phonetic + semantic", frozenset({"lexical", "phonetic", "semantic"}), IndicSBERTEncoder())
        )

    reports = [
        evaluate_pairs(pairs, meta, encoder=encoder, enabled_signals=signals, configuration=name)
        for name, signals, encoder in configurations
    ]
    baseline = evaluate_soundex_baseline(pairs)

    print(f"Dataset: {meta.name}  (synthetic={meta.synthetic})")
    print(f"Pairs: {len(pairs)}  labeled: {reports[0].labeled_pairs}  ambiguous: {reports[0].ambiguous_pairs}")
    print()
    print("| Configuration | Merge precision | Merge recall | Merge F1 | Review recall | False merges | Silent misses | Ask rate | p50 ms | p95 ms | Semantic |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in reports:
        print(
            f"| {r.configuration} | {_fmt(r.merge_precision)} | {_fmt(r.merge_recall)} | {_fmt(r.merge_f1)} "
            f"| {_fmt(r.review_recall)} | {r.false_merges} | {r.silent_misses} | {r.ask_rate:.3f} "
            f"| {r.latency_ms_p50} | {r.latency_ms_p95} | {r.semantic_status} |"
        )
    print(
        f"| baseline: {baseline.name} | {_fmt(baseline.precision)} | {_fmt(baseline.recall)} | {_fmt(baseline.f1)} "
        f"| – | {baseline.false_positives} | – | – | – | – | – |"
    )
    print()
    for r in reports:
        print(f"[{r.configuration}] false merges: {r.false_merge_ids or 'none'}; silent misses: {r.silent_miss_ids or 'none'}")
        print("  per category (merge/ask/new):", {k: f"{v.merge}/{v.ask}/{v.new}" for k, v in r.categories.items()})
        print("  ambiguous pairs:", r.ambiguous_actions)

    if args.json:
        args.json.write_text(
            json.dumps(
                {"reports": [r.model_dump() for r in reports], "baseline": baseline.model_dump()},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
