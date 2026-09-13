# Dispute-outcome datasets (#90)

This directory is intentionally empty. ArogyaRakshak has **no historical IRDAI / Insurance
Ombudsman dispute-outcome data**, so `POST /api/v1/billnyay/outcome-estimate` returns
`INSUFFICIENT_EVIDENCE` and no probability.

A dataset placed here is used only if it validates against
`billnyay.outcome.dataset.DisputeOutcomeDataset`:

```json
{
  "name": "…",
  "is_synthetic": false,
  "provenance": {
    "publisher": "Organisation that published the outcomes",
    "source_url": "https://…",
    "retrieved_on": "YYYY-MM-DD",
    "license": "…",
    "description": "What the records are and how they were extracted"
  },
  "records": [
    {"dispute_category": "pre_existing_disease", "forum": "insurance_ombudsman", "outcome": "ALLOWED", "decision_year": 2024}
  ]
}
```

- `forum`: `insurer_grievance`, `insurance_ombudsman` or `consumer_commission`
- `outcome`: `ALLOWED`, `PARTIALLY_ALLOWED`, `DISMISSED` or `WITHDRAWN_OR_SETTLED`
- Synthetic datasets (`"is_synthetic": true`) are ignored for estimates.
- Do not add records that could identify a complainant.

Before trusting estimates from a new dataset, run
`billnyay.outcome.evaluation.temporal_holdout_evaluation` and record the results.
