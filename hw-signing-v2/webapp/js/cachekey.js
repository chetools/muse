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
