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


def check_cpu_only_torch_pin() -> list[str]:
    """EasyOCR (via packages/kadi) transitively pulls torch/torchvision. Without a
    pinned CPU-only build, pip resolves the default CUDA wheel — ~2.8 GB of unused
    nvidia-*/triton packages, since packages/kadi/kadi/ocr/ocr_parser.py always runs
    EasyOCR with gpu=False. This previously exhausted CI runner disk (see #141).
    Guards against the constraints file being removed or unwired from either the
    Dockerfile or CI without anyone noticing until the next disk-exhaustion failure.
    """
    errors = []
    constraints_file = ROOT_DIR / "apps" / "api" / "constraints-cpu.txt"
    if not constraints_file.exists():
        return ["CPU Torch Pin: apps/api/constraints-cpu.txt is missing."]

    constraints_content = constraints_file.read_text(encoding="utf-8")
    if "download.pytorch.org/whl/cpu" not in constraints_content:
        errors.append("CPU Torch Pin: constraints-cpu.txt no longer points at the PyTorch CPU wheel index.")
    if not re.search(r"^torch==\S+\+cpu\s*$", constraints_content, re.MULTILINE):
        errors.append("CPU Torch Pin: constraints-cpu.txt no longer pins a torch==<version>+cpu build.")
    if not re.search(r"^torchvision==\S+\+cpu\s*$", constraints_content, re.MULTILINE):
        errors.append("CPU Torch Pin: constraints-cpu.txt no longer pins a torchvision==<version>+cpu build.")

    dockerfile = ROOT_DIR / "apps" / "api" / "Dockerfile"
    if dockerfile.exists():
        docker_content = dockerfile.read_text(encoding="utf-8")
        if "constraints-cpu.txt" not in docker_content:
            errors.append("CPU Torch Pin: apps/api/Dockerfile no longer installs Kadi with -c constraints-cpu.txt.")
    else:
        errors.append("CPU Torch Pin: apps/api/Dockerfile not found.")

    ci_workflow = ROOT_DIR / ".github" / "workflows" / "ci.yml"
    if ci_workflow.exists():
        ci_content = ci_workflow.read_text(encoding="utf-8")
        if "constraints-cpu.txt" not in ci_content:
            errors.append("CPU Torch Pin: .github/workflows/ci.yml backend job no longer uses constraints-cpu.txt.")
    else:
        errors.append("CPU Torch Pin: .github/workflows/ci.yml not found.")

    return errors


def check_docker_postgres_binding() -> list[str]:
    """Postgres must never bind to every interface on the host (P0-5): the `api`
    service reaches it over the internal Docker network by service name
    (DATABASE_URL=...@postgres:5432/...), so a host port mapping is only for local
    debugging and must be localhost-only. Guards against docker-compose.yml regressing
    to an unbound "5432:5432" (which binds 0.0.0.0) without anyone noticing."""
    errors = []
    compose_file = ROOT_DIR / "docker-compose.yml"
    if not compose_file.exists():
        return ["Postgres Binding: docker-compose.yml is missing."]

    content = compose_file.read_text(encoding="utf-8")
    if re.search(r'^\s*-\s*"5432:5432"\s*$', content, re.MULTILINE):
        errors.append(
            'Postgres Binding: docker-compose.yml binds "5432:5432" (all interfaces). '
            'Use "127.0.0.1:5432:5432" or remove the port mapping entirely.'
        )
    return errors


def main() -> int:
    print("=" * 60)
    print("  ArogyaRakshak CI Guardrails & Invariant Verification")
    print("=" * 60)

    all_errors = []

    print("[1/7] Checking BYOD Zero-Retention Invariants...")
    byod_errors = check_byod_zero_retention()
    if byod_errors:
        all_errors.extend(byod_errors)
        print(f"  ❌ Failed with {len(byod_errors)} violation(s)")
    else:
        print("  ✓ PASSED: Zero persistent document directories.")

    print("[2/7] Checking Model Grounding Guard...")
    model_errors = check_model_grounding()
    if model_errors:
        all_errors.extend(model_errors)
        print(f"  ❌ Failed with {len(model_errors)} violation(s)")
    else:
        print("  ✓ PASSED: No prohibited deprecated models.")

    print("[3/7] Checking Monorepo Package Hygiene...")
    pkg_errors = check_package_hygiene()
    if pkg_errors:
        all_errors.extend(pkg_errors)
        print(f"  ❌ Failed with {len(pkg_errors)} violation(s)")
    else:
        print(f"  ✓ PASSED: All {len(REQUIRED_PACKAGES)} packages lowercase & valid.")

    print("[4/7] Checking Database Table Prefix Conventions...")
    db_errors = check_database_table_prefixes()
    if db_errors:
        all_errors.extend(db_errors)
        print(f"  ❌ Failed with {len(db_errors)} violation(s)")
    else:
        print("  ✓ PASSED: All ORM tables strictly prefixed by module.")

    print("[5/7] Scanning for Accidental API Key Leaks...")
    sec_errors = check_secret_patterns()
    if sec_errors:
        all_errors.extend(sec_errors)
        print(f"  ❌ Failed with {len(sec_errors)} violation(s)")
    else:
        print("  ✓ PASSED: No sensitive API keys detected.")

    print("[6/7] Checking CPU-Only PyTorch Pin (Kadi/EasyOCR)...")
    torch_errors = check_cpu_only_torch_pin()
    if torch_errors:
        all_errors.extend(torch_errors)
        print(f"  ❌ Failed with {len(torch_errors)} violation(s)")
    else:
        print("  ✓ PASSED: torch/torchvision pinned to CPU wheels in Dockerfile & CI.")

    print("[7/7] Checking Postgres Is Not Bound to All Interfaces...")
    pg_errors = check_docker_postgres_binding()
    if pg_errors:
        all_errors.extend(pg_errors)
        print(f"  ❌ Failed with {len(pg_errors)} violation(s)")
    else:
        print("  ✓ PASSED: Postgres port mapping is localhost-only.")

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
