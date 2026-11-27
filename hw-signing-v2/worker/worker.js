// hw-grading — HW Signing v2 grading Worker.
//
// Interface per ~/workspace/hw-signing-v2/SPEC.md. This Worker replaces
// nothing: the v1 signing Worker stays in service for v1 assignments.
// This one holds prompt packages and grading jobs in D1 (binding DB).
//
// Secrets (Worker settings only, never in this file, never logged or
// returned): SIGNING_SECRET (HMAC, as v1), ADMIN_TOKEN, GRADING_TOKEN.
// Tokens are compared in constant time.
//
// Grade signing (format v2). Canonical signed text, one value per line,
// in this order:
//   v (=2), job_id, audio_sha256, transcript_sha256, pkg,
//   pkg_content_sha256, completeness, accuracy, critique_sha256,
//   youtube_video_sha256 (or "none"), t
// Bundles graded from 2.7.0 carry one more line,
// chromaprint_sha256 (the SHA-256 hex of the raw fingerprint bytes,
// or "none"), between youtube_video_sha256 and t; bundles graded
// earlier have no such line and keep the form above. Verify accepts
// both forms and recomputes with the form the submitted bundle
// carries, so a tampered chromaprint_sha256 fails verification.
// 2.7.1: a verify body with NO chromaprint field is accepted when
// the receipt matches either the old form or the "none" form —
// the submission package prints no Chromaprint line for a
// fingerprint-less job, so the audit app has no field to send for
// exactly the bundles that were signed over "none".
// 2.7.2: a grading result that names its claim instance
// (claimed_at, issued at claim time) is bound to that instance;
// the body-size cap counts bytes actually read, not the
// Content-Length header; dedup crosses semester databases;
// a package status change naming a database that does not hold
// the package is refused; a repeat proven duplicate reports
// alias_created as "the submitted code retrieves this job".
// 2.7.3: video bindings gain a history (job_bindings table).
// Finalising an already-final job with a DIFFERENT video whose
// fresh check token verifies performs a superseding rebind: the
// bundle is re-signed with the new video's hash and the change
// is recorded in the job's binding history; the earlier binding
// stays on record as superseded. /jobs/status and POST
// /jobs/binding expose the current bound video hash and the
// history. POST /admin/jobs/release-binding (admin token) clears
// a job's binding back to unbound, recorded as a release.
// 2.8.0: simplification. Kind is eliminated at creation (every new
// job is created as practice; finalize still marks a job final).
// Web Push is removed entirely. Duration statistics are removed.
// /youtube-check returns no token. The write-only columns
// youtube_status, retrieval_name and retrieved_at, the
// job_bindings and job_code_aliases tables, the Chromaprint
// similarity dedup layer and its proof-of-holding duplicate
// response, cross-semester fan-out (only the current semester
// database is queried), the newest-open version upgrade, the
// salted code hash and its legacy retrieval scan, and the optional
// claim binding are all removed: a duplicate is answered with
// status only, retrieval is by code_lookup only, a job is created
// under the version its link hash resolves to (a closed version
// fails creation), and a grading result must name its claimed_at.
// 2.7.4: video binding is eliminated. /jobs/finalize no longer
// verifies a YouTube check token, records a video hash, or
// re-signs a graded bundle with one: it marks the job final
// (one final per recording, as before) and holds the bundle in
// the no-video form a link-less job is signed in at grading
// (youtube_video_sha256 "none"); youtube_* fields an older page
// still sends are accepted and ignored. Re-finalizing an
// already-final job succeeds idempotently. The binding routes
// POST /jobs/binding and POST /admin/jobs/release-binding are
// removed (404), /jobs/status no longer carries a binding field,
// and nothing writes to job_bindings (the table and its existing
// rows are left in place as a historical record).
// t is stamped from the server clock at result time, never taken from
// the caller. receipt = base64url(HMAC-SHA-256(secret, canonical text)).
// Verify recomputes the receipt from the claimed values; no stored
// record is needed.
//
// /youtube-check (2.8.0) returns {video_id, status, title,
// checked_at} and no token; nothing about a link is stored. The
// jobs table keeps youtube_video_sha256 only as a legacy column:
// finalize strips it from a graded bundle by re-signing the bundle
// in the no-video form.
//
// Semester databases: one D1 database per semester, but (2.8.0)
// every operation routes to the CURRENT semester database only —
// the binding named by db_meta's current_binding pointer in the
// primary database (binding DB). Other semester databases are not
// queried.

const SERVICE_VERSION = "2.8.0";
const FORMAT_V = "2";
const CLAIM_MINUTES = 15;
// Job lifetime (2.6.0): an ungraded job is kept for up to
// UNGRADED_TTL_MS after creation, so a submission made while the
// teacher's Muse is not polling is not lost; once graded, the job
// (result bundle, hashes, fingerprint and — from 2.7.0 — the
// transcript text, which is no longer nulled at grading; see
// handleResult) is kept for GRADED_TTL_MS after grading and then
// expires. Before 2.4.1 every job expired 48 h after creation,
// graded or not; graded jobs were kept 48 h after grading before
// 2.6.0.
const UNGRADED_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const GRADED_TTL_MS = 180 * 24 * 60 * 60 * 1000;
const MAX_TRANSCRIPT_CHARS = 200000;
const MAX_CRITIQUE_CHARS = 20000;
const MAX_PACKAGE_CHARS = 500000;

const SHA256_HEX = /^[0-9a-f]{64}$/;
// Retrieval is by code only (no name). The creation rule (2.4.1):
// letters and numbers only, at least 8 characters — the code is the
// only credential for status, retrieval and finalize, so a short code
// is guessable. The minimum applies at creation only; lookup does not
// re-validate length, so jobs created before 2.4.1 with shorter codes
// remain retrievable. Jobs are looked up by code_lookup, the SHA-256
// hex of "<pkg>\n<code>", which is also the uniqueness key: one code
// per package, enforced by the jobs_code_lookup unique index.
const RETRIEVAL_CODE = /^[A-Za-z0-9]{8,128}$/;

async function codeLookupFor(pkg, code) {
  return sha256Hex(`${pkg}\n${code}`);
}
const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
const PKG_ID = /^(.*) v(\d+)$/;

function base64url(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}


function bytesToHex(bytes) {
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}


const enc = (s) => new TextEncoder().encode(s);

async function sha256Hex(data) {
  const bytes = typeof data === "string" ? enc(data) : data;
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return bytesToHex(new Uint8Array(digest));
}

