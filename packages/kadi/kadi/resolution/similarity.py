"""
Kadi entity resolution — surface string similarity (#28).

Deterministic, standard-library measures that form the *lexical* signal of the entity
resolver (``kadi.resolution.resolver``):

- normalized Levenshtein ratio (edit distance)
- Jaro-Winkler (reported for inspection; not part of the combined score)
- fuzzy core-token overlap (Jaccard and containment), so word order and dosage/unit
  qualifiers do not hide a match: "Type 2 diabetes mellitus" ~ "Diabetes mellitus type 2",
  "Tab Paracetamol 650mg" ~ "Paracetamol".

Conflict detectors must block an automatic merge no matter how similar two names look:
differing quantities (650 mg vs 500 mg, "Day 1" vs "Day 2"), dosage forms (tablet vs
injection), variant letters ("Hepatitis A" vs "Hepatitis B") and laterality (left vs
right knee). A qualifier present on only one side is *missing*, not conflicting.

Every score here is similarity evidence in [0, 1], not a probability.
"""

import unicodedata
from collections import Counter
from typing import FrozenSet, Iterable, List, Sequence, Set, Tuple

from pydantic import BaseModel

# "a" is deliberately absent: a standalone letter is a variant marker ("Hepatitis A").
GENERIC_STOPWORDS: FrozenSet[str] = frozenset(
    {"the", "of", "and", "with", "for", "an", "in", "on", "to", "&"}
)

_ROMAN_NUMERAL_MARKERS = frozenset({"i", "ii", "iii", "iv", "v", "vi"})
_LATERALITY_ALIASES = {"left": "left", "lt": "left", "right": "right", "rt": "right", "bilateral": "bilateral"}

# Words that name the *kind* of facility rather than the facility itself. "Lifeline
# Hospital" and "Lifeline Multispeciality Hospital" differ only in these.
FACILITY_STOPWORDS: FrozenSet[str] = frozenset(
    {
        "hospital", "hospitals", "clinic", "clinics", "nursing", "home", "centre", "center",
        "multispeciality", "multispecialty", "multi", "speciality", "specialty", "super",
        "superspeciality", "medical", "institute", "pvt", "ltd", "private", "limited",
        "llp", "trust", "healthcare", "health", "care",
    }
)

UNIT_TOKENS: FrozenSet[str] = frozenset(
    {"mg", "ml", "mcg", "µg", "g", "gm", "gms", "kg", "iu", "unit", "units", "%"}
)

# Unit -> multiplier to milligrams, so "0.5 g" and "500 mg" are not a false conflict.
_MASS_TO_MG = {"g": 1000.0, "gm": 1000.0, "gms": 1000.0, "mg": 1.0, "mcg": 0.001, "µg": 0.001}

_DOSAGE_FORM_ALIASES = {
    "tab": "tablet", "tabs": "tablet", "tablet": "tablet", "tablets": "tablet",
    "cap": "capsule", "caps": "capsule", "capsule": "capsule", "capsules": "capsule",
    "inj": "injection", "injection": "injection", "injections": "injection",
    "syp": "syrup", "syrup": "syrup",
    "susp": "suspension", "suspension": "suspension",
    "drop": "drops", "drops": "drops",
    "cream": "cream", "ointment": "ointment", "oint": "ointment", "gel": "gel",
    "spray": "spray", "inhaler": "inhaler", "sachet": "sachet", "powder": "powder",
    "lotion": "lotion", "solution": "solution", "soln": "solution", "infusion": "infusion",
}

# Weight applied to token containment. Containment alone ("Hypertension" inside
# "Pulmonary hypertension") is weaker evidence than full overlap, so it can reach the
# ask-user band but never the merge band on its own.
CONTAINMENT_WEIGHT = 0.85

# Minimum Levenshtein ratio for two tokens to count as the same word. Deliberately
# strict: "amoxicillin"/"ampicillin" (0.82) are different antibiotics.
FUZZY_TOKEN_MIN_RATIO = 0.85
FUZZY_TOKEN_MIN_LENGTH = 5


def _char_class(ch: str) -> str:
    if ch.isdigit():
        return "digit"
    if unicodedata.category(ch)[0] in ("L", "M"):
        # Letters and combining marks. Devanagari vowel signs and virama are marks, so
        # this keeps "क्रोसिन" in one token instead of splitting it at every matra.
        return "alpha"
    return "sep"


def tokenize(text: str) -> List[str]:
    """NFKC-normalized, casefolded tokens. Digits and letters are split ("650mg" -> "650",
    "mg"); a decimal point between digits is kept; "%" is its own token."""
    s = unicodedata.normalize("NFKC", text or "").casefold()
    tokens: List[str] = []
    buf: List[str] = []
    current = None

    def flush() -> None:
        nonlocal current
        if buf:
            tokens.append("".join(buf))
            buf.clear()
        current = None

    for i, ch in enumerate(s):
        cls = _char_class(ch)
        if cls == "sep":
            if ch == "." and current == "digit" and i + 1 < len(s) and s[i + 1].isdigit():
                buf.append(ch)
                continue
            flush()
            if ch == "%":
                tokens.append("%")
            continue
        if current is not None and cls != current:
            flush()
        buf.append(ch)
        current = cls
    flush()
    return tokens


