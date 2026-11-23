# Run summary (2026-11-23, 50 dummy accounts)

Numbers from n8n execution 60, after calibrating the lookalike floor and ceiling to 0.65 / 0.78.
Rows are in `sample-run.csv`. Grade with `python scripts/grade_run.py`.

| | |
|---|---|
| Accounts processed | 50 |
| Run time | 409 s (about 8 s per account) |
| Tiers | A 20, B 8, C 22 |
| HubSpot | 50 updated, 0 errors |
| First lines written (tier A and B only) | 28 |
| QA pass on first try | 21 |
| QA pass after one retry | 6 |
| Flagged for human review | 1 (27 words, limit is 25) |
| Brief JSON parse failures | 2 (fell back to the raw signal, first line still passed QA) |
| Lookalike similarity | min 0.638, median 0.705, max 0.773 |
| Tokens, Haiku briefs | 22,552 in / 32,600 out |
| Tokens, Sonnet first lines | 12,606 in / 9,900 out |

## Tier vs how the dummy data was generated

|        | A  | B | C  |
|--------|----|---|----|
| good   | 15 | 0 | 0  |
| medium | 5  | 8 | 7  |
| poor   | 0  | 0 | 15 |

- Good-fit accounts in tier A: 15 of 15
- Poor-fit accounts in tier C: 15 of 15
- Poor-fit accounts in tier A: 0

## Before calibration (first run, floor 0.30 / ceiling 0.70)

Good-fit in tier A was 15 of 15, but only 3 of 15 poor-fit accounts landed in tier C.
Gemini similarities sit in a narrow band (0.64 to 0.78), so a 0.30 floor gave almost every
account most of the 40 lookalike points. Setting the floor and ceiling to the observed range fixed it.