async function hmacBase64url(secret, text) {
  const key = await crypto.subtle.importKey(
    "raw",
    enc(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc(text));
  return base64url(new Uint8Array(sig));
}

// ------------------------------------------------------- Chromaprint
// A fingerprint is the base64 of the raw Chromaprint bytes for the
// normalised WAV: little-endian uint32 per item, one item per
// ~0.124 s. Decode validates and returns a Uint32Array, or null
// when the field is absent, malformed or out of range — a bad
// fingerprint is ignored, never a reason to reject a job. The
// fingerprint is used only for the signed bundle's
// chromaprint_sha256; the similarity dedup layer was removed in
// 2.8.0 (dedup is exact audio SHA-256 only). Cap: 3 hours of
// audio. Measured rate is about 29,055 items per hour (a 3,600 s
// file yields 29,055 items), so a full 3-hour recording yields
// about 87,165 items; 87,200 covers it.
const FP_MAX_ITEMS = 87200;

function decodeChromaprint(value) {
  if (typeof value !== "string" || value.length === 0) return null;
  // 2.7.1: length guard before any decoding — FP_MAX_ITEMS items
  // are FP_MAX_ITEMS * 4 bytes, at most ~465,100 base64 characters;
  // a longer value is invalid without being decoded first.
  if (value.length > 470000) return null;
  if (value.length % 4 !== 0 || /[^A-Za-z0-9+/=]/.test(value)) return null;
  let bin;
  try {
    bin = atob(value);
  } catch {
    return null;
  }
  if (bin.length % 4 !== 0) return null;
  const items = bin.length / 4;
  if (items < 1 || items > FP_MAX_ITEMS) return null;
  const out = new Uint32Array(items);
  for (let i = 0; i < items; i++) {
    out[i] =
      (bin.charCodeAt(i * 4) |
        (bin.charCodeAt(i * 4 + 1) << 8) |
        (bin.charCodeAt(i * 4 + 2) << 16) |
        (bin.charCodeAt(i * 4 + 3) << 24)) >>>
      0;
  }
  return out;
}

// The raw bytes a stored fingerprint decodes to (little-endian
// uint32 per item), or null when the stored value is absent or
// invalid. Built from decodeChromaprint's validated items so the
// byte form can never drift from the comparison form; the grade
// bundle's chromaprint_sha256 (2.7.0) is the SHA-256 of these bytes.
function decodeChromaprintBytes(value) {
  const items = decodeChromaprint(value);
  if (!items) return null;
  const bytes = new Uint8Array(items.length * 4);
  const view = new DataView(bytes.buffer);
  for (let i = 0; i < items.length; i++) {
    view.setUint32(i * 4, items[i], true);
  }
  return bytes;
}

// SHA-256 hex of the raw fingerprint bytes, or "none" when the job
// has no valid fingerprint (the bundle field's empty form).
async function chromaprintSha256(value) {
  const bytes = decodeChromaprintBytes(value);
  return bytes ? sha256Hex(bytes) : "none";
}

// Constant-time comparison, so a wrong value leaks nothing about the
// right one through timing.
function timingSafeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function isText(v, max) {
  return typeof v === "string" && v.length >= 1 && v.length <= max;
}

function isScore(n) {
  return Number.isInteger(n) && n >= 0 && n <= 5;
}

function isHash(v) {
  return typeof v === "string" && SHA256_HEX.test(v.toLowerCase());
}

function json(body, status = 200) {
  const headers = {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "access-control-allow-headers": "content-type, authorization, x-admin-token, x-grading-token",
  };
  // A 204 response must carry no body: constructing one with a body
  // throws, which turned the browser's CORS preflight (OPTIONS) into
  // a 500 in v1. Keep this branch first and bodyless.
  if (status === 204) return new Response(null, { status, headers });
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...headers, "content-type": "application/json" },
  });
}

async function readJson(request, maxBytes = 1500000) {
  // Reject an oversize body before parsing it. The largest
  // legitimate body is a job (a 200,000-character transcript plus a
  // fingerprint) or a package text (500,000 characters, given the
  // larger cap at that route); anything beyond the cap is refused
  // without being materialised field by field. 2.7.1 enforced the
  // cap through the Content-Length header only, which a chunked or
  // streamed body simply omits; 2.7.2 counts the bytes as they are
  // read and refuses the moment the cap is passed, keeping the
  // header check as a fast path.
  const len = Number(request.headers.get("content-length") || 0);
  if (Number.isFinite(len) && len > maxBytes) return null;
  try {
    let text;
    if (request.body && typeof request.body.getReader === "function") {
      const reader = request.body.getReader();
      const chunks = [];
      let total = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        total += value.byteLength;
        if (total > maxBytes) {
          try { await reader.cancel(); } catch { /* already refused */ }
          return null;
        }
        chunks.push(value);
      }
      const buf = new Uint8Array(total);
      let off = 0;
      for (const c of chunks) { buf.set(c, off); off += c.byteLength; }
      text = new TextDecoder().decode(buf);
    } else {
      text = await request.text();
      if (text.length > maxBytes) return null;
    }
    return JSON.parse(text);
  } catch {
    return null;
  }
}

// The pkg identifier used in links and jobs is "<name> v<version>".
// The packages table stores the name in pkg and the version separately.
function parsePkgId(pkg) {
  if (typeof pkg !== "string") return null;
  const m = PKG_ID.exec(pkg);
  if (!m) return null;
  return { name: m[1], version: Number(m[2]), full: pkg };
}

function parseVideoId(raw) {
  if (typeof raw !== "string") return null;
  let u;
  try {
    u = new URL(raw);
  } catch {
    return null;
  }
  const host = u.hostname.toLowerCase();
  let id = null;
  if (host === "youtu.be" || host === "www.youtu.be") {
    id = u.pathname.split("/").filter(Boolean)[0] || null;
  } else if (
    ["youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"].includes(host)
  ) {
    if (u.pathname === "/watch") {
      id = u.searchParams.get("v");
    } else {
      const m = /^\/(shorts|live|embed|v)\/([^/]+)/.exec(u.pathname);
      if (m) id = m[2];
    }
  }
  return id && VIDEO_ID.test(id) ? id : null;
}

// Token check against an env secret. Accepts either
// `Authorization: Bearer <token>` or the dedicated header for the
// secret (X-Admin-Token for ADMIN_TOKEN, X-Grading-Token for
// GRADING_TOKEN) — the teacher skills' scripts send the dedicated
// headers, other clients send Bearer. Returns an error Response, or
// null when the caller is authorised. Fails closed when the token
// is not configured.
function requireToken(request, env, envName) {
  if (!env[envName]) {
    return json({ error: envName.toLowerCase() + " not configured" }, 500);
  }
  const header = request.headers.get("authorization") || "";
  let token = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!token) {
    const altHeader = "x-" + envName.toLowerCase().replace(/_/g, "-");
    token = request.headers.get(altHeader) || "";
  }
  if (!token || !timingSafeEqual(token, env[envName])) {
    return json({ error: "unauthorized" }, 401);
  }
  return null;
}

function requireSigning(env) {
  return env.SIGNING_SECRET
    ? null
    : json({ error: "signing secret not configured" }, 500);
}

function requireDb(env) {
  return env.DB ? null : json({ error: "database not configured" }, 500);
}

// ---------------------------------------------------------------- D1

async function getPackageRow(db, name, version) {
  return db.prepare(
    "SELECT * FROM packages WHERE pkg = ? AND version = ?",
  )
    .bind(name, version)
    .first();
}

async function getJobRow(db, jobId) {
  return db.prepare("SELECT * FROM jobs WHERE job_id = ?")
    .bind(jobId)
    .first();
}

// ------------------------------------------------- semester databases
// One database per semester, but (2.8.0) every operation routes to
// the CURRENT semester database only: the binding named by
// db_meta's current_binding pointer in the primary database
// (binding DB), falling back to the primary database itself when
// the pointer is absent or names no binding in env. Other semester
// databases are not queried by any handler.

// The binding of the current semester database: db_meta's
// current_binding in the primary database, falling back to "DB".
async function currentBinding(env) {
  try {
    const row = await env.DB.prepare(
      "SELECT value FROM db_meta WHERE key = ?",
    )
      .bind("current_binding")
      .first();
    if (row && typeof row.value === "string" && row.value) {
      return row.value;
    }
  } catch {
    // No db_meta yet: the primary database is the default.
  }
  return "DB";
}

