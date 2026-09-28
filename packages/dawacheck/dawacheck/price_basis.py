"""
DawaCheck — price basis: what a billed amount actually buys.

NPPA ceiling prices are per dosage unit (one tablet, one capsule, one vial). A bill or a
receipt often states a strip, pack or line total instead. Comparing a strip price with a
per-tablet ceiling produces absurd "overcharged by 1,400%" results, so every comparison
first establishes the basis of the billed amount and converts it to a price per unit —
or refuses to compare.

Rules (no rule ever guesses):
  * A basis comes from the patient's own declaration (manual check) or from what the
    document itself states (the bill line, or a "rate per tablet" column heading).
  * A strip/pack price is converted only when the number of units in it is stated.
  * A line total is converted only when the number of units is stated.
  * Contradictory or missing information -> CANNOT_COMPARE with a plain reason.
  * The only default is the legacy manual-API contract ("MRP per tablet/unit") for a
    caller that sends no basis and whose medicine name states no pack — reported as
    such (`basis_source = API_DEFAULT`), never as a document fact.
"""

import re
from enum import Enum
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Tuple

from pydantic import BaseModel, Field


class PriceBasis(str, Enum):
    PER_UNIT = "PER_UNIT"  # one tablet / capsule / vial
    PER_STRIP = "PER_STRIP"  # one strip of N units
    PER_PACK = "PER_PACK"  # one pack / box / bottle of N units
    LINE_TOTAL = "LINE_TOTAL"  # the amount for a stated number of units
    UNKNOWN = "UNKNOWN"


class ComparisonStatus(str, Enum):
    COMPARED = "COMPARED"
    CANNOT_COMPARE = "CANNOT_COMPARE"


# Dosage forms. Tablets and capsules are different formulations with different NPPA
# ceilings, so they are not treated as interchangeable.
_FORM_WORDS: Tuple[Tuple[str, str], ...] = (
    (r"tabs?|tablets?", "tablet"),
    (r"caps?|capsules?", "capsule"),
    (r"inj|injections?|vials?|ampoules?|amps?|iv", "injection"),
    (r"syr|syrups?|suspensions?|susp|ml", "liquid"),
)
UNIT_NOUN = {"tablet": "tablet", "capsule": "capsule", "injection": "vial", "liquid": "bottle"}
_FORM_PHRASE = {"tablet": "a tablet", "capsule": "a capsule", "injection": "an injection", "liquid": "a liquid (syrup/suspension)"}


def detect_forms(text: str) -> FrozenSet[str]:
    lowered = f" {text.lower()} "
    found = set()
    for pattern, form in _FORM_WORDS:
        if re.search(rf"(?<![a-z])(?:{pattern})(?![a-z])", lowered):
            found.add(form)
    return frozenset(found)


# --- What a line of text says about quantity ------------------------------------------

_STRIP_SIZE_RES = (
    re.compile(r"\bstrips?\s*(?:of\s*)?(\d{1,3})\b"),
    re.compile(r"\b(\d{1,3})\s*(?:tabs?|tablets?|caps?|capsules?)\s*(?:/|per|in\s+a|in\s+one|in)\s*strip\b"),
)
_PACK_SIZE_RES = (
    re.compile(r"\b(?:pack|box|bottle|carton)s?\s*(?:of\s*)?(\d{1,4})\b"),
    re.compile(r"\b(\d{1,4})\s*(?:tabs?|tablets?|caps?|capsules?|vials?)\s*(?:/|per|in\s+a|in\s+one|in)\s*(?:pack|box)\b"),
    # Indian pack notation: "Dolo 650 Tablet 15's", "(10s)".
    re.compile(r"(?<![\w.])(\d{1,3})\s*'\s*s\b|(?<![\w.])(\d{1,3})s\b"),
    # "1x10" / "10 x 10" pack notation — but never a dosing schedule such as "x 5 days".
    re.compile(r"(?<![\w.\-])(\d{1,2})\s*[x×]\s*(\d{1,3})\b(?!\s*(?:days?|d\b|weeks?|wks?|months?|times?))"),
)
_PER_UNIT_RE = re.compile(
    r"(?:/\s*|\bper\s+|\beach\s+|\bof\s+one\s+)(tabs?|tablets?|caps?|capsules?|units?|vials?|ampoules?|amps?|nos?)\b"
    r"|\beach\b|\bunit\s+(?:price|rate)\b|\bper\s+unit\b"
)
_QTY_RES = (
    re.compile(r"\b(?:qty|quantity|nos)\.?\s*[:\-=]?\s*(-?\d+(?:\.\d+)?)\b"),
    re.compile(r"\b(\d{1,4})\s*(?:nos?|units?|pcs|pieces)\b"),
    re.compile(r"[x×]\s*(\d{1,4})\s*(?:tabs?|tablets?|caps?|capsules?|vials?|nos?)\b"),
    re.compile(r"\b(\d{1,4})\s*(?:tabs|tablets|caps|capsules|vials)\b"),
)
_STRIP_WORD_RE = re.compile(r"\bstrips?\b")
_PACK_WORD_RE = re.compile(r"\b(?:pack|box|bottle|carton)s?\b")


