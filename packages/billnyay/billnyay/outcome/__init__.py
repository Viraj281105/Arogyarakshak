"""IRDAI appeal outcome estimation (#90): evidence-grounded base rates, or no number."""

from billnyay.outcome.dataset import DisputeOutcomeDataset, load_dataset, load_registered_dataset
from billnyay.outcome.estimator import OutcomeEstimate, OutcomeQuery, estimate_outcome, wilson_interval

__all__ = [
    "DisputeOutcomeDataset",
    "OutcomeEstimate",
    "OutcomeQuery",
    "estimate_outcome",
    "load_dataset",
    "load_registered_dataset",
    "wilson_interval",
]
