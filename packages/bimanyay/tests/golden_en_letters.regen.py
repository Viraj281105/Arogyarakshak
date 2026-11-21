"""Regenerates golden_en_letters.json: the English BimaNyay output BEFORE the message catalogue.

The golden file must come from the code at the BASE commit 4d34190 (the last commit before
the catalogue), never from the current code, otherwise it proves nothing. Command:

    git archive 4d34190 packages/bimanyay | tar -x -C /tmp/base      # pre-catalogue package
    PYTHONPATH=/tmp/base/packages/bimanyay:packages/kadi \
        python packages/bimanyay/tests/golden_en_letters.regen.py packages/bimanyay/tests/golden_en_letters.json

(Windows: extract to any scratch directory and use ';' in PYTHONPATH.) Reviewers can re-run it
and diff: the file is byte-for-byte the pre-catalogue output. test_catalogue.py compares the
current code against it.
"""

import json
import sys

import bimanyay
from bimanyay import ClaimDenialInput, analyze_insurance_denial

assert not hasattr(bimanyay, "catalogue"), "run this against the pre-catalogue package (4d34190)"

BASE = dict(policy_number="SYN-0001", insurer_name="Synthetic Insurer Ltd", claimed_amount=100000.0,
            denied_or_deducted_amount=60000.0, diagnosis="Hypertensive crisis",
            denial_reason_raw="Hypertension not disclosed at proposal stage")
CASES = {
    "ped_over_5y": dict(policy_age_years=6.0, denial_category="PED_NON_DISCLOSURE"),
    "ped_under_5y": dict(policy_age_years=2.5, denial_category="PED_NON_DISCLOSURE"),
    "ped_exactly_5y": dict(policy_age_years=5.0, denial_category="PED_NON_DISCLOSURE"),
    "ped_just_under_5y": dict(policy_age_years=4.99, denial_category="PED_NON_DISCLOSURE"),
    "pre_existing_alias": dict(policy_age_years=6.0, denial_category="PRE_EXISTING"),
    "lowercase_category": dict(policy_age_years=6.0, denial_category="ped_non_disclosure"),
    "investigation": dict(policy_age_years=3.0, denial_category="INVESTIGATION_ONLY"),
    "room_rent": dict(policy_age_years=2.0, denial_category="ROOM_RENT_CAPPING"),
    "delay": dict(policy_age_years=1.0, denial_category="DELAYED_INTIMATION"),
    "general": dict(policy_age_years=4.0, denial_category="EXCLUSION_CLAUSE"),
}

if __name__ == "__main__":
    out = {}
    for name, extra in CASES.items():
        result = analyze_insurance_denial(ClaimDenialInput(**BASE, **extra))
        out[name] = {"input": {**BASE, **extra}, "result": result.model_dump()}
    with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
