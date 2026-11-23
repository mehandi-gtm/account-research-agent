# Ideal Customer Profile (fictional seller)

The seller in this demo is a made-up company that sells an outbound pipeline service to B2B software teams.

**Good fit**
- B2B SaaS (any vertical)
- 20 to 500 employees
- Based in the EU, UK or US
- Uses HubSpot or Salesforce
- Sales-led or hybrid go-to-market
- A recent "why now" signal: hiring SDRs, a new sales leader, fresh funding, a CRM change, a first RevOps hire

**Poor fit**
- Agencies, e-commerce brands, manufacturing, hospitality, non-profits
- Under 10 or over 1,000 employees
- No CRM, or a spreadsheet as the CRM

## Scoring (0 to 100)
| Part | Points | Where it is computed |
|---|---|---|
| Firmographics: industry 15, size 10, region 10, CRM 7, motion 3 | 45 | `code/score_icp.py` |
| Signals: strength of the freshest signals, decayed by age | 15 | `code/score_icp.py` |
| Lookalike: cosine similarity to the nearest closed-won customer in Qdrant | 40 | Qdrant search, mapped in `code/score_icp.py` |

Tier A is 70 or more, tier B is 45 to 69, and tier C is under 45. Only tiers A and B get a first line.
