// QA gate for the AI-written first line. Runs before anything is written to the CRM.
// n8n Code node (JavaScript), mode "Run Once for Each Item".
// Expects on the item: company_name, top_signal, first_line, and qa_attempt (1 or 2).
// Output: the item plus qa_status ("pass" | "retry" | "needs_review") and qa_errors[].
// Route "retry" back to the first-line writer once. Then "needs_review" goes to the CRM flagged.

const MAX_WORDS = 25;

const PLACEHOLDER_PATTERNS = [
  /\{\{.*?\}\}/,          // unrendered template tags
  /\[[A-Z][^\]]*\]/,      // [Company], [First Name]
  /<[^>]+>/,              // <company>
  /\b(undefined|null|NaN)\b/,
  /\bTODO\b|\bTBD\b|lorem ipsum/i,
];

const BANNED_PHRASES = [
  'hope this finds you', 'i came across', 'i noticed that you', 'quick question',
  'touch base', 'synergy', 'game-changer', 'revolutionize', 'as an ai',
  'i wanted to reach out',
];

function check(item) {
  const line = String(item.first_line ?? '').trim();
  const errors = [];

  if (!line) errors.push('empty');
  for (const re of PLACEHOLDER_PATTERNS) {
    if (re.test(line)) errors.push(`placeholder: ${line.match(re)[0]}`);
  }
  const words = line.split(/\s+/).filter(Boolean).length;
  if (words > MAX_WORDS) errors.push(`too long: ${words} words`);

  const lower = line.toLowerCase();
  for (const p of BANNED_PHRASES) if (lower.includes(p)) errors.push(`banned phrase: "${p}"`);

  // Must reference the company or something concrete from the signal.
  const company = String(item.company_name ?? '').toLowerCase().replace(/ (labs|hq|systems|co)$/, '');
  const signalWords = String(item.top_signal ?? '')
    .toLowerCase()
    .replace(/\(.*?\)/g, '')
    .split(/\W+/)
    .filter((w) => w.length > 4);
  const mentionsCompany = company && lower.includes(company);
  const mentionsSignal = signalWords.some((w) => lower.includes(w));
  if (!mentionsCompany && !mentionsSignal) errors.push('no company or signal reference');

  if ((line.match(/!/g) || []).length > 1) errors.push('too many exclamation marks');
  if (/^(hi|hey|hello|dear)\b/i.test(line)) errors.push('starts with a greeting');

  return errors;
}

const item = $input.item.json;
const errors = check(item);
const attempt = Number(item.qa_attempt ?? 1);

return {
  json: {
    ...item,
    qa_errors: errors,
    qa_status: errors.length === 0 ? 'pass' : attempt < 2 ? 'retry' : 'needs_review',
    qa_attempt: attempt,
  },
};
