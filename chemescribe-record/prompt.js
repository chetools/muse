// The correction prompt this page hands to the reader, verbatim.
// Keeping it in one module means the visible prompt box, the two copy
// buttons and the node tests all work from exactly the same text.
export const PROMPT_TEXT = 'Correct the transcript below with the ChemEScribe skill ' +
  '(https://github.com/chetools/muse/tree/main/chemescribe-skill). Use the skill’s ' +
  'chemical-engineering glossary in context: apply its certain corrections, resolve ' +
  'sound-alike terms from the sentence context, and fix other mishearings only where ' +
  'a glossary term fits both the sound and the context. Keep my wording and sentences ' +
  'as spoken. Do not change numbers, units, or negations. List every correction you ' +
  'make, and leave anything you cannot settle in the skill’s slash form — the heard ' +
  'word first, then the possibilities, slash-separated with no spaces.\n\nTranscript:\n';

// "Copy prompt": the prompt alone; it ends with "Transcript:" and a
// blank line where the transcript goes.
export function promptPayload() {
  return PROMPT_TEXT;
}

// "Copy prompt with transcript": the prompt followed by the current
// raw transcript, ready to paste into Muse in one action.
export function promptWithTranscript(transcript) {
  return PROMPT_TEXT + String(transcript || '');
}
