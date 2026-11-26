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
 * the Worker protocol is unchanged, and codes students picked
 * before 2.5.4 still retrieve their jobs through the manual box.
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

/* ---------------- duration comparison ----------------
 * The page's audio duration (the decoded audio track) and the
 * YouTube player's duration (the whole transcoded presentation) are
 * not the same quantity, so an identical upload can differ by a
 * fraction of a second, and a camera file whose video track runs
 * past its audio by more. The comparison therefore has three bands:
 *   pass    — difference at most DURATION_PASS_S: no action needed.
 *   confirm — difference up to max(2 s, 2% of the audio): the link
 *             may be used only after the student plays the preview
 *             and explicitly confirms it is the same recording.
 *   block   — beyond that tolerance: the link cannot be used for
 *             this recording at all.
 * When either duration is unknown (the preview could not report
 * one), the band is 'unknown', which is handled like 'confirm': the
 * student must play the preview and confirm. The Worker stores one
 * anonymous statistic per reported comparison (POST /stats/duration)
 * so the pass band can be tightened later from measured data.
 */
export const DURATION_PASS_S = 1.0;

export function classifyDuration(audioS, videoS) {
  const a = Number(audioS);
  const v = Number(videoS);
  if (!(a > 0) || !(v > 0)) {
    return { band: 'unknown', diffS: null, tolS: null };
  }
  const diffS = Math.abs(v - a);
  const tolS = Math.max(2, 0.02 * a);
  const band = diffS <= DURATION_PASS_S ? 'pass'
    : diffS <= tolS ? 'confirm' : 'block';
  return { band, diffS, tolS };
}

/* ---------------- submission verification ----------------
 * Before a submission ZIP is built, the page recomputes the hashes
 * of the exact contents it is about to package — the WAV bytes, the
 * canonical transcript built from the job recording's own cached
 * chunks, and the critique in the result bundle — and compares them
 * with the hashes the grading Worker signed. Returns a list of
 * failure codes (empty when everything matches): 'audio',
 * 'transcript', 'critique'. Pure; the caller supplies the hashes it
 * computed so this stays Node-testable.
 */
export function verifyBundleContents(bundle, actual) {
  const failures = [];
  if (!bundle || !actual) return ['audio', 'transcript', 'critique'];
  if (actual.wavSha256 !== bundle.audio_sha256) failures.push('audio');
  if (actual.transcriptSha256 !== bundle.transcript_sha256) {
    failures.push('transcript');
  }
  if (actual.critiqueSha256 !== bundle.critique_sha256) {
    failures.push('critique');
  }
  return failures;
}

/* ---------------- fingerprint-form submissions (2.6.0) ----------------
 * The ZIP form is decided by the job's signed bundle, never by
 * date: a bundle graded under Worker 2.7.0 carries a signed
 * chromaprint_sha256 — the SHA-256 of the raw Chromaprint bytes —
 * when the job had a fingerprint, and the submission ZIP then holds
 * the fingerprint bytes instead of the WAV. The string "none" (the
 * job had no fingerprint) and a missing field (the job was graded
 * before Worker 2.7.0) both mean the WAV form, exactly as before.
 */
export function bundleChromaprintSha(bundle) {
  const v = bundle && bundle.chromaprint_sha256;
  return typeof v === 'string' && SHA256_HEX.test(v) ? v : null;
}

// The fingerprint form's counterpart of verifyBundleContents: the
// hashes of the exact contents about to be packaged — the raw
// fingerprint bytes the status response returned, the canonical
// transcript, and the critique in the result bundle — compared
// with the hashes the grading Worker signed. Returns a list of
// failure codes (empty when everything matches): 'fingerprint',
// 'transcript', 'critique'. Pure; the caller supplies the hashes.
export function verifyFingerprintContents(bundle, actual) {
  const failures = [];
  if (!bundle || !actual) return ['fingerprint', 'transcript', 'critique'];
  if (actual.fingerprintSha256 !== bundle.chromaprint_sha256) {
    failures.push('fingerprint');
  }
  if (actual.transcriptSha256 !== bundle.transcript_sha256) {
    failures.push('transcript');
  }
  if (actual.critiqueSha256 !== bundle.critique_sha256) {
    failures.push('critique');
  }
  return failures;
}

