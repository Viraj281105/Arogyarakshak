"""
Historical dispute-outcome datasets for IRDAI appeal outcome estimation (#90).

**No such dataset ships with ArogyaRakshak.** An outcome estimate is only as honest as the
historical results behind it, and the repository holds none: the CSVs under ``data/raw``
that look related are 1–2 row mock scaffolds, not dispute records. Until a real dataset is
added, every estimate is ``INSUFFICIENT_EVIDENCE``.

To register one, place a JSON file in ``billnyay/data/dispute_outcomes/`` matching
``DisputeOutcomeDataset``. Provenance is mandatory (publisher, source URL, retrieval date,
licence), and datasets marked ``is_synthetic`` are refused outside evaluation code.
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("BillNyay.Outcome.Dataset")

Forum = Literal["insurer_grievance", "insurance_ombudsman", "consumer_commission"]
Outcome = Literal["ALLOWED", "PARTIALLY_ALLOWED", "DISMISSED", "WITHDRAWN_OR_SETTLED"]

FAVOURABLE_OUTCOMES = frozenset({"ALLOWED", "PARTIALLY_ALLOWED"})
UNKNOWN_RESULT_OUTCOMES = frozenset({"WITHDRAWN_OR_SETTLED"})

DATASET_DIR = Path(__file__).resolve().parent.parent / "data" / "dispute_outcomes"


class DisputeOutcomeRecord(BaseModel):
    dispute_category: str = Field(..., min_length=1, max_length=64)
    forum: Forum
    outcome: Outcome
    decision_year: int = Field(..., ge=2000, le=2100)


class DatasetProvenance(BaseModel):
    publisher: str = Field(..., min_length=3)
    source_url: str = Field(..., pattern=r"^https?://\S+$")
    retrieved_on: date
    license: str = Field(..., min_length=2)
    description: str = Field(..., min_length=10)


class DisputeOutcomeDataset(BaseModel):
    name: str = Field(..., min_length=3)
    is_synthetic: bool
    provenance: DatasetProvenance
    records: List[DisputeOutcomeRecord] = Field(..., min_length=1)


def load_dataset(path: Path) -> DisputeOutcomeDataset:
    """Loads and validates one dataset file. Raises ValueError/ValidationError if invalid."""
    return DisputeOutcomeDataset.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def load_registered_dataset(directory: Path = DATASET_DIR) -> Optional[DisputeOutcomeDataset]:
    """The first valid, non-synthetic dataset in `directory`, or None. Invalid or synthetic
    files are logged and never used for estimates."""
    if not directory.is_dir():
        return None
    for path in sorted(directory.glob("*.json")):
        try:
            dataset = load_dataset(path)
        except (ValueError, ValidationError, OSError):
            logger.warning("Ignoring invalid dispute-outcome dataset file: %s", path.name)
            continue
        if dataset.is_synthetic:
            logger.warning("Ignoring synthetic dispute-outcome dataset for estimates: %s", path.name)
            continue
        return dataset
    return None
