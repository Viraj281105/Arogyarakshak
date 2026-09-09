#!/usr/bin/env python3
"""
ArogyaRakshak CI Guardrails & Architectural Invariants Scanner
Validates repository invariants, BYOD zero-retention compliance,
model grounding, package hygiene, and database naming conventions.
"""

import os
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Prohibited deprecated models per AGENTS.md
PROHIBITED_MODELS = [
    "llama3-70b",
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
]

# Mandatory domain packages
REQUIRED_PACKAGES = [
    "kadi",
    "billnyay",
    "daavisetu",
    "bimanyay",
    "schemesetu",
    "dawacheck",
]

# Mandatory table prefixes per AGENTS.md
ALLOWED_TABLE_PREFIXES = (
    "kadi_",
    "billnyay_",
    "daavisetu_",
    "bimanyay_",
    "schemesetu_",
    "dawacheck_",
)

# Directories that must NEVER exist (BYOD Zero-Retention)
FORBIDDEN_PERSISTENT_DIRS = [
    "uploads",
    "storage/documents",
    "data/patient_docs",
    "data/uploads",
]

# File scan skip lists
IGNORE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
}


def check_byod_zero_retention() -> list[str]:
    """Verify no persistent patient document directories exist."""
    errors = []
    for d in FORBIDDEN_PERSISTENT_DIRS:
        target = ROOT_DIR / d
        if target.exists() and target.is_dir():
            errors.append(f"BYOD Invariant Violation: Forbidden persistent directory exists: {d}")
    return errors


def check_model_grounding() -> list[str]:
    """Scan source code for forbidden deprecated Groq models."""
    errors = []
    # Pattern to detect string literal usage of prohibited models
    # Exclude AGENTS.md, PROJECT_CONTEXT.md, and ci_guardrails.py itself
    skip_files = {"AGENTS.md", "PROJECT_CONTEXT.md", "ci_guardrails.py", "config.py"}

    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            if file in skip_files:
                continue
            if not file.endswith((".py", ".ts", ".tsx", ".json", ".yml", ".yaml")):
                continue

            file_path = Path(root) / file
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for model in PROHIBITED_MODELS:
                    # Match model enclosed in quotes or as word boundary
                    if f'"{model}"' in content or f"'{model}'" in content or f"`{model}`" in content:
                        rel_path = file_path.relative_to(ROOT_DIR)
                        errors.append(
                            f"Model Grounding Violation: Prohibited model '{model}' found in {rel_path}"
                        )
            except Exception as e:
                errors.append(f"Failed to read {file_path}: {e}")
    return errors


def check_package_hygiene() -> list[str]:
    """Validate monorepo package structure and lowercase naming."""
    errors = []
    packages_dir = ROOT_DIR / "packages"
    if not packages_dir.exists():
        return ["Package Hygiene: 'packages' directory does not exist!"]

    found_packages = {p.name for p in packages_dir.iterdir() if p.is_dir() and not p.name.startswith(".")}

    for req in REQUIRED_PACKAGES:
        if req not in found_packages:
            errors.append(f"Package Hygiene: Required domain package '{req}' missing in packages/")

    for pkg in found_packages:
        if not pkg.islower():
            errors.append(f"Package Hygiene: Package '{pkg}' is not strictly lowercase!")
        has_config = (packages_dir / pkg / "pyproject.toml").exists() or (packages_dir / pkg / "setup.py").exists()
        if not has_config:
            errors.append(f"Package Hygiene: Package '{pkg}' is missing pyproject.toml or setup.py!")

    return errors


def check_database_table_prefixes() -> list[str]:
    """Verify all database models adhere to module prefix conventions."""
    errors = []
    models_file = ROOT_DIR / "apps" / "api" / "app" / "models.py"
    if not models_file.exists():
        return ["Database Models: 'apps/api/app/models.py' not found!"]

    content = models_file.read_text(encoding="utf-8")
    # Find all __tablename__ = "..."
    matches = re.findall(r'__tablename__\s*=\s*["\']([^"\']+)["\']', content)
    for table_name in matches:
        if not any(table_name.startswith(prefix) for prefix in ALLOWED_TABLE_PREFIXES):
            errors.append(
                f"Database Model Convention: Table '{table_name}' does not start with an allowed prefix: "
                f"{ALLOWED_TABLE_PREFIXES}"
            )
    return errors


def check_secret_patterns() -> list[str]:
    """Scan for accidental real API keys or tokens committed to git."""
    errors = []
    # Match standard Groq API key patterns (gsk_...)
    groq_key_pattern = re.compile(r"gsk_[A-Za-z0-9]{30,}")

    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            if file in {"ci_guardrails.py", ".env.example"}:
                continue
            if not file.endswith((".py", ".ts", ".tsx", ".json", ".md", ".env")):
                continue

            file_path = Path(root) / file
            # Allow .env if it only has placeholders
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for match in groq_key_pattern.finditer(content):
                    rel_path = file_path.relative_to(ROOT_DIR)
                    matched_str = match.group()
                    if "your_groq_api_key" not in matched_str and "placeholder" not in matched_str:
                        errors.append(f"Security: Potential real Groq API key detected in {rel_path}")
            except Exception as e:
                errors.append(f"Failed to scan {file_path}: {e}")
    return errors


def main() -> int:
    print("=" * 60)
    print("  ArogyaRakshak CI Guardrails & Invariant Verification")
    print("=" * 60)

    all_errors = []

    print("[1/5] Checking BYOD Zero-Retention Invariants...")
    byod_errors = check_byod_zero_retention()
    if byod_errors:
        all_errors.extend(byod_errors)
        print(f"  ❌ Failed with {len(byod_errors)} violation(s)")
    else:
        print("  ✓ PASSED: Zero persistent document directories.")

    print("[2/5] Checking Model Grounding Guard...")
    model_errors = check_model_grounding()
    if model_errors:
        all_errors.extend(model_errors)
        print(f"  ❌ Failed with {len(model_errors)} violation(s)")
    else:
        print("  ✓ PASSED: No prohibited deprecated models.")

    print("[3/5] Checking Monorepo Package Hygiene...")
    pkg_errors = check_package_hygiene()
    if pkg_errors:
        all_errors.extend(pkg_errors)
        print(f"  ❌ Failed with {len(pkg_errors)} violation(s)")
    else:
        print(f"  ✓ PASSED: All {len(REQUIRED_PACKAGES)} packages lowercase & valid.")

    print("[4/5] Checking Database Table Prefix Conventions...")
    db_errors = check_database_table_prefixes()
    if db_errors:
        all_errors.extend(db_errors)
        print(f"  ❌ Failed with {len(db_errors)} violation(s)")
    else:
        print("  ✓ PASSED: All ORM tables strictly prefixed by module.")

    print("[5/5] Scanning for Accidental API Key Leaks...")
    sec_errors = check_secret_patterns()
    if sec_errors:
        all_errors.extend(sec_errors)
        print(f"  ❌ Failed with {len(sec_errors)} violation(s)")
    else:
        print("  ✓ PASSED: No sensitive API keys detected.")

    print("=" * 60)
    if all_errors:
        print(f"TOTAL VIOLATIONS: {len(all_errors)}")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print("ALL ARCHITECTURAL INVARIANTS & SECURITY CHECKS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
