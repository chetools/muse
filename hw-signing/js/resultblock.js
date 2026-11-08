// Student-Muse result block: extraction, parsing, hash validation.
// Pure functions (hashing is injected by the caller from js/hash.js).
//
// Format — Stage 6 (the grading skill) emits exactly this:
//   === RESULT ===
//   Completeness: 4/5
//   Accuracy: 3/5
//   Tally:
//   - <point label>: full — "<quoted transcript passage>"
//   - <point label>: half — "<quoted transcript passage>"
//   Critique:
//   <critique text, one or more lines>
//   === END RESULT ===
//   SHA256: <64 lowercase hex characters>
// Hash definition (identical to the skill's scripts/block_hash.py): the
// SHA-256, lowercase hex, of the block exactly as emitted — the text from
// the first character of the === RESULT === line through the end of the
// === END RESULT === line, every line (including the last) terminated by
// exactly one LF, encoded as UTF-8. The SHA256 line sits outside the
// hashed text. Delimiter lines must match exactly, as in the skill.

export const RESULT_START = '=== RESULT ===';
export const RESULT_END = '=== END RESULT ===';
const HASH_LINE_RE = /^SHA256: ([0-9a-f]{64})$/;

// Split pasted text into { block, hash } — block is the canonical hashed
// text (lines joined by LF, with a final LF), hash the value from the
// SHA256 line. Null when the delimiters or the hash line are absent.
export function extractResultBlock(pasted) {
  const lines = String(pasted || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n')
    .split('\n');
  const start = lines.indexOf(RESULT_START);
  const end = start < 0 ? -1 : lines.indexOf(RESULT_END, start);
  if (start < 0 || end < 0) return null;
  const block = lines.slice(start, end + 1).join('\n') + '\n';
  let hash = null;
  for (let i = end + 1; i < lines.length; i++) {
    if (lines[i] === '') continue;
    const m = lines[i].match(HASH_LINE_RE);
    if (!m) return null; // first non-blank line after the block is not the hash line
    hash = m[1];
    break;
  }
  if (!hash) return null;
  return { block, hash };
}

// Parse the block's contents. Returns { completeness, accuracy, tally,
// critique } with tally entries { label, score, passage }, or null when
// the block does not follow the format.
export function parseResultBlock(block) {
  const lines = String(block || '').split('\n');
  const comp = lines.join('\n').match(/^Completeness: ([0-5])\/5\s*$/m);
  const acc = lines.join('\n').match(/^Accuracy: ([0-5])\/5\s*$/m);
  if (!comp || !acc) return null;
  const tallyStart = lines.findIndex((l) => l.trim() === 'Tally:');
  const critiqueStart = lines.findIndex((l) => l.trim() === 'Critique:');
  if (tallyStart < 0 || critiqueStart < 0 || critiqueStart <= tallyStart) {
    return null;
  }
  const tally = [];
  for (const line of lines.slice(tallyStart + 1, critiqueStart)) {
    const t = line.trim();
    if (!t) continue;
    const m = t.match(/^- (.+?): (full|half|zero) — "(.*)"$/);
    if (!m) return null;
    tally.push({ label: m[1], score: m[2], passage: m[3] });
  }
  if (!tally.length) return null;
  const critique = lines
    .slice(critiqueStart + 1)
    .filter((l) => l.trim() !== RESULT_END)
    .join('\n')
    .trim();
  if (!critique) return null;
  return {
    completeness: Number(comp[1]),
    accuracy: Number(acc[1]),
    tally,
    critique,
  };
}

// Validate pasted text: delimiters present, hash matches the block
// exactly as emitted, and the block parses. sha256HexFn is js/hash.js's
// sha256Hex. Returns { ok: true, parsed } or { ok: false, reason }.
export async function validateResultBlock(pasted, sha256HexFn) {
  const extracted = extractResultBlock(pasted);
  if (!extracted) {
    return { ok: false, reason: 'Result block or its SHA256 line not found.' };
  }
  const computed = await sha256HexFn(extracted.block);
  if (computed !== extracted.hash) {
    return { ok: false, reason: 'Result block hash does not match the block. The block was changed after Muse emitted it.' };
  }
  const parsed = parseResultBlock(extracted.block);
  if (!parsed) {
    return { ok: false, reason: 'Result block does not follow the required format.' };
  }
  return { ok: true, parsed };
}
