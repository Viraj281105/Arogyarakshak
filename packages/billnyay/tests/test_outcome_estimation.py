"""IRDAI appeal outcome estimation framework (#90).

Every dataset built in this file is explicitly synthetic and exists only to check the
arithmetic and the refusal paths. No real outcome data exists in the repository."""

from datetime import date

import pytest
from pydantic import ValidationError

from billnyay.outcome.dataset import (
    DATASET_DIR,
    DatasetProvenance,
    DisputeOutcomeDataset,
    DisputeOutcomeRecord,
    load_registered_dataset,
)
from billnyay.outcome.estimator import OutcomeQuery, estimate_outcome, wilson_interval
from billnyay.outcome.evaluation import brier_score, log_loss, reliability_bins, temporal_holdout_evaluation

PROVENANCE = DatasetProvenance(
    publisher="ArogyaRakshak unit tests",
    source_url="https://example.invalid/synthetic",
    retrieved_on=date(2026, 9, 13),
    license="test-only",
    description="Synthetic records for arithmetic tests",
)


def _records(category, forum, year, allowed=0, partial=0, dismissed=0, withdrawn=0):
    spec = [("ALLOWED", allowed), ("PARTIALLY_ALLOWED", partial), ("DISMISSED", dismissed), ("WITHDRAWN_OR_SETTLED", withdrawn)]
    return [
        DisputeOutcomeRecord(dispute_category=category, forum=forum, outcome=outcome, decision_year=year)
        for outcome, count in spec
        for _ in range(count)
    ]


def _synthetic(records):
    return DisputeOutcomeDataset(name="synthetic-test", is_synthetic=True, provenance=PROVENANCE, records=records)


def test_repository_ships_no_outcome_dataset():
    assert load_registered_dataset() is None
    assert (DATASET_DIR / "README.md").exists()


def test_no_dataset_means_no_probability():
    estimate = estimate_outcome(OutcomeQuery(dispute_category="PED_NON_DISCLOSURE"), None)
    assert estimate.status == "INSUFFICIENT_EVIDENCE"
    assert estimate.probability_favourable is None
    assert estimate.interval_95 is None
    assert estimate.admissibility_checks == "UNEVALUATED"


def test_synthetic_data_is_refused_for_real_estimates():
    dataset = _synthetic(_records("PED_NON_DISCLOSURE", "insurance_ombudsman", 2022, allowed=40))
    estimate = estimate_outcome(OutcomeQuery(dispute_category="PED_NON_DISCLOSURE"), dataset)
    assert estimate.status == "SYNTHETIC_DATA_REFUSED"
    assert estimate.probability_favourable is None


def test_provenance_is_mandatory():
    with pytest.raises(ValidationError):
        DatasetProvenance(publisher="x", source_url="not a url", retrieved_on=date.today(), license="x", description="too short")
    with pytest.raises(ValidationError):
        DisputeOutcomeDataset(name="no-provenance", is_synthetic=False, records=[])


def test_registered_directory_ignores_synthetic_and_invalid_files(tmp_path):
    (tmp_path / "a_invalid.json").write_text("{not json", encoding="utf-8")
    dataset = _synthetic(_records("X", "insurance_ombudsman", 2022, allowed=1))
    (tmp_path / "b_synthetic.json").write_text(dataset.model_dump_json(), encoding="utf-8")
    assert load_registered_dataset(tmp_path) is None


def test_base_rate_with_wilson_interval_and_disclosed_exclusions():
    records = _records("PED_NON_DISCLOSURE", "insurance_ombudsman", 2022, allowed=24, partial=6, dismissed=10, withdrawn=5)
    records += _records("PED_NON_DISCLOSURE", "consumer_commission", 2022, dismissed=50)  # other forum
    estimate = estimate_outcome(
        OutcomeQuery(dispute_category="ped_non_disclosure"), _synthetic(records), allow_synthetic=True
    )
    assert estimate.status == "ESTIMATED"
    assert estimate.sample_size == 40
    assert estimate.excluded_withdrawn_or_settled == 5
    assert estimate.probability_favourable == 0.75
    low, high = estimate.interval_95
    assert low == pytest.approx(0.5981, abs=1e-3) and high == pytest.approx(0.8581, abs=1e-3)
    assert any("5 withdrawn or settled" in c for c in estimate.caveats)
    assert any("SYNTHETIC DATA" in c for c in estimate.caveats)
    assert any("not a prediction" in c for c in estimate.caveats)


def test_too_few_matching_disputes_is_insufficient_evidence():
    records = _records("ROOM_RENT_CAPPING", "insurance_ombudsman", 2022, allowed=20, dismissed=9)
    estimate = estimate_outcome(OutcomeQuery(dispute_category="ROOM_RENT_CAPPING"), _synthetic(records), allow_synthetic=True)
    assert estimate.status == "INSUFFICIENT_EVIDENCE"
    assert estimate.sample_size == 29
    assert estimate.probability_favourable is None


def test_wilson_interval_edges():
    assert wilson_interval(0, 10)[0] == 0.0
    assert wilson_interval(10, 10)[1] == 1.0
    with pytest.raises(ValueError):
        wilson_interval(0, 0)


def test_scoring_rules_known_values():
    assert brier_score([0.8, 0.2], [True, False]) == pytest.approx(0.04)
    assert log_loss([0.5], [True]) == pytest.approx(0.693147, abs=1e-6)
    bins = reliability_bins([0.1, 0.15, 0.9, 1.0], [False, True, True, True], bins=5)
    assert bins[0].count == 2 and bins[0].observed_rate == 0.5
    assert bins[4].count == 2 and bins[4].mean_predicted == 0.95


def test_temporal_holdout_uses_only_earlier_years():
    train = _records("PED_NON_DISCLOSURE", "insurance_ombudsman", 2021, allowed=30, dismissed=10)
    test = _records("PED_NON_DISCLOSURE", "insurance_ombudsman", 2023, allowed=7, dismissed=3)
    report = temporal_holdout_evaluation(_synthetic(train + test), test_from_year=2023)
    assert report.synthetic is True
    assert (report.test_disputes, report.estimated, report.refused_insufficient_evidence) == (10, 10, 0)
    # Every test dispute is predicted at the training rate 0.75.
    assert report.brier_score == pytest.approx((7 * 0.25**2 + 3 * 0.75**2) / 10)
    assert report.base_rate_brier_score == report.brier_score
    assert report.interval_coverage == 1.0  # test rate 0.7 lies inside the training interval
