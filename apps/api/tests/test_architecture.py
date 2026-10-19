"""Architecture fitness checks that do not need import-linter installed (ADR-018).

``lint-imports`` (CI backend job) enforces the import contracts in ``.importlinter``. These
tests make sure the contracts keep covering the code: a new top-level ``app`` module or a
new route module must be added to the matching contract, or it silently escapes it.
"""

import configparser
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
APP = REPO / "apps" / "api" / "app"
ENDPOINTS = APP / "api" / "v1" / "endpoints"


def _contracts() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(REPO / ".importlinter", encoding="utf-8")
    return parser


def _listed(section: str, key: str) -> set:
    return {line.strip() for line in _contracts()[section][key].splitlines() if line.strip()}


def test_every_app_module_below_http_is_covered():
    # Everything under app/ except the HTTP layer (app.api) and the entrypoint (app.main).
    modules = {
        f"app.{p.stem}" if p.is_file() else f"app.{p.name}"
        for p in APP.iterdir()
        if (p.suffix == ".py" and p.stem != "__init__") or (p.is_dir() and (p / "__init__.py").exists())
    } - {"app.api", "app.main"}
    covered = _listed("importlinter:contract:no-route-imports-below-http", "source_modules")
    missing = sorted(modules - covered)
    assert not missing, (
        f"{missing} are not in the 'no-route-imports-below-http' contract in .importlinter. "
        "Add them so they cannot start importing route modules."
    )


def test_every_route_module_is_in_the_independence_contract():
    routes = {f"app.api.v1.endpoints.{p.stem}" for p in ENDPOINTS.glob("*.py") if p.stem != "__init__"}
    covered = _listed("importlinter:contract:routes-independent", "modules")
    assert routes == covered, (
        f"Route modules and the 'routes-independent' contract differ: missing {sorted(routes - covered)}, "
        f"stale {sorted(covered - routes)}."
    )


def test_every_domain_package_is_framework_free_and_independent():
    packages = {p.name for p in (REPO / "packages").iterdir() if (p / p.name / "__init__.py").exists()}
    framework_free = _listed("importlinter:contract:packages-framework-free", "source_modules")
    independent = _listed("importlinter:contract:domain-modules-independent", "modules")
    assert packages == framework_free, f"packages-framework-free must list exactly {sorted(packages)}"
    assert independent == packages - {"kadi"}, "domain-modules-independent must list every module except kadi"


def test_route_modules_do_not_define_shared_use_cases_used_elsewhere():
    """No module outside app.api imports a route module (cheap textual backstop for the
    import contract, so it also runs where import-linter is not installed)."""
    offenders = []
    for path in APP.rglob("*.py"):
        if (APP / "api") in path.parents or path.name == "main.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "from app.api" in text or "import app.api" in text:
            offenders.append(str(path.relative_to(REPO)))
    assert not offenders, f"These modules import the HTTP layer: {offenders}"