def normalize_surface(text: str) -> str:
    return " ".join(tokenize(text))


def levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb))
            )
        previous = current
    return previous[-1]


def levenshtein_ratio(a: str, b: str) -> float:
    """1 - distance / max length. Two empty strings carry no evidence and score 0."""
    if not a or not b:
        return 0.0
    return 1.0 - levenshtein_distance(a, b) / max(len(a), len(b))


def jaro_winkler(a: str, b: str, prefix_scale: float = 0.1) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    window = max(max(len(a), len(b)) // 2 - 1, 0)
    a_flags = [False] * len(a)
    b_flags = [False] * len(b)
    matches = 0
    for i, ca in enumerate(a):
        lo, hi = max(0, i - window), min(i + window + 1, len(b))
        for j in range(lo, hi):
            if not b_flags[j] and b[j] == ca:
                a_flags[i] = b_flags[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    a_matched = [ca for ca, f in zip(a, a_flags) if f]
    b_matched = [cb for cb, f in zip(b, b_flags) if f]
    transpositions = sum(x != y for x, y in zip(a_matched, b_matched)) / 2
    jaro = (matches / len(a) + matches / len(b) + (matches - transpositions) / matches) / 3
    prefix = 0
    for x, y in zip(a[:4], b[:4]):
        if x != y:
            break
        prefix += 1
    return jaro + prefix * prefix_scale * (1 - jaro)


def _as_number(token: str):
    try:
        return float(token)
    except ValueError:
        return None


def extract_quantities(tokens: Sequence[str]) -> List[float]:
    """Numbers in the name, with mass units normalized to milligrams."""
    quantities: List[float] = []
    for i, tok in enumerate(tokens):
        value = _as_number(tok)
        if value is None:
            continue
        unit = tokens[i + 1] if i + 1 < len(tokens) else ""
        quantities.append(round(value * _MASS_TO_MG.get(unit, 1.0), 6))
    return quantities


def _is_submultiset(small: Sequence[float], large: Sequence[float]) -> bool:
    return not (Counter(small) - Counter(large))


def numeric_conflict(a: str, b: str) -> bool:
    """True when both names carry quantities and neither set contains the other.

    "Dolo 650" / "Dolo 500" conflict; "Vitamin D3" / "Vitamin D3 60000 IU" do not — the
    second only adds a quantity the first did not state."""
    qa, qb = extract_quantities(tokenize(a)), extract_quantities(tokenize(b))
    if not qa or not qb:
        return False
    return not (_is_submultiset(qa, qb) or _is_submultiset(qb, qa))


def variant_markers(tokens: Iterable[str]) -> Set[str]:
    """Standalone Latin letters and small roman numerals: "Hepatitis A", "Stage II"."""
    return {
        t for t in tokens
        if (len(t) == 1 and t.isascii() and t.isalpha()) or t in _ROMAN_NUMERAL_MARKERS
    }


def variant_conflict(a: str, b: str) -> bool:
    ma, mb = variant_markers(tokenize(a)), variant_markers(tokenize(b))
    return bool(ma) and bool(mb) and ma != mb


# Prefix pairs with opposite clinical meaning. "Hyperthyroidism" and "Hypothyroidism" are
# one edit apart and opposite conditions.
_OPPOSING_PREFIXES: Tuple[Tuple[str, str], ...] = (
    ("hyper", "hypo"), ("hyper", "normo"), ("hypo", "normo"), ("brady", "tachy"),
    ("pre", "post"), ("ante", "post"), ("intra", "extra"), ("inter", "intra"),
    ("micro", "macro"),
)


def _stem_after(token: str, prefix: str):
    if token.startswith(prefix) and len(token) - len(prefix) >= 3:
        return token[len(prefix):]
    return None


def opposing_prefix_conflict(a: str, b: str) -> bool:
    """True when two tokens share a stem behind opposite prefixes (hyper-/hypo-thyroidism,
    brady-/tachy-cardia) or are the bare opposite prefixes themselves (pre / post)."""
    ta, tb = tokenize(a), tokenize(b)
    for x in ta:
        for y in tb:
            if x == y:
                continue
            for p, q in _OPPOSING_PREFIXES:
                if {x, y} == {p, q}:
                    return True
                for (u, pu), (v, pv) in (((x, p), (y, q)), ((x, q), (y, p))):
                    su, sv = _stem_after(u, pu), _stem_after(v, pv)
                    if su and sv and (su == sv or levenshtein_ratio(su, sv) >= FUZZY_TOKEN_MIN_RATIO):
                        return True
    return False


def laterality(tokens: Iterable[str]) -> Set[str]:
    return {_LATERALITY_ALIASES[t] for t in tokens if t in _LATERALITY_ALIASES}


def laterality_conflict(a: str, b: str) -> bool:
    la, lb = laterality(tokenize(a)), laterality(tokenize(b))
    return bool(la) and bool(lb) and la != lb


def dosage_forms(tokens: Iterable[str]) -> Set[str]:
    return {_DOSAGE_FORM_ALIASES[t] for t in tokens if t in _DOSAGE_FORM_ALIASES}


def dosage_form_conflict(a: str, b: str) -> bool:
    fa, fb = dosage_forms(tokenize(a)), dosage_forms(tokenize(b))
    return bool(fa) and bool(fb) and not (fa & fb)


def _is_stopword(tok: str, stopwords: FrozenSet[str], fuzzy: bool) -> bool:
    if tok in stopwords:
        return True
    if not fuzzy or len(tok) < 6:
        return False
    return any(
        len(s) >= 6 and abs(len(s) - len(tok)) <= 2 and levenshtein_ratio(tok, s) >= FUZZY_TOKEN_MIN_RATIO
        for s in stopwords
    )


def core_tokens(
    tokens: Sequence[str],
    stopwords: FrozenSet[str] = GENERIC_STOPWORDS,
    fuzzy_stopwords: bool = False,
) -> List[str]:
    """Tokens that identify the entity: no numbers, units, dosage forms, laterality,
    variant markers or stopwords.

    ``fuzzy_stopwords`` also drops near-spellings of stopwords (for romanized text, where
    "मल्टीस्पेशालिटी" becomes "maltispesaliti", not "multispesialiti"). It is off by default
    because it can swallow a real name close to a stopword ("Medica" ~ "medical")."""
    core: List[str] = []
    for tok in tokens:
        if _as_number(tok) is not None or tok in UNIT_TOKENS or tok in _DOSAGE_FORM_ALIASES:
            continue
        if tok in _LATERALITY_ALIASES or _is_stopword(tok, stopwords, fuzzy_stopwords):
            continue
        if tok in variant_markers([tok]) or (len(tok) < 2 and tok.isascii()):
            continue
        core.append(tok)
    return core


def _tokens_match(x: str, y: str) -> bool:
    if x == y:
        return True
    if min(len(x), len(y)) < FUZZY_TOKEN_MIN_LENGTH:
        return False
    return levenshtein_ratio(x, y) >= FUZZY_TOKEN_MIN_RATIO


def fuzzy_token_overlap(a: Sequence[str], b: Sequence[str]) -> Tuple[float, float]:
    """(Jaccard, containment) over token sets, where near-identical tokens match."""
    set_a, set_b = list(dict.fromkeys(a)), list(dict.fromkeys(b))
    if not set_a or not set_b:
        return 0.0, 0.0
    smaller, larger = (set_a, set_b) if len(set_a) <= len(set_b) else (set_b, set_a)
    unmatched = list(larger)
    matched = 0
    for tok in smaller:
        for candidate in unmatched:
            if _tokens_match(tok, candidate):
                unmatched.remove(candidate)
                matched += 1
                break
    jaccard = matched / (len(set_a) + len(set_b) - matched)
    containment = matched / len(smaller)
    return jaccard, containment


class StringSimilarity(BaseModel):
    normalized_a: str
    normalized_b: str
    levenshtein_ratio: float
    jaro_winkler: float
    core_levenshtein_ratio: float
    token_jaccard: float
    token_containment: float
    score: float
    numeric_conflict: bool
    dosage_form_conflict: bool


def string_similarity(
    a: str,
    b: str,
    stopwords: FrozenSet[str] = GENERIC_STOPWORDS,
    fuzzy_stopwords: bool = False,
) -> StringSimilarity:
    """Combined lexical similarity.

    score = max(full-string Levenshtein ratio, core-token Levenshtein ratio,
                core-token Jaccard, CONTAINMENT_WEIGHT * core-token containment)
    """
    ta, tb = tokenize(a), tokenize(b)
    na, nb = " ".join(ta), " ".join(tb)
    ca = core_tokens(ta, stopwords, fuzzy_stopwords)
    cb = core_tokens(tb, stopwords, fuzzy_stopwords)

    lev = levenshtein_ratio(na, nb)
    core_lev = levenshtein_ratio(" ".join(ca), " ".join(cb)) if ca and cb else 0.0
    jaccard, containment = fuzzy_token_overlap(ca, cb)
    score = max(lev, core_lev, jaccard, CONTAINMENT_WEIGHT * containment)

    return StringSimilarity(
        normalized_a=na,
        normalized_b=nb,
        levenshtein_ratio=round(lev, 4),
        jaro_winkler=round(jaro_winkler(na, nb), 4),
        core_levenshtein_ratio=round(core_lev, 4),
        token_jaccard=round(jaccard, 4),
        token_containment=round(containment, 4),
        score=round(min(max(score, 0.0), 1.0), 4),
        numeric_conflict=numeric_conflict(a, b),
        dosage_form_conflict=dosage_form_conflict(a, b),
    )
