// Muse handoff file: one saved file carrying everything the student's
// Muse needs — the assignment configuration, the grading instructions
// (the standalone grading prompt, in this webapp's result-block format),
// and the anonymised transcript exactly as exported by the page.
// The student gives this file, together with the teacher's prompt
// package, to their Muse instead of copying the transcript by hand:
// a file preserves the text byte for byte, where a copy through a chat
// window can change characters and break the result block's hash check.
// Pure functions.

export const HANDOFF_FILE_NAME = 'claude-handoff.md';

const FORMAT_SAMPLE = [
  '=== RESULT ===',
  'Completeness: N/5',
  'Accuracy: N/5',
  'Tally:',
  '- <item label>: full — "<quoted passage>"',
  '- <item label>: half — "<quoted passage>"',
  '- <item label>: zero — "<quoted passage or not stated>"',
  'Critique:',
  '<critique text>',
  '=== END RESULT ===',
  'SHA256: <hash>',
].join('\n');

export function buildHandoff(cfg, transcript) {
  const c = cfg || {};
  const lines = [];
  lines.push('# Grading handoff');
  lines.push('');
  lines.push('Course: ' + (c.course || '(not in the configured link)'));
  lines.push('Assignment: ' + (c.asg || '(not in the configured link)'));
  lines.push('Prompt package: ' + (c.pkg || '(not in the configured link)'));
  lines.push('');
  lines.push('## Instructions for Muse');
  lines.push('');
  lines.push(
    'Grade the transcript at the end of this file against the prompt ' +
    'package identified above, which the student supplies with this ' +
    'file. Report the result ONLY as a result block in the exact ' +
    'format below, with its SHA256 line. No text outside the block ' +
    'and its SHA256 line.');
  lines.push('');
  lines.push('Grading rules:');
  lines.push(
    '- For every key point and every connection in the package\'s ' +
    'checklist, award full, half, or zero, and quote the transcript ' +
    'passage that earns the mark (for zero, quote the nearest ' +
    'relevant passage, or write "not stated" in the quotes).');
  lines.push(
    '- A statement that contradicts a connection voids that ' +
    'connection: mark it zero even if the connection is also stated ' +
    'correctly elsewhere.');
  lines.push(
    '- Completeness (0-5, whole number, rounding up) measures ' +
    'coverage: the weighted fraction of checklist items marked half ' +
    'or better. Accuracy (0-5, whole number, rounding up) measures ' +
    'correctness: the weighted fraction of earned marks over the ' +
    'items attempted.');
  lines.push(
    '- The critique states what the explanation lacked. Never quote ' +
    'the checklist, the key, or any weights in the critique.');
  lines.push('- These are predicted grades.');
  lines.push('');
  lines.push('Format, exactly:');
  lines.push('');
  lines.push(FORMAT_SAMPLE);
  lines.push('');
  lines.push(
    'Hash rule: the SHA256 line holds the SHA-256 (lowercase hex) of ' +
    'the block exactly as emitted — every character from the start ' +
    'of "=== RESULT ===" through the end of the "=== END RESULT ===" ' +
    'line, each line ending in a single newline (LF), UTF-8. The ' +
    'SHA256 line itself is not part of the hashed text.');
  lines.push('');
  lines.push(
    'Do NOT invent or estimate the hash. Write the block to a file, ' +
    'compute the hash by running code (for example Python\'s ' +
    'hashlib over the file), and only then output the block with ' +
    'the computed SHA256 line appended. If you cannot run code, say ' +
    'so plainly instead of emitting a hash.');
  lines.push('');
  lines.push('## Transcript (anonymised)');
  lines.push('');
  lines.push(String(transcript || ''));
  lines.push('');
  return lines.join('\n');
}
