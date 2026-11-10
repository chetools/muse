// Vocabulary sets for the suspected-identifier heuristic, built from the
// copied ChemEScribe bundle (chemescribe-base/corrections.js, unmodified):
// the glossary vocabulary from the correction pairs' heard forms and terms,
// and the bundled English wordlist. Pure; runs in Node and in the browser.

import { PAIRS, WORDLIST_TEXT } from '../chemescribe-base/corrections.js';

function wordsOf(text, into) {
  for (const w of String(text).toLowerCase().split(/[^a-zà-ÿ0-9]+/)) {
    if (w) into.add(w);
  }
}

export function buildVocabulary() {
  const vocab = new Set();
  for (const p of PAIRS) {
    wordsOf(p.heard, vocab);
    wordsOf(p.term, vocab);
    for (const alt of p.alts || []) wordsOf(alt, vocab);
  }
  const wordlist = new Set(WORDLIST_TEXT.split(' ').filter(Boolean));
  return { vocab, wordlist };
}
