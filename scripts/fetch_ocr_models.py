#!/usr/bin/env python
"""Fetch the EasyOCR model weights (operator-run; never called by the application).

The API builds its OCR readers with ``download_enabled=False``: a request must never trigger a
network download. Run this script ONCE at image build time (or on a maintenance host) with
network access to the official EasyOCR release host, then bake/mount the resulting directory:

    python scripts/fetch_ocr_models.py --download --languages en,hi,mr --dest /opt/easyocr/model

and set ``EASYOCR_MODULE_PATH=/opt/easyocr`` (the application reads ``$EASYOCR_MODULE_PATH/model``).
Nothing is downloaded unless ``--download`` is passed. Weights are ~15 MB (en), ~83 MB (detector) and
~215 MB (Devanagari, shared by hi and mr).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable, List, Optional, Sequence

SUPPORTED = ("en", "hi", "mr")


def default_reader_factory(languages: Sequence[str], dest: Path):
    import easyocr

    return easyocr.Reader(
        list(languages), gpu=False, download_enabled=True, model_storage_directory=str(dest)
    )


def fetch(
    languages: Sequence[str],
    dest: Path,
    reader_factory: Callable[[Sequence[str], Path], object] = default_reader_factory,
) -> List[str]:
    """Download (via EasyOCR) the weights for ``languages`` into ``dest``; return the file names."""
    unknown = [c for c in languages if c not in SUPPORTED]
    if unknown:
        raise ValueError(f"unsupported language code(s): {', '.join(unknown)}")
    dest.mkdir(parents=True, exist_ok=True)
    reader_factory(tuple(languages), dest)
    return sorted(p.name for p in dest.glob("*.pth"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--languages", default="en,hi,mr")
    parser.add_argument("--dest", type=Path, default=None, help="default: $EASYOCR_MODULE_PATH/model")
    parser.add_argument("--download", action="store_true", help="required: confirm the network download")
    args = parser.parse_args(argv)

    if not args.download:
        print("refusing to download without --download (see --help)", file=sys.stderr)
        return 2
    dest = args.dest
    if dest is None:
        base = os.environ.get("EASYOCR_MODULE_PATH", "").strip()
        if not base:
            print("pass --dest or set EASYOCR_MODULE_PATH", file=sys.stderr)
            return 2
        dest = Path(base) / "model"
    languages = [c.strip().lower() for c in args.languages.split(",") if c.strip()]
    try:
        files = fetch(languages, dest)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"models in {dest}: {', '.join(files) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
