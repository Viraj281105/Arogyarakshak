"""
NPPA Schedule-I database ingestion service.

Parses the official NPPA Schedule-I PDF and upserts the
structured ceiling-price records into the API database.
"""

from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NppaReferencePrice
from dawacheck.nppa.parser import parse_nppa_pdf


class NppaReferenceRecord(BaseModel):
    """Validated NPPA reference record before database insertion."""

    sl_no: PositiveInt
    medicine: str = Field(min_length=1)
    dosage_form_strength: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    ceiling_price: PositiveFloat
    existing_so_no: str = Field(min_length=1)
    existing_so_date: str = Field(min_length=1)


def _validate_records(
    records: Sequence[dict[str, str]],
) -> list[NppaReferenceRecord]:
    """Validate parser output using Pydantic."""

    validated: list[NppaReferenceRecord] = []

    for record in records:
        validated.append(
            NppaReferenceRecord(
                sl_no=int(record["sl_no"]),
                medicine=record["medicine"],
                dosage_form_strength=record["dosage_form_strength"],
                unit=record["unit"],
                ceiling_price=float(record["ceiling_price"]),
                existing_so_no=record["existing_so_no"],
                existing_so_date=record["existing_so_date"],
            )
        )

    return validated


async def ingest_nppa_reference_prices(
    session: AsyncSession,
    pdf_path: str | Path,
) -> int:
    """
    Parse an NPPA PDF and upsert all reference prices.

    Returns:
        Number of NPPA records processed.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"NPPA PDF not found: {pdf_path}"
        )

    records = parse_nppa_pdf(pdf_path)
    validated_records = _validate_records(records)

    if not validated_records:
        raise ValueError("NPPA PDF produced no reference records.")

    result = await session.execute(
        select(NppaReferencePrice)
    )

    existing_records = {
        record.sl_no: record
        for record in result.scalars().all()
    }

    for record in validated_records:
        database_record = existing_records.get(record.sl_no)

        if database_record is None:
            database_record = NppaReferencePrice(
                id=f"nppa-2025-{record.sl_no:03d}",
                sl_no=record.sl_no,
                medicine=record.medicine,
                dosage_form_strength=record.dosage_form_strength,
                unit=record.unit,
                ceiling_price=record.ceiling_price,
                existing_so_no=record.existing_so_no,
                existing_so_date=record.existing_so_date,
            )

            session.add(database_record)
            continue

        database_record.medicine = record.medicine
        database_record.dosage_form_strength = (
            record.dosage_form_strength
        )
        database_record.unit = record.unit
        database_record.ceiling_price = record.ceiling_price
        database_record.existing_so_no = record.existing_so_no
        database_record.existing_so_date = record.existing_so_date

    await session.flush()

    return len(validated_records)