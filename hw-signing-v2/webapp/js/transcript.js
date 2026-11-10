// Scrubbing, canonical transcript, and suspected-identifier detection.
// Pure functions. A chunk is { start: seconds, raw: string, corrected: string }
// where corrected is the glossary-corrected text before scrubbing.

export function parseScrubWords(fieldText) {
  const seen = new Set();
  const words = [];
  for (const part of String(fieldText || '').split(/[\n,]+/)) {
    const w = part.trim();
    if (w && !seen.has(w.toLowerCase())) {
      seen.add(w.toLowerCase());
      words.push(w);
    }
  }
  return words;
}

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Remove every occurrence of each scrub word (longest first, case-insensitive,
// at letter/digit boundaries like the correction pass), then repair the
// spacing the removal leaves behind. Returns { text, removed }.
export function scrubText(text, words) {
  let out = String(text || '');
  let removed = 0;
  const ordered = [...(words || [])].filter(Boolean)
    .sort((a, b) => b.length - a.length);
  for (const w of ordered) {
    const re = new RegExp(
      '(?<![A-Za-z0-9])' + escapeRegExp(w) + '(?![A-Za-z0-9])', 'gi');
    out = out.replace(re, () => { removed += 1; return ''; });
  }
  if (removed) {
    out = out
      .replace(/\s+([,.;:!?])/g, '$1')
      .replace(/([(\[])\s+/g, '$1')
      .replace(/\s+/g, ' ')
      .trim();
  }
  return { text: out, removed };
}

// Scrub one string that will be shown or exported as metadata (for example
// a source file name). Same removal rule as the transcript.
export function scrubMetadata(value, words) {
  return scrubText(value, words).text;
}

// Apply scrub words to both the raw and corrected text of every chunk.
export function scrubChunks(chunks, words) {
  return (chunks || []).map((c) => ({
    start: c.start,
    raw: scrubText(c.raw, words).text,
    text: scrubText(c.corrected, words).text,
  }));
}

// [mm:ss] with total minutes, zero-padded to two digits (can exceed 59) —
// the same marker form as the submission package's transcript lines, so
// a canonical line and its package line carry the same marker.
export function formatChunkMarker(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const mm = String(Math.floor(s / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  return '[' + mm + ':' + ss + ']';
}

// Canonical transcript (plan, Interfaces): scrubbed plain text, one chunk
// per line, LF line endings, no trailing spaces, and no trailing newline.
// Chunk whitespace is collapsed so each chunk is one line. Since 2.4.2
// each line begins with the chunk's [mm:ss] start marker (the teacher's
// direction, 2026-11-10: time markers in future transcripts), so a point
// in the transcript — in particular an injection flag — can be located
// in the recording.
export function canonicalTranscript(scrubbedChunks) {
  return (scrubbedChunks || [])
    .map((c) => {
      const text = String(c.text || '').replace(/\s+/g, ' ').trim();
      return text ? formatChunkMarker(c.start) + ' ' + text : '';
    })
    .filter((line) => line.length > 0)
    .join('\n');
}

// The pre-2.4.2 canonical form: the same lines without the markers.
// Used only to verify a bundle graded before 2.4.2, whose signed
// transcript checksum was taken over the markerless form.
export function legacyCanonicalTranscript(scrubbedChunks) {
  return (scrubbedChunks || [])
    .map((c) => String(c.text || '').replace(/\s+/g, ' ').trim())
    .filter((line) => line.length > 0)
    .join('\n');
}

const EMAIL_RE = /[\w.+-]+@[\w-]+(\.[\w-]+)+/g;
const WORD_RE = /[A-Za-z][A-Za-z'’-]*[A-Za-z]|[A-Za-z]/g;

// Suspected identifiers in scrubbed text, for the student review screen:
// email-like patterns, and capitalised words that are not sentence-initial
// and appear in neither the glossary vocabulary nor the English wordlist.
// Returns [{ word, count, reason }] sorted by count, then alphabetically.
export function findSuspects(scrubbedChunks, vocabSet, wordlistSet) {
  const found = new Map();
  const add = (word, reason) => {
    const key = word.toLowerCase() + '|' + reason;
    const prev = found.get(key);
    if (prev) prev.count += 1;
    else found.set(key, { word, count: 1, reason });
  };
  for (const chunk of scrubbedChunks || []) {
    const text = String(chunk.text || '');
    for (const m of text.matchAll(EMAIL_RE)) add(m[0], 'email-like pattern');
    for (const m of text.matchAll(WORD_RE)) {
      const word = m[0];
      if (!/^[A-Z]/.test(word)) continue;
      const before = text.slice(0, m.index).replace(/\s+$/, '');
      const sentenceInitial = before === '' || /[.!?…]["'”’)\]]*$/.test(before);
      if (sentenceInitial) continue;
      const lower = word.toLowerCase().replace(/['’]s$/, '');
      if (vocabSet && vocabSet.has(lower)) continue;
      if (wordlistSet && wordlistSet.has(lower)) continue;
      add(word, 'capitalised word not in the glossary vocabulary');
    }
  }
  return [...found.values()]
    .sort((a, b) => b.count - a.count || a.word.localeCompare(b.word));
}

// [mm:ss] or [h:mm:ss] plain-text timestamp, as on the base page.
export function formatClock(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  if (s >= 3600) return Math.floor(s / 3600) + ':' + mm + ':' + ss;
  return mm + ':' + ss;
}

// Duration in seconds, the SI unit, to one decimal place: "754.0 s".
export function formatDuration(seconds) {
  const v = Math.round((Number(seconds) || 0) * 10) / 10;
  return v.toFixed(1) + ' s';
}
