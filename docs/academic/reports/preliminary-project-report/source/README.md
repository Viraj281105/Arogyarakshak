# Report sources

- `content/*.txt` — chapter text in a light markup (`@chapter`, `##`, `!figure`, `!table`, `!eq`, `!callout`, `[n]` references).
- `figures/figs_arch.py`, `figures/figs_mod.py` — SVG diagrams rendered to PNG with headless Microsoft Edge: `python figs_arch.py <outdir>` (writes `<outdir>/png`).
- `screenshots/` — real screenshots of the running web client (demo mode, synthetic Scenario A, 4 Nov 2026).
- `build.js` — DOCX builder (`npm install docx@9`): `node build.js content <outdir>/png screenshots out.docx`.
- `word_export.ps1` — opens the DOCX in Microsoft Word, updates the Contents / List of Figures / List of Tables fields and exports the PDF.
