#!/usr/bin/env python
"""Devanagari OCR baseline (Wave 2 stream A; phase4-expansion-plan.md workstream A, step 1).

Rasterises the PDFs in ``--docs`` (default: ``data/raw/devanagari_public_docs``) and runs EasyOCR
twice per page, once with ``["en"]`` (today's setting) and once with ``["hi", "mr", "en"]``. For
each page and configuration it records the number of segments, a confidence histogram, latency
and, per configuration, the peak process memory. The result is one JSON file written OUTSIDE the
repository (``--out`` is refused when it resolves inside the git work tree).

What this is NOT: there is no reference transcription yet, so no WER/CER and no accuracy claim
is made or computable here. Confidence is the engine's own score, not correctness. Segment text is
not written to the report (counts and scores only) unless ``--include-text`` is passed.

Models must already be cached (EASYOCR_MODULE_PATH); this script downloads nothing: it builds
readers with ``download_enabled=False`` so a missing weight fails instead of fetching.

Usage:
    python scripts/devanagari_ocr_baseline.py --out D:/scratch/ocr_baseline.json --max-pages 1
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCS_RELATIVE = Path("data") / "raw" / "devanagari_public_docs"
CONFIGS: Tuple[Tuple[str, ...], ...] = (("en",), ("hi", "mr", "en"))
REVIEW_THRESHOLD = 0.5  # the low-confidence review threshold used by the OCR trust gate
HISTOGRAM_BINS = 10


def peak_memory_mb() -> Optional[float]:
    """Peak resident memory of this process in MB, or None when it cannot be read."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = Counters()
            counters.cb = ctypes.sizeof(Counters)
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(Counters),
                wintypes.DWORD,
            ]
            if not psapi.GetProcessMemoryInfo(
                kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
            ):
                return None
            return round(counters.PeakWorkingSetSize / (1024 * 1024), 1)
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # ru_maxrss is KB on Linux, bytes on macOS.
        return round(peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024, 1)
    except Exception:
        return None


def confidence_histogram(confidences: Iterable[float], bins: int = HISTOGRAM_BINS) -> List[int]:
    """Counts of confidences in ``bins`` equal-width buckets over [0, 1]; 1.0 lands in the last."""
    counts = [0] * bins
    for value in confidences:
        index = min(bins - 1, max(0, int(float(value) * bins)))
        counts[index] += 1
    return counts


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _has_pdfs(path: Path) -> bool:
    return path.is_dir() and any(path.rglob("*.pdf"))


def default_docs_dir() -> Path:
    """The corpus in this checkout when it holds PDFs, else the main checkout's (the PDFs
    are git-ignored, so a linked worktree has the README but not the files)."""
    here = REPO_ROOT / DEFAULT_DOCS_RELATIVE
    if _has_pdfs(here):
        return here
    git_file = REPO_ROOT / ".git"
    if git_file.is_file():  # linked worktree: ".git" is a file "gitdir: <main>/.git/worktrees/x"
        text = git_file.read_text(encoding="utf-8", errors="ignore").strip()
        if text.startswith("gitdir:"):
            gitdir = Path(text.split(":", 1)[1].strip())
            if "worktrees" in gitdir.parts:
                candidate = gitdir.parents[2] / DEFAULT_DOCS_RELATIVE
                if _has_pdfs(candidate):
                    return candidate
    return here


def rasterise_pdf(path: Path, dpi: int, max_pages: int) -> List[Tuple[int, Any]]:
    """In-memory BGR arrays for up to ``max_pages`` pages: ``[(page_number, ndarray), ...]``."""
    import fitz
    import numpy as np

    pages = []
    with fitz.open(path) as doc:
        for index, page in enumerate(doc):
            if index >= max_pages:
                break
            scale = dpi / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            pages.append((index + 1, np.ascontiguousarray(rgb[:, :, ::-1])))
    return pages


def default_reader_factory(languages: Sequence[str]):
    import easyocr

    return easyocr.Reader(list(languages), gpu=False, download_enabled=False)


def measure_page(reader: Any, image: Any, include_text: bool = False) -> Dict[str, Any]:
    started = time.perf_counter()
    results = reader.readtext(image)
    latency = time.perf_counter() - started
    confidences = [float(r[2]) for r in results if len(r) >= 3]
    record: Dict[str, Any] = {
        "segments": len(results),
        "confidence_histogram": confidence_histogram(confidences),
        "mean_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
        "below_review_threshold": sum(1 for c in confidences if c < REVIEW_THRESHOLD),
        "latency_s": round(latency, 3),
    }
    if include_text:
        record["texts"] = [r[1] for r in results]
    return record


def run_baseline(
    pdfs: Sequence[Path],
    configs: Sequence[Sequence[str]] = CONFIGS,
    dpi: int = 200,
    max_pages: int = 1,
    reader_factory: Callable[[Sequence[str]], Any] = default_reader_factory,
    include_text: bool = False,
    rasterise: Callable[[Path, int, int], List[Tuple[int, Any]]] = rasterise_pdf,
) -> Dict[str, Any]:
    pages_by_doc = {pdf.name: rasterise(pdf, dpi, max_pages) for pdf in pdfs}
    runs = []
    for languages in configs:
        load_started = time.perf_counter()
        reader = reader_factory(languages)
        load_s = round(time.perf_counter() - load_started, 3)
        records = []
        for name, pages in pages_by_doc.items():
            for page_number, image in pages:
                record = measure_page(reader, image, include_text=include_text)
                record.update({"document": name, "page": page_number})
                records.append(record)
        runs.append(
            {
                "languages": list(languages),
                "model_load_s": load_s,
                # Peak working set of the whole process so far: monotone, so the later
                # configuration's figure includes the earlier one's memory.
                "peak_memory_mb_so_far": peak_memory_mb(),
                "pages": records,
            }
        )
    return {
        "kind": "devanagari_ocr_baseline",
        "note": (
            "No reference transcription exists: no WER/CER or accuracy is reported. "
            "Confidence is the engine's own score."
        ),
        "dpi": dpi,
        "max_pages_per_document": max_pages,
        "review_threshold": REVIEW_THRESHOLD,
        "device": "cpu",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "documents": {name: len(pages) for name, pages in pages_by_doc.items()},
        "runs": runs,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--docs", type=Path, default=None, help="directory containing the PDFs")
    parser.add_argument("--out", type=Path, required=True, help="JSON output path (outside git)")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--max-pages", type=int, default=1, help="pages per document (CPU OCR is slow)")
    parser.add_argument("--include-text", action="store_true", help="also write recognised text")
    args = parser.parse_args(argv)

    out = args.out.resolve()
    if _inside(out, REPO_ROOT):
        print(f"refusing to write inside the repository: {out}", file=sys.stderr)
        return 2
    docs = args.docs or default_docs_dir()
    pdfs = sorted(docs.rglob("*.pdf")) if docs.is_dir() else []
    if not pdfs:
        print(f"no PDFs found under {docs}", file=sys.stderr)
        return 2

    report = run_baseline(
        pdfs, dpi=args.dpi, max_pages=args.max_pages, include_text=args.include_text
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for run in report["runs"]:
        pages = run["pages"]
        total = sum(p["latency_s"] for p in pages)
        print(
            f"{'+'.join(run['languages'])}: {len(pages)} page(s), {total:.1f}s OCR, "
            f"peak memory {run['peak_memory_mb_so_far']} MB, load {run['model_load_s']}s"
        )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