// The current semester database as {binding, db}, or null when the
// primary database is not configured.
async function currentDb(env) {
  if (!env.DB || typeof env.DB.prepare !== "function") return null;
  const binding = await currentBinding(env);
  if (
    binding !== "DB" &&
    /^DB_[A-Z0-9_]+$/.test(binding) &&
    env[binding] &&
    typeof env[binding].prepare === "function"
  ) {
    return { binding, db: env[binding] };
  }
  return { binding: "DB", db: env.DB };
}

// The current database's row for package `name` at `version`, as
// {binding, db, row}, or null when the current database does not
// hold it. Other semester databases are not checked.
async function resolvePackage(env, name, version) {
  const cur = await currentDb(env);
  if (!cur) return null;
  const row = await getPackageRow(cur.db, name, version);
  return row ? { binding: cur.binding, db: cur.db, row } : null;
}

// Resolve the package for student job creation and link
// verification, which carry the package name + version AND the
// link's content hash, within the current database only. Returns
// {match, sawRow}: match is the {binding, db, row} or null; sawRow
// records whether the current database holds the name + version at
// all, so the caller can tell an unknown package from a hash
// mismatch.
async function resolvePackageByHash(env, name, version, contentSha256) {
  const cur = await currentDb(env);
  if (!cur) return { match: null, sawRow: false };
  const row = await getPackageRow(cur.db, name, version);
  if (!row) return { match: null, sawRow: false };
  const match = timingSafeEqual(
    row.content_sha256.toLowerCase(),
    String(contentSha256).toLowerCase(),
  )
    ? { binding: cur.binding, db: cur.db, row }
    : null;
  return { match, sawRow: true };
}

// The current database's row for a job, as {binding, db, row}, or
// null when the current database does not hold the job.
async function findJobDb(env, jobId) {
  const cur = await currentDb(env);
  if (!cur) return null;
  const row = await getJobRow(cur.db, jobId);
  return row ? { binding: cur.binding, db: cur.db, row } : null;
}

// The job a retrieval code names, in the current database only
// (swept first): {binding, db, row}, or {error} with the retrieval
// error Response when the current database does not hold the job.
async function jobByRetrievalCurrent(env, body) {
  const cur = await currentDb(env);
  if (!cur) return { error: json({ error: "database not configured" }, 500) };
  await sweep(cur.db, new Date().toISOString());
  const row = await jobByRetrieval(cur.db, body);
  if (isErrorResponse(row)) return { error: row };
  return { binding: cur.binding, db: cur.db, row };
}


// Job lifecycle maintenance, run at the start of job-related calls:
// jobs past their expiry lose their transcript and result and
// become "expired"; claims past their 15 min lease return to "queued".
// The expiry a student should be shown for a live job: for an
// ungraded job the created_at + UNGRADED_TTL_MS cap (a job created
// before 2.4.1 carries a stored expires_at of creation + 48 h, which
// no longer governs it while it is ungraded); for a graded job
// graded_at + GRADED_TTL_MS (180 days since 2.6.0; the stored
// expires_at holds exactly that for jobs graded under 2.6.0, and
// graded_at + 48 h for jobs graded under 2.4.1–2.5.0, which no longer
// governs them either).
function effectiveExpiresAt(row) {
  if (row.status === "queued" || row.status === "claimed") {
    return new Date(
      Date.parse(row.created_at) + UNGRADED_TTL_MS,
    ).toISOString();
  }
  if (row.status === "ready" && row.graded_at) {
    return new Date(
      Date.parse(row.graded_at) + GRADED_TTL_MS,
    ).toISOString();
  }
  return row.expires_at;
}

async function sweep(db, nowIso) {
  // Graded (ready) jobs expire GRADED_TTL_MS after grading, measured
  // from graded_at so jobs graded before 2.4.1 follow the same rule.
  await db.prepare(
    "UPDATE jobs SET status = ?, transcript = NULL, critique = NULL, " +
      "result_json = NULL, push_json = NULL, chromaprint = NULL, " +
      "receipt = NULL, completeness = NULL, accuracy = NULL, " +
      "youtube_video_sha256 = NULL " +
      "WHERE status = ? AND graded_at <= ?",
  )
    .bind(
      "expired",
      "ready",
      new Date(Date.parse(nowIso) - GRADED_TTL_MS).toISOString(),
    )
    .run();
  // Any other non-queued status (none is defined today) expires at
  // its stored expires_at.
  await db.prepare(
    "UPDATE jobs SET status = ?, transcript = NULL, critique = NULL, " +
      "result_json = NULL, push_json = NULL, chromaprint = NULL, " +
      "receipt = NULL, completeness = NULL, accuracy = NULL, " +
      "youtube_video_sha256 = NULL " +
      "WHERE expires_at <= ? AND status <> ? " +
      "AND status <> ? AND status <> ? AND status <> ?",
  )
    .bind("expired", nowIso, "expired", "queued", "claimed", "ready")
    .run();
  // Ungraded jobs expire only at the ungraded cap, measured from
  // creation, whatever their stored expires_at says (jobs created
  // before 2.4.1 carry creation + 48 h there).
  const ungradedCutoff = new Date(
    Date.parse(nowIso) - UNGRADED_TTL_MS,
  ).toISOString();
  for (const st of ["queued", "claimed"]) {
    await db.prepare(
      "UPDATE jobs SET status = ?, transcript = NULL, critique = NULL, " +
        "result_json = NULL, push_json = NULL, chromaprint = NULL, " +
      "receipt = NULL, completeness = NULL, accuracy = NULL, " +
      "youtube_video_sha256 = NULL " +
        "WHERE status = ? AND created_at <= ?",
    )
      .bind("expired", st, ungradedCutoff)
      .run();
  }
  await db.prepare(
    "UPDATE jobs SET status = ?, claimed_at = NULL, claim_expires = NULL " +
      "WHERE status = ? AND claim_expires <= ?",
  )
    .bind("queued", "claimed", nowIso)
    .run();
}

async function jobCounts(db, pkgFull) {
  const { results } = await db.prepare(
    "SELECT status FROM jobs WHERE pkg = ?",
  )
    .bind(pkgFull)
    .all();
  const counts = { total: results.length };
  for (const r of results) counts[r.status] = (counts[r.status] || 0) + 1;
  return counts;
}

async function packageMeta(db, row) {
  const full = `${row.pkg} v${row.version}`;
  return {
    pkg: full,
    version: row.version,
    content_sha256: row.content_sha256,
    status: row.status,
    trial: row.trial_json ? JSON.parse(row.trial_json) : null,
    jobs: await jobCounts(db, full),
    created_at: row.created_at,
  };
}

// ------------------------------------------------------------ handlers

async function handleRoot(env) {
  // 2.8.0: only the current semester database is used, and Web
  // Push (and its VAPID key) is removed, so no vapid_public_key is
  // advertised.
  return json({
    service: "hw-grading",
    version: SERVICE_VERSION,
    storage: "d1",
    databases: env.DB ? 1 : 0,
  });
}

async function handleYoutubeCheck(request, env) {
  const body = await readJson(request);
  if (!body || typeof body !== "object") {
    return json({ error: "invalid request body" }, 400);
  }
  const videoId = parseVideoId(body.url);
  if (!videoId) return json({ error: "not a YouTube video URL" }, 400);
  const watchUrl = `https://www.youtube.com/watch?v=${videoId}`;
  const oembedUrl =
    `https://www.youtube.com/oembed?url=${encodeURIComponent(watchUrl)}&format=json`;
  let status = "private_or_missing";
  let title = null;
  try {
    const res = await fetch(oembedUrl);
    if (res.status === 200) {
      status = "ok";
      // The video's title is returned to the student who supplied
      // the link, so they can recognise the video as theirs (or see
      // that it is a different homework's). Nothing about the link —
      // title included — is stored on the Worker.
      try {
        const body = await res.json();
        if (body && typeof body.title === "string" && body.title.trim()) {
          title = body.title.trim().slice(0, 200);
        }
      } catch { title = null; }
    }
  } catch {
    status = "private_or_missing";
  }
  const checked_at = new Date().toISOString();
  // 2.8.0: no token is generated or returned.
  return json({ video_id: videoId, status, title, checked_at });
}