// Client-side mirror of the Worker's POST /jobs validation. Returns
// { ok: true } or { ok: false, reason } — the reason of the FIRST
// failed check, in the Worker's order of concern.
export function validateJobPayload(body) {
  const fail = (reason) => ({ ok: false, reason });
  if (!body || typeof body !== 'object') return fail('No job to submit.');
  if (!body.pkg || String(body.pkg).length > 128) return fail('No prompt package in the configured link.');
  if (!SHA256_HEX.test(body.pkg_content_sha256 || '')) {
    return fail('This link is incomplete. Use the link your teacher put in Canvas.');
  }
  if (body.kind !== 'practice' && body.kind !== 'final') {
    return fail('Job kind is missing.');
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
    return fail('The recovery code for this job could not be made. Reload the page and send again.');
  }
  if (body.kind === 'final') {
    if (!body.youtube_token) return fail('A submission with a link needs the YouTube link checked first.');
    if (!body.youtube_video_id || !/^[A-Za-z0-9_-]{11}$/.test(body.youtube_video_id)) {
      return fail('No video ID came back from the check.');
    }
    if (!body.youtube_checked_at || Number.isNaN(Date.parse(body.youtube_checked_at))) {
      return fail('No check time came back from the check.');
    }
  }
  return { ok: true };
}

// Assemble the POST /jobs body from page state. youtube fields are
// included only for final jobs; the link itself is never sent — only
// the Worker's check token and the video ID. chromaprint (2.6.0) is
// the raw Chromaprint as base64, included only when the page computed
// one; a job sent without it is graded the same and dedupes on the
// exact audio hash only.
export function buildJobPayload(state) {
  const body = {
    pkg: state.pkg,
    pkg_content_sha256: state.pkgContentSha256,
    kind: state.kind,
    transcript: state.transcript,
    audio_sha256: state.audioSha256,
    transcript_sha256: state.transcriptSha256,
    versions: { ...state.versions },
    retrieval_code: state.retrievalCode,
  };
  if (state.chromaprint) body.chromaprint = state.chromaprint;
  if (state.kind === 'final') {
    body.youtube_token = state.youtubeToken;
    body.youtube_video_id = state.youtubeVideoId;
    body.youtube_checked_at = state.youtubeCheckedAt;
  }
  return body;
}

/* ---------------- localStorage job entries ----------------
 * A list of { pkg, course, asg, retrieval_code, kind,
 * youtube_link, youtube_title, youtube_checked_at, created_at,
 * expires_at }.
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
 * a final entry, then the earliest created — and the locally kept
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
      (entry.youtube_link ? 4 : 0) + (entry.kind === 'final' ? 2 : 0) +
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
      if (e.kind === 'final') keep.entry.kind = 'final';
      dropped.add(i);
    }
    keep.entry.job_id = keep.jobId;
  }
  return (items || []).filter((_, i) => !dropped.has(i));
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

/* ---------------- duplicate responses (2.6.0) ----------------
 * When the submitted recording already has a live job under the
 * resolved prompt package version, POST /jobs returns the existing
 * job instead of creating one:
 *   {duplicate:true, job_id, created_at, expires_at, pkg, status,
 *    queue_ahead?, result?, alias_created}
 * `result` is the existing result bundle when the job is ready;
 * `queue_ahead` is present while it is queued or claimed.
 */

// The kind of a job from its result bundle: a bundle whose signed
// youtube_video_sha256 names a checked video is a final job; 'none'
// (or a missing value) is a practice job. The same rule the manual
// retrieval path uses to label a job it did not create.
export function kindFromResultBundle(bundle) {
  return bundle && bundle.youtube_video_sha256 &&
    bundle.youtube_video_sha256 !== 'none' ? 'final' : 'practice';
}

