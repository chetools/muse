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
// its fingerprint. Nothing else is stored in IndexedDB.
//
// All database access is lazy (inside the functions), so importing
// this module outside a browser is harmless.

import { cacheHit, toCachedChunk, recordingFirstWords } from './cachekey.js';

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
      // Refresh the WAV blob — the bytes are identical by fingerprint,
      // but a partial record may predate the blob being kept.
      let dirty = false;
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

export async function cacheDelete(audioSha256) {
  await withStore('readwrite', (store) => {
    store.delete(audioSha256);
  });
}
