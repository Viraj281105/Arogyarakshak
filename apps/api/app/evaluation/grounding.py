"""
Hallucination rate and grounding score for generated legal letters (#115).

A *claim* is a checkable statement of fact that a letter makes. Seven kinds are extracted
by regular expressions, in English, Hindi and Marathi text:

    amount      ₹ / INR / Rs. figures                      -> float
    policy_no   the value after "Policy No." / पॉलिसी क्र.   -> upper-cased token
    clause      Clause / Section / Regulation / Rule N      -> "rule14(1)(b)"
    percent     "2%"                                        -> float
    days        "15-day", "15 days", "१५ दिन"               -> int
    date        "May 29, 2024", "29 मई 2024"                -> ISO date
    clinician   "Dr. X", "the treating physician certified" -> never grounded

A claim is **grounded** when its (kind, value) is in the allowed set built from (a) the
facts the letter was generated from — the denial input and the audit result — and (b) a
small static reference library (``STATIC_REFERENCE``). A **clinician** claim can never be
grounded: the system never supplies a named clinician's opinion (ADR-011).

    grounding_score    = grounded claims / extracted claims
    hallucination_rate = ungrounded claims / extracted claims   (= 1 - grounding_score)
    letters_with_ungrounded = share of letters with at least one ungrounded claim

What this proves and what it does not: it detects a letter that asserts a figure, a
citation, a deadline or a clinician opinion that is not in its source. It does NOT judge
legal correctness (the static library is the team's own statement of the template's fixed
claims, not independently verified law), does not see claims written in words ("sixty
thousand rupees") or case-law citations, and says nothing about the Groq-written letter
path, which is not run offline. The detector is itself validated on labelled letters that
contain injected hallucinations, including two it is known to miss.
"""

import logging
import re
from typing import Any, Callable, Dict, Hashable, List, Optional, Sequence, Set, Tuple

from app.evaluation.metrics import multiset_match_counts, precision_recall_f1, safe_div

logger = logging.getLogger("arogyarakshak.evaluation.grounding")

Claim = Tuple[str, Hashable]  # (kind, normalised value)

# Fixed statements the BimaNyay templates make in every letter, stated here independently of
# the template code. TEAM-STATED, NOT INDEPENDENTLY VERIFIED LAW: they are the reference the
# letters are held to, so a letter that drifts (a different deadline, rate or date) is caught.
STATIC_REFERENCE = (
    "IRDAI Master Circular on Health Insurance Business (May 29, 2024)",
    "penal interest at Bank Rate + 2%",
    "statutory 15-day resolution window",
    "Insurance Ombudsman Rules, 2017, Rule 14(1)(b)",
)

_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_MARKS = {"बी": "b", "ए": "a", "सी": "c", "डी": "d"}

_MONTHS = {
    **{m: i for i, m in enumerate(
        ["january", "february", "march", "april", "may", "june", "july", "august",
         "september", "october", "november", "december"], 1)},
    **{m: i for i, m in enumerate(
        ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त",
         "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"], 1)},
    **{m: i for i, m in enumerate(
        ["जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून", "जुलै", "ऑगस्ट",
         "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"], 1)},
}
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))

