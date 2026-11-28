// Scrubbing and the canonical transcript.
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

// The match pattern for one removal entry (see scrubText for the
// separator-variant rule), or null for an empty entry.
function entryPattern(w) {
  const pattern = String(w).split(/[\s-]+/).filter(Boolean)
    .map(escapeRegExp).join('(?:[,\\s-]+)');
  return pattern || null;
}

function entryRegex(w) {
  const pattern = entryPattern(w);
  return pattern
    ? new RegExp('(?<![A-Za-z0-9])' + pattern + '(?![A-Za-z0-9])', 'gi')
    : null;
}

// The spacing repair applied after any removal.
function repairSpacing(out) {
  return out
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/([(\[])\s+/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
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
    // 2.6.12: a removal entry also matches its separator variants —
    // the words of the entry joined by any run of spaces, hyphens
    // or commas — so "Ann-Marie Lee" removes "Ann Marie Lee" and
    // "Ann, Marie Lee" as well as the exact form. (A name spoken as
    // one joined word, e.g. "CarlosCo", still cannot be matched
    // safely and is left as it stands.)
    const re = entryRegex(w);
    if (!re) continue;
    out = out.replace(re, () => { removed += 1; return ''; });
  }
  if (removed) out = repairSpacing(out);
  return { text: out, removed };
}

// ------------------------------------------------- A2 (2.8.0)
// Selective removal for an entry that appears more than once.
// When an entry appears more than PICKER_THRESHOLD times in the
// corrected transcript, the student picks which appearances to
// remove (the picker in main.js); only those are removed. An
// entry that appears exactly once is removed in full — there is
// only the one. (Threshold lowered from 5 to 1 in 2.8.1: a name
// is rarely said more than once, and a second appearance is
// already a choice the student should make.) Appearances are
// counted with the same matching the removal uses, per chunk,
// in chunk order — the ordinal of an appearance is its position
// in that sequence across the whole transcript.
export const PICKER_THRESHOLD = 1;

// The appearances of one entry across the chunks' corrected
// texts: [{ ordinal, phrase }] in order, where phrase is a short
// window of surrounding text from the appearance's own chunk.
export function entryAppearances(chunks, word) {
  const out = [];
  for (const c of chunks || []) {
    const re = entryRegex(word);
    if (!re) break;
    const text = String(c.corrected || '');
    let m;
    while ((m = re.exec(text)) !== null) {
      const start = m.index;
      const end = start + m[0].length;
      const phrase = text
        .slice(Math.max(0, start - 28), Math.min(text.length, end + 28))
        .replace(/\s+/g, ' ')
        .trim();
      out.push({ ordinal: out.length, phrase });
      if (m[0].length === 0) re.lastIndex += 1;
    }
  }
  return out;
}

// Remove only the selected appearances of one entry from one
// text; ordinals are local to this text. Returns { text, removed }.
export function scrubTextSelective(text, word, removeOrdinals) {
  const re = entryRegex(word);
  if (!re || !removeOrdinals || removeOrdinals.size === 0) {
    return { text: String(text || ''), removed: 0 };
  }
  let ord = 0;
  let removed = 0;
  const out = String(text || '').replace(re, (m) => {
    if (removeOrdinals.has(ord++)) { removed += 1; return ''; }
    return m;
  });
  return { text: removed ? repairSpacing(out) : out, removed };
}

// scrubChunks with one entry applied selectively. The ordinals
// are global across the chunks' corrected texts (the sequence
// entryAppearances returns); within a chunk, the raw text's
// appearances are removed at the same local positions — the raw
// and corrected texts of a chunk carry the same words in the
// same order, the glossary pass having changed spellings only.
// The output chunk carries the selectively-scrubbed corrected
// text in its `corrected` field as well as in `text` (2.8.1), so
// a following scrubChunks pass — which builds its text from
// `corrected` — works on this pass's output; before 2.8.1 the
// field was absent and the composed result came out blank.
export function scrubChunksSelective(chunks, word, removeOrdinals) {
  let base = 0;
  return (chunks || []).map((c) => {
    const re = entryRegex(word);
    const count = re ? (String(c.corrected || '').match(re) || []).length : 0;
    const local = new Set();
    for (let i = 0; i < count; i++) {
      if (removeOrdinals && removeOrdinals.has(base + i)) local.add(i);
    }
    base += count;
    const corrected = scrubTextSelective(c.corrected, word, local).text;
    return {
      start: c.start,
      raw: scrubTextSelective(c.raw, word, local).text,
      corrected,
      text: corrected,
    };
  });
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