function validVersions(v) {
  return (
    v &&
    typeof v === "object" &&
    isText(v.webapp, 64) &&
    isText(v.model, 64) &&
    isText(v.glossary, 64)
  );
}

// The one live (non-expired) final job for a (package, audio
// fingerprint), or null. The jobs_one_final partial unique index in
// schema.sql enforces this invariant in the database; this lookup is
// the friendly pre-check and the post-race arbiter.
async function findLiveFinal(db, pkgFull, audioSha256) {
  return db.prepare(
    "SELECT job_id FROM jobs WHERE pkg = ? AND audio_sha256 = ? " +
      "AND kind = ? AND status <> ?",
  )
    .bind(pkgFull, audioSha256, "final", "expired")
    .first();
}

// Dedup (2.8.0): the live job for the same recording under the
// resolved package version, by exact audio SHA-256 only, or null.
// The jobs_one_per_recording partial unique index in schema.sql
// is the backstop. Earliest created_at wins.
async function findLiveDuplicate(db, pkgFull, audioSha256) {
  const { results } = await db.prepare(
    "SELECT * FROM jobs WHERE pkg = ? AND audio_sha256 = ? " +
      "AND status <> ? ORDER BY created_at",
  )
    .bind(pkgFull, audioSha256, "expired")
    .all();
  return (results && results.length) ? results[0] : null;
}

// The duplicate response for POST /jobs (2.8.0): no new job is
// created and the response carries STATUS ONLY — the duplicate's
// identity and status (and queue position while it waits) — with
// no result bundle, grades, critique or transcript, and no alias
// is created for the submitted code. Retrieval of the existing
// job is only with its original code.
async function duplicateResponse(db, dupRow) {
  const out = {
    duplicate: true,
    job_id: dupRow.job_id,
    created_at: dupRow.created_at,
    expires_at: effectiveExpiresAt(dupRow),
    pkg: dupRow.pkg,
    status: dupRow.status,
  };
  if (dupRow.status === "queued" || dupRow.status === "claimed") {
    out.queue_ahead = await queueAhead(db, dupRow);
  }
  return json(out);
}

async function handleJobCreate(request, env) {
  const badSecret = requireSigning(env);
  if (badSecret) return badSecret;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const body = await readJson(request);
  if (!body || typeof body !== "object") {
    return json({ error: "invalid request body" }, 400);
  }
  const parsed = parsePkgId(body.pkg);
  if (
    !parsed ||
    !isHash(body.pkg_content_sha256) ||
    typeof body.transcript !== "string" ||
    body.transcript.length < 1 ||
    body.transcript.length > MAX_TRANSCRIPT_CHARS ||
    !isHash(body.audio_sha256) ||
    !isHash(body.transcript_sha256) ||
    !validVersions(body.versions) ||
    typeof body.retrieval_code !== "string" ||
    !RETRIEVAL_CODE.test(body.retrieval_code)
  ) {
    // 2.8.0: kind, youtube_* and push_subscription fields are not
    // read at creation; a body carrying them (an older page) is
    // accepted and they are ignored.
    return json({ error: "invalid request body" }, 400);
  }

  // transcript_sha256 is verified, not only shape-checked: the value
  // signed at result time must be the hash of the transcript actually
  // stored, so a mismatch is rejected here rather than signed later.
  // (Review fix F3.) The shared understanding with the webapp:
  // body.transcript IS the webapp's canonical transcript string —
  // canonicalTranscript() in webapp js/transcript.js collapses each
  // scrubbed chunk's whitespace to a single line, prefixes it with
  // the chunk's [mm:ss] start marker (since webapp 2.4.2; earlier
  // versions sent no markers), drops empty chunks, and joins with
  // "\n" (LF, no trailing newline) — and the webapp
  // sets transcript_sha256 to the SHA-256 hex of exactly that string
  // (webapp js/main.js: sha256Hex(canonical())). The recompute is
  // therefore over the received string itself.
  const transcriptHash = await sha256Hex(body.transcript);
  if (!timingSafeEqual(transcriptHash, body.transcript_sha256.toLowerCase())) {
    return json({ error: "transcript hash mismatch" }, 400);
  }

  const now = new Date();
  const nowIso = now.toISOString();
  // Current semester database only (2.8.0): it is swept, and the
  // package is resolved by the link's name, version AND content
  // hash within it (see resolvePackageByHash).
  const cur = await currentDb(env);
  if (!cur) return json({ error: "database not configured" }, 500);
  const db = cur.db;
  await sweep(db, nowIso);
  const resolved = await resolvePackageByHash(
    env,
    parsed.name,
    parsed.version,
    body.pkg_content_sha256,
  );
  if (!resolved.match) {
    return resolved.sawRow
      ? json({ error: "package content hash mismatch" }, 400)
      : json({ error: "unknown package" }, 404);
  }
  const pkgRow = resolved.match.row;

  // Version resolution (2.8.0): the job is created under the
  // version its link hash resolves to — there is no upgrade to a
  // newer open version. If that version is not open, creation
  // fails: the version is closed.
  if (pkgRow.status !== "open") {
    return json(
      { error: `package version is closed: ${parsed.full} is not open` },
      409,
    );
  }
  const resolvedFull = parsed.full;

  // Chromaprint (optional): decode and validate; an invalid,
  // oversize or absent fingerprint is ignored — a bad fingerprint
  // never rejects a job. The fingerprint is stored for the signed
  // bundle's chromaprint_sha256 only; it plays no part in dedup.
  const fpItems = decodeChromaprint(body.chromaprint);
  const storedChromaprint = fpItems ? body.chromaprint : null;
  const codeLookup = await codeLookupFor(parsed.full, body.retrieval_code);

  // Dedup (2.8.0): exact audio SHA-256 only, after resolution and
  // before insert. On a match no new job is created; the response
  // carries status only (see duplicateResponse). This runs before
  // the code-uniqueness check, so a duplicate submission is
  // answered as a duplicate even with a code already used by
  // another job. Same-code resubmission of the same job is also
  // answered here, as the duplicate.
  const dup = await findLiveDuplicate(
    db,
    resolvedFull,
    body.audio_sha256.toLowerCase(),
  );
  if (dup) return duplicateResponse(db, dup);

  // The lookup embeds the requested pkg string while the job row is
  // stored under the resolved version, so the clash check — like
  // retrieval — keys on the lookup alone.
  const codeClash = await db.prepare(
    "SELECT job_id FROM jobs WHERE code_lookup = ?",
  )
    .bind(codeLookup)
    .first();
  if (codeClash) {
    return json({ error: "retrieval code already used for this package" }, 409);
  }

  const jobId = crypto.randomUUID();
  const expiresIso = new Date(now.getTime() + UNGRADED_TTL_MS).toISOString();
  // INSERT compatibility (2.8.0): the column list is unchanged from
  // 2.7.x so the statement runs against live databases, whose
  // inert columns (retrieval_name, code_salt, code_hash,
  // youtube_status, youtube_video_sha256, push_json, retrieved_at)
  // receive constant values ("", NULL or "none"); no salted code
  // hash, push subscription or video hash is stored. schema.sql
  // for new databases drops the write-only columns.
  try {
    await db.prepare(
      "INSERT INTO jobs (job_id, pkg, retrieval_name, code_lookup, code_salt, code_hash, " +
        "kind, status, transcript, audio_sha256, transcript_sha256, chromaprint, " +
        "versions_json, youtube_status, youtube_video_sha256, completeness, " +
        "accuracy, critique, result_json, receipt, push_json, claimed_at, " +
        "claim_expires, created_at, graded_at, retrieved_at, expires_at) " +
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )
      .bind(
        jobId,
        resolvedFull,
        "",
        codeLookup,
        null,
        null,
        "practice",
        "queued",
        body.transcript,
        body.audio_sha256.toLowerCase(),
        body.transcript_sha256.toLowerCase(),
        storedChromaprint,
        JSON.stringify({
          webapp: body.versions.webapp,
          model: body.versions.model,
          glossary: body.versions.glossary,
        }),
        "none",
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        nowIso,
        null,
        null,
        expiresIso,
      )
      .run();
  } catch {
    // A UNIQUE constraint fired despite the checks above: a concurrent
    // create won the race. Re-check the dedup rule — the
    // jobs_one_per_recording partial index (one live job per audio
    // fingerprint per resolved version, all kinds) or the
    // jobs_code_lookup index (one job per retrieval code per
    // package). A dedup match is returned as the duplicate, as the
    // one-final catch did before 2.6.0. (Review fix F2, extended.)
    const raced = await findLiveDuplicate(
      db,
      resolvedFull,
      body.audio_sha256.toLowerCase(),
    );
    if (raced) return duplicateResponse(db, raced);
    return json({ error: "retrieval code already used for this package" }, 409);
  }
  return json({
    job_id: jobId,
    created_at: nowIso,
    expires_at: expiresIso,
    pkg: resolvedFull,
  });
}

