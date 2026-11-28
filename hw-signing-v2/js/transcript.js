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
// texts: [{ ordinal, phrase, phraseMatchStart, phraseMatchLength }]
// in order, where phrase is a short window of surrounding text
// from the appearance's own chunk, and the phraseMatch fields
// locate the appearance itself inside the phrase (2.9.1: the
// picker highlights exactly those characters, so the student
// sees which words a checkbox would remove). The phrase is
// assembled from its three parts — before, match, after — each
// whitespace-collapsed as the whole window used to be; the two
// constructions agree because a match never begins or ends with
// whitespace (the entry pattern starts and ends with an entry
// part), so no whitespace run spans a part boundary.
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
      const before = text.slice(Math.max(0, start - 28), start)
        .replace(/\s+/g, ' ');
      const match = text.slice(start, end).replace(/\s+/g, ' ');
      const after = text.slice(end, Math.min(text.length, end + 28))
        .replace(/\s+/g, ' ');
      const joined = before + match + after;
      const phrase = joined.trim();
      // Any leading trim comes out of the "before" part: it is
      // at most the one collapsed space a leading whitespace run
      // leaves, and the match itself is never trimmed away.
      const lead = joined.length - joined.trimStart().length;
      out.push({
        ordinal: out.length,
        phrase,
        phraseMatchStart: Math.max(0, before.length - lead),
        phraseMatchLength: match.length,
      });
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

// ------------------------------------------------- Highlight (2.9.1)
// removalSegments: what the transcript view and the picker show
// on a coloured background — the substrings the removal state
// will remove. The view is a rendering layer only; the scrubbed
// text that is sent is still produced by the functions above,
// untouched. To keep highlight and removal from ever disagreeing,
// the spans are found by replaying the scrub's own passes — the
// selective passes in list order, then the full pass, longest
// first — with the same entryRegex matching and the same spacing
// repair, over a tracked text: every character carries the index
// it holds in the chunk's corrected text, so a removal found in
// the evolving (already partly scrubbed, spacing-repaired) text
// is recorded in the original text's coordinates.

// One chunk's corrected text under tracking: chars (UTF-16 code
// units, so indices agree with the regex matches), the original
// index of each char, and the removed spans found so far, as
// [start, end) in original coordinates.
function trackText(text) {
  const s = String(text || '');
  const chars = new Array(s.length);
  const origin = new Array(s.length);
  for (let i = 0; i < s.length; i++) { chars[i] = s[i]; origin[i] = i; }
  return { chars, origin, spans: [] };
}

function trackString(st) { return st.chars.join(''); }

// Every match of the entry regex in the string, as [start, end).
function findMatches(re, s) {
  const out = [];
  if (!re) return out;
  let m;
  while ((m = re.exec(s)) !== null) {
    out.push([m.index, m.index + m[0].length]);
    if (m[0].length === 0) re.lastIndex += 1;
  }
  return out;
}

// Record the given matches (ascending, non-overlapping, in
// current-string coordinates) as removed spans and delete them.
function trackRemoveMatches(st, matches) {
  for (let k = matches.length - 1; k >= 0; k--) {
    const [s, e] = matches[k];
    if (e <= s) continue;
    st.spans.push([st.origin[s], st.origin[e - 1] + 1]);
    st.chars.splice(s, e - s);
    st.origin.splice(s, e - s);
  }
}

// Delete the given ranges (ascending, non-overlapping, in
// current-string coordinates) without recording them: the
// spacing repair's deletions, which remove no words.
function trackDeleteRanges(st, ranges) {
  for (let k = ranges.length - 1; k >= 0; k--) {
    const [s, e] = ranges[k];
    if (e <= s) continue;
    st.chars.splice(s, e - s);
    st.origin.splice(s, e - s);
  }
}

