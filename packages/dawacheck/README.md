# DawaCheck

**Medicine pricing verification** module for ArogyaRakshak. ("Dawa" = medicine)

## Future Role

- Upload a medicine strip photo or prescription → OCR reads drug name/batch
- Benchmark MRP against NPPA ceiling prices for Schedule-I formulations (~800–900 price-controlled drugs)
- Flag overcharging → suggest generic substitutes
- Deliberately scoped to Schedule-I only — the one segment with a clean, finite, government-published ground-truth price
- DB table prefix: `dawacheck_` (e.g. `dawacheck_nppa_prices`)
- API route prefix: `/api/dawacheck/...`

See [Technical Documentation §3](../docs/ArogyaRakshak_Technical_Documentation.md) for full design.
