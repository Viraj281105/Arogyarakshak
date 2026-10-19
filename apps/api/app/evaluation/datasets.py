"""Loader for the labelled evaluation datasets (JSONL, first line ``{"_meta": {...}}``)."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "evaluation"


class DatasetError(ValueError):
    pass


def load_dataset(path: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Returns (meta, rows). Refuses any dataset that is not explicitly flagged synthetic,
    so a real-looking number can never be produced from an unlabelled file."""
    meta = None
    rows: List[Dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "_meta" in obj:
                meta = obj["_meta"]
            else:
                rows.append(obj)
    if meta is None:
        raise DatasetError(f"{path}: first line must be a _meta record")
    if meta.get("synthetic") is not True:
        raise DatasetError(f"{path}: _meta.synthetic must be true")
    ids = [r.get("id") for r in rows]
    if len(set(ids)) != len(ids):
        raise DatasetError(f"{path}: duplicate row ids")
    return meta, rows
