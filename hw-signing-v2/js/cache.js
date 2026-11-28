// IndexedDB recordings cache (SPEC, Webapp section).
//
// Store `recordings` in database `hw-signing-v2`, keyed by
// audio_sha256, holding
//   { audio_sha256, model, glossary, wavBlob,
//     chunks: [{start_s, end_s, raw, corrected}],
//     duration_s, created_at, windows_done, complete }
// The wavBlob and windows_done/complete fields extend the SPEC's
// listed record shape: the blob is what lets a later visit rebuild
// the submission ZIP and re-download the WAV without the source
// file, and the progress fields are what chunk-level resume needs.
//
// Chunks are the pipeline's corrected (glossary-applied) text BEFORE
// scrubbing. Nothing identifying is added by the cache: the record
// holds the recording the student already has on this machine, under
// its fingerprint. Two fields join the record in 2.8.0:
// transcription_run_id (the current transcription run's identifier,
// sent with the job — see cachekey.js) and sent_sketches (the
// irreversible per-package sketches of transcripts sent from this
// recording, for the page-side near-duplicate check — see
// sketch.js). Nothing else is stored in IndexedDB.
//
// All database access is lazy (inside the functions), so importing
// this module outside a browser is harmless.

import { cacheHit, resetStaleRecord, toCachedChunk, recordingFirstWords, mintRunId, liveSketches } from './cachekey.js';

