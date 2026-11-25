# Code analysis: `apps/api/app`

Archify Code Analysis, first run for this folder, 2026-11-25 (working tree of
`wave3/transformation`, before the commit). How to read and re-run: [../README.md](../README.md).

120 files analysed (tests and generated files excluded), no parse errors.

| Severity | Count |
|---|---|
| error | 0 |
| warning | 3 |
| info | 13 |

No import cycle was reported. The three warnings are function complexity:

| Function | File | Cyclomatic complexity |
|---|---|---|
| `case_timeline` | `case_timeline.py` | 31 |
| `compare` | `evaluation/regression.py` | 27 |
| `_run_pipeline` | `services/case_ingestion.py` | 26 |

None was introduced as a new function in this pass; they are left open. There is no earlier run to
compare against. Static findings are maintenance signals, not defects; `lint-imports` (6 contracts
kept) enforces the layering rules.