_AMOUNT = re.compile(r"(?:₹|\b(?:INR|Rs)\.?)\s*([0-9][0-9,]*(?:\.[0-9]+)?)", re.IGNORECASE)
_POLICY = re.compile(
    r"(?:Policy\s*(?:No\.?|Number)|पॉलिसी\s*(?:संख्या|क्र\.?|क्रमांक))\s*[:.]?\s*([A-Za-z0-9][A-Za-z0-9\-/]*)",
    re.IGNORECASE,
)
_CLAUSE_EN = re.compile(r"\b(Clause|Section|Regulation|Rule)\s+(\d+(?:\([^)\s]{1,3}\))*)", re.IGNORECASE)
_CLAUSE_DEV = re.compile(r"(?:नियम|कलम|धारा|खंड)\s+(\d+(?:\([^)\s]{1,3}\))*)")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_DAYS = re.compile(r"\b(\d+)\s*-?\s*(?:days?|दिन|दिवस)", re.IGNORECASE)
_DATE_MDY = re.compile(rf"\b({_MONTH_ALT})\s+(\d{{1,2}}),?\s+(\d{{4}})", re.IGNORECASE)
_DATE_DMY = re.compile(rf"\b(\d{{1,2}})\s+({_MONTH_ALT})\s+(\d{{4}})", re.IGNORECASE)
_CLINICIAN = re.compile(
    r"\b(?:Dr\.?|Doctor)\s+(?-i:[A-Z])[\w.]*"
    r"|डॉ\.?\s*\S+"
    r"|\b(?:treating|attending)\s+(?:physician|doctor)\b[^.\n]{0,40}?"
    r"\b(?:certif\w*|opin\w*|review\w*|confirm\w*|stat\w*)\b",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    text = text.translate(_DIGITS)
    for dev, lat in _MARKS.items():
        text = text.replace(f"({dev})", f"({lat})")
    return text


def _date(day: str, month: str, year: str) -> Optional[str]:
    m = _MONTHS.get(month.lower()) or _MONTHS.get(month)
    return f"{int(year):04d}-{m:02d}-{int(day):02d}" if m else None


def extract_claims(text: str) -> List[Claim]:
    """Every checkable claim in ``text`` (duplicates kept: each occurrence is a claim)."""
    t = _norm(text)
    out: List[Claim] = []
    for m in _AMOUNT.finditer(t):
        out.append(("amount", round(float(m.group(1).replace(",", "").rstrip(".")), 2)))
    for m in _POLICY.finditer(t):
        out.append(("policy_no", m.group(1).upper()))
    for m in _CLAUSE_EN.finditer(t):
        out.append(("clause", f"{m.group(1).lower()}{m.group(2).lower()}"))
    for m in _CLAUSE_DEV.finditer(t):
        out.append(("clause", f"rule{m.group(1).lower()}"))
    for m in _PERCENT.finditer(t):
        out.append(("percent", float(m.group(1))))
    for m in _DAYS.finditer(t):
        out.append(("days", int(m.group(1))))
    for m in _DATE_MDY.finditer(t):
        d = _date(m.group(2), m.group(1), m.group(3))
        if d:
            out.append(("date", d))
    for m in _DATE_DMY.finditer(t):
        d = _date(m.group(1), m.group(2), m.group(3))
        if d:
            out.append(("date", d))
    for m in _CLINICIAN.finditer(t):
        out.append(("clinician", " ".join(m.group(0).lower().split())))
    return out


def allowed_claims(facts: Dict[str, Any]) -> Set[Claim]:
    """Claims a letter may make: facts of its own case, the audit's own text, and the static
    reference library. Never contains a ``clinician`` claim."""
    allowed: Set[Claim] = {
        ("amount", round(float(facts["claimed_amount"]), 2)),
        ("amount", round(float(facts["denied_amount"]), 2)),
        ("policy_no", str(facts["policy_number"]).upper()),
    }
    sources = [facts.get("grounds", ""), facts.get("denial_reason", ""), facts.get("diagnosis", ""),
               *STATIC_REFERENCE]
    for v in facts.get("violations") or []:
        sources += [v.get("clause_reference", ""), v.get("statute_or_circular", "")]
    for s in sources:
        allowed.update(c for c in extract_claims(s) if c[0] != "clinician")
    return allowed


def ground_letter(letter: str, facts: Dict[str, Any]) -> Dict[str, Any]:
    claims = extract_claims(letter)
    allowed = allowed_claims(facts)
    ungrounded = [c for c in claims if c not in allowed]
    return {"claims": claims, "ungrounded": ungrounded}


def _tuples(items: Sequence[Sequence[Any]]) -> List[Claim]:
    return [(str(k), v) for k, v in items]


# --- detector validation: labelled letters with injected hallucinations ---------------------

def evaluate_detector(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Each row: ``letter``, ``facts``, ``gold_ungrounded`` ([[kind, value], ...]). Scores the
    detector's ungrounded set against the gold set as multisets (claim-level P/R/F1)."""
    tp = fp = fn = 0
    letters_ok = 0
    missed: List[Dict[str, Any]] = []
    spurious: List[Dict[str, Any]] = []
    for row in rows:
        got = ground_letter(row["letter"], row["facts"])["ungrounded"]
        gold = _tuples(row.get("gold_ungrounded", []))
        c = multiset_match_counts(gold, got)
        tp, fp, fn = tp + c["tp"], fp + c["fp"], fn + c["fn"]
        letters_ok += (c["fp"] == 0 and c["fn"] == 0)
        if c["fn"]:
            remaining = list(got)
            miss = []
            for g in gold:
                if g in remaining:
                    remaining.remove(g)
                else:
                    miss.append(list(g))
            missed.append({"id": row["id"], "category": row.get("category"), "missed": miss})
        if c["fp"]:
            remaining_gold = list(gold)
            extra = []
            for g in got:
                if g in remaining_gold:
                    remaining_gold.remove(g)
                else:
                    extra.append(list(g))
            spurious.append({"id": row["id"], "category": row.get("category"), "spurious": extra})
    return {
        "rows": len(rows),
        "gold_ungrounded_claims": tp + fn,
        "tp": tp, "fp": fp, "fn": fn,
        **precision_recall_f1(tp, fp, fn),
        "letters_exactly_right": safe_div(letters_ok, len(rows)),
        "missed": missed,
        "spurious": spurious,
    }


# --- production letters ---------------------------------------------------------------------

Generator = Callable[[Dict[str, Any], str], List[Tuple[str, str, Dict[str, Any]]]]
# generator(input dict, language) -> [(document name, text, facts), ...]


def evaluate_production(rows: List[Dict[str, Any]], generator: Generator,
                        languages: Tuple[str, ...] = ("en", "hi", "mr")) -> Dict[str, Any]:
    total_claims = ungrounded_claims = letters = letters_bad = 0
    by_kind: Dict[str, Dict[str, int]] = {}
    failures: List[Dict[str, Any]] = []
    for row in rows:
        for lang in languages:
            for doc, text, facts in generator(row["input"], lang):
                g = ground_letter(text, facts)
                letters += 1
                total_claims += len(g["claims"])
                ungrounded_claims += len(g["ungrounded"])
                for kind, _ in g["claims"]:
                    by_kind.setdefault(kind, {"claims": 0, "ungrounded": 0})["claims"] += 1
                for kind, _ in g["ungrounded"]:
                    by_kind.setdefault(kind, {"claims": 0, "ungrounded": 0})["ungrounded"] += 1
                if g["ungrounded"]:
                    letters_bad += 1
                    failures.append({"id": row["id"], "language": lang, "document": doc,
                                     "ungrounded": [list(c) for c in g["ungrounded"]]})
    logger.info("Grounding: %d letters, %d claims, %d ungrounded", letters, total_claims, ungrounded_claims)
    return {
        "letters": letters,
        "claims": total_claims,
        "ungrounded_claims": ungrounded_claims,
        "grounding_score": safe_div(total_claims - ungrounded_claims, total_claims),
        "hallucination_rate": safe_div(ungrounded_claims, total_claims),
        "letters_with_ungrounded": safe_div(letters_bad, letters),
        "by_kind": by_kind,
        "failures": failures,
    }


def evaluate_grounding(detector_rows: List[Dict[str, Any]], scenario_rows: List[Dict[str, Any]],
                       generator: Generator) -> Dict[str, Any]:
    return {
        "metric": "grounding",
        "detector_rows": len(detector_rows),
        "detector": evaluate_detector(detector_rows),
        "production": evaluate_production(scenario_rows, generator),
        "failures": [],
    }
