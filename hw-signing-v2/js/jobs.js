// Grading jobs (SPEC, Webapp section): payload validation, the
// localStorage job entries, and the Worker job calls. Validation and
// the storage helpers are pure (storage and fetch are injectable);
// the API helpers take fetch as a parameter, as in package.js.
//
// The job carries the scrubbed transcript and no name, no Canvas
// identity and no YouTube link. Retrieval is by code only; the
// Worker stores a lookup hash of the code, never the code itself.

import { normaliseWorkerBase } from './config.js';

export const JOBS_STORAGE_KEY = 'hw-signing.jobs.v2';
export const TRANSCRIPT_MAX_CHARS = 200000;

// The retrieval code creation rule, identical to the Worker's
// validation: letters and numbers only, at least 8 characters — the
// code is the only credential for retrieving the grade, so a short
// code is guessable. The rule is applied only when a job is created
// (validateJobPayload); status, finalize and retrieved calls do not
// apply it, so jobs created before 2.4.1 with shorter codes remain
// retrievable.
export const RETRIEVAL_CODE_RE = /^[A-Za-z0-9]{8,128}$/;

/* ---------------- recovery token generation (2.5.4) ----------------
 * Since 2.5.4 the student no longer picks a retrieval code: the
 * page generates one at send time and keeps it in the job entry, as
 * before. The generated value IS the retrieval code on the wire —
 * the Worker protocol is unchanged. The page offers no manual
 * retrieval: a job is listed only on the browser that sent it (or
 * that holds an entry for it).
 * The token is 24 characters drawn uniformly from the 62-character
 * code alphabet (about 143 bits), so an unused token is not
 * guessable and a collision with another job's code is not a
 * practical event. Bytes are drawn from crypto.getRandomValues and
 * mapped by rejection sampling (bytes >= 248 are discarded, since
 * 248 is the largest multiple of 62 not exceeding 256), so every
 * alphabet character is equally likely. The byte source is
 * injectable so the mapping is testable without real randomness.
 */
export const RECOVERY_TOKEN_LENGTH = 24;
const TOKEN_ALPHABET =
  'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';

export function generateRetrievalToken(randomBytes) {
  const draw = randomBytes || ((n) => {
    const buf = new Uint8Array(n);
    globalThis.crypto.getRandomValues(buf);
    return buf;
  });
  let out = '';
  while (out.length < RECOVERY_TOKEN_LENGTH) {
    const bytes = draw(RECOVERY_TOKEN_LENGTH - out.length);
    for (const b of bytes) {
      if (b >= 248) continue;
      out += TOKEN_ALPHABET[b % 62];
      if (out.length === RECOVERY_TOKEN_LENGTH) break;
    }
  }
  return out;
}

const SHA256_HEX = /^[0-9a-f]{64}$/;

