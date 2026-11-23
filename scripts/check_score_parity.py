"""Check that code/score_icp.js (used in n8n) and code/score_icp.py give identical results.

Scores all 50 accounts with a spread of lookalike similarities in both languages.
Needs Python 3.10+ and Node.js:
    python scripts/check_score_parity.py
"""

import csv
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from score_icp import score_account  # noqa: E402

TODAY = "2026-11-23"
signals = json.loads((ROOT / "data/signals.json").read_text(encoding="utf-8"))
accounts = list(csv.DictReader((ROOT / "data/accounts.csv").open(encoding="utf-8")))

rng = random.Random(7)
cases = []
for a in accounts:
    for sim in (None, round(rng.uniform(0.2, 0.9), 3), round(rng.uniform(0.2, 0.9), 3)):
        cases.append({"a": a, "signals": signals.get(a["domain"], []), "sim": sim})

js = (
    "const { scoreAccount } = require(process.argv[1]);"
    "const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
    "console.log(JSON.stringify(cases.map(c => scoreAccount(c.a, c.signals, c.sim, process.argv[2]))));"
)
out = subprocess.run(["node", "-e", js, str(ROOT / "code/score_icp.js"), TODAY],
                     input=json.dumps(cases), capture_output=True, text=True, check=True)
js_results = json.loads(out.stdout)

mismatches = 0
for case, js_r in zip(cases, js_results):
    py_r = score_account(case["a"], case["signals"], case["sim"], TODAY)
    if py_r != js_r:
        mismatches += 1
        print("MISMATCH", case["a"]["account_id"], case["sim"], py_r, js_r)

print(f"{len(cases)} cases, {mismatches} mismatches")
sys.exit(1 if mismatches else 0)
