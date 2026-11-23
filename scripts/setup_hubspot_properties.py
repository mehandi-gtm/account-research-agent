"""Create the custom company properties the agent writes to. Safe to run twice.

Needs a HubSpot service key (or legacy private app token) with crm.schemas.companies.write and
crm.objects.companies.write. Put it in .env (see .env.example) or the environment:
    python scripts/setup_hubspot_properties.py

Uses 7 custom properties, which fits HubSpot's free CRM.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.hubapi.com/crm/v3/properties/companies"
GROUP = "account_research"

PROPERTIES = [
    {"name": "ara_icp_score", "label": "ICP Score", "type": "number", "fieldType": "number"},
    {"name": "ara_icp_tier", "label": "ICP Tier", "type": "enumeration", "fieldType": "select",
     "options": [{"label": t, "value": t, "displayOrder": i} for i, t in enumerate("ABC")]},
    {"name": "ara_top_signal", "label": "Top Buying Signal", "type": "string", "fieldType": "text"},
    {"name": "ara_first_line", "label": "First Line", "type": "string", "fieldType": "textarea"},
    {"name": "ara_research_brief", "label": "Research Brief", "type": "string", "fieldType": "textarea"},
    {"name": "ara_score_reasons", "label": "Score Reasons", "type": "string", "fieldType": "textarea"},
    {"name": "ara_qa_status", "label": "First Line QA", "type": "enumeration", "fieldType": "select",
     "options": [{"label": "Pass", "value": "pass", "displayOrder": 0},
                 {"label": "Needs review", "value": "needs_review", "displayOrder": 1},
                 {"label": "Skipped (tier C)", "value": "skipped", "displayOrder": 2}]},
]


def load_token() -> str:
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "HUBSPOT_PRIVATE_APP_TOKEN" and value.strip():
                os.environ.setdefault("HUBSPOT_PRIVATE_APP_TOKEN", value.strip())
    token = os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN")
    if not token:
        sys.exit("HUBSPOT_PRIVATE_APP_TOKEN is not set (see .env.example)")
    return token


def post(url: str, body: dict, token: str) -> int:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        if e.code == 409:  # already exists
            return 409
        sys.exit(f"HubSpot returned {e.code}: {e.read().decode()[:300]}")


def main() -> None:
    token = load_token()
    status = post(f"{API}/groups", {"name": GROUP, "label": "Account Research Agent"}, token)
    print(f"group {GROUP}: {'exists' if status == 409 else 'created'}")
    for prop in PROPERTIES:
        status = post(API, {**prop, "groupName": GROUP}, token)
        print(f"{prop['name']}: {'exists' if status == 409 else 'created'}")


if __name__ == "__main__":
    main()