class QuantityFacts(BaseModel):
    """What a piece of text states about quantity. Every field is None unless stated."""

    basis: Optional[PriceBasis] = None
    units_per_pack: Optional[float] = None
    quantity: Optional[float] = None
    forms: List[str] = Field(default_factory=list)
    evidence: Optional[str] = None
    conflict: Optional[str] = None
    source: str = "none"  # "line" | "document" | "declared" | "none"


def _first_int(match: "re.Match[str]") -> Optional[float]:
    nums = [g for g in match.groups() if g]
    if not nums:
        return None
    if len(nums) == 2:  # "1x10": one strip of ten -> 10 units; "10x10": 100 units
        return float(int(nums[0]) * int(nums[1]))
    return float(nums[0])


def parse_quantity_text(text: str) -> QuantityFacts:
    """Reads the quantity/pack statements in one line of text (a bill line description,
    or a medicine name as the patient typed it). Pure, deterministic, never guesses."""
    lowered = (text or "").lower()
    evidence: List[str] = []
    sizes: Dict[str, List[float]] = {"strip": [], "pack": []}
    pack_spans: List[Tuple[int, int]] = []

    for kind, regexes in (("strip", _STRIP_SIZE_RES), ("pack", _PACK_SIZE_RES)):
        for rx in regexes:
            for m in rx.finditer(lowered):
                size = _first_int(m)
                if size is not None:
                    sizes[kind].append(size)
                    pack_spans.append(m.span())
                    evidence.append(m.group(0).strip())

    quantities: List[float] = []
    qty_spans: List[Tuple[int, int]] = []
    for rx in _QTY_RES:
        for m in rx.finditer(lowered):
            # A count inside an already-read pack statement ("strip of 10 tablets") is the
            # pack size, not a quantity; overlapping quantity patterns are one statement.
            start, end = m.span()
            if any(start < p_end and p_start < end for p_start, p_end in pack_spans + qty_spans):
                continue
            qty_spans.append((start, end))
            try:
                quantities.append(float(m.group(1)))
                evidence.append(m.group(0).strip())
            except (TypeError, ValueError):
                continue

    per_unit = _PER_UNIT_RE.search(lowered)
    if per_unit:
        evidence.append(per_unit.group(0).strip())

    forms = sorted(detect_forms(lowered))
    facts = QuantityFacts(forms=forms, evidence="; ".join(dict.fromkeys(evidence)) or None, source="line")

    strip_sizes = set(sizes["strip"])
    pack_sizes = set(sizes["pack"])
    all_sizes = strip_sizes | pack_sizes
    qtys = set(quantities)

    if len(all_sizes) > 1:
        facts.conflict = "The text states more than one pack size."
        return facts
    if len(qtys) > 1:
        facts.conflict = "The text states more than one quantity."
        return facts

    size = next(iter(all_sizes)) if all_sizes else None
    qty = next(iter(qtys)) if qtys else None
    has_strip = bool(strip_sizes) or bool(_STRIP_WORD_RE.search(lowered))
    has_pack = bool(pack_sizes) or bool(_PACK_WORD_RE.search(lowered))

    if per_unit and (size is not None or has_strip or has_pack):
        facts.conflict = "The text states both a per-unit price and a pack size."
        return facts
    if qty is not None and (size is not None or has_strip or has_pack):
        # "Qty 2" next to "strip of 10": bills differ on whether the quantity counts
        # tablets or strips, so the total cannot be converted with certainty.
        facts.conflict = "The text states both a quantity and a pack size; it is not clear whether the quantity counts units or packs."
        return facts

    if per_unit:
        facts.basis = PriceBasis.PER_UNIT
    elif size is not None or has_strip or has_pack:
        facts.basis = PriceBasis.PER_STRIP if has_strip else PriceBasis.PER_PACK
        facts.units_per_pack = size
    elif qty is not None:
        facts.basis = PriceBasis.LINE_TOTAL
        facts.quantity = qty
    else:
        facts.source = "none"
    return facts


