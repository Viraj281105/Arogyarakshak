"""
SchemeSetu — single source of truth for the scheme eligibility criteria the rule engine reports.

`agent.check_eligibility`, `reasoning_agent` and the consent-bounded recommendation trigger
(`triggers.py`, #92) all read these records.

Income is a NON-DETERMINATIVE factor. Neither scheme defines a single annual-income ceiling in
the official sources cited below, so the engine records and reports income but never uses it
to decide eligibility. The Phase-2 figures (PMJAY Rs 2,50,000; MJPJAY Rs 1,50,000) were
unverified project heuristics and have been removed. Rs 1.50 lakh was in fact MJPJAY's
per-family insurance cover for 2020-2024, not an income limit.

- AB PM-JAY: families identified from SECC-2011 (6 rural deprivation / 11 urban occupational
  criteria), revised in January 2022 with state-verified databases; ASHA / Anganwadi Worker /
  Anganwadi Helper families since March 2024; every person aged 70+ irrespective of income
  since October 2024. The engine collects none of these facts, so PM-JAY is always reported as
  needing verification.
- MJPJAY: the GR dated 28 July 2023 extends the scheme to all families in Maharashtra, and the
  integrated scheme runs from 1 July 2024. The engine checks only the stated state of residence.

Sources were retrieved on 2026-09-13. The SHAS portal (jeevandayee.gov.in) and the GR text
itself could not be reached from the development environment, so the MJPJAY citations are
Government of Maharashtra portals that restate the GR; see `verification_gaps`.
"""

from typing import FrozenSet, List, Literal, Optional

from pydantic import BaseModel

# OFFICIAL_SOURCE_CITED: a Government statement of the rule itself (Cabinet decision, written
# parliamentary reply). OFFICIAL_RESTATEMENT_CITED: a Government portal restating an order whose
# text was not retrieved.
CriteriaProvenance = Literal["OFFICIAL_SOURCE_CITED", "OFFICIAL_RESTATEMENT_CITED"]
IncomeRole = Literal["NON_DETERMINATIVE"]

RETRIEVED_ON = "2026-09-13"


class Citation(BaseModel):
    url: str
    document: str
    publisher: str
    date: Optional[str]  # as shown by the source; None when the page shows no date
    retrieved_on: str = RETRIEVED_ON
    supports: str


class SchemeCriteria(BaseModel):
    scheme_name: str
    short_name: str
    applicable_states: Optional[FrozenSet[str]] = None  # None: applies in every state
    official_basis: str
    income_role: IncomeRole = "NON_DETERMINATIVE"
    criteria_not_evaluated: List[str]
    verification_steps: List[str]
    provenance: CriteriaProvenance
    citations: List[Citation]
    verification_gaps: List[str] = []

    def applies_to_state(self, state: Optional[str]) -> bool:
        if self.applicable_states is None:
            return True
        return (state or "").strip().lower() in self.applicable_states


_PIB_PUBLISHER = "Press Information Bureau, Ministry of Health and Family Welfare, Government of India"

