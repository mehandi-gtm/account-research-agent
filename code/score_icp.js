// ICP fit score: firmographics (45) + signals (15) + lookalike (40) = 0-100.
// JavaScript port of code/score_icp.py, used in the n8n Code node ("Run Once for Each Item")
// because the n8n instance has no Python runner. scripts/check_score_parity.py proves both
// versions give identical scores on all 50 accounts.

const ICP_REGIONS = ['EU', 'UK', 'US'];
const GOOD_CRMS = ['HubSpot', 'Salesforce'];
const OK_CRMS = ['Pipedrive', 'Zoho CRM'];

// Lookalike: cosine similarity below SIM_FLOOR scores 0, at or above SIM_CEIL scores 40.
// Calibrated on the first 50-account run: similarities ranged 0.649 to 0.782.
const SIM_FLOOR = 0.65;
const SIM_CEIL = 0.78;

const SIGNAL_HALF_LIFE_DAYS = 45;

// Python-style round (banker's rounding) so scores match score_icp.py exactly.
function pyRound(x) {
  const r = Math.round(x);
  return Math.abs(x % 1) === 0.5 && r % 2 !== 0 ? r - 1 : r;
}

function firmographicPoints(a) {
  let pts = 0;
  const why = [];
  if (a.industry.startsWith('B2B SaaS')) { pts += 15; why.push('B2B SaaS (+15)'); }
  else if (a.industry === 'IT Services') { pts += 4; why.push('IT services, adjacent (+4)'); }

  const emp = parseInt(a.employees, 10);
  if (emp >= 20 && emp <= 500) { pts += 10; why.push(emp + ' employees, in range (+10)'); }
  else if ((emp >= 10 && emp < 20) || (emp > 500 && emp <= 1000)) { pts += 5; why.push(emp + ' employees, near range (+5)'); }

  if (ICP_REGIONS.includes(a.region)) { pts += 10; why.push(a.region + ' region (+10)'); }

  if (GOOD_CRMS.includes(a.crm)) { pts += 7; why.push('uses ' + a.crm + ' (+7)'); }
  else if (OK_CRMS.includes(a.crm)) { pts += 3; why.push('uses ' + a.crm + ' (+3)'); }

  if (a.sales_motion === 'Sales-led' || a.sales_motion === 'Hybrid') { pts += 3; why.push(a.sales_motion + ' motion (+3)'); }
  return [pts, why];
}

function dayNumber(iso) {
  return Math.round(Date.parse(iso.slice(0, 10) + 'T00:00:00Z') / 86400000);
}

function signalPoints(signals, today) {
  let raw = 0;
  const why = [];
  for (const s of signals) {
    const age = Math.max(0, dayNumber(today) - dayNumber(s.date));
    const value = s.strength * 5 * Math.pow(0.5, age / SIGNAL_HALF_LIFE_DAYS);
    raw += value;
    why.push(s.detail + ', ' + age + 'd ago (+' + value.toFixed(1) + ')');
  }
  return [Math.min(15, pyRound(raw)), why];
}

function lookalikePoints(similarity) {
  if (similarity === null || similarity === undefined) return 0;
  const x = (similarity - SIM_FLOOR) / (SIM_CEIL - SIM_FLOOR);
  return pyRound(40 * Math.max(0, Math.min(1, x)));
}

function tier(score) {
  return score >= 70 ? 'A' : score >= 45 ? 'B' : 'C';
}

function scoreAccount(a, signals, similarity, today) {
  const [fPts, fWhy] = firmographicPoints(a);
  const [sPts, sWhy] = signalPoints(signals, today);
  const lPts = lookalikePoints(similarity);
  const total = fPts + sPts + lPts;
  const reasons = [...fWhy, ...sWhy];
  if (similarity !== null && similarity !== undefined) {
    reasons.push('lookalike similarity ' + similarity.toFixed(2) + ' (+' + lPts + ')');
  }
  return {
    icp_score: total,
    icp_tier: tier(total),
    score_firmographic: fPts,
    score_signals: sPts,
    score_lookalike: lPts,
    score_reasons: reasons,
  };
}

// ---- n8n wrapper (Code node, "Run Once for Each Item"). `run_date` comes from Join Signals.
if (typeof $input !== 'undefined') {
  const a = $input.item.json;
  return { json: { ...a, ...scoreAccount(a, a.signals || [], a.lookalike_similarity, a.run_date) } };
}

module.exports = { scoreAccount };
