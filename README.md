# Account research agent

An n8n agent that researches a list of target accounts, scores each one against an ideal customer profile, writes a personalised first line for the good ones and pushes everything into HubSpot. It is built with n8n, Claude, Qdrant and a few small code nodes.

All the data is fictional: 50 made-up companies on `.example` domains, plus a made-up seller. Nothing here touches a real company.

## What it does

For each account in `data/accounts.csv`:

1. **Joins buying signals** from `data/signals.json`. These are 0 to 3 dated events, such as hiring SDRs, a new sales leader, funding, a CRM change or a first RevOps hire.
2. **Writes a research brief** with Claude Haiku. The brief covers what the company sells, who it sells to, how it goes to market, the strongest "why now", and a neutral paragraph used for embedding.
3. **Finds lookalikes.** The brief is embedded with Gemini, and Qdrant returns the 3 most similar closed-won customers from `data/closed_won.csv`.
4. **Scores ICP fit from 0 to 100.** Firmographics are worth 45 points, signals 15 (decayed by age with a 45-day half-life) and lookalike similarity 40. Tier A is 70+, B is 45 to 69, C is under 45. Every score comes with a list of reasons.
5. **Writes a first line** with Claude Sonnet, for tiers A and B only. A code check (`code/qa_check.js`) rejects a line that is empty, over 25 words, has a leftover placeholder, uses a banned phrase, opens with a greeting, or names neither the company nor its signal. A rejected line is retried once with the QA errors; if the retry also fails, the line is flagged for a human.
6. **Upserts the company in HubSpot.** It searches by domain, then updates the record if found or creates it if not. The agent writes 7 custom properties: score, tier, score reasons, top buying signal, research brief, first line and QA status.

```
accounts + signals → brief (Haiku) → Qdrant lookalikes → ICP score → first line (Sonnet) → QA → HubSpot
                                                              └── tier C skips the first line
```

## Results from one run

These are the real numbers from n8n execution 60 on 2026-11-23, covering 50 accounts. Full rows are in [`results/sample-run.csv`](results/sample-run.csv) and the summary is in [`results/run-summary.md`](results/run-summary.md).

| | |
|---|---|
| Accounts | 50 in 409 s (about 8 s each) |
| Tiers | A 20, B 8, C 22 |
| HubSpot | 50 updated, 0 errors |
| First lines | 28 written. 21 passed QA first try, 6 passed after one retry, 1 flagged for review |
| Tokens | Haiku 22.5K in / 32.6K out. Sonnet 12.6K in / 9.9K out |

The account generator also writes an answer key (`data/answer_key.csv`) recording whether each account was made as a good, medium or poor fit. The agent never sees it. Grading the run against it with `python scripts/grade_run.py` gives:

|        | A  | B | C  |
|--------|----|---|----|
| good   | 15 | 0 | 0  |
| medium | 5  | 8 | 7  |
| poor   | 0  | 0 | 15 |

All 15 good fits landed in tier A, and all 15 poor fits landed in tier C.

### What calibration fixed

The first run used a lookalike floor of 0.30 and a ceiling of 0.70. Good fits were already 15 of 15 in tier A, but only 3 of 15 poor fits landed in tier C. Gemini similarities in this data sit in a narrow band (0.64 to 0.78), so almost every account got most of the 40 lookalike points. Setting the floor and ceiling to the observed range (0.65 and 0.78) fixed it. One constant change, one re-run.

### Known gaps

- 2 of 50 research briefs came back as JSON the parser couldn't read. Those accounts fell back to the raw signal, and their first lines still passed QA.
- One first line was 27 words against a 25-word limit. It is flagged `needs_review` in HubSpot rather than sent.

## Repo layout

| Path | What it is |
|---|---|
| `n8n/account-research-agent.json` | Main workflow (27 nodes) |
| `n8n/seed-closed-won.json` | Run once: embeds the 15 closed-won customers into Qdrant |
| `code/score_icp.py` | ICP scoring, the reference version |
| `code/score_icp.js` | The same scoring in JavaScript, used in the n8n Code node |
| `code/join_signals.js`, `code/qa_check.js` | Other Code node logic |
| `prompts/` | Research brief and first-line prompts |
| `data/` | Fictional accounts, signals, closed-won customers, ICP and answer key |
| `scripts/generate_accounts.py` | Makes a new fictional dataset (`--n 100 --seed 7`) |
| `scripts/setup_hubspot_properties.py` | Creates the 7 HubSpot company properties |
| `scripts/check_score_parity.py` | Proves the Python and JS scoring match (150 cases, 0 mismatches) |
| `scripts/grade_run.py` | Grades a run against the answer key |

The scoring is written twice on purpose. The n8n instance has no Python runner, so the Code node runs the JS port. The Python version is easier to read and test, and `check_score_parity.py` keeps the two in line.

## Run it yourself

You need an n8n instance (self-hosted or cloud), plus free tiers of Anthropic, Google AI Studio (Gemini), Qdrant Cloud and HubSpot.

1. **HubSpot:** create a service key (or private app) with company read/write and schema write. Put it in `.env` (see `.env.example`), then run `python scripts/setup_hubspot_properties.py`.
2. **n8n credentials:** create Anthropic, Google Gemini (PaLM API), Qdrant and HubSpot App Token credentials.
3. **Import** both files from `n8n/`, then pick your credentials on every node marked `REPLACE_ME`.
4. **Seed Qdrant:** run "ARA - Seed closed-won" once.
5. **Run** "ARA - Account research agent". To try a few accounts first, put their IDs in `TEST_IDS` in the "Get Accounts" node.
6. **Grade it:** copy the `rows` from the "Run Summary" node into `results/sample-run.csv`, then run `python scripts/grade_run.py`.

The accounts and signals are inlined in the "Get Accounts" and "Get Signals" Code nodes, so the workflow runs without access to this repo.

Python 3.10+ for the scripts (standard library only) and Node.js for the parity check.