export const CACHE_DB_NAME = 'hw-signing-v2';
export const CACHE_STORE = 'recordings';

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(CACHE_DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(CACHE_STORE)) {
        db.createObjectStore(CACHE_STORE, { keyPath: 'audio_sha256' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function requestToPromise(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function withStore(mode, fn) {
  const db = await openDb();
  try {
    const tx = db.transaction(CACHE_STORE, mode);
    const done = new Promise((resolve, reject) => {
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error || new Error('IndexedDB transaction aborted'));
    });
    const out = await fn(tx.objectStore(CACHE_STORE));
    await done;
    return out;
  } finally {
    db.close();
  }
}

// The record for a fingerprint, or null when absent or when the
// record was made by a different model or glossary version.
export async function cacheGet(audioSha256, model, glossary) {
  if (!audioSha256) return null;
  const record = await withStore('readonly', (store) =>
    requestToPromise(store.get(audioSha256)));
  return cacheHit(record, model, glossary) ? record : null;
}

// Create the record for a freshly fingerprinted recording, if none
// exists yet. An existing record (e.g. a partial run) is kept. The
// source file name is kept with the record (this machine only, like
// the chunks) so a saved recording can be recognised in the list and
// at ZIP time; it is metadata from the student's own file and is
// scrubbed again wherever it is displayed.
export async function cacheInit(audioSha256, { model, glossary, wavBlob, duration_s, source_name }) {
  await withStore('readwrite', async (store) => {
    const existing = await requestToPromise(store.get(audioSha256));
    if (existing) {
      // Stale-version record reset (2.6.15): a record made by an
      // older model or glossary version is reset to a fresh
      // transcript state under the current versions — see
      // resetStaleRecord in cachekey.js.
      const reset = resetStaleRecord(existing,
        { model, glossary, wavBlob, duration_s, source_name });
      if (reset) { store.put(reset); return; }
      // Refresh the WAV blob — the bytes are identical by fingerprint,
      // but a partial record may predate the blob being kept.
      let dirty = false;
      // A record from before 2.8.0 has no run identifier: mint
      // one for the run its chunks belong to.
      if (!existing.transcription_run_id) {
        existing.transcription_run_id = mintRunId();
        dirty = true;
      }
      if (!existing.wavBlob && wavBlob) { existing.wavBlob = wavBlob; dirty = true; }
      if (!existing.source_name && source_name) {
        existing.source_name = source_name;
        dirty = true;
      }
      if (dirty) store.put(existing);
      return;
    }
    store.put({
      audio_sha256: audioSha256,
      model,
      glossary,
      wavBlob: wavBlob || null,
      chunks: [],
      duration_s: duration_s || 0,
      source_name: source_name || '',
      created_at: new Date().toISOString(),
      windows_done: 0,
      complete: false,
      transcription_run_id: mintRunId(),
      sent_sketches: [],
    });
  });
}

// Append one completed chunk (pipeline item shape: {start, end, raw,
// corrected}). Chunks are appended in transcription order.
export async function cachePutChunk(audioSha256, item) {
  await withStore('readwrite', async (store) => {
    const record = await requestToPromise(store.get(audioSha256));
    if (!record) return;
    record.chunks.push(toCachedChunk(item));
    store.put(record);
  });
}

// Record that the first n transcription windows are done, so an
// interrupted run resumes at window n instead of starting over. A
// window that produced no chunk still counts as done.
export async function cacheWindowDone(audioSha256, windowsDone) {
  await withStore('readwrite', async (store) => {
    const record = await requestToPromise(store.get(audioSha256));
    if (!record) return;
    if (windowsDone > (record.windows_done || 0)) {
      record.windows_done = windowsDone;
      store.put(record);
    }
  });
}

// Mark the transcription complete for this recording.
export async function cacheComplete(audioSha256) {
  await withStore('readwrite', async (store) => {
    const record = await requestToPromise(store.get(audioSha256));
    if (!record) return;
    record.complete = true;
    store.put(record);
  });
}

// Summaries for the recordings list UI, newest first: date,
// duration, size, progress state, the source file name and the
// transcript's opening words — the two things a student recognises
// a recording by. Both are pre-scrub; the list UI scrubs them with
// the student's current removal list before display.
export async function cacheList() {
  const all = await withStore('readonly', (store) =>
    requestToPromise(store.getAll()));
  return (all || [])
    .map((r) => ({
      audio_sha256: r.audio_sha256,
      model: r.model,
      glossary: r.glossary,
      duration_s: r.duration_s || 0,
      size_bytes: r.wavBlob ? r.wavBlob.size : 0,
      created_at: r.created_at || '',
      chunks: (r.chunks || []).length,
      complete: !!r.complete,
      source_name: r.source_name || '',
      first_words: recordingFirstWords(r.chunks),
    }))
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
}

// ------------------------------------------------------------
// Sent-transcript sketches (Component A, 2.8.0). A sketch is
// { pkg, count, words: { wordHash: occurrences }, expires_at } —
// the irreversible sketch of one as-sent transcript (see
// sketch.js), stored in the recording's record, never in
// localStorage. The expiry is the sending job's Worker expiry
// (7 days ungraded, 180 days once graded), extended when the job
// is later seen graded (cacheExtendSketchExpiry).

// Store the sketch of a transcript just sent for `pkg`.
export async function cacheAddSentSketch(audioSha256, { pkg, sketch, expires_at }) {
  if (!audioSha256 || !sketch) return;
  await withStore('readwrite', async (store) => {
    const record = await requestToPromise(store.get(audioSha256));
    if (!record) return;
    const live = liveSketches(record.sent_sketches);
    live.push({ pkg, count: sketch.count, words: sketch.words, expires_at: expires_at || '' });
    record.sent_sketches = live;
    store.put(record);
  });
}

// The live sketches stored for `pkg` on this recording.
export async function cacheSentSketches(audioSha256, pkg) {
  if (!audioSha256) return [];
  const record = await withStore('readonly', (store) =>
    requestToPromise(store.get(audioSha256)));
  if (!record) return [];
  return liveSketches(record.sent_sketches).filter((s) => s.pkg === pkg);
}

// Extend the expiry of this recording's sketches for `pkg` to
// `expiresAt` where that is later than what is stored — called
// when a job for the recording is seen graded, whose horizon
// (180 days) replaces the ungraded one (7 days).
export async function cacheExtendSketchExpiry(audioSha256, pkg, expiresAt) {
  if (!audioSha256 || !expiresAt) return;
  await withStore('readwrite', async (store) => {
    const record = await requestToPromise(store.get(audioSha256));
    if (!record || !Array.isArray(record.sent_sketches)) return;
    let dirty = false;
    for (const s of record.sent_sketches) {
      if (s.pkg === pkg && String(expiresAt) > String(s.expires_at || '')) {
        s.expires_at = expiresAt;
        dirty = true;
      }
    }
    if (dirty) store.put(record);
  });
}

export async function cacheDelete(audioSha256) {
  await withStore('readwrite', (store) => {
    store.delete(audioSha256);
  });
}
