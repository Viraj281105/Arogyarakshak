"""
Appeal completeness (#107) — is a generated IRDAI appeal draft complete?

Scores the BimaNyay Level-1 GRO appeal letter against the weighted checklist from the
issue: Patient Details 15%, Policy Info 20%, Clauses 30%, Justification 25%, References 10%.

Every check is a deterministic text test of the draft against the facts the draft was
built from (the denial input and the audit result). Inside a category each applicable
check weighs the same. A category with no applicable check (``clauses`` when the audit
cited no violation) is dropped and the remaining weights are renormalised, so a letter is
never penalised for a citation that does not exist.

What this measures: whether the *template wiring* puts the facts and citations in the
letter, in English, Hindi and Marathi. It does NOT measure legal correctness, tone, or
whether the cited provision really supports the ground (``unverified_clause_citations``
counts citations the auditor itself marks UNVERIFIED). Offline and deterministic.
"""

import logging
import re
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.evaluation.metrics import safe_div

logger = logging.getLogger("arogyarakshak.evaluation.appeal_completeness")

WEIGHTS: Dict[str, float] = {
    "patient": 0.15,
    "policy": 0.20,
    "clauses": 0.30,
    "justification": 0.25,
    "references": 0.10,
}

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_PLACEHOLDER = re.compile(r"\[[^\]\n]{1,40}\]")
_NAME_WORDS = ("name", "नाम", "नाव")
_CLAIM_LABEL = re.compile(r"Claim\s*No|दावा\s*(?:क्र|क्रमांक|संख्या)", re.IGNORECASE)
_FIFTEEN_DAYS = re.compile(r"\b15\s*-?\s*(?:day|दिन|दिवस)", re.IGNORECASE)
_CIRCULAR = re.compile(r"Master Circular|मास्टर परिपत्र")
_CIRCULAR_DATE = re.compile(r"May 29, 2024|29 (?:मई|मे) 2024")
_BHAROSA = re.compile(r"Bima Bharosa|बीमा भरोसा|विमा भरोसा", re.IGNORECASE)
_OMBUDSMAN = re.compile(r"Ombudsman|लोकपाल", re.IGNORECASE)

Check = Tuple[str, Optional[bool]]  # (name, passed) — None means not applicable


def normalise(text: str) -> str:
    """Devanagari digits -> ASCII, so amounts and days compare across languages."""
    return text.translate(_DEVANAGARI_DIGITS)


def _money(value: float) -> str:
    return f"{value:,.2f}"


def _name_placeholder_left(text: str) -> bool:
    return any(any(w in p.lower() for w in _NAME_WORDS) for p in _PLACEHOLDER.findall(text))


def _claim_reference_filled(text: str) -> bool:
    """A claim-number label must be present AND its value must not be a placeholder."""
    for m in _CLAIM_LABEL.finditer(text):
        tail = text[m.end(): m.end() + 24]
        if not _PLACEHOLDER.search(tail.split("\n")[0]):
            return True
    return False


def run_checks(letter: str, facts: Dict[str, Any]) -> Dict[str, List[Check]]:
    """``facts``: policy_number, insurer_name, diagnosis, claimed_amount, denied_amount,
    denial_reason, grounds, violations ([{clause_reference, statute_or_circular}])."""
    text = normalise(letter)
    denied = _money(facts["denied_amount"])
    violations = facts.get("violations") or []
    return {
        "patient": [
            ("diagnosis_stated", facts["diagnosis"] in text),
            ("claim_amounts_stated", _money(facts["claimed_amount"]) in text and denied in text),
            ("policyholder_name_filled", not _name_placeholder_left(text)),
        ],
        "policy": [
            ("policy_number_stated", facts["policy_number"] in text),
            ("insurer_named", facts["insurer_name"] in text),
            ("claim_reference_filled", _claim_reference_filled(text)),
            ("denial_reason_quoted", facts["denial_reason"] in text),
        ],
        "clauses": [
            (f"clause_cited[{i}]",
             normalise(v["clause_reference"]) in text and normalise(v["statute_or_circular"]) in text)
            for i, v in enumerate(violations)
        ],
        "justification": [
            ("grounds_stated", normalise(facts["grounds"]) in text),
            ("relief_amount_restated", text.count(denied) >= 2),
            ("resolution_window_demanded", bool(_FIFTEEN_DAYS.search(text))),
        ],
        "references": [
            ("master_circular_cited", bool(_CIRCULAR.search(text))),
            ("circular_date_cited", bool(_CIRCULAR_DATE.search(text))),
            ("escalation_path_named", bool(_BHAROSA.search(text)) and bool(_OMBUDSMAN.search(text))),
        ],
    }


def score_checks(checks: Dict[str, List[Check]]) -> Dict[str, Any]:
    """Weighted score in [0, 1] from ``run_checks`` output."""
    categories: Dict[str, Optional[float]] = {}
    weighted = applicable_weight = 0.0
    failed: List[str] = []
    for cat, items in checks.items():
        applicable = [(n, ok) for n, ok in items if ok is not None]
        failed += [f"{cat}.{n}" for n, ok in applicable if not ok]
        if not applicable:
            categories[cat] = None
            continue
        share = sum(1 for _, ok in applicable if ok) / len(applicable)
        categories[cat] = share
        weighted += WEIGHTS[cat] * share
        applicable_weight += WEIGHTS[cat]
    return {
        "score": safe_div(weighted, applicable_weight),
        "applicable_weight": round(applicable_weight, 10),
        "categories": categories,
        "failed": failed,
    }


Drafter = Callable[[Dict[str, Any], str], Tuple[str, Dict[str, Any]]]
# drafter(input dict, language) -> (letter text, facts dict for run_checks)


def evaluate_appeal_completeness(rows: List[Dict[str, Any]], drafter: Drafter,
                                 languages: Tuple[str, ...] = ("en", "hi", "mr")) -> Dict[str, Any]:
    per_language: Dict[str, List[float]] = defaultdict(list)
    cat_pass: Dict[str, List[float]] = defaultdict(list)
    failed_counter: Counter = Counter()
    scores: List[float] = []
    complete = 0
    unverified = 0
    low: List[Dict[str, Any]] = []
    for row in rows:
        for lang in languages:
            letter, facts = drafter(row["input"], lang)
            result = score_checks(run_checks(letter, facts))
            score = result["score"]
            scores.append(score)
            per_language[lang].append(score)
            complete += not result["failed"]
            for cat, share in result["categories"].items():
                if share is not None:
                    cat_pass[cat].append(share)
            failed_counter.update(result["failed"])
            unverified += sum(1 for v in facts.get("violations") or []
                              if str(v["clause_reference"]).upper().startswith("UNVERIFIED"))
            if result["failed"]:
                low.append({"id": row["id"], "language": lang, "score": round(score, 4),
                            "failed": result["failed"]})
    n = len(scores)
    logger.info("Appeal completeness: %d letters, mean score %.3f", n, sum(scores) / n if n else 0.0)
    return {
        "metric": "appeal_completeness",
        "weights": WEIGHTS,
        "scenarios": len(rows),
        "letters": n,
        "mean_score": safe_div(sum(scores), n),
        "fully_complete_share": safe_div(complete, n),
        "per_language": {lang: safe_div(sum(v), len(v)) for lang, v in per_language.items()},
        "per_category": {c: safe_div(sum(v), len(v)) for c, v in cat_pass.items()},
        "failed_check_counts": dict(failed_counter.most_common()),
        "unverified_clause_citations": unverified,
        "failures": low,
    }
