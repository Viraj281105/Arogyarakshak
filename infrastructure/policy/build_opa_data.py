"""Builds the single OPA data document the Rego fixture tests read.

    python infrastructure/policy/build_opa_data.py --out /tmp/opa-fixtures.json
    opa test infrastructure/policy/rego /tmp/opa-fixtures.json -v

Why this exists: OPA loads every JSON/YAML file it is given as a data document merged into the
SAME root (the file path is not part of the data path), so passing the fixtures directory made
every fixture's top-level `kind` collide ("conflicting values at data.bad.kind"). Here each
fixture is mounted under its file name instead: ``data.good.<name>`` and ``data.bad.<name>``,
which is what ``rego/fixtures_test.rego`` reads. The corpus itself stays one file per case so the
Python checker and the generated Kyverno tests keep iterating the same files.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict

import yaml

HERE = pathlib.Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"


def build(fixtures: pathlib.Path = FIXTURES) -> Dict[str, Dict[str, Any]]:
    """{'good': {name: doc}, 'bad': {name: doc}} with names taken from the file stems."""
    data: Dict[str, Dict[str, Any]] = {}
    for verdict in ("good", "bad"):
        folder = fixtures / verdict
        docs: Dict[str, Any] = {}
        for path in sorted(folder.glob("*.y*ml")):
            if path.stem in docs:
                raise ValueError(f"duplicate fixture name {path.stem!r} in {verdict}/")
            docs[path.stem] = yaml.safe_load(path.read_text(encoding="utf-8"))
        data[verdict] = docs
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    data = build()
    args.out.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {args.out} ({len(data['good'])} good, {len(data['bad'])} bad fixtures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
