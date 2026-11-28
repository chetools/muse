// Component A (webapp 2.8.0): the page-side near-duplicate check
// and its irreversible sketch.
//
// At send time the page snapshots the as-sent transcript as a
// sketch — a multiset of per-word hashes plus the word count —
// and stores it in the recording's IndexedDB record (see
// cache.js). No transcript text is stored for the check, and
// nothing is stored in localStorage. Before a later send for the
// same package, the page builds the new transcript's word counts
// and measures how many words it ADDS against each stored sketch:
// the surplus of the new multiset over the old one, counted
// gross — removed words never offset added words. If the surplus
// is fewer than ADDED_WORDS_THRESHOLD against any earlier
// same-package sketch, the send is refused in the page.
//
// A multiset surplus is the additions count of a word alignment
// that ignores order; for the local edits this check exists to
// catch (a few words deleted, a short passage swapped) it equals
// the aligned count. Pure — Node-tested (the word hash is
// injectable so tests need no Web Crypto).

import { sha256Hex } from './hash.js';

export const ADDED_WORDS_THRESHOLD = 8;

// The plan's normalisation: strip the [mm:ss] chunk markers,
// lowercase, ignore punctuation, split on whitespace.
export function normaliseWords(text) {
  return String(text || '')
    .replace(/\[\d+:\d+\]/g, ' ')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s'-]/gu, ' ')
    .split(/\s+/)
    .filter(Boolean);
}

// The sketch's word hash: the first 16 hex characters (64 bits)
// of the word's SHA-256 — enough that collisions between distinct
// words are not a practical event, and irreversible in the sense
// that the sketch holds no text and no order.
export async function wordHash(word) {
  return (await sha256Hex(word)).slice(0, 16);
}

// Build the sketch of a canonical transcript. hashFn maps a word
// to its sketch hash (defaults to wordHash; tests inject a simple
// function). Returns { count, words: { hash: occurrences } }.
export async function buildSketch(text, hashFn) {
  const hash = hashFn || wordHash;
  const words = normaliseWords(text);
  const counts = new Map();
  for (const w of words) counts.set(w, (counts.get(w) || 0) + 1);
  const out = {};
  for (const [w, n] of counts) out[await hash(w)] = n;
  return { count: words.length, words: out };
}

// How many words `text` adds against a stored sketch: the gross
// surplus of the new word multiset over the sketch's, with early
// exit at `cap` (the caller only needs to know whether the count
// reaches the threshold). Synchronous: the caller builds the new
// side's hash counts once (buildWordCounts) and compares against
// any number of sketches.
export function addedWords(newCounts, sketch, cap) {
  const limit = cap || ADDED_WORDS_THRESHOLD;
  let added = 0;
  const old = (sketch && sketch.words) || {};
  for (const [h, n] of newCounts) {
    added += Math.max(0, n - (old[h] || 0));
    if (added >= limit) return added;
  }
  return added;
}

// The new transcript's word-hash counts as a Map, built with the
// same hashing as buildSketch.
export async function buildWordCounts(text, hashFn) {
  const hash = hashFn || wordHash;
  const counts = new Map();
  for (const w of normaliseWords(text)) {
    const h = await hash(w);
    counts.set(h, (counts.get(h) || 0) + 1);
  }
  return counts;
}