// Parse the video ID out of a YouTube URL in any of the forms the
// Worker accepts (watch, youtu.be, shorts, live, embed), and, since
// 2.6.16, out of a YouTube Studio edit address
// (studio.youtube.com/video/<id>/edit): the student sets the video
// to Unlisted in Studio, so the Studio address is the one in their
// browser, and the page converts it to the canonical watch form
// instead of refusing it. Returns the 11-character ID, or null.
// The Worker re-parses the canonical watch URL on /youtube-check
// and is the authority.
export function parseYouTubeVideoId(url) {
  let u;
  try { u = new URL(String(url || '').trim()); } catch { return null; }
  if (!/^https?:$/.test(u.protocol)) return null;
  const host = u.hostname.toLowerCase().replace(/^www\.|^m\./, '');
  let id = null;
  if (host === 'youtu.be') {
    id = u.pathname.split('/').filter(Boolean)[0] || null;
  } else if (host === 'studio.youtube.com') {
    const m = u.pathname.match(/^\/video\/([^/?#]+)/);
    if (m) id = m[1];
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

/* ---------------- duration comparison ----------------
 * Removed in 2.6.18: the page no longer compares the video's
 * length with the recording's. The comparison depended on a cued
 * player reporting a duration, which it often does not, and it
 * was only ever a proxy for sameness of recording — which the
 * teacher audit's acoustic cross-check on the submitted ZIP
 * establishes directly. The Worker's /stats/duration endpoint
 * remains, but the page no longer reports to it.
 */

/* ---------------- fingerprint-form submissions ----------------
 * Since webapp 2.7.0 the fingerprint form is the only submission
 * ZIP form: there is no audio (WAV) form. A bundle graded under
 * Worker 2.7.0 carries a signed chromaprint_sha256 — the SHA-256
 * of the raw Chromaprint bytes — when the job had a fingerprint,
 * and the submission ZIP holds the fingerprint bytes. The string
 * "none" (the job had no fingerprint) and a missing field (the job
 * was graded before Worker 2.7.0) mean no fingerprint form can be
 * built for that job.
 */
export function bundleChromaprintSha(bundle) {
  const v = bundle && bundle.chromaprint_sha256;
  return typeof v === 'string' && SHA256_HEX.test(v) ? v : null;
}

// The fingerprint form's verification (2.7.0): the only re-hash
// left before packaging is the locally held fingerprint bytes
// against the signed chromaprint_sha256. The critique is not
// re-hashed, and Worker-supplied parts (the fallback transcript)
// are not re-hashed either. Returns ['fingerprint'] on a mismatch,
// [] when the bytes match. Pure; the caller supplies the hash.
export function verifyFingerprintContents(bundle, actual) {
  if (!bundle || !actual) return ['fingerprint'];
  return actual.fingerprintSha256 !== bundle.chromaprint_sha256
    ? ['fingerprint'] : [];
}

// Client-side mirror of the Worker's POST /jobs validation. Returns
// { ok: true } or { ok: false, reason } — the reason of the FIRST
// failed check, in the Worker's order of concern.
export function validateJobPayload(body) {
  const fail = (reason) => ({ ok: false, reason });
  if (!body || typeof body !== 'object') return fail('No job to submit.');
  if (!body.pkg || String(body.pkg).length > 128) return fail('No prompt package in this link.');
  if (!SHA256_HEX.test(body.pkg_content_sha256 || '')) {
    return fail('This link is incomplete. Use the link your teacher put in Canvas.');
  }
  if (typeof body.transcript !== 'string' || !body.transcript.trim()) {
    return fail('Your transcript is empty.');
  }
  if (body.transcript.length > TRANSCRIPT_MAX_CHARS) {
    return fail('Your transcript is longer than 200,000 characters.');
  }
  if (!SHA256_HEX.test(body.audio_sha256 || '')) return fail('Your recording’s hash is missing.');
  if (!SHA256_HEX.test(body.transcript_sha256 || '')) return fail('Your transcript’s checksum is missing.');
  const v = body.versions || {};
  if (!v.webapp || !v.model || !v.glossary) return fail('Component versions are missing.');
  if (typeof body.retrieval_code !== 'string' ||
      !RETRIEVAL_CODE_RE.test(body.retrieval_code)) {
    return fail('This job could not be prepared for sending. Reload the page and send again.');
  }
  return { ok: true };
}

// Assemble the POST /jobs body from page state (2.7.0): no kind
// and no YouTube fields are sent. chromaprint is the raw
// Chromaprint as base64; the send flow blocks when no fingerprint
// was computed, so in practice it is always present.
// 2.8.0 (Worker 2.9.0): run_id — the per-transcription-run
// identifier from the recording's cache record — is sent when
// known. 2.9.0 (Worker 2.10.0): the proof of work rides as
// pow_chain — { count, chunk_hashes, nonces }, the per-chunk
// proof the page built during the transcription (see pow.js) —
// when a completed chain is presented. Both are optional in the
// body: the Worker treats a missing run_id as the empty
// identifier and, in its permissive phase, a missing proof as
// no proof presented. (The 2.8.x single-shot token fields are
// no longer sent, and Worker 2.10.0 no longer accepts them
// either — the old proof is eliminated on both sides.)
export function buildJobPayload(state) {
  const body = {
    pkg: state.pkg,
    pkg_content_sha256: state.pkgContentSha256,
    transcript: state.transcript,
    audio_sha256: state.audioSha256,
    transcript_sha256: state.transcriptSha256,
    versions: { ...state.versions },
    retrieval_code: state.retrievalCode,
  };
  if (state.chromaprint) body.chromaprint = state.chromaprint;
  if (state.runId) body.run_id = state.runId;
  if (state.powChain && Number.isInteger(state.powChain.count) &&
      Array.isArray(state.powChain.chunk_hashes) &&
      Array.isArray(state.powChain.nonces)) {
    body.pow_chain = {
      count: state.powChain.count,
      chunk_hashes: [...state.powChain.chunk_hashes],
      nonces: [...state.powChain.nonces],
    };
  }
  return body;
}

/* ---------------- localStorage job entries ----------------
 * A list of { pkg, course, asg, retrieval_code, finalised,
 * youtube_link, youtube_title, youtube_checked_at, created_at,
 * expires_at }.
 * finalised (2.7.0) is a boolean set when finalizeJob succeeds in
 * this browser (finalize is idempotent, so a repeat success sets
 * it the same way).
 * Entries stored by older versions carry kind instead: on load,
 * kind 'final' is read as finalised true (see loadJobEntries).
 * youtube_title is the title the Worker returned at the link check,
 * kept locally so the student can recognise the video again at ZIP
 * time; it is never sent with the job. youtube_checked_at (2.4.4) is
 * the link check's time, kept locally for the same reason: the ZIP
 * download name carries it. It is never sent with the job either —
 * at send and finalize time it travels only inside the check token
 * the Worker verifies. youtube_link is held only
 * here, on the student's own browser, so the HTML can be built at ZIP
 * creation on a later visit; it is never sent to the Worker with the
 * job. (SPEC names the other fields; the link field is the local
 * keeping the SPEC's packaging step requires.)
 */

function defaultStorage() {
  try { return globalThis.localStorage || null; } catch { return null; }
}

// 2.6.12: an entry is polled only against the Worker that created
// it. Entries record their Worker address at creation; an entry
// from before 2.6.12 has none and is polled only against the
// production Worker. Without this, any link naming another Worker
// address would send every stored retrieval code — the sole
// retrieval credential — to that address on page load.
export const CANONICAL_WORKER_HOST = 'hw-grading.carloscomail.workers.dev';

export function entryPollable(entry, workerBase) {
  const base = normaliseWorkerBase(workerBase);
  if (!base) return false;
  if (entry && entry.worker) {
    return normaliseWorkerBase(entry.worker) === base;
  }
  try {
    return new URL(base).hostname === CANONICAL_WORKER_HOST;
  } catch {
    return false;
  }
}

export function loadJobEntries(storage) {
  const store = storage || defaultStorage();
  if (!store) return [];
  try {
    const parsed = JSON.parse(store.getItem(JOBS_STORAGE_KEY) || '[]');
    if (!Array.isArray(parsed)) return [];
    // 2.7.0 compat: an entry stored by an older version carries
    // kind instead of finalised; kind 'final' reads as finalised.
    return parsed.map((e) => {
      if (!e || typeof e !== 'object') return e;
      const { kind, ...rest } = e;
      return { ...rest, finalised: e.finalised === true || kind === 'final' };
    });
  } catch { return []; }
}

export function saveJobEntries(entries, storage) {
  const store = storage || defaultStorage();
  if (!store) return;
  try { store.setItem(JOBS_STORAGE_KEY, JSON.stringify(entries || [])); } catch { /* full/blocked: entries are a convenience */ }
}

export function addJobEntry(entry, storage) {
  const entries = loadJobEntries(storage)
    .filter((e) => !(e.pkg === entry.pkg && e.retrieval_code === entry.retrieval_code));
  entries.push(entry);
  saveJobEntries(entries, storage);
  return entries;
}

export function removeJobEntry(pkg, retrievalCode, storage) {
  const entries = loadJobEntries(storage)
    .filter((e) => !(e.pkg === pkg && e.retrieval_code === retrievalCode));
  saveJobEntries(entries, storage);
  return entries;
}

// Storage helper: drop entries at or past their stored expiry. The
// stored expiry is a cache of the Worker's governing expiry, so this
// is not the liveness test — renderJobs asks the Worker about every
// entry and drops it on an "expired" report, because an entry written
// before 2.4.1 can carry an expiry (creation + 48 h) that the Worker
// no longer applies to a still-ungraded job.
export function pruneExpiredEntries(entries, nowMs) {
  const now = typeof nowMs === 'number' ? nowMs : Date.now();
  return (entries || []).filter((e) => {
    const t = Date.parse(e.expires_at || '');
    return Number.isNaN(t) || t > now;
  });
}

/* ---------------- one row per underlying job (2.5.3) ----------------
 * Local entries are keyed by retrieval code, but several codes can
 * retrieve the SAME underlying job: the Worker's duplicate path
 * (2.6.0) stores each submitted code as an alias for the existing
 * job, and the page files one entry per alias code. Rendering one
 * row per entry then showed one job two or three times, each row
 * with its own ZIP button — and only the entry that happened to
 * carry the locally kept YouTube link could pass ZIP verification,
 * so the other rows' buttons always failed. (Student report,
 * 2026-11-24: up to three ZIP buttons, only one of which worked.)
 *
 * collapseSameJobEntries(items) takes [{ entry, jobId }] — jobId is
 * the Worker's job_id for the entry's job, from the entry itself
 * (entries filed since 2.5.3 carry it) or from its ready result
 * bundle, and may be null when neither is known yet — and returns
 * the items to keep: at most one per distinct jobId. Entries with
 * no known jobId are always kept (nothing proves they are the same
 * job). Within a same-job group the survivor is the entry most
 * able to build the ZIP — one carrying a YouTube link first, then
 * a finalised entry, then the earliest created — and the locally kept
 * YouTube fields (link, title, check time) are merged onto it from
 * every group member that has them, so the surviving row is the
 * working one. The survivor's entry gains job_id. Pure: the caller
 * persists the kept entries, so the collapsed state is what the
 * next visit loads.
 */
export function collapseSameJobEntries(items) {
  const groups = new Map(); // jobId -> [indices]
  (items || []).forEach((item, i) => {
    if (!item || !item.jobId) return;
    if (!groups.has(item.jobId)) groups.set(item.jobId, []);
    groups.get(item.jobId).push(i);
  });
  const dropped = new Set();
  for (const idxs of groups.values()) {
    if (idxs.length < 2) {
      const only = items[idxs[0]];
      if (only.entry && !only.entry.job_id) only.entry.job_id = only.jobId;
      continue;
    }
    const score = (entry) =>
      (entry.youtube_link ? 4 : 0) + (entry.finalised ? 2 : 0) +
      (entry.youtube_title ? 1 : 0);
    const ranked = [...idxs].sort((a, b) => {
      const d = score(items[b].entry) - score(items[a].entry);
      if (d) return d;
      const ta = Date.parse(items[a].entry.created_at || '') || 0;
      const tb = Date.parse(items[b].entry.created_at || '') || 0;
      return ta - tb || a - b;
    });
    const keep = items[ranked[0]];
    for (const i of ranked.slice(1)) {
      const e = items[i].entry;
      for (const f of ['youtube_link', 'youtube_title', 'youtube_checked_at']) {
        if (!keep.entry[f] && e[f]) keep.entry[f] = e[f];
      }
      if (e.finalised) keep.entry.finalised = true;
      dropped.add(i);
    }
    keep.entry.job_id = keep.jobId;
  }
  return (items || []).filter((_, i) => !dropped.has(i));
}

/* ---------------- Worker calls (fetch injectable) ---------------- */

async function postJson(workerBase, path, body, fetchFn) {
  const base = normaliseWorkerBase(workerBase);
  if (!base) throw new Error('no grading service address configured');
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
  if (!base) throw new Error('no grading service address configured');
  const doFetch = fetchFn || globalThis.fetch;
  const res = await doFetch(base + '/');
  if (!res.ok) throw new Error('the grading service answered HTTP ' + res.status);
  return res.json();
}

// POST /youtube-check {url} → {video_id, status, checked_at, token}.
export async function requestYouTubeCheck(workerBase, url, fetchFn) {
  const { status, ok, data } = await postJson(workerBase, '/youtube-check', { url }, fetchFn);
  if (!ok || !data) throw new Error('YouTube check failed (HTTP ' + status + ').');
  return data;
}

// POST /jobs → {job_id, created_at, expires_at}. Throws with the
// Worker's error message on failure (e.g. duplicate code). A
// duplicate response (2.6.0) is returned as-is, not thrown: it
// carries job_id and duplicate:true, and the caller shows the
// existing job through the normal jobs-list path.
export async function submitJob(workerBase, payload, fetchFn) {
  const { status, ok, data } = await postJson(workerBase, '/jobs', payload, fetchFn);
  if (data && data.duplicate) return data;
  if (!ok || !data || !data.job_id) {
    throw new Error((data && data.error) || ('job submission failed (HTTP ' + status + ')'));
  }
  return data;
}

/* ---------------- duplicate responses ----------------
 * When the submitted transcript is a byte-identical resubmission
 * of a live job (Worker 2.9.0: same package, recording,
 * transcript and transcription run), POST /jobs returns the
 * existing job instead of creating one:
 *   {duplicate:true, job_id, created_at, expires_at, pkg, status,
 *    queue_ahead?, result?}
 * `result` is the existing result bundle when the job is ready;
 * `queue_ahead` is present while it is queued or claimed. The
 * submitted code does NOT retrieve the existing job (no alias is
 * created — the Worker has never created one since 2.8.0), so the
 * page stores no entry for a duplicate: the send handler shows
 * the queue state or grades from the response in the status line
 * beside the Send button. (The pre-2.8.0 alias entry builder was
 * removed in webapp 2.8.0; it expected an alias_created field the
 * Worker no longer sends, so every duplicate took its null path.)
 */

// POST /jobs/status → {status, data} where data is the status body
// (the result bundle when ready; queue_ahead — how many jobs are
// ahead in the grading queue — while waiting), or null on 403: the
// Worker returns the same 403 for every wrong code, and the page
// preserves that indistinguishability. For a ready job the body
// also carries the Worker's stored transcript text and chromaprint
// (Worker 2.7.0) as top-level fields beside the result bundle; they
// reach the caller through data unchanged and feed the
// fingerprint-form ZIP path. Since Worker 2.9.0 the body also
// carries the grader's injection_flags at the top level for a
// ready job; the page copies them into the submission package
// (see package.js), which is how the teacher's audit app receives
// them — the audit app does not scan for them itself.
export async function fetchJobStatus(workerBase, creds, fetchFn) {
  const { status, ok, data } = await postJson(workerBase, '/jobs/status', {
    pkg: creds.pkg,
    retrieval_code: creds.retrieval_code,
  }, fetchFn);
  if (status === 403) return { status: 'forbidden', data: null };
  if (!ok || !data) throw new Error('status check failed (HTTP ' + status + ')');
  return { status: data.status, data };
}

// POST /jobs/finalize → marks an existing job final (the Canvas
// submission job). Since 2.6.19 the call carries no YouTube fields:
// no video is bound to the job, and any youtube fields a caller
// still passes are dropped here rather than sent. The call is
// idempotent: finalising a job that already stands final returns
// the same success (Worker 2.9.0 removed the one-final rule
// entirely — there is no "already final" conflict response; the
// pre-2.8.0 page branch that recognised one was removed in webapp
// 2.8.0). Throws with the Worker's error message on failure.
export async function finalizeJob(workerBase, payload, fetchFn) {
  const { status, ok, data } = await postJson(workerBase, '/jobs/finalize', {
    pkg: payload.pkg,
    retrieval_code: payload.retrieval_code,
  }, fetchFn);
  if (!ok || !data || !data.ok) {
    throw new Error((data && data.error) || ('finalize failed (HTTP ' + status + ')'));
  }
  return data;
}