_DOC_STATEMENT_RE = re.compile(
    r"\b(?:rate|price|mrp|cost|amount)s?\b[^\n]{0,30}?\bper\s+"
    r"(tablets?\s*/\s*capsules?|tabs?\s*/\s*caps?|tablets?|tabs?|capsules?|caps?|units?|vials?|strips?|packs?)\b",
    re.IGNORECASE,
)


def document_price_statement(text: str) -> Optional[QuantityFacts]:
    """A document-wide statement of the price basis, e.g. a column heading
    "Rate per tablet/capsule (Rs)". Returns None when no line states one, and None when
    the document states two different bases (it cannot then speak for every line)."""
    found: Dict[PriceBasis, Tuple[str, List[str]]] = {}
    for line in (text or "").splitlines():
        m = _DOC_STATEMENT_RE.search(line)
        if not m:
            continue
        unit = m.group(1).lower()
        if unit.startswith("strip"):
            basis = PriceBasis.PER_STRIP
        elif unit.startswith("pack"):
            basis = PriceBasis.PER_PACK
        else:
            basis = PriceBasis.PER_UNIT
        found.setdefault(basis, (line.strip()[:80], sorted(detect_forms(unit))))
    if len(found) != 1:
        return None
    basis, (evidence, forms) = next(iter(found.items()))
    return QuantityFacts(basis=basis, forms=forms, evidence=evidence, source="document")


def price_facts_for_medicine(
    description: str, document_statement: Optional[QuantityFacts]
) -> Dict[str, Any]:
    """The facts to store with an extracted medicine: its own line's statements first,
    then a document-wide statement. Serialisable (stored in entity meta)."""
    line = parse_quantity_text(description)
    if line.conflict or line.basis is not None:
        return line.model_dump(mode="json")
    if document_statement is not None:
        # The line's own dosage form wins; a "per tablet/capsule" heading only fills in
        # the form when the line names none.
        merged = document_statement.model_copy(update={"forms": line.forms or document_statement.forms})
        return merged.model_dump(mode="json")
    return line.model_dump(mode="json")


def annotate_medicine_price_facts(medicines: Iterable[Dict[str, Any]], document_text: str) -> None:
    """Adds ``price_facts`` to each extracted medicine dict (in place) from its source
    line (``source_line``, set by Kadi's grounding) or its name, plus any document-wide
    rate statement. Removes ``source_line`` afterwards: only the derived facts and the
    short matched snippet are kept, never the raw line."""
    statement = document_price_statement(document_text)
    for med in medicines:
        description = str(med.pop("source_line", None) or med.get("name") or "")
        med["price_facts"] = price_facts_for_medicine(description, statement)


# --- Resolving a billed amount to a per-unit price ------------------------------------


class BilledPrice(BaseModel):
    amount: float
    basis: PriceBasis
    basis_source: str  # DECLARED | DOCUMENT_LINE | DOCUMENT_HEADER | API_DEFAULT | NONE
    units_per_pack: Optional[float] = None
    quantity: Optional[float] = None
    forms: List[str] = Field(default_factory=list)
    evidence: Optional[str] = None
    problem: Optional[str] = None  # set when a per-unit price cannot be established
    problem_code: Optional[str] = None


_SOURCE_BY_FACT = {"line": "DOCUMENT_LINE", "document": "DOCUMENT_HEADER", "declared": "DECLARED"}


def _coerce_basis(value: Any) -> Optional[PriceBasis]:
    if value is None or value == "":
        return None
    try:
        return PriceBasis(str(value).upper())
    except ValueError:
        return PriceBasis.UNKNOWN