// Shared auth for /jobs/status and /jobs/finalize. Retrieval is
// by code only: the code_lookup hash (SHA-256 of "<pkg>\n<code>")
// is the only lookup (2.8.0 — the salted-hash legacy scan for
// pre-2.1.0 rows and the alias lookup are removed; NULL
// code_lookup rows are pre-2.1.0 and long expired). An unknown
// code and a wrong code deliberately return the identical 403
// body. Returns the job row, or an error Response.
async function jobByRetrieval(db, body) {
  if (
    !body ||
    typeof body !== "object" ||
    typeof body.pkg !== "string" ||
    typeof body.retrieval_code !== "string"
  ) {
    return json({ error: "invalid retrieval code" }, 403);
  }
  const lookup = await codeLookupFor(body.pkg, body.retrieval_code);
  const row = await db.prepare(
    "SELECT * FROM jobs WHERE code_lookup = ?",
  )
    .bind(lookup)
    .first();
  if (row) return row;
  return json({ error: "invalid retrieval code" }, 403);
}

// How many jobs are ahead of this one in the grading queue, within
// the job's own semester database (2.7.0; the /jobs/pending order
// itself merges all semester databases): every job in that
// database currently claimed (being graded), plus every queued job
// created earlier. For a claimed job, the jobs claimed before it.
async function queueAhead(db, row) {
  if (row.status === "claimed") {
    const r = await db.prepare(
      "SELECT COUNT(*) AS n FROM jobs WHERE status = ? AND claimed_at < ?",
    )
      .bind("claimed", row.claimed_at)
      .first();
    return r ? r.n : 0;
  }
  const claimed = await db.prepare(
    "SELECT COUNT(*) AS n FROM jobs WHERE status = ?",
  )
    .bind("claimed")
    .first();
  const earlier = await db.prepare(
    "SELECT COUNT(*) AS n FROM jobs WHERE status = ? AND created_at < ?",
  )
    .bind("queued", row.created_at)
    .first();
  return (claimed ? claimed.n : 0) + (earlier ? earlier.n : 0);
}

function isErrorResponse(v) {
  return v instanceof Response;
}

async function handleJobStatus(request, env) {
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const body = await readJson(request);
  // Current semester database only (2.8.0).
  const found = await jobByRetrievalCurrent(env, body);
  if (found.error) return found.error;
  const db = found.db;
  const row = found.row;
  // The sweep above has already expired every job that is due, under
  // the ungraded cap or the graded expiry as its status requires, so
  // the stored status is the whole determination here.
  if (row.status === "expired") {
    return json({ status: "expired" });
  }
  const out = { status: row.status, expires_at: effectiveExpiresAt(row) };
  if (row.status === "queued" || row.status === "claimed") {
    out.queue_ahead = await queueAhead(db, row);
  }
  if (row.status === "ready" && row.result_json) {
    const bundle = JSON.parse(row.result_json);
    delete bundle.injection_flags;
    out.result = bundle;
    // 2.7.0: the code holder also receives the stored transcript
    // and the stored fingerprint, so the submission package can be
    // rebuilt on a computer that never held the recording.
    out.transcript = row.transcript;
    out.chromaprint = row.chromaprint ?? null;
  }
  return json(out);
}

// POST /jobs/finalize {pkg, retrieval_code} — turn an existing job
// into the final (Canvas submission) job. Allowed in any live
// status. Since 2.7.4 no video is bound: any youtube_* fields an
// older page still sends (youtube_token, youtube_video_id,
// youtube_checked_at) are accepted and ignored — the token is NOT
// verified — no video hash is recorded, and a graded bundle is
// held in, or brought to, the no-video form a link-less job is
// signed in at grading (youtube_video_sha256 "none"; see
// handleResult, which signs row.youtube_video_sha256 || "none").
// The one-final-per-recording rule applies as at intake.
// Re-finalizing a job that is already final (under any version)
// succeeds idempotently with the job's current receipt: the page
// calls finalize on every Generate ZIP confirm, including for a
// job an earlier ZIP generation already marked final. The
// decision to submit is thus made after the grade is seen, with
// no second grading.
async function handleJobFinalize(request, env) {
  const badSecret = requireSigning(env);
  if (badSecret) return badSecret;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const body = await readJson(request);
  const found = await jobByRetrievalCurrent(env, body);
  if (found.error) return found.error;
  const db = found.db;
  const row = found.row;
  if (row.status === "expired") {
    return json({ error: "job expired" }, 410);
  }
  const priorFinal = await findLiveFinal(db, row.pkg, row.audio_sha256);
  if (priorFinal && priorFinal.job_id !== row.job_id) {
    return json({ error: "a final job already exists for this recording" }, 409);
  }
  let receipt = row.receipt;
  let resultJson = row.result_json;
  if (row.status === "ready" && row.result_json) {
    const bundle = JSON.parse(row.result_json);
    if (bundle.youtube_video_sha256 !== "none") {
      // A bundle bound under an earlier version is brought to the
      // no-video form. gradeCanonical signs in the bundle's own
      // form (2.7.0): a bundle carrying chromaprint_sha256 is
      // re-signed with it, a pre-2.7.0 bundle without the field
      // keeps the old canonical and does not gain the field.
      bundle.youtube_video_sha256 = "none";
      receipt = await hmacBase64url(env.SIGNING_SECRET, gradeCanonical(bundle));
      bundle.receipt = receipt;
      resultJson = JSON.stringify(bundle);
    }
  }
  try {
    await db.prepare(
      "UPDATE jobs SET kind = ?, youtube_status = ?, " +
        "youtube_video_sha256 = NULL, result_json = ?, receipt = ? " +
        "WHERE job_id = ?",
    )
      .bind("final", "none", resultJson, receipt, row.job_id)
      .run();
  } catch {
    return json({ error: "a final job already exists for this recording" }, 409);
  }
  return json({ ok: true, receipt });
}

