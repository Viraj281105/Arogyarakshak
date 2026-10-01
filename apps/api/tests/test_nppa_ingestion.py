import asyncio
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base
from app.models import NppaReferencePrice
from app.services.nppa_ingestion import ingest_nppa_reference_prices


PROJECT_ROOT = Path(__file__).resolve().parents[3]
NPPA_PDF = PROJECT_ROOT / "data" / "raw" / "NPPA.pdf"


def test_nppa_ingestion_inserts_and_updates_748_records() -> None:
    """NPPA ingestion should insert 748 records and remain idempotent."""

    async def run_test() -> None:
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
        )

        async with engine.begin() as connection:
            await connection.run_sync(
                NppaReferencePrice.__table__.create
            )

        SessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with SessionLocal() as session:
            inserted_count = await ingest_nppa_reference_prices(
                session,
                NPPA_PDF,
            )

            await session.commit()

            assert inserted_count == 748

            count_result = await session.execute(
                select(func.count()).select_from(
                    NppaReferencePrice
                )
            )

            assert count_result.scalar_one() == 748

            first_result = await session.execute(
                select(NppaReferencePrice).where(
                    NppaReferencePrice.sl_no == 1
                )
            )

            first_record = first_result.scalar_one()

            assert first_record.medicine == "5-aminosalicylic Acid"
            assert first_record.ceiling_price == 8.06

            second_run_count = await ingest_nppa_reference_prices(
                session,
                NPPA_PDF,
            )

            await session.commit()

            assert second_run_count == 748

            final_count_result = await session.execute(
                select(func.count()).select_from(
                    NppaReferencePrice
                )
            )

            assert final_count_result.scalar_one() == 748

        await engine.dispose()

    asyncio.run(run_test())