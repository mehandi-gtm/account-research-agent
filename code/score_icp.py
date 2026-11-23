"""ICP fit score: firmographics (45) + signals (15) + lookalike (40) = 0-100.

The scoring logic is a pure function, so it can be tested locally:
    python code/score_icp.py
The n8n wrapper is at the bottom. Paste the whole file into a Python Code node.
"""

# No imports: n8n's Python sandbox blocks them by default, so dates are handled by hand.

ICP_REGIONS = {"EU", "UK", "US"}
GOOD_CRMS = {"HubSpot", "Salesforce"}
OK_CRMS = {"Pipedrive", "Zoho CRM"}

# Lookalike: cosine similarity below SIM_FLOOR scores 0, at or above SIM_CEIL scores 40.
# Calibrated on the first 50-account run (2026-11-23): Gemini similarities ranged 0.649 to 0.782,
# so the floor and ceiling are the lowest and highest values seen.
SIM_FLOOR = 0.65
SIM_CEIL = 0.78

SIGNAL_HALF_LIFE_DAYS = 45


def firmographic_points(a: dict) -> tuple[int, list[str]]:
    pts, why = 0, []
    if a["industry"].startswith("B2B SaaS"):
        pts += 15; why.append("B2B SaaS (+15)")
    elif a["industry"] == "IT Services":
        pts += 4; why.append("IT services, adjacent (+4)")

    emp = int(a["employees"])
    if 20 <= emp <= 500:
        pts += 10; why.append(f"{emp} employees, in range (+10)")
    elif 10 <= emp < 20 or 500 < emp <= 1000:
        pts += 5; why.append(f"{emp} employees, near range (+5)")

    if a["region"] in ICP_REGIONS:
        pts += 10; why.append(f"{a['region']} region (+10)")

    if a["crm"] in GOOD_CRMS:
        pts += 7; why.append(f"uses {a['crm']} (+7)")
    elif a["crm"] in OK_CRMS:
        pts += 3; why.append(f"uses {a['crm']} (+3)")

    if a["sales_motion"] in ("Sales-led", "Hybrid"):
        pts += 3; why.append(f"{a['sales_motion']} motion (+3)")
    return pts, why


def day_number(iso: str) -> int:
    """Days since 1970-01-01 for a 'YYYY-MM-DD' string (Howard Hinnant's days_from_civil)."""
    y, m, d = (int(p) for p in iso[:10].split("-"))
    y -= m <= 2
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def signal_points(signals: list[dict], today: str) -> tuple[int, list[str]]:
    """Each signal is worth strength * 5, halved every SIGNAL_HALF_LIFE_DAYS. Capped at 15."""
    raw, why = 0.0, []
    for s in signals:
        age = max(0, day_number(today) - day_number(s["date"]))
        value = s["strength"] * 5 * 0.5 ** (age / SIGNAL_HALF_LIFE_DAYS)
        raw += value
        why.append(f"{s['detail']}, {age}d ago (+{value:.1f})")
    return min(15, round(raw)), why


def lookalike_points(similarity: float | None) -> int:
    if similarity is None:
        return 0
    x = (similarity - SIM_FLOOR) / (SIM_CEIL - SIM_FLOOR)
    return round(40 * max(0.0, min(1.0, x)))


def tier(score: int) -> str:
    return "A" if score >= 70 else "B" if score >= 45 else "C"


def score_account(a: dict, signals: list[dict], similarity: float | None, today: str) -> dict:
    f_pts, f_why = firmographic_points(a)
    s_pts, s_why = signal_points(signals, today)
    l_pts = lookalike_points(similarity)
    total = f_pts + s_pts + l_pts
    reasons = f_why + s_why
    if similarity is not None:
        reasons.append(f"lookalike similarity {similarity:.2f} (+{l_pts})")
    return {
        "icp_score": total,
        "icp_tier": tier(total),
        "score_firmographic": f_pts,
        "score_signals": s_pts,
        "score_lookalike": l_pts,
        "score_reasons": reasons,
    }


# ---------------------------------------------------------------------------
# n8n Code node (Python, mode "Run Once for Each Item"): paste everything above
# this block, then add these lines at the end of the node instead of __main__.
# `run_date` (YYYY-MM-DD) is set by the "Join Signals" node.
#
#   a = dict(_item["json"])
#   a.update(score_account(a, a.get("signals") or [], a.get("lookalike_similarity"), a["run_date"]))
#   return {"json": a}
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    demo = {"industry": "B2B SaaS - Fintech", "employees": 120, "region": "EU",
            "crm": "HubSpot", "sales_motion": "Sales-led"}
    sigs = [{"detail": "Posted 4 open SDR/BDR roles", "strength": 3, "date": "2026-11-10"}]
    print(score_account(demo, sigs, 0.62, "2026-11-23"))