async function handlePending(request, env) {
  const badAuth = requireToken(request, env, "GRADING_TOKEN");
  if (badAuth) return badAuth;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const nowIso = new Date().toISOString();
  // Current semester database only (2.8.0): sweep and read it.
  // The sweep has expired every due job, so a job still in status
  // queued is live. Each entry carries the current binding as
  // `db` for compatibility with claim/result callers. The kind
  // field is dropped (2.8.0).
  const cur = await currentDb(env);
  if (!cur) return json({ error: "database not configured" }, 500);
  await sweep(cur.db, nowIso);
  const { results } = await cur.db.prepare(
    "SELECT job_id, pkg, created_at, transcript FROM jobs " +
      "WHERE status = ? ORDER BY created_at",
  )
    .bind("queued")
    .all();
  const merged = (results || []).map((r) => ({
    job_id: r.job_id,
    pkg: r.pkg,
    created_at: r.created_at,
    transcript_chars: r.transcript ? r.transcript.length : 0,
    db: cur.binding,
  }));
  return json(merged);
}

async function handleClaim(request, env) {
  const badAuth = requireToken(request, env, "GRADING_TOKEN");
  if (badAuth) return badAuth;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const body = await readJson(request);
  if (!body || typeof body !== "object" || !isText(body.job_id, 128)) {
    return json({ error: "invalid request body" }, 400);
  }
  const now = new Date();
  // Current semester database only (2.8.0): it is swept and the
  // job is looked up there alone; a `db` field in the body does
  // not redirect the lookup.
  const nowIso = now.toISOString();
  const cur = await currentDb(env);
  if (!cur) return json({ error: "database not configured" }, 500);
  await sweep(cur.db, nowIso);
  const target = await findJobDb(env, body.job_id);  const db = target.db;
  const row = target.row;
  // After the sweep, a claimable job (queued, or claimed with an
  // expired lease) is exactly a job in status "queued".
  if (row.status !== "queued") {
    return json({ error: "job is not claimable" }, 409);
  }
  const claimExpires = new Date(now.getTime() + CLAIM_MINUTES * 60 * 1000);
  const claimedAtIso = now.toISOString();
  // The claim is this UPDATE, guarded on the job still being queued —
  // not the status check above, which a racing poller can pass at the
  // same moment. Only the first UPDATE matches status = 'queued'; a
  // loser sees changes === 0 and gets 409. (Review fix F1.)
  const upd = await db.prepare(
    "UPDATE jobs SET status = ?, claimed_at = ?, claim_expires = ? " +
      "WHERE job_id = ? AND status = ?",
  )
    .bind(
      "claimed",
      claimedAtIso,
      claimExpires.toISOString(),
      row.job_id,
      "queued",
    )
    .run();
  if (!upd.meta || upd.meta.changes === 0) {
    return json({ error: "job is not claimable" }, 409);
  }
  const parsed = parsePkgId(row.pkg);
  const pkgRow = parsed
    ? await getPackageRow(db, parsed.name, parsed.version)
    : null;
  if (!pkgRow) return json({ error: "package record missing" }, 500);
  return json({
    job_id: row.job_id,
    // 2.7.2: the claim instance identifier. The grader returns it
    // with the result, binding the result to this claim (see
    // handleResult); claimed_at is unique to a claim because a job
    // can hold only one live claim at a time.
    claimed_at: claimedAtIso,
    transcript: row.transcript,
    audio_sha256: row.audio_sha256,
    transcript_sha256: row.transcript_sha256,
    versions: JSON.parse(row.versions_json),
    package: {
      pkg: row.pkg,
      text: pkgRow.text,
      content_sha256: pkgRow.content_sha256,
    },
  });
}

// Canonical signed text for a v2 grade (see header comment). The
// form is chosen by the bundle itself: a bundle carrying a
// chromaprint_sha256 string (graded from 2.7.0) signs with that
// line between youtube_video_sha256 and t; a pre-2.7.0 bundle
// without the field signs with the original form. Signing,
// re-signing at finalize, and verification all go through this one
// function, so each bundle keeps the form it was created in.
function gradeCanonical(f) {
  const lines = [
    FORMAT_V,
    f.job_id,
    f.audio_sha256,
    f.transcript_sha256,
    f.pkg,
    f.pkg_content_sha256,
    String(f.completeness),
    String(f.accuracy),
    f.critique_sha256,
    f.youtube_video_sha256,
  ];
  if (typeof f.chromaprint_sha256 === "string") {
    lines.push(f.chromaprint_sha256);
  }
  lines.push(f.t);
  return lines.join("\n");
}

async function handleResult(request, env) {
  const badAuth = requireToken(request, env, "GRADING_TOKEN");
  if (badAuth) return badAuth;
  const badSecret = requireSigning(env);
  if (badSecret) return badSecret;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const body = await readJson(request);
  if (
    !body ||
    typeof body !== "object" ||
    !isText(body.job_id, 128) ||
    !isScore(body.completeness) ||
    !isScore(body.accuracy) ||
    typeof body.critique !== "string" ||
    body.critique.length < 1 ||
    body.critique.length > MAX_CRITIQUE_CHARS ||
    (body.injection_flags !== undefined &&
      body.injection_flags !== null &&
      !Array.isArray(body.injection_flags)) ||
    !isText(body.claimed_at, 64)
  ) {
    // 2.8.0: claimed_at is mandatory — a result naming no claim
    // instance is rejected (the optional fallback is removed).
    return json({ error: "invalid request body" }, 400);
  }
  const now = new Date();
  // Current semester database only (2.8.0), resolved as in claim.
  const nowIso = now.toISOString();
  const cur = await currentDb(env);
  if (!cur) return json({ error: "database not configured" }, 500);
  await sweep(cur.db, nowIso);
  const target = await findJobDb(env, body.job_id);  const db = target.db;
  const row = target.row;
  if (
    row.status !== "claimed" ||
    !row.claim_expires ||
    Date.parse(row.claim_expires) <= now.getTime()
  ) {
    return json({ error: "no live claim on this job" }, 409);
  }
  // Claim binding (mandatory, 2.8.0): the result must name its
  // claim instance (claimed_at, issued by /grading/claim —
  // validated as present above) and is accepted only for that
  // instance.
  if (row.claimed_at !== body.claimed_at) {
    return json({ error: "result does not match the live claim" }, 409);
  }
  const parsed = parsePkgId(row.pkg);
  const pkgRow = parsed
    ? await getPackageRow(db, parsed.name, parsed.version)
    : null;
  if (!pkgRow) return json({ error: "package record missing" }, 500);

  const t = now.toISOString();
  const critiqueSha256 = await sha256Hex(body.critique);
  const bundle = {
    v: 2,
    job_id: row.job_id,
    audio_sha256: row.audio_sha256,
    transcript_sha256: row.transcript_sha256,
    pkg: row.pkg,
    pkg_content_sha256: pkgRow.content_sha256,
    completeness: body.completeness,
    accuracy: body.accuracy,
    critique: body.critique,
    critique_sha256: critiqueSha256,
    youtube_video_sha256: row.youtube_video_sha256 || "none",
    // 2.7.0: the fingerprint's hash is signed into the bundle, so
    // the fingerprint a student later presents with the bundle can
    // be checked against the grade it belongs to.
    chromaprint_sha256: await chromaprintSha256(row.chromaprint),
    t,
  };
  bundle.receipt = await hmacBase64url(
    env.SIGNING_SECRET,
    gradeCanonical(bundle),
  );
  const stored = { ...bundle, injection_flags: body.injection_flags || [] };
  // Grading starts the job's remaining lifetime: it now expires
  // GRADED_TTL_MS after grading, replacing the ungraded cap. The
  // transcript text is kept (2.7.0, reversing the 2.6.0 transcript
  // minimisation): the text, transcript_sha256, the acoustic
  // fingerprint, the result bundle and the code lookup are kept
  // for the 180 days, and status returns the
  // transcript and fingerprint with the bundle. The text is removed
  // only when the job expires (see sweep).
  const gradedExpires = new Date(
    Date.parse(t) + GRADED_TTL_MS,
  ).toISOString();
  // 2.7.1: the UPDATE is guarded by the same live-claim condition
  // the read above checked. Without the guard, a claim that expired
  // and was re-claimed by another grader between the read and this
  // UPDATE could still be overwritten by the first grader's result,
  // and two concurrent result posts could both land, the second
  // silently replacing the first (and invalidating its receipt).
  const upd = await db.prepare(
    "UPDATE jobs SET status = ?, completeness = ?, accuracy = ?, " +
      "critique = ?, result_json = ?, receipt = ?, graded_at = ?, " +
      "expires_at = ?, claim_expires = NULL WHERE job_id = ? " +
      "AND status = ? AND claim_expires > ? AND claimed_at = ?",
  )
    .bind(
      "ready",
      body.completeness,
      body.accuracy,
      body.critique,
      JSON.stringify(stored),
      bundle.receipt,
      t,
      gradedExpires,
      row.job_id,
      "claimed",
      nowIso,
      body.claimed_at,
    )
    .run();
  if (!upd || !upd.meta || upd.meta.changes !== 1) {
    return json({ error: "no live claim on this job" }, 409);
  }
  // 2.8.0: Web Push is removed — no push is sent at result time.
  return json({ ok: true, receipt: bundle.receipt });
}

