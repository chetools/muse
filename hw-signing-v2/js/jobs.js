// Grading jobs (SPEC, Webapp section): payload validation, the
// localStorage job entries, and the Worker job calls. Validation and
// the storage helpers are pure (storage and fetch are injectable);
// the API helpers take fetch as a parameter, as in package.js.
//
// The job carries the scrubbed transcript and no name, no Canvas
// identity and no YouTube link. The Worker stores only a salted hash
// of the retrieval code.

import { normaliseWorkerBase } from './config.js';

export const JOBS_STORAGE_KEY = 'hw-signing.jobs.v2';
export const TRANSCRIPT_MAX_CHARS = 200000;

// The retrieval name rule, identical to the Worker's validation.
export const RETRIEVAL_NAME_RE = /^[a-z0-9][a-z0-9-]{2,23}$/;

const SHA256_HEX = /^[0-9a-f]{64}$/;

// Parse the video ID out of a YouTube URL in any of the forms the
// Worker accepts (watch, youtu.be, shorts, live, embed). Returns the
// 11-character ID, or null. Mirrors the Worker's parser; the Worker
// re-parses on /youtube-check and is the authority.
export function parseYouTubeVideoId(url) {
  let u;
  try { u = new URL(String(url || '').trim()); } catch { return null; }
  if (!/^https?:$/.test(u.protocol)) return null;
  const host = u.hostname.toLowerCase().replace(/^www\.|^m\./, '');
  let id = null;
  if (host === 'youtu.be') {
    id = u.pathname.split('/').filter(Boolean)[0] || null;
  } else if (host === 'youtube.com' || host === 'youtube-nocookie.com') {
    if (u.pathname === '/watch') id = u.searchParams.get('v');
    else {
      const m = u.pathname.match(/^\/(?:shorts|live|embed)\/([^/?#]+)/);
      if (m) id = m[1];
    }
  }
  return id && /^[A-Za-z0-9_-]{11}$/.test(id) ? id : null;
}

export function canonicalWatchUrl(videoId) {
  return 'https://www.youtube.com/watch?v=' + videoId;
}

// A retrieval name must satisfy the format rule AND must not contain
// any of the student's own scrub words: the name is the one place in
// this flow where a student could put an identifier back into a
// record that was just scrubbed. Matching is deliberately strict —
// a blocked student picks another name, which costs nothing — but it
// is not substring-blind for very short words:
// - a multi-word scrub entry collapsed ("Jordan Lee" → "jordanlee",
//   length >= 4) blocks anywhere in the name;
// - a token of length >= 3 blocks anywhere ("jordan", "priya");
// - a 2-letter token blocks only as a whole hyphen-separated segment
//   ("al-paso" blocks; "always-7" and "final-try" do not);
// - single letters are ignored.
export function validateRetrievalName(name, scrubWords) {
  const n = String(name || '');
  if (!RETRIEVAL_NAME_RE.test(n)) {
    return {
      ok: false,
      reason: 'Use 3–24 characters: lowercase letters, digits and hyphens, starting with a letter or digit.',
    };
  }
  const blocked = { ok: false, reason: 'That name contains a word from your removal list. Pick a name that does not identify you.' };
  const segments = n.split('-');
  for (const w of scrubWords || []) {
    const raw = String(w || '').toLowerCase();
    if (!raw) continue;
    const collapsed = raw.replace(/[^a-z0-9]+/g, '');
    if (collapsed.length >= 4 && n.includes(collapsed)) return blocked;
    for (const token of raw.split(/[^a-z0-9]+/)) {
      if (token.length >= 3 && n.includes(token)) return blocked;
      if (token.length === 2 && segments.includes(token)) return blocked;
    }
  }
  return { ok: true };
}

// Client-side mirror of the Worker's POST /jobs validation. Returns
// { ok: true } or { ok: false, reason } — the reason of the FIRST
// failed check, in the Worker's order of concern.
export function validateJobPayload(body) {
  const fail = (reason) => ({ ok: false, reason });
  if (!body || typeof body !== 'object') return fail('No job to submit.');
  if (!body.pkg || String(body.pkg).length > 128) return fail('No prompt package in the configured link.');
  if (!SHA256_HEX.test(body.pkg_content_sha256 || '')) {
    return fail('The configured link carries no valid package content hash (ph).');
  }
  if (body.kind !== 'practice' && body.kind !== 'final') {
    return fail('Choose Practice or Final.');
  }
  if (typeof body.transcript !== 'string' || !body.transcript.trim()) {
    return fail('The transcript is empty.');
  }
  if (body.transcript.length > TRANSCRIPT_MAX_CHARS) {
    return fail('The transcript is longer than 200,000 characters.');
  }
  if (!SHA256_HEX.test(body.audio_sha256 || '')) return fail('The audio fingerprint is missing.');
  if (!SHA256_HEX.test(body.transcript_sha256 || '')) return fail('The transcript checksum is missing.');
  const v = body.versions || {};
  if (!v.webapp || !v.model || !v.glossary) return fail('Component versions are missing.');
  if (!RETRIEVAL_NAME_RE.test(body.retrieval_name || '')) {
    return fail('The retrieval name does not follow the format rule.');
  }
  if (typeof body.retrieval_code !== 'string' ||
      body.retrieval_code.length < 4 || body.retrieval_code.length > 128) {
    return fail('Enter a retrieval code of at least 4 characters.');
  }
  if (body.kind === 'final') {
    if (!body.youtube_token) return fail('A final submission needs the YouTube link checked first.');
    if (!body.youtube_video_id || !/^[A-Za-z0-9_-]{11}$/.test(body.youtube_video_id)) {
      return fail('The checked YouTube video ID is missing.');
    }
    if (!body.youtube_checked_at || Number.isNaN(Date.parse(body.youtube_checked_at))) {
      return fail('The YouTube check time is missing.');
    }
  }
  return { ok: true };
}

// Assemble the POST /jobs body from page state. youtube fields are
// included only for final jobs; the link itself is never sent — only
// the Worker's check token and the video ID.
export function buildJobPayload(state) {
  const body = {
    pkg: state.pkg,
    pkg_content_sha256: state.pkgContentSha256,
    kind: state.kind,
    transcript: state.transcript,
    audio_sha256: state.audioSha256,
    transcript_sha256: state.transcriptSha256,
    versions: { ...state.versions },
    retrieval_name: state.retrievalName,
    retrieval_code: state.retrievalCode,
  };
  if (state.kind === 'final') {
    body.youtube_token = state.youtubeToken;
    body.youtube_video_id = state.youtubeVideoId;
    body.youtube_checked_at = state.youtubeCheckedAt;
  }
  if (state.pushSubscription) body.push_subscription = state.pushSubscription;
  return body;
}

/* ---------------- localStorage job entries ----------------
 * A list of { pkg, course, asg, retrieval_name, retrieval_code, kind,
 * youtube_link, created_at, expires_at }. youtube_link is held only
 * here, on the student's own browser, so the HTML can be built at ZIP
 * creation on a later visit; it is never sent to the Worker with the
 * job. (SPEC names the other fields; the link field is the local
 * keeping the SPEC's packaging step requires.)
 */

function defaultStorage() {
  try { return globalThis.localStorage || null; } catch { return null; }
}

export function loadJobEntries(storage) {
  const store = storage || defaultStorage();
  if (!store) return [];
  try {
    const parsed = JSON.parse(store.getItem(JOBS_STORAGE_KEY) || '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch { return []; }
}

export function saveJobEntries(entries, storage) {
  const store = storage || defaultStorage();
  if (!store) return;
  try { store.setItem(JOBS_STORAGE_KEY, JSON.stringify(entries || [])); } catch { /* full/blocked: entries are a convenience */ }
}

export function addJobEntry(entry, storage) {
  const entries = loadJobEntries(storage)
    .filter((e) => !(e.pkg === entry.pkg && e.retrieval_name === entry.retrieval_name));
  entries.push(entry);
  saveJobEntries(entries, storage);
  return entries;
}

export function removeJobEntry(pkg, retrievalName, storage) {
  const entries = loadJobEntries(storage)
    .filter((e) => !(e.pkg === pkg && e.retrieval_name === retrievalName));
  saveJobEntries(entries, storage);
  return entries;
}

// Entries at or past their expiry are dropped; the Worker has deleted
// the job's transcript and result by then in any case.
export function pruneExpiredEntries(entries, nowMs) {
  const now = typeof nowMs === 'number' ? nowMs : Date.now();
  return (entries || []).filter((e) => {
    const t = Date.parse(e.expires_at || '');
    return Number.isNaN(t) || t > now;
  });
}

/* ---------------- Worker calls (fetch injectable) ---------------- */

async function postJson(workerBase, path, body, fetchFn) {
  const base = normaliseWorkerBase(workerBase);
  if (!base) throw new Error('no grading Worker address configured');
  const doFetch = fetchFn || globalThis.fetch;
  const res = await doFetch(base + path, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON error body */ }
  return { status: res.status, ok: res.ok, data };
}

// GET / — service info, including vapid_public_key when configured.
export async function fetchWorkerInfo(workerBase, fetchFn) {
  const base = normaliseWorkerBase(workerBase);
  if (!base) throw new Error('no grading Worker address configured');
  const doFetch = fetchFn || globalThis.fetch;
  const res = await doFetch(base + '/');
  if (!res.ok) throw new Error('grading Worker answered HTTP ' + res.status);
  return res.json();
}

// POST /youtube-check {url} → {video_id, status, checked_at, token}.
export async function requestYouTubeCheck(workerBase, url, fetchFn) {
  const { status, ok, data } = await postJson(workerBase, '/youtube-check', { url }, fetchFn);
  if (!ok || !data) throw new Error('YouTube check failed (HTTP ' + status + ').');
  return data;
}

// POST /jobs → {job_id, created_at, expires_at}. Throws with the
// Worker's error message on failure (e.g. duplicate name, second
// final for one fingerprint).
export async function submitJob(workerBase, payload, fetchFn) {
  const { status, ok, data } = await postJson(workerBase, '/jobs', payload, fetchFn);
  if (!ok || !data || !data.job_id) {
    throw new Error((data && data.error) || ('job submission failed (HTTP ' + status + ')'));
  }
  return data;
}

// POST /jobs/status → {status, data} where data is the status body
// (including the result bundle when ready), or null on 403 — the
// Worker returns the same 403 for an unknown name and a wrong code,
// and the page preserves that indistinguishability.
export async function fetchJobStatus(workerBase, creds, fetchFn) {
  const { status, ok, data } = await postJson(workerBase, '/jobs/status', {
    pkg: creds.pkg,
    retrieval_name: creds.retrieval_name,
    retrieval_code: creds.retrieval_code,
  }, fetchFn);
  if (status === 403) return { status: 'forbidden', data: null };
  if (!ok || !data) throw new Error('status check failed (HTTP ' + status + ')');
  return { status: data.status, data };
}

// POST /jobs/retrieved → marks the job retrieved on the Worker.
export async function markJobRetrieved(workerBase, creds, fetchFn) {
  const { ok } = await postJson(workerBase, '/jobs/retrieved', {
    pkg: creds.pkg,
    retrieval_name: creds.retrieval_name,
    retrieval_code: creds.retrieval_code,
  }, fetchFn);
  return ok;
}