def resolve_billed_price(
    amount: Any,
    *,
    declared_basis: Any = None,
    units_per_pack: Any = None,
    quantity: Any = None,
    name_text: str = "",
    facts: Optional[Mapping[str, Any]] = None,
    allow_api_default: bool = False,
) -> BilledPrice:
    """Establishes the basis of `amount`.

    `declared_*` come from the person entering the price (manual check). `facts` come
    from the document (stored `price_facts`). `name_text` is read too, so "Dolo 650
    (15s)" entered as "per tablet" is caught as a contradiction rather than compared.
    """
    try:
        amount_f = float(amount)
    except (TypeError, ValueError):
        amount_f = float("nan")

    name_facts = parse_quantity_text(name_text) if name_text else QuantityFacts()
    doc = QuantityFacts.model_validate(dict(facts)) if isinstance(facts, Mapping) and facts else None
    declared = _coerce_basis(declared_basis)

    forms = sorted(set(name_facts.forms) | set(doc.forms if doc else []))

    def _num(v: Any) -> Optional[float]:
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return float("nan")

    upp = _num(units_per_pack)
    qty = _num(quantity)

    def fail(code: str, reason: str, basis: PriceBasis = PriceBasis.UNKNOWN, source: str = "NONE", evidence: Optional[str] = None) -> BilledPrice:
        return BilledPrice(
            amount=amount_f, basis=basis, basis_source=source, units_per_pack=upp, quantity=qty,
            forms=forms, evidence=evidence, problem=reason, problem_code=code,
        )

    if not (amount_f == amount_f) or amount_f <= 0:  # NaN or non-positive
        return fail("INVALID_AMOUNT", "No valid billed amount was recorded for this medicine.")

    if declared is not None and declared != PriceBasis.UNKNOWN:
        if name_facts.conflict:
            return fail("CONFLICTING_QUANTITY", name_facts.conflict, declared, "DECLARED", name_facts.evidence)
        # The name the person typed must not contradict the basis they chose.
        if declared == PriceBasis.PER_UNIT and name_facts.basis not in (None, PriceBasis.PER_UNIT):
            return fail(
                "BASIS_CONTRADICTS_NAME",
                f"You entered a price per tablet/unit, but the name mentions a quantity or pack ('{name_facts.evidence}'). "
                "Check whether the amount is for one unit or for the whole strip/pack.",
                declared, "DECLARED", name_facts.evidence,
            )
        if declared in (PriceBasis.PER_STRIP, PriceBasis.PER_PACK):
            size = upp if upp is not None else name_facts.units_per_pack
            if size is None:
                return fail("PACK_SIZE_MISSING", "The number of units in the strip/pack was not stated, so the price per unit cannot be worked out.", declared, "DECLARED")
            if not (size == size) or size <= 0 or size != int(size):
                return fail("INVALID_QUANTITY", "The number of units in the strip/pack must be a whole number above zero.", declared, "DECLARED")
            return BilledPrice(amount=amount_f, basis=declared, basis_source="DECLARED", units_per_pack=size, forms=forms, evidence=name_facts.evidence)
        if declared == PriceBasis.LINE_TOTAL:
            count = qty if qty is not None else name_facts.quantity
            if count is None:
                return fail("QUANTITY_MISSING", "The number of units billed was not stated, so the price per unit cannot be worked out.", declared, "DECLARED")
            if not (count == count) or count <= 0 or count != int(count):
                return fail("INVALID_QUANTITY", "The number of units billed must be a whole number above zero.", declared, "DECLARED")
            return BilledPrice(amount=amount_f, basis=declared, basis_source="DECLARED", quantity=count, forms=forms)
        return BilledPrice(amount=amount_f, basis=PriceBasis.PER_UNIT, basis_source="DECLARED", forms=forms)

    # No declaration: use what the text/document states.
    for f in (name_facts if name_text else None, doc):
        if f is None:
            continue
        if f.conflict:
            return fail("CONFLICTING_QUANTITY", f.conflict, source=_SOURCE_BY_FACT.get(f.source, "NONE"), evidence=f.evidence)
    chosen = None
    if name_text and name_facts.basis is not None:
        chosen = name_facts
    elif doc is not None and doc.basis is not None:
        chosen = doc
    if chosen is not None:
        source = _SOURCE_BY_FACT.get(chosen.source, "DOCUMENT_LINE")
        if chosen.basis in (PriceBasis.PER_STRIP, PriceBasis.PER_PACK):
            if chosen.units_per_pack is None:
                return fail(
                    "PACK_SIZE_MISSING",
                    "The document prices this medicine per strip/pack but does not say how many units the strip/pack holds.",
                    chosen.basis, source, chosen.evidence,
                )
            if chosen.units_per_pack <= 0:
                return fail("INVALID_QUANTITY", "The stated pack size is zero.", chosen.basis, source, chosen.evidence)
        if chosen.basis == PriceBasis.LINE_TOTAL and (chosen.quantity is None or chosen.quantity <= 0 or chosen.quantity != int(chosen.quantity)):
            return fail("INVALID_QUANTITY", "The stated quantity is not a whole number above zero.", chosen.basis, source, chosen.evidence)
        return BilledPrice(
            amount=amount_f, basis=chosen.basis, basis_source=source,
            units_per_pack=chosen.units_per_pack, quantity=chosen.quantity, forms=forms, evidence=chosen.evidence,
        )

    if allow_api_default:
        return BilledPrice(amount=amount_f, basis=PriceBasis.PER_UNIT, basis_source="API_DEFAULT", forms=forms)
    return fail(
        "BASIS_UNKNOWN",
        "The document does not say whether this amount is for one tablet, a strip, a pack or several units, "
        "so it cannot be compared with a per-unit ceiling price.",
    )