// Build the localStorage entry for a duplicate response, or null
// when nothing is to be stored. The entry is filed under the
// submitted code (the alias) so the existing job renders through the
// normal jobs-list path — queue state while queued or claimed,
// grades and critique when ready — and finalize and ZIP work from
// it exactly as from the original entry. When alias_created is
// false the submitted code is already used by a different job for
// the pkg, so it does not retrieve this job and nothing is stored
// under it. The entry's kind follows the existing job: the result
// bundle decides it when the job is ready; while the job is still
// queued or claimed there is no result yet, so the submitted kind
// stands until the jobs list learns the ready bundle.
export function duplicateJobEntry(response, submitted) {
  if (!response || !response.duplicate || !response.alias_created) return null;
  const kind = response.result
    ? kindFromResultBundle(response.result) : submitted.kind;
  const isFinal = kind === 'final' && submitted.kind === 'final';
  return {
    pkg: submitted.pkg,
    course: submitted.course,
    asg: submitted.asg,
    retrieval_code: submitted.retrieval_code,
    job_id: response.job_id || '',
    kind,
    youtube_link: isFinal ? (submitted.youtube_link || '') : '',
    youtube_title: isFinal ? (submitted.youtube_title || '') : '',
    youtube_checked_at: isFinal ? (submitted.youtube_checked_at || '') : '',
    created_at: response.created_at,
    expires_at: response.expires_at,
  };
}

// POST /jobs/status → {status, data} where data is the status body
// (the result bundle when ready; queue_ahead — how many jobs are
// ahead in the grading queue — while waiting), or null on 403: the
// Worker returns the same 403 for every wrong code, and the page
// preserves that indistinguishability. For a ready job the body
// also carries the Worker's stored transcript text and chromaprint
// (Worker 2.7.0) as top-level fields beside the result bundle; they
// reach the caller through data unchanged and feed the
// fingerprint-form ZIP path.
export async function fetchJobStatus(workerBase, creds, fetchFn) {
  const { status, ok, data } = await postJson(workerBase, '/jobs/status', {
    pkg: creds.pkg,
    retrieval_code: creds.retrieval_code,
  }, fetchFn);
  if (status === 403) return { status: 'forbidden', data: null };
  if (!ok || !data) throw new Error('status check failed (HTTP ' + status + ')');
  return { status: data.status, data };
}

// POST /jobs/finalize → turns an existing job into the final
// (Canvas submission) job by attaching a fresh YouTube check. The
// Worker verifies the check token exactly as at intake, enforces
// one final per recording, and re-signs a graded job's result bundle
// with the video hash. Throws with the Worker's error message.
export async function finalizeJob(workerBase, payload, fetchFn) {
  const { status, ok, data } = await postJson(workerBase, '/jobs/finalize', {
    pkg: payload.pkg,
    retrieval_code: payload.retrieval_code,
    youtube_token: payload.youtube_token,
    youtube_video_id: payload.youtube_video_id,
    youtube_checked_at: payload.youtube_checked_at,
  }, fetchFn);
  if (!ok || !data || !data.ok) {
    throw new Error((data && data.error) || ('finalize failed (HTTP ' + status + ')'));
  }
  return data;
}

// POST /stats/duration {pkg, context, audio_s, video_s} → records
// one anonymous duration comparison on the Worker (no video ID, no
// link, no student information) so the duration bands can be
// recalibrated from measured same-recording differences. Best
// effort: returns true when stored, false otherwise; a failure never
// affects the student's flow.
export async function reportDurationStat(workerBase, stat, fetchFn) {
  try {
    const { ok } = await postJson(workerBase, '/stats/duration', {
      pkg: stat.pkg || '',
      context: stat.context || '',
      audio_s: stat.audioS,
      video_s: stat.videoS,
    }, fetchFn);
    return !!ok;
  } catch { return false; }
}

// POST /jobs/retrieved → marks the job retrieved on the Worker.
export async function markJobRetrieved(workerBase, creds, fetchFn) {
  const { ok } = await postJson(workerBase, '/jobs/retrieved', {
    pkg: creds.pkg,
    retrieval_code: creds.retrieval_code,
  }, fetchFn);
  return ok;
}
