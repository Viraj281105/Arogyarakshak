"""
Turn one document's OCR line items and extraction result into entity-resolution mentions.

Pure (no database, no network): split out of ``case_ingestion._run_pipeline``
(restructuring, 2026-10) so the decision about what is stored from a document — and what is
deliberately not (the patient's name; the raw text beyond a redacted excerpt) — reads and
tests on its own.
"""

from typing import Any, Dict, List, Tuple

from dawacheck.price_basis import annotate_medicine_price_facts
from kadi.line_items import ground_medicine_source_lines
from kadi.redaction import redact_pii

from app.kadi_resolution import MentionInput


def build_mentions(line_items: List[Dict[str, Any]], extracted: Any, text: str, filename: str) -> Tuple[List[MentionInput], float]:
    """(mentions, total of the OCR bill lines). ``extracted`` is a kadi ExtractedEntities;
    its medicines are annotated in place with grounded quantity/price facts."""
    mentions: List[MentionInput] = []
    total_cost = 0.0

    # 1. Billing line items from OCR. Never merged by entity resolution: two
    # identical bill lines are separate charges (possible double billing).
    for item in line_items:
        mentions.append(
            MentionInput(
                entity_type="billing_item",
                name=item["item"],
                value=str(item["charged"]),
                meta={"charged": item["charged"], "source_file": filename},
            )
        )
        total_cost += item["charged"]

    # 2. Structured clinical entities from extraction agent
    extraction_meta = {"source_file": filename, "source": "kadi_extraction"}
    if extracted.hospital_name:
        mentions.append(
            MentionInput("hospital", extracted.hospital_name, extracted.hospital_name, dict(extraction_meta))
        )

    # The patient's name is deliberately NOT persisted. It is a direct identifier,
    # ADR-003 limits stored records to de-identified clinical metadata, and no
    # module reads it: DaaviSetu takes patient_name from its own request payload.
    # It stays available in-memory to the extraction result for this request only.

    if extracted.diagnosis:
        mentions.append(
            MentionInput("diagnosis", extracted.diagnosis, extracted.diagnosis, dict(extraction_meta))
        )

    # Entity resolution (app.kadi_resolution) blocks by type: a procedure is only
    # ever compared with procedures. The old exact-name check compared against
    # every queued entity, so OCR's same-named billing_item line silently
    # suppressed the procedure entity BillNyay's ICD audit (#64) needs.
    for proc in extracted.procedures:
        proc_name = proc.get("name")
        if proc_name:
            mentions.append(
                MentionInput("procedure", proc_name, str(proc.get("amount", 0.0)), {**proc, **extraction_meta})
            )

    # What the document says about each medicine's quantity or pack ("strip of 15",
    # "Qty 10", a "Rate per tablet" column) is read now, while the text is still in
    # memory, so DawaCheck can later compare like with like — or refuse to. Only the
    # derived facts and a short matched snippet are stored, never the line itself.
    ground_medicine_source_lines(text, extracted.medicines)
    annotate_medicine_price_facts(extracted.medicines, text)
    for med in extracted.medicines:
        med_name = med.get("name")
        if med_name:
            mentions.append(
                MentionInput("medicine", med_name, str(med.get("cost", 0.0)), {**med, **extraction_meta})
            )

    # Document excerpt, with direct identifiers stripped. BillNyay's appeal
    # pipeline reads this to recover denial codes, insurer reasons and policy
    # clauses, so it cannot be dropped — but it must not retain the patient's
    # name, contact details or government IDs.
    excerpt_meta: Dict[str, Any] = {"source_file": filename, "redacted": True}
    # P0-4: an LLM-returned extraction is never trusted merely for being valid
    # JSON — surface any integrity warnings (possible prompt-injection phrasing,
    # or an LLM total_amount that could not be reconciled against a deterministic
    # reading of the same text) on the persisted record rather than dropping them.
    if extracted.extraction_warnings:
        excerpt_meta["extraction_warnings"] = extracted.extraction_warnings
    mentions.append(
        MentionInput(
            "document_text",
            "Document Text Excerpt",
            redact_pii(text)[:1000],
            excerpt_meta,
        )
    )
    return mentions, total_cost
