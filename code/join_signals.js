// n8n Code node (JavaScript), mode "Run Once for All Items".
// Input 1: the account rows from "Extract from File" (accounts.csv).
// signals.json is fetched by an earlier HTTP Request node named "Get Signals".
// Output: one item per account with `signals` (newest first) and `top_signal`.

const signalsByDomain = $('Get Signals').first().json;
const runStartedAt = new Date().toISOString();
const runDate = runStartedAt.slice(0, 10); // used for signal decay in Score ICP

return $input.all().map(({ json: account }) => {
  const signals = signalsByDomain[account.domain] ?? [];
  // Strongest signal wins; ties go to the most recent one.
  const top = [...signals].sort(
    (a, b) => b.strength - a.strength || b.date.localeCompare(a.date)
  )[0];

  return {
    json: {
      ...account,
      employees: Number(account.employees),
      tech_stack: String(account.tech_stack || '').split(';').filter(Boolean),
      signals,
      top_signal: top ? `${top.detail} (${top.date})` : null,
      run_date: runDate,
      run_started_at: runStartedAt,
    },
  };
});
