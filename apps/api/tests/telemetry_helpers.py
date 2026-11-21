"""Shared helpers for the telemetry tests: PHI-shaped strings that must never become a label."""

import re


PHI_SAMPLES = [
    "CASE-1a2b3c4d5e6f7a8b",
    "Ramesh Kumar Sharma",
    "9876543210",
    "1234-5678-9012",
    "ramesh@example.com",
    "Patient has diabetes mellitus type 2",
    "/api/v1/kadi/cases/CASE-1a2b3c4d5e6f7a8b/entities",
    'inj"ection\n{label="x"}',
    "रमेश कुमार",
]


def label_values(text: str):
    """Every label value on every sample line of Prometheus exposition text."""
    values = []
    for line in text.splitlines():
        if line.startswith("#") or "{" not in line:
            continue
        inner = line[line.index("{") + 1 : line.rindex("}")]
        values.extend(re.findall(r'="((?:[^"\\]|\\.)*)"', inner))
    return values
