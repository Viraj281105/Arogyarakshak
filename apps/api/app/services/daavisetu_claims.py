"""
DaaviSetu stored-claim mapping — application helper.

Moved out of ``app.api.v1.endpoints.daavisetu`` (ADR-018): the Claim Pack rebuilds the
pre-authorisation PDF from a stored claim and must not import a route module to do so.
"""

from app.models import DaaviSetuClaim
from daavisetu.generator import ClaimData


def claim_data_from_record(claim_record: DaaviSetuClaim) -> ClaimData:
    return ClaimData(
        policy_number=claim_record.policy_number,
        patient_name=claim_record.patient_name,
        hospital_name=claim_record.hospital_name,
        diagnosis=claim_record.diagnosis,
        estimated_cost=claim_record.estimated_cost,
        treatment_plan=claim_record.treatment_plan,
        sum_insured=claim_record.sum_insured,
    )


# Former private name, kept for existing importers.
_claim_data_from_record = claim_data_from_record