async function handleVerifyGrade(request, env) {
  const bad = requireSigning(env);
  if (bad) return bad;
  const body = await readJson(request);
  if (
    !body ||
    typeof body !== "object" ||
    !(body.v === 2 || body.v === "2") ||
    !isText(body.job_id, 128) ||
    !isHash(body.audio_sha256) ||
    !isHash(body.transcript_sha256) ||
    !isText(body.pkg, 128) ||
    !isHash(body.pkg_content_sha256) ||
    !isScore(body.completeness) ||
    !isScore(body.accuracy) ||
    !isHash(body.critique_sha256) ||
    !(
      body.youtube_video_sha256 === "none" ||
      isHash(body.youtube_video_sha256)
    ) ||
    !(
      body.chromaprint_sha256 === undefined ||
      body.chromaprint_sha256 === "none" ||
      isHash(body.chromaprint_sha256)
    ) ||
    !isText(body.t, 64) ||
    Number.isNaN(Date.parse(body.t)) ||
    typeof body.receipt !== "string" ||
    !/^[A-Za-z0-9_-]{43}$/.test(body.receipt)
  ) {
    return json({ error: "invalid request body" }, 400);
  }
  const f = {
    job_id: body.job_id,
    audio_sha256: body.audio_sha256.toLowerCase(),
    transcript_sha256: body.transcript_sha256.toLowerCase(),
    pkg: body.pkg,
    pkg_content_sha256: body.pkg_content_sha256.toLowerCase(),
    completeness: body.completeness,
    accuracy: body.accuracy,
    critique_sha256: body.critique_sha256.toLowerCase(),
    youtube_video_sha256:
      body.youtube_video_sha256 === "none"
        ? "none"
        : body.youtube_video_sha256.toLowerCase(),
    t: body.t,
  };
  // Dual form (2.7.0): a bundle carrying a chromaprint_sha256
  // string is recomputed with the new canonical, a bundle without
  // the field with the pre-2.7.0 canonical (see gradeCanonical).
  if (typeof body.chromaprint_sha256 === "string") {
    f.chromaprint_sha256 =
      body.chromaprint_sha256 === "none"
        ? "none"
        : body.chromaprint_sha256.toLowerCase();
    const expected = await hmacBase64url(env.SIGNING_SECRET, gradeCanonical(f));
    return json({ valid: timingSafeEqual(expected, body.receipt) });
  }
  // No chromaprint field in the body (2.7.1): two different signed
  // bundles reach this point in that shape. A pre-2.7.0 bundle was
  // signed with the old canonical and carries no line anywhere. A
  // 2.7.0 bundle for a job with no fingerprint was signed with
  // chromaprint_sha256 "none", but the student page prints the
  // Chromaprint SHA-256 line in the submission package only for a
  // real hash, so the teacher audit app — which builds this body
  // from the package — has no field to send. Accept the receipt if
  // it matches either canonical form: both are HMACs over every
  // other field, and the "none" form asserts exactly that the job
  // carried no fingerprint, so no tampered value gains anything.
  const expectedOld = await hmacBase64url(env.SIGNING_SECRET, gradeCanonical(f));
  if (timingSafeEqual(expectedOld, body.receipt)) return json({ valid: true });
  const expectedNone = await hmacBase64url(
    env.SIGNING_SECRET,
    gradeCanonical({ ...f, chromaprint_sha256: "none" }),
  );
  return json({ valid: timingSafeEqual(expectedNone, body.receipt) });
}

// --------------------------------------------------------------- admin

async function handlePackageCreate(request, env) {
  const badAuth = requireToken(request, env, "ADMIN_TOKEN");
  if (badAuth) return badAuth;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const body = await readJson(request, 4000000);
  if (
    !body ||
    typeof body !== "object" ||
    typeof body.pkg_name !== "string" ||
    !/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(body.pkg_name) ||
    typeof body.text !== "string" ||
    body.text.length < 1 ||
    body.text.length > MAX_PACKAGE_CHARS ||
    (body.binding !== undefined &&
      body.binding !== null &&
      typeof body.binding !== "string")
  ) {
    return json({ error: "invalid request body" }, 400);
  }
  // Current semester database only (2.8.0): the package lands in
  // the current database. A `binding` field naming a different
  // database is refused — packages are created in the active
  // semester only.
  const cur = await currentDb(env);
  if (!cur) return json({ error: "database not configured" }, 500);
  if (
    body.binding !== undefined &&
    body.binding !== null &&
    body.binding !== cur.binding
  ) {
    return json(
      { error: "packages are created in the current semester database only", db: cur.binding },
      400,
    );
  }
  const db = cur.db;
  const contentSha256 = await sha256Hex(body.text);
  const dupe = await db.prepare(
    "SELECT version FROM packages WHERE pkg = ? AND content_sha256 = ?",
  )
    .bind(body.pkg_name, contentSha256)
    .first();
  if (dupe) {
    return json({ error: "identical package text already stored" }, 409);
  }
  const maxRow = await db.prepare(
    "SELECT MAX(version) AS max_version FROM packages WHERE pkg = ?",
  )
    .bind(body.pkg_name)
    .first();
  const version = (maxRow && maxRow.max_version ? maxRow.max_version : 0) + 1;
  const createdAt = new Date().toISOString();
  await db.prepare(
    "INSERT INTO packages (pkg, version, text, content_sha256, status, " +
      "trial_json, override_reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
  )
    .bind(
      body.pkg_name,
      version,
      body.text,
      contentSha256,
      "draft",
      null,
      null,
      createdAt,
    )
    .run();
  return json({
    pkg: `${body.pkg_name} v${version}`,
    version,
    content_sha256: contentSha256,
    status: "draft",
  });
}