// repairSpacing over the tracked text: the same four steps, in
// the same order, expressed as deletions and collapses so the
// origin of every surviving character is preserved.
function trackRepairSpacing(st) {
  let ranges = [];
  for (const m of trackString(st).matchAll(/\s+(?=[,.;:!?])/g)) {
    ranges.push([m.index, m.index + m[0].length]);
  }
  trackDeleteRanges(st, ranges);
  ranges = [];
  for (const m of trackString(st).matchAll(/(?<=[(\[])\s+/g)) {
    ranges.push([m.index, m.index + m[0].length]);
  }
  trackDeleteRanges(st, ranges);
  const cur = trackString(st);
  ranges = [];
  for (const m of cur.matchAll(/\s+/g)) {
    st.chars[m.index] = ' ';
    if (m[0].length > 1) ranges.push([m.index + 1, m.index + m[0].length]);
  }
  trackDeleteRanges(st, ranges);
  const s = trackString(st);
  const lead = s.match(/^\s*/)[0].length;
  if (lead === s.length) {
    if (lead) trackDeleteRanges(st, [[0, lead]]);
    return;
  }
  const trail = s.match(/\s*$/)[0].length;
  ranges = [];
  if (lead) ranges.push([0, lead]);
  if (trail) ranges.push([s.length - trail, s.length]);
  trackDeleteRanges(st, ranges);
}

// One selective pass over one chunk, mirroring scrubTextSelective
// as scrubChunksSelective drives it: the matches are counted in
// the chunk's current text, the ones whose global ordinal (base
// + local position) is in removedSet are removed, and the
// spacing is repaired when anything went. Returns the number of
// appearances counted, so the caller can advance the base.
function trackSelectivePass(st, word, removedSet, base) {
  const re = entryRegex(word);
  if (!re) return 0;
  const matches = findMatches(re, trackString(st));
  const chosen = matches.filter((_, i) => removedSet && removedSet.has(base + i));
  if (chosen.length) {
    trackRemoveMatches(st, chosen);
    trackRepairSpacing(st);
  }
  return matches.length;
}

// The full pass over one chunk, mirroring scrubText: every entry,
// longest first, all its matches removed from the evolving text,
// then one spacing repair if anything was removed.
function trackFullPass(st, words) {
  const ordered = [...(words || [])].filter(Boolean)
    .sort((a, b) => b.length - a.length);
  let removed = 0;
  for (const w of ordered) {
    const matches = findMatches(entryRegex(w), trackString(st));
    if (matches.length) {
      trackRemoveMatches(st, matches);
      removed += matches.length;
    }
  }
  if (removed) trackRepairSpacing(st);
}

// The segments of each chunk's corrected text under a removal
// state: [{ start, segments: [{ text, removed }] }], where the
// segments concatenate to the chunk's corrected text exactly and
// the removed segments are the substrings the composed scrub
// (selective passes for the entries in `selective` — a Map of
// entry -> Set of removed appearance ordinals, in list order —
// then the full pass for the `ordinary` entries) removes from
// it. Overlapping spans (a later match spanning an earlier
// removal, joined by the spacing repair) are merged for display.
export function removalSegments(chunks, selective, ordinary) {
  const list = chunks || [];
  const states = list.map((c) => trackText(c.corrected));
  for (const [word, removedSet] of selective || []) {
    let base = 0;
    for (const st of states) {
      base += trackSelectivePass(st, word, removedSet, base);
    }
  }
  for (const st of states) trackFullPass(st, ordinary);
  return list.map((c, i) => {
    const src = String(c.corrected || '');
    const spans = states[i].spans.slice()
      .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const merged = [];
    for (const [s, e] of spans) {
      const last = merged[merged.length - 1];
      if (last && s <= last[1]) { if (e > last[1]) last[1] = e; }
      else merged.push([s, e]);
    }
    const segments = [];
    let pos = 0;
    for (const [s, e] of merged) {
      if (s > pos) segments.push({ text: src.slice(pos, s), removed: false });
      if (e > s) segments.push({ text: src.slice(s, e), removed: true });
      pos = Math.max(pos, e);
    }
    if (pos < src.length) {
      segments.push({ text: src.slice(pos), removed: false });
    }
    return { start: c.start, segments };
  });
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