# --- Comparing with a per-unit ceiling ------------------------------------------------


class PriceComparison(BaseModel):
    status: ComparisonStatus
    billed_amount: float
    price_basis: PriceBasis
    basis_source: str
    price_basis_label: str
    basis_evidence: Optional[str] = None
    billed_unit_price: Optional[float] = None
    ceiling_unit_price: float
    unit_label: str
    is_overcharged: Optional[bool] = None
    deviation_percentage: Optional[float] = None
    reason_code: Optional[str] = None
    reason: Optional[str] = None


def _fmt_n(n: Optional[float]) -> str:
    return f"{n:g}" if n is not None else "?"


def basis_label(billed: BilledPrice, unit: str) -> str:
    if billed.basis == PriceBasis.PER_UNIT:
        return f"per {unit}"
    if billed.basis == PriceBasis.PER_STRIP:
        return f"per strip of {_fmt_n(billed.units_per_pack)}" if billed.units_per_pack else "per strip (size not stated)"
    if billed.basis == PriceBasis.PER_PACK:
        return f"per pack of {_fmt_n(billed.units_per_pack)}" if billed.units_per_pack else "per pack (size not stated)"
    if billed.basis == PriceBasis.LINE_TOTAL:
        return f"total for {_fmt_n(billed.quantity)} {unit}s" if billed.quantity else "line total (quantity not stated)"
    return "basis not stated"


def compare_with_ceiling(
    billed: BilledPrice, ceiling_per_unit: float, reference_form: Optional[str]
) -> PriceComparison:
    """Compares only like with like: a per-unit billed price against a per-unit ceiling,
    for the same dosage form. Anything else is CANNOT_COMPARE, with the reason."""
    unit = UNIT_NOUN.get(reference_form or "", "unit")
    common = dict(
        billed_amount=billed.amount,
        price_basis=billed.basis,
        basis_source=billed.basis_source,
        price_basis_label=basis_label(billed, unit),
        basis_evidence=billed.evidence,
        ceiling_unit_price=round(ceiling_per_unit, 2),
        unit_label=unit,
    )

    if billed.problem:
        return PriceComparison(status=ComparisonStatus.CANNOT_COMPARE, reason_code=billed.problem_code, reason=billed.problem, **common)

    if reference_form and billed.forms and reference_form not in billed.forms:
        return PriceComparison(
            status=ComparisonStatus.CANNOT_COMPARE,
            reason_code="DOSAGE_FORM_MISMATCH",
            reason=(
                f"The bill describes {' / '.join(_FORM_PHRASE.get(f, f) for f in billed.forms)} but the reference "
                f"ceiling is for {_FORM_PHRASE.get(reference_form, reference_form)}; different dosage forms have "
                "different ceiling prices."
            ),
            **common,
        )

    if billed.basis == PriceBasis.PER_UNIT:
        divisor = 1.0
    elif billed.basis in (PriceBasis.PER_STRIP, PriceBasis.PER_PACK):
        divisor = float(billed.units_per_pack or 0)
    elif billed.basis == PriceBasis.LINE_TOTAL:
        divisor = float(billed.quantity or 0)
    else:
        divisor = 0.0
    if divisor <= 0:
        return PriceComparison(
            status=ComparisonStatus.CANNOT_COMPARE,
            reason_code="BASIS_UNKNOWN",
            reason="The price per unit cannot be worked out from the information available.",
            **common,
        )

    unit_price = round(billed.amount / divisor, 2)
    ceiling = round(ceiling_per_unit, 2)
    over = unit_price > ceiling
    deviation = round(((unit_price - ceiling) / ceiling) * 100, 2) if over and ceiling > 0 else 0.0
    return PriceComparison(
        status=ComparisonStatus.COMPARED,
        billed_unit_price=unit_price,
        is_overcharged=over,
        deviation_percentage=deviation,
        **common,
    )