async function handlePackageList(request, env) {
  const badAuth = requireToken(request, env, "ADMIN_TOKEN");
  if (badAuth) return badAuth;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  // Current semester database only (2.8.0), each meta tagged with
  // the current binding as `db`.
  const cur = await currentDb(env);
  if (!cur) return json({ error: "database not configured" }, 500);
  await sweep(cur.db, new Date().toISOString());
  const { results } = await cur.db.prepare(
    "SELECT * FROM packages ORDER BY pkg, version",
  ).all();
  const out = [];
  for (const row of results || []) {
    out.push({ ...(await packageMeta(cur.db, row)), db: cur.binding });
  }
  return json(out);
}

async function handlePackageShow(request, env, pkgId) {
  const badAuth = requireToken(request, env, "ADMIN_TOKEN");
  if (badAuth) return badAuth;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const parsed = parsePkgId(pkgId);
  if (!parsed) return json({ error: "unknown package" }, 404);
  // Current semester database only (2.8.0): the package is looked
  // up there alone.
  const found = await resolvePackage(env, parsed.name, parsed.version);
  if (!found) return json({ error: "unknown package" }, 404);
  const db = found.db;
  const row = found.row;
  const meta = await packageMeta(db, row);
  // Optional text slicing: ?text_offset=N&text_length=M returns
  // only that slice of the package text, with text_total set to
  // the full length. The teacher audit app reads large package
  // texts this way because a whole-text response (tens of KB) is
  // the response most often cut short by a dropped connection;
  // slices are counted in Unicode code points (Array.from), so a
  // client counting the same way reassembles the text exactly.
  // No parameters: the full record, as before.
  const url = new URL(request.url);
  if (!url.searchParams.has("text_offset")
      && !url.searchParams.has("text_length")) {
    return json({ ...meta, text: row.text,
                  override_reason: row.override_reason });
  }
  const offsetRaw = url.searchParams.get("text_offset") ?? "0";
  const lengthRaw = url.searchParams.get("text_length") ?? "6000";
  if (!/^\d+$/.test(offsetRaw) || !/^\d+$/.test(lengthRaw)) {
    return json({ error: "invalid text slice" }, 400);
  }
  const offset = Number(offsetRaw);
  const length = Number(lengthRaw);
  if (length < 1 || length > 20000) {
    return json({ error: "invalid text slice" }, 400);
  }
  const chars = Array.from(row.text);
  return json({
    ...meta,
    text: chars.slice(offset, offset + length).join(""),
    text_offset: offset,
    text_total: chars.length,
    override_reason: row.override_reason,
  });
}

const TRANSITIONS = {
  draft: ["trialled", "retired"],
  trialled: ["open"],
  open: ["closed"],
  closed: ["retired"],
  retired: [],
};

async function handlePackageStatus(request, env, pkgId) {
  const badAuth = requireToken(request, env, "ADMIN_TOKEN");
  if (badAuth) return badAuth;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const parsed = parsePkgId(pkgId);
  if (!parsed) return json({ error: "unknown package" }, 404);
  const body = await readJson(request);
  // Current semester database only (2.8.0). An optional `db` body
  // field naming a different database is refused, not silently
  // satisfied from the current database — a status change is a
  // mutation.
  const found = await resolvePackage(env, parsed.name, parsed.version);
  if (!found) return json({ error: "unknown package" }, 404);
  if (
    body &&
    typeof body === "object" &&
    typeof body.db === "string" &&
    body.db !== found.binding
  ) {
    return json(
      { error: "package is not held in the named database", db: body.db },
      404,
    );
  }
  const db = found.db;
  const row = found.row;
  if (!body || typeof body !== "object" || typeof body.status !== "string") {
    return json({ error: "invalid request body" }, 400);
  }
  const target = body.status;
  if (!(target in TRANSITIONS)) {
    return json({ error: "unknown status" }, 400);
  }
  if (!TRANSITIONS[row.status].includes(target)) {
    return json(
      { error: `cannot move ${row.status} to ${target}` },
      409,
    );
  }
  let trialJson = row.trial_json;
  let overrideReason = row.override_reason;
  if (body.override_reason !== undefined && body.override_reason !== null) {
    if (!isText(body.override_reason, 512)) {
      return json({ error: "invalid override_reason" }, 400);
    }
    overrideReason = body.override_reason;
  }
  if (target === "trialled") {
    const trial = body.trial;
    if (
      !trial ||
      typeof trial !== "object" ||
      !isScore(trial.completeness) ||
      !isScore(trial.accuracy)
    ) {
      return json({ error: "trial with completeness and accuracy required" }, 400);
    }
    const perfect = trial.completeness === 5 && trial.accuracy === 5;
    if (!perfect && !isText(overrideReason, 512)) {
      return json(
        { error: "trial below 5/5 requires an override reason" },
        400,
      );
    }
    trialJson = JSON.stringify({
      completeness: trial.completeness,
      accuracy: trial.accuracy,
    });
  }
  await db.prepare(
    "UPDATE packages SET status = ?, trial_json = ?, override_reason = ? " +
      "WHERE pkg = ? AND version = ?",
  )
    .bind(target, trialJson, overrideReason, parsed.name, parsed.version)
    .run();
  const updated = await getPackageRow(db, parsed.name, parsed.version);
  return json(await packageMeta(db, updated));
}

// --------------------------------------------------------------- router

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "OPTIONS") {
      return json({}, 204);
    }

    if (request.method === "GET" && path === "/") {
      return handleRoot(env);
    }
    if (request.method === "POST" && path === "/youtube-check") {
      return handleYoutubeCheck(request, env);
    }
    // 2.8.0: /stats/duration and /admin/duration-stats are removed
    // (404, below).
    if (request.method === "POST" && path === "/jobs") {
      return handleJobCreate(request, env);
    }
    if (request.method === "POST" && path === "/jobs/status") {
      return handleJobStatus(request, env);
    }
    // 2.8.0: /jobs/retrieved is removed (404, below) — its only
    // effect was stamping the write-only retrieved_at column.
    if (request.method === "POST" && path === "/jobs/finalize") {
      return handleJobFinalize(request, env);
    }
    if (request.method === "GET" && path === "/grading/pending") {
      return handlePending(request, env);
    }
    if (request.method === "POST" && path === "/grading/claim") {
      return handleClaim(request, env);
    }
    if (request.method === "POST" && path === "/grading/result") {
      return handleResult(request, env);
    }
    if (request.method === "POST" && path === "/verify-grade") {
      return handleVerifyGrade(request, env);
    }
    if (request.method === "POST" && path === "/admin/packages") {
      return handlePackageCreate(request, env);
    }
    if (request.method === "GET" && path === "/admin/packages") {
      return handlePackageList(request, env);
    }
    if (path.startsWith("/admin/packages/")) {
      const pkgId = decodeURIComponent(path.slice("/admin/packages/".length));
      if (request.method === "GET") {
        return handlePackageShow(request, env, pkgId);
      }
      if (request.method === "POST" && pkgId.endsWith("/status")) {
        // /admin/packages/<pkg>/status (pkgId is already decoded)
        const id = pkgId.slice(0, -"/status".length);
        return handlePackageStatus(request, env, id);
      }
    }

    return json({ error: "not found" }, 404);
  },
};
