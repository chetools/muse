// Cache key rules for the IndexedDB recordings store (SPEC, Webapp
// section). Pure functions — the Node tests exercise these directly.
//
// A cached transcription is a property of the recording and of the
// pipeline that produced it, and of nothing else: the key is the audio
// fingerprint plus the model version plus the glossary bundle version.
// Course, assignment and prompt package are deliberately NOT inputs —
// a transcript made under one course's link is the correct transcript
// under another's, and packaging/grading metadata is applied later,
// fresh, under whichever link is open.

// The IndexedDB store is keyed by audio_sha256 alone (one record per
// recording); this key identifies the transcription within the record.
export function cacheKey(audioSha256, model, glossary) {
  return [audioSha256, model, glossary].join('|');
}

// A record is a hit only when it was produced by the same model and
// the same glossary bundle as the page is running now. A version
// change on either makes every older record a miss.
export function cacheHit(record, model, glossary) {
  if (!record) return false;
  return record.audio_sha256 != null &&
    record.model === model &&
    record.glossary === glossary;
}

// A transcription run identifier (2.8.0): minted when a record's
// transcription state is created or reset, and kept across
// resumes of the same run (a resumed run is the same run). It is
// sent with the job (Worker 2.9.0) so a byte-identical
// resubmission of the same run is recognised as a replay, while
// a genuine re-transcription — a new record, or a record reset
// by a model or glossary change — carries a new identifier and
// is a new submission. 16 random bytes as hex (32 characters).
export function mintRunId(randomBytes) {
  const draw = randomBytes || ((n) => {
    const buf = new Uint8Array(n);
    globalThis.crypto.getRandomValues(buf);
    return buf;
  });
  return [...draw(16)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

// The live sketches of a record (2.8.0): sent-transcript sketches
// whose stored expiry is still ahead — the Worker's horizons
// (7 days ungraded, 180 days graded) as recorded at send time or
// last extended when the job was seen graded. An unparseable
// expiry keeps the sketch, matching pruneExpiredEntries'
// convention in jobs.js. Pure.
export function liveSketches(sketches, nowMs) {
  const now = typeof nowMs === 'number' ? nowMs : Date.now();
  return (sketches || []).filter((s) => {
    const t = Date.parse((s && s.expires_at) || '');
    return Number.isNaN(t) || t > now;
  });
}

// The reset for a record made by a different model or glossary
// version (2.6.15): its chunks can never be served (cacheHit
// refuses them), and a fresh transcription run must not append to
// them or resume from their window count — the mixed record
// would keep the old version stamps and stay unrestorable for
// ever. Returns the record reset to a fresh transcript state
// under the current versions, or null when the record is current
// (or absent). The WAV bytes are identical by fingerprint and
// are kept; a newly supplied blob, duration or source name wins.
export function resetStaleRecord(existing, { model, glossary, wavBlob, duration_s, source_name }) {
  if (!existing) return null;
  if (existing.model === model && existing.glossary === glossary) return null;
  return {
    ...existing,
    model,
    glossary,
    chunks: [],
    windows_done: 0,
    complete: false,
    // The reset starts a new transcription run (2.8.0). The
    // sent_sketches are kept (the spread above): they belong to
    // sends under this recording, and each expires on its own
    // recorded horizon.
    transcription_run_id: mintRunId(),
    // The chain (2.9.0) is bound to the run and to the chunks,
    // both of which the reset replaces: it restarts with the
    // new run, so the stored partial chain is dropped.
    pow_chain: null,
    wavBlob: wavBlob || existing.wavBlob || null,
    duration_s: duration_s || existing.duration_s || 0,
    source_name: source_name || existing.source_name || '',
  };
}

// The shape a cached chunk is stored in: pipeline timestamps in
// seconds, raw model text, and the glossary-corrected text BEFORE
// scrubbing. Scrubbing is never cached — it is re-applied fresh on
// every load from the student's current removal list.
export function toCachedChunk(item) {
  return {
    start_s: item.start,
    end_s: item.end,
    raw: item.raw,
    corrected: item.corrected,
  };
}

export function fromCachedChunk(cached) {
  return {
    start: cached.start_s,
    end: cached.end_s,
    raw: cached.raw,
    corrected: cached.corrected,
  };
}

// The opening words of a recording's corrected transcript, from its
// cached chunks. Recordings and jobs are otherwise identified only
// by dates, durations and fingerprint prefixes, which are easy to
// confuse when a student has several takes of the same assignment;
// the opening words are what the student recognises. The text is
// pre-scrub, like everything in the cache: callers that display it
// apply the student's current removal list first.
export function recordingFirstWords(cachedChunks, wordCount = 12) {
  const text = (cachedChunks || [])
    .map((c) => String((c && c.corrected) || ''))
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!text) return '';
  return text.split(' ').slice(0, wordCount).join(' ');
}