PMJAY = SchemeCriteria(
    scheme_name="PMJAY (Ayushman Bharat)",
    short_name="PMJAY",
    official_basis=(
        "Family identified from SECC-2011 deprivation (rural) or occupational (urban) criteria, or "
        "from a state-verified beneficiary database; an ASHA, Anganwadi Worker or Anganwadi Helper "
        "family; or a member aged 70 or above, irrespective of income. No annual income ceiling "
        "is defined."
    ),
    criteria_not_evaluated=[
        "SECC-2011 deprivation/occupational listing or state-verified beneficiary database",
        "ASHA / Anganwadi Worker / Anganwadi Helper family",
        "age 70 or above (eligible irrespective of income)",
    ],
    verification_steps=[
        "Ask the help desk at an empanelled hospital whether your family is a listed AB PM-JAY "
        "beneficiary (every government hospital with in-patient services is empanelled).",
        "If a family member is aged 70 or above, they are eligible irrespective of income and can "
        "be issued a distinct AB PM-JAY card.",
        "If a family member is an ASHA, Anganwadi Worker or Anganwadi Helper, the family is covered "
        "under the March 2024 expansion.",
    ],
    provenance="OFFICIAL_SOURCE_CITED",
    citations=[
        Citation(
            url="https://www.pib.gov.in/PressReleasePage.aspx?PRID=2116209",
            document=(
                "Update on Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (AB PM-JAY) "
                "(written reply in the Lok Sabha, Release ID 2116209)"
            ),
            publisher=_PIB_PUBLISHER,
            date="2025-03-28",
            supports=(
                "Beneficiary families were identified from SECC-2011 on 6 deprivation and 11 "
                "occupational criteria; the base was revised to 12 crore families in January 2022 "
                "with state-verified databases; ASHA/AWW/AWH families were added in March 2024; "
                "senior citizens aged 70+ were added on 29 October 2024 irrespective of "
                "socio-economic status."
            ),
        ),
        Citation(
            url="https://www.pib.gov.in/PressReleasePage.aspx?PRID=2053883",
            document=(
                "Cabinet approves health coverage to all senior citizens of the age 70 years and "
                "above irrespective of income under AB PM-JAY (Release ID 2053883)"
            ),
            publisher=_PIB_PUBLISHER,
            date="2024-09-11",
            supports=(
                "All senior citizens aged 70 and above are eligible irrespective of income, with a "
                "distinct card and a top-up cover for families already covered."
            ),
        ),
    ],
)

MJPJAY = SchemeCriteria(
    scheme_name="MJPJAY (Mahatma Jyotirao Phule Jan Arogya Yojana)",
    short_name="MJPJAY",
    applicable_states=frozenset({"maharashtra", "mh"}),
    official_basis=(
        "All families in Maharashtra (GR dated 28 July 2023; integrated scheme in force from "
        "1 July 2024). No annual income ceiling is defined."
    ),
    criteria_not_evaluated=[
        "documents accepted as proof of eligibility (e.g. ration card)",
    ],
    verification_steps=[
        "Ask the Arogyamitra at an MJPJAY network hospital which documents you need to show "
        "(for example your ration card).",
        "Treatment is cashless at government and private network hospitals in Maharashtra.",
    ],
    provenance="OFFICIAL_RESTATEMENT_CITED",
    citations=[
        Citation(
            url=(
                "https://zpjalna.maharashtra.gov.in/en/scheme/"
                "pradhan-mantri-jan-arogya-yojana-and-mahatma-jyotirao-phule-jan-arogya-yojana/"
            ),
            document="Pradhan Mantri Jan Arogya Yojana and Mahatma Jyotirao Phule Jan Arogya Yojana",
            publisher="Zilla Parishad Jalna, Government of Maharashtra",
            date="2025-02-21 (page last-updated stamp)",
            supports=(
                "The GR dated 28 July 2023 implements MJPJAY for all families in the state; the "
                "integrated scheme from 1 July 2024 covers all population of Maharashtra with "
                "Rs 5 lakh per family per year. Rs 1.50 lakh was the 2020-2024 MJPJAY cover."
            ),
        ),
        Citation(
            url=(
                "https://zpdharashiv.maharashtra.gov.in/en/scheme/"
                "pradhan-mantri-jan-arogya-yojana-and-mahatma-jyotirao-phule-jan-arogya-yojana/"
            ),
            document="Pradhan Mantri Jan Arogya Yojana and Mahatma Jyotirao Phule Jan Arogya Yojana",
            publisher="Zilla Parishad Dharashiv, Government of Maharashtra",
            date=None,
            supports=(
                "Same restatement of the GR dated 28 July 2023; lists all ration card holders as "
                "beneficiaries."
            ),
        ),
    ],
    verification_gaps=[
        "The text of the GR dated 28 July 2023 and the SHAS portal (jeevandayee.gov.in) were not "
        "retrieved; documentary requirements are unverified.",
    ],
)

SCHEME_CRITERIA: List[SchemeCriteria] = [PMJAY, MJPJAY]


def format_inr(amount: float) -> str:
    """Indian digit grouping: 250000 -> "2,50,000"."""
    digits = f"{int(round(amount))}"
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail])
