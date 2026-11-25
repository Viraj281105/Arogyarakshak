"""The synthetic demonstration account (ADR-029, docs/DEMO_GUIDE.md).

One account, ``DEMO_ACCOUNT_EMAIL``, that exists only on a server where demo operations are
allowed (CLINICAL_DEMO_MODE on and APP_ENV not production). It signs in like any other
account: there is no bypass. Provisioning rotates its password, erases every case it owns
and loads the committed synthetic documents again through the real pipeline.

The account's rules outside this module live in app.services.accounts: the address can
never be registered by anyone, receives no email, and cannot sign in (or keep a session)
once demo operations are off.
"""

import logging
import secrets
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.clinical.demo_control import SCENARIOS, load_scenario
from app.services import accounts, case_actions

logger = logging.getLogger("arogyarakshak.demo")

# Synthetic tracking histories, so a demonstration can show the journey after a report.
# Each entry: (status, days before today or None, note). Every title and note says DEMO.
_DEMO_ACTIONS: Dict[str, Tuple[Dict[str, Any], List[Tuple[str, "int | None", "str | None"]]]] = {
    "A": (
        {
            "module": "billnyay",
            "kind": "clarification_request",
            "title": "DEMO: ask the hospital to clarify the lines above the CGHS reference",
            "institution": "Sunrise Multispeciality Hospital (synthetic)",
            "contact_method": "email",
        },
        [
            ("draft_prepared", None, None),
            ("sent", 6, "DEMO: synthetic record. Sent to the billing desk."),
            ("response_received", 2, "DEMO: synthetic record. The desk asked for two more days."),
        ],
    ),
    "B": (
        {
            "module": "daavisetu",
            "kind": "collect_documents",
            "title": "DEMO: collect the documents the readiness check did not find",
        },
        [],
    ),
    "D": (
        {
            "module": "bimanyay",
            "kind": "appeal_or_grievance",
            "title": "DEMO: grievance to the insurer about the repudiation",
            "institution": "Demo Health Insurer (fictional)",
            "contact_method": "letter",
        },
        [("draft_prepared", None, None), ("sent", 10, "DEMO: synthetic record."), ("awaiting_response", None, None)],
    ),
}


async def _seed_actions(db: AsyncSession, case_ids: Dict[str, str]) -> int:
    today: date = datetime.utcnow().date()
    seeded = 0
    for scenario_id, (fields, history) in _DEMO_ACTIONS.items():
        case_id = case_ids.get(scenario_id)
        if not case_id:
            continue
        action = await case_actions.create_action(db, case_id, fields)
        for status, days_ago, note in history:
            await case_actions.record_event(
                db,
                case_id,
                action["id"],
                {
                    "status": status,
                    "occurred_on": None if days_ago is None else today - timedelta(days=days_ago),
                    "note": note,
                },
            )
        seeded += 1
    return seeded


async def provision_demo_account(
    db: AsyncSession, scenarios: Iterable[str] = tuple(SCENARIOS)
) -> Dict[str, Any]:
    """Creates or resets the demo account and its cases. Returns the new password once;
    only its scrypt hash is stored. Raises PermissionError when demo operations are off."""
    # 18 random bytes: 24 URL-safe characters, within the password policy.
    password = secrets.token_urlsafe(18)
    user_id, erased = await accounts.reset_demo_user(db, password)
    cases = []
    for scenario_id in scenarios:
        loaded = await load_scenario(db, scenario_id, owner_user_id=user_id)
        cases.append(
            {"scenario": loaded["scenario"], "title": loaded["title"], "case_id": loaded["case_id"]}
        )
    actions = await _seed_actions(db, {c["scenario"]: c["case_id"] for c in cases})
    logger.info("Demo account reset: %d case(s) erased, %d loaded, %d action(s).", erased, len(cases), actions)
    return {
        "email": accounts.DEMO_ACCOUNT_EMAIL,
        "display_name": accounts.DEMO_ACCOUNT_NAME,
        "password": password,
        "cases_erased": erased,
        "cases": cases,
        "actions": actions,
    }
