"""Generate a fictional B2B account list for the account research agent.

Everything here is made up. Company names are random word pairs, every domain
uses the reserved `.example` TLD (RFC 2606), and every contact is invented.

Outputs (in --out, default ./data):
  accounts.csv     target accounts to research
  signals.json     0-3 dated buying signals per account, keyed by domain
  closed_won.csv   "best customer" profiles that get embedded into Qdrant
  answer_key.csv   the fit each account was generated with (good/medium/poor).
                   The agent never sees it; it is only used to grade the run.

Usage:
  python scripts/generate_accounts.py                 # 50 accounts, seed 42
  python scripts/generate_accounts.py --n 100 --seed 7

Stdlib only. The same seed always gives the same files.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

NAME_A = [
    "Amber", "Birch", "Cobalt", "Delta", "Ember", "Fable", "Granite", "Harbor",
    "Indigo", "Juniper", "Kestrel", "Lumen", "Maple", "Nimbus", "Onyx", "Pylon",
    "Quill", "Raven", "Saffron", "Tidal", "Umber", "Vesper", "Willow", "Zephyr",
    "Copper", "Fjord", "Lark", "Moss", "Orbit", "Prism",
]
NAME_B = [
    "loop", "stack", "field", "path", "grid", "forge", "wave", "point", "line",
    "craft", "works", "base", "flow", "yard", "mint", "lane", "beam", "shift",
]
SUFFIX = ["", "", "", " Labs", " HQ", " Systems", " Co"]

# (industry, what they build, who for). First group is in the ICP.
ICP_INDUSTRIES = [
    ("B2B SaaS - Fintech", "invoice automation software", "mid-market finance teams"),
    ("B2B SaaS - HR Tech", "a hiring and onboarding platform", "fast-growing tech companies"),
    ("B2B SaaS - Devtools", "an API monitoring tool", "engineering teams"),
    ("B2B SaaS - Martech", "a webinar and event platform", "B2B marketing teams"),
    ("B2B SaaS - Logistics", "freight visibility software", "shippers and 3PLs"),
    ("B2B SaaS - Security", "a vendor risk management platform", "compliance teams"),
    ("B2B SaaS - Data", "a customer data platform", "product-led SaaS companies"),
]
NON_ICP_INDUSTRIES = [
    ("Marketing Agency", "paid social campaigns", "local businesses"),
    ("E-commerce Brand", "sustainable home goods", "consumers"),
    ("Manufacturing", "industrial fasteners", "construction suppliers"),
    ("Hospitality", "a chain of boutique hotels", "leisure travellers"),
    ("Non-profit", "community education programs", "low-income families"),
    ("IT Services", "managed IT support", "small offices"),
]

COUNTRIES = {
    "EU": ["Netherlands", "Germany", "Ireland", "Sweden", "Denmark", "France"],
    "UK": ["United Kingdom"],
    "US": ["United States"],
    "Other": ["Brazil", "South Africa", "Japan", "Indonesia"],
}

CRMS_GOOD = ["HubSpot", "Salesforce"]
CRMS_OTHER = ["Pipedrive", "Zoho CRM", "None", "Spreadsheet"]
STACK_POOL = [
    "Slack", "Gong", "Outreach", "Apollo", "Intercom", "Segment", "Snowflake",
    "Zapier", "Notion", "Stripe", "Clay", "LinkedIn Sales Navigator", "Shopify",
    "WordPress", "Mailchimp", "QuickBooks",
]
MOTIONS = ["Sales-led", "Hybrid", "Product-led"]
FUNDING = ["Bootstrapped", "Seed", "Series A", "Series B", "Series C"]

FIRST = [
    "Ava", "Liam", "Noor", "Mateo", "Freya", "Kenji", "Zara", "Lukas", "Imani",
    "Oskar", "Priya", "Elena", "Tomas", "Hana", "Ruben", "Sofia", "Aidan",
    "Leila", "Nils", "Clara", "Dev", "Ines", "Jonas", "Mila",
]
LAST = [
    "Verhoeven", "Lindqvist", "Okafor", "Brennan", "Castell", "Moreau",
    "Hartmann", "Sato", "Delgado", "Novak", "Ashworth", "Kowalski", "Rahman",
    "Fischer", "Quinn", "Larsen", "Mensah", "Varga", "Ortiz", "Bauer",
]
TITLES_GOOD = [
    "VP Sales", "Head of Revenue Operations", "Head of Growth", "CRO",
    "Director of Sales", "Sales Operations Manager",
]
TITLES_OTHER = ["Office Manager", "Founder", "Marketing Coordinator", "CEO", "IT Manager"]

# Signal templates: (type, source, detail template, strength 1-3)
SIGNALS = [
    ("hiring_sdrs", "job_post", "Posted {k} open SDR/BDR roles", 3),
    ("new_sales_leader", "linkedin_post", "Hired a new {title}", 3),
    ("funding", "press_release", "Announced a {stage} round", 3),
    ("crm_change", "tech_change", "Moved from {old} to {new}", 2),
    ("market_expansion", "press_release", "Launched in {market}", 2),
    ("revops_hire", "job_post", "Hiring a first RevOps / GTM Engineer", 3),
    ("product_launch", "press_release", "Launched a new {product} product line", 1),
    ("headcount_growth", "linkedin_post", "Headcount up {pct}% in 6 months", 2),
]

MARKETS = ["the DACH region", "the Nordics", "the UK", "North America", "Benelux"]
PRODUCTS = ["enterprise", "self-serve", "analytics", "AI assistant"]

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def unique_name(rng: random.Random, used: set[str]) -> str:
    while True:
        name = rng.choice(NAME_A) + rng.choice(NAME_B) + rng.choice(SUFFIX)
        if name not in used:
            used.add(name)
            return name


def domain_for(name: str) -> str:
    slug = "".join(ch for ch in name.lower() if ch.isalnum())
    return f"{slug}.example"


def pick_region(rng: random.Random, fit: str) -> tuple[str, str]:
    weights = {
        "good": {"EU": 5, "UK": 2, "US": 4, "Other": 0},
        "medium": {"EU": 3, "UK": 1, "US": 3, "Other": 2},
        "poor": {"EU": 2, "UK": 1, "US": 2, "Other": 4},
    }[fit]
    region = rng.choices(list(weights), weights=list(weights.values()))[0]
    return region, rng.choice(COUNTRIES[region])


def build_company(rng: random.Random, fit: str, used: set[str]) -> dict:
    """fit = good | medium | poor. Controls how close the company is to the ICP."""
    name = unique_name(rng, used)
    if fit == "poor" or (fit == "medium" and rng.random() < 0.3):
        industry, builds, buyers = rng.choice(NON_ICP_INDUSTRIES)
    else:
        industry, builds, buyers = rng.choice(ICP_INDUSTRIES)

    if fit == "good":
        employees = rng.randint(40, 450)
        crm = rng.choice(CRMS_GOOD)
        motion = rng.choice(["Sales-led", "Sales-led", "Hybrid"])
        funding = rng.choice(["Seed", "Series A", "Series B"])
    elif fit == "medium":
        employees = rng.choice([rng.randint(8, 25), rng.randint(60, 300), rng.randint(500, 1500)])
        crm = rng.choice(CRMS_GOOD + CRMS_OTHER[:2])
        motion = rng.choice(MOTIONS)
        funding = rng.choice(FUNDING)
    else:
        employees = rng.choice([rng.randint(3, 15), rng.randint(1500, 8000)])
        crm = rng.choice(CRMS_OTHER)
        motion = rng.choice(["Product-led", "Sales-led"])
        funding = rng.choice(["Bootstrapped", "Bootstrapped", "Series C"])

    region, country = pick_region(rng, fit)
    stack = rng.sample(STACK_POOL, k=rng.randint(3, 6))
    title = rng.choice(TITLES_GOOD if fit != "poor" or rng.random() < 0.3 else TITLES_OTHER)
    first, last = rng.choice(FIRST), rng.choice(LAST)
    domain = domain_for(name)

    return {
        "company_name": name,
        "domain": domain,
        "industry": industry,
        "description": f"{name} builds {builds} for {buyers}.",
        "employees": employees,
        "country": country,
        "region": region,
        "sales_motion": motion,
        "funding_stage": funding,
        "crm": crm,
        "tech_stack": ";".join(stack),
        "contact_first_name": first,
        "contact_last_name": last,
        "contact_title": title,
        "contact_email": f"{first.lower()}.{last.lower()}@{domain}",
    }


def build_signals(rng: random.Random, company: dict, fit: str, today: date) -> list[dict]:
    n = rng.choices([0, 1, 2, 3], weights={
        "good": [1, 3, 4, 2], "medium": [3, 4, 2, 1], "poor": [6, 3, 1, 0],
    }[fit])[0]
    out = []
    for sig_type, source, template, strength in rng.sample(SIGNALS, k=n):
        detail = template.format(
            k=rng.randint(2, 6),
            title=rng.choice(["VP Sales", "CRO", "Head of Sales"]),
            stage=rng.choice(["Seed", "Series A", "Series B"]),
            old=rng.choice(["Pipedrive", "a spreadsheet", "Zoho CRM"]),
            new=rng.choice(CRMS_GOOD),
            market=rng.choice(MARKETS),
            product=rng.choice(PRODUCTS),
            pct=rng.randint(15, 60),
        )
        days_ago = rng.randint(3, 120)
        out.append({
            "type": sig_type,
            "source": source,
            "detail": detail,
            "strength": strength,
            "date": (today - timedelta(days=days_ago)).isoformat(),
        })
    return sorted(out, key=lambda s: s["date"], reverse=True)


WHY_WON = [
    "New sales leader needed pipeline visibility in the first 90 days",
    "SDR team doubled and lead routing broke",
    "Moved to a new CRM and needed clean data plus enrichment",
    "Series A board asked for a repeatable outbound motion",
    "Expanding into Europe and needed account research at scale",
    "RevOps hire wanted to replace manual list building",
]


def build_closed_won(rng: random.Random, n: int, used: set[str]) -> list[dict]:
    rows = []
    for i in range(n):
        c = build_company(rng, "good", used)
        rows.append({
            "customer_id": f"CW-{i + 1:03d}",
            "company_name": c["company_name"],
            "domain": c["domain"],
            "industry": c["industry"],
            "description": c["description"],
            "employees": c["employees"],
            "region": c["region"],
            "sales_motion": c["sales_motion"],
            "crm": c["crm"],
            "tech_stack": c["tech_stack"],
            "why_won": rng.choice(WHY_WON),
            "deal_size_usd": rng.choice([6000, 9000, 12000, 18000, 24000]),
        })
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=50, help="number of target accounts")
    p.add_argument("--closed-won", type=int, default=15, help="number of closed-won profiles")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--today", default="2026-11-23", help="reference date for signal dates")
    p.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data"))
    args = p.parse_args()

    rng = random.Random(args.seed)
    today = date.fromisoformat(args.today)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    used: set[str] = set()
    # Roughly 30% good fit, 40% medium, 30% poor, shuffled.
    n_good, n_poor = round(args.n * 0.3), round(args.n * 0.3)
    fits = ["good"] * n_good + ["poor"] * n_poor + ["medium"] * (args.n - n_good - n_poor)
    rng.shuffle(fits)

    accounts, signals, key = [], {}, []
    for i, fit in enumerate(fits):
        c = build_company(rng, fit, used)
        accounts.append({"account_id": f"ACC-{i + 1:03d}", **c})
        key.append({"account_id": f"ACC-{i + 1:03d}", "domain": c["domain"], "generated_fit": fit})
        signals[c["domain"]] = build_signals(rng, c, fit, today)

    closed_won = build_closed_won(rng, args.closed_won, used)

    write_csv(out / "accounts.csv", accounts)
    write_csv(out / "closed_won.csv", closed_won)
    write_csv(out / "answer_key.csv", key)
    (out / "signals.json").write_text(json.dumps(signals, indent=2), encoding="utf-8")

    with_signal = sum(1 for s in signals.values() if s)
    print(f"accounts.csv    {len(accounts)} rows")
    print(f"signals.json    {sum(len(s) for s in signals.values())} signals across {with_signal} accounts")
    print(f"closed_won.csv  {len(closed_won)} rows")
    print(f"written to      {out}")


if __name__ == "__main__":
    main()
