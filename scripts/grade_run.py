"""Grade a run against data/answer_key.csv (how the fake data was generated: good / medium / poor fit).

Input: results/sample-run.csv from the "Run Summary" node (account_id, icp_tier, icp_score, ...).
    python scripts/grade_run.py results/sample-run.csv
"""

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
run_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results/sample-run.csv"

key = {r["account_id"]: r["generated_fit"] for r in csv.DictReader((ROOT / "data/answer_key.csv").open(encoding="utf-8"))}
run = {r["account_id"]: r for r in csv.DictReader(run_path.open(encoding="utf-8"))}

matrix = Counter((key[a], run[a]["icp_tier"]) for a in run)
fits, tiers = ["good", "medium", "poor"], ["A", "B", "C"]

print("generated fit vs ICP tier")
print("        " + "".join(f"{t:>6}" for t in tiers) + "   total")
for f in fits:
    row = [matrix[(f, t)] for t in tiers]
    print(f"{f:<8}" + "".join(f"{n:>6}" for n in row) + f"{sum(row):>8}")

good_total = sum(matrix[("good", t)] for t in tiers)
poor_total = sum(matrix[("poor", t)] for t in tiers)
print()
print(f"good-fit accounts in tier A or B: {matrix[('good', 'A')] + matrix[('good', 'B')]} of {good_total}")
print(f"good-fit accounts in tier A:      {matrix[('good', 'A')]} of {good_total}")
print(f"poor-fit accounts in tier C:      {matrix[('poor', 'C')]} of {poor_total}")
print(f"poor-fit accounts in tier A:      {matrix[('poor', 'A')]}")
