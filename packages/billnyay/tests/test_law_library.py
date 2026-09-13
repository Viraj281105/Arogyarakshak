"""
Provenance checks for billnyay/data/law_library.json.

Every statute the Regulatory agent can cite must say where it came from and
whether it was actually checked against a primary source.
"""

import json
import os
from datetime import date
from urllib.parse import urlparse

import pytest

from billnyay.agents import regulatory
from billnyay.agents.regulatory import run_regulatory_agent

LIBRARY_PATH = os.path.join(
    os.path.dirname(regulatory.__file__), "..", "data", "law_library.json"
)
PRIMARY_SOURCE_HOSTS = ("irdai.gov.in", "cioins.co.in", "egazette.gov.in")
PROVENANCE_FIELDS = ("source_url", "issued_on", "verified_on", "verification_status")


def _library():
    with open(LIBRARY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _is_primary_source(url):
    host = urlparse(url or "").hostname or ""
    return any(host == h or host.endswith("." + h) for h in PRIMARY_SOURCE_HOSTS)


def _assert_provenance(entry):
    for field in PROVENANCE_FIELDS:
        assert field in entry, f"{entry['statute_name']} is missing {field}"
    assert entry["verification_status"] in {"verified", "unverified"}
    assert entry.get("verification_note")
    if entry["verification_status"] == "verified":
        assert _is_primary_source(entry["source_url"])
        date.fromisoformat(entry["issued_on"])
        date.fromisoformat(entry["verified_on"])
    else:
        # An unverified entry must not look verified.
        assert entry["verified_on"] is None


@pytest.mark.parametrize("entry", _library(), ids=lambda e: e["category"])
def test_law_library_entry_has_provenance(entry):
    _assert_provenance(entry)


def test_exclusions_guidelines_use_verified_reference():
    # "194/09/2020" was never an IRDAI reference; the exclusions guidelines are
    # IRDAI/HLT/REG/CIR/177/09/2019 dated 27.09.2019. (verification_note may still
    # mention the old string as history, so only the citable fields are checked.)
    for e in _library():
        assert "194/09/2020" not in e["statute_name"] + e["statute_text"]
    entry = next(e for e in _library() if e["category"] == "claims_exclusion")
    assert "IRDAI/HLT/REG/CIR/177/09/2019" in entry["statute_name"]
    assert entry["issued_on"] == "2019-09-27"
    assert entry["verification_status"] == "verified"


def test_fallback_library_matches_json():
    by_name = {e["statute_name"]: e for e in _library()}
    for entry in regulatory._FALLBACK_LAW_LIBRARY:
        _assert_provenance(entry)
        assert by_name.get(entry["statute_name"]) == entry


def test_regulatory_agent_surfaces_verification_status():
    result = run_regulatory_agent(denial_data={})
    assert result["legal_points"]
    for point in result["legal_points"]:
        assert point["verification_status"] in {"verified", "unverified"}
        assert "source_url" in point
