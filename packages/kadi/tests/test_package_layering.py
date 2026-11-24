"""Layering guards for the ``kadi`` -> ``kadi.llm`` import cycle fix (ADR-027).

``kadi.llm`` once imported ``kadi.redaction`` (a root-level module) while root modules such
as ``kadi.extraction`` import ``kadi.llm``: a package-level cycle found by the Archify Code
Analysis of ``packages/kadi``. ``kadi.redaction`` now lives in the dependency-free
``kadi.privacy`` package. These tests fail if either direction of that layering regresses;
``.importlinter`` enforces the same rule for the whole repository in CI.

The same report found ``kadi`` <-> ``kadi.ocr``: ``kadi/__init__`` imported ``kadi.ocr.ocr_parser``
eagerly while that module imports Kadi root modules. ``parse_document`` is now re-exported lazily
(PEP 562); the last three tests pin that behaviour.
"""

import ast
import subprocess
import sys
from pathlib import Path

import kadi
import kadi.privacy.redaction
import kadi.redaction

KADI_ROOT = Path(kadi.__file__).resolve().parent


def _kadi_imports(path: Path) -> set[str]:
    """Every ``kadi...`` module a file imports, relative imports resolved to absolute."""
    package = ".".join(path.relative_to(KADI_ROOT.parent).with_suffix("").parts[:-1])
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - (node.level - 1)]
                module = ".".join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ""
            found.add(module)
    return {name for name in found if name == "kadi" or name.startswith("kadi.")}


def test_redaction_alias_is_the_privacy_implementation():
    assert kadi.redaction.redact_pii is kadi.privacy.redaction.redact_pii
    assert kadi.redaction.contains_direct_identifier is kadi.privacy.redaction.contains_direct_identifier
    assert kadi.redaction.REDACTION_MARK is kadi.privacy.redaction.REDACTION_MARK
    assert kadi.redaction.__all__ == ["REDACTION_MARK", "contains_direct_identifier", "redact_pii"]


def test_privacy_package_imports_nothing_from_kadi():
    offenders = {
        str(path.relative_to(KADI_ROOT)): sorted(_kadi_imports(path))
        for path in (KADI_ROOT / "privacy").glob("*.py")
        if _kadi_imports(path)
    }
    assert offenders == {}


def test_llm_package_only_imports_llm_and_privacy():
    allowed = ("kadi.llm", "kadi.privacy")
    offenders = {}
    for path in (KADI_ROOT / "llm").glob("*.py"):
        bad = sorted(
            name for name in _kadi_imports(path)
            if not any(name == ok or name.startswith(ok + ".") for ok in allowed)
        )
        if bad:
            offenders[str(path.relative_to(KADI_ROOT))] = bad
    assert offenders == {}


def _run_python(code: str) -> str:
    """Run ``code`` in a fresh interpreter so ``sys.modules`` is not polluted by other tests."""
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def test_importing_kadi_does_not_load_the_ocr_module():
    """``kadi.ocr`` imports Kadi root modules, so the package root must not import it eagerly."""
    out = _run_python("import sys, kadi; print('kadi.ocr.ocr_parser' in sys.modules)")
    assert out == "False"


def test_parse_document_is_still_exported_from_the_package_root():
    out = _run_python(
        "import kadi\n"
        "from kadi import parse_document\n"
        "import kadi.ocr.ocr_parser as m\n"
        "print(parse_document is m.parse_document and kadi.parse_document is m.parse_document"
        " and 'parse_document' in dir(kadi) and 'parse_document' in kadi.__all__)"
    )
    assert out == "True"


def test_unknown_package_attribute_still_raises_attribute_error():
    assert not hasattr(kadi, "definitely_not_a_kadi_export")
