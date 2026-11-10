// hw-grading — HW Signing v2 grading Worker.
//
// Interface per ~/workspace/hw-signing-v2/SPEC.md. This Worker replaces
// nothing: the v1 signing Worker stays in service for v1 assignments.
// This one holds prompt packages and grading jobs in D1 (binding DB).
//
// Secrets (Worker settings only, never in this file, never logged or
// returned): SIGNING_SECRET (HMAC, as v1), ADMIN_TOKEN, GRADING_TOKEN,
// VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY (base64url, for Web Push).
// Tokens are compared in constant time.
//
// Grade signing (format v2). Canonical signed text, one value per line,
// in this order:
//   v (=2), job_id, audio_sha256, transcript_sha256, pkg,
//   pkg_content_sha256, completeness, accuracy, critique_sha256,
//   youtube_video_sha256 (or "none"), t
// t is stamped from the server clock at result time, never taken from
// the caller. receipt = base64url(HMAC-SHA-256(secret, canonical text)).
// Verify recomputes the receipt from the claimed values; no stored
// record is needed.
//
// YouTube check tokens use the same HMAC: token = base64url(HMAC over
// "video_id\nstatus\nchecked_at"). Nothing about a link is stored; the
// jobs table keeps only youtube_status ("ok" / "none") and, for final
// jobs, youtube_video_sha256 (SHA-256 hex of the video ID).

const SERVICE_VERSION = "2.4.2";
const FORMAT_V = "2";
const CLAIM_MINUTES = 15;
// Job lifetime (2.4.1): an ungraded job is kept for up to
// UNGRADED_TTL_MS after creation, so a submission made while the
// teacher's Muse is not polling is not lost; once graded, the job
// (transcript and result) is kept for GRADED_TTL_MS after grading and
// then expires. Before 2.4.1 every job expired 48 h after creation,
// graded or not.
const UNGRADED_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const GRADED_TTL_MS = 48 * 60 * 60 * 1000;
const YOUTUBE_TOKEN_MAX_AGE_MS = 24 * 60 * 60 * 1000;
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

function base64urlToBytes(s) {
  let b64 = s.replaceAll("-", "+").replaceAll("_", "/");
  while (b64.length % 4) b64 += "=";
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function bytesToHex(bytes) {
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function concatBytes(...parts) {
  let n = 0;
  for (const p of parts) n += p.length;
  const out = new Uint8Array(n);
  let off = 0;
  for (const p of parts) {
    out.set(p, off);
    off += p.length;
  }
  return out;
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

async function readJson(request) {
  try {
    return await request.json();
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

async function getPackageRow(env, name, version) {
  return env.DB.prepare(
    "SELECT * FROM packages WHERE pkg = ? AND version = ?",
  )
    .bind(name, version)
    .first();
}

async function getJobRow(env, jobId) {
  return env.DB.prepare("SELECT * FROM jobs WHERE job_id = ?")
    .bind(jobId)
    .first();
}

// Job lifecycle maintenance, run at the start of job-related calls:
// jobs past their expiry lose their transcript and result and
// become "expired"; claims past their 15 min lease return to "queued".
// The expiry a student should be shown for a live job: for an
// ungraded job the created_at + UNGRADED_TTL_MS cap (a job created
// before 2.4.1 carries a stored expires_at of creation + 48 h, which
// no longer governs it while it is ungraded); for a graded job
// graded_at + GRADED_TTL_MS (the stored expires_at holds exactly
// that for jobs graded under 2.4.1; a job graded before 2.4.1 carries
// creation + 48 h there, which no longer governs it either).
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

async function sweep(env, nowIso) {
  // Graded (ready) jobs expire GRADED_TTL_MS after grading, measured
  // from graded_at so jobs graded before 2.4.1 follow the same rule.
  await env.DB.prepare(
    "UPDATE jobs SET status = ?, transcript = NULL, critique = NULL, " +
      "result_json = NULL, push_json = NULL " +
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
  await env.DB.prepare(
    "UPDATE jobs SET status = ?, transcript = NULL, critique = NULL, " +
      "result_json = NULL, push_json = NULL " +
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
    await env.DB.prepare(
      "UPDATE jobs SET status = ?, transcript = NULL, critique = NULL, " +
        "result_json = NULL, push_json = NULL " +
        "WHERE status = ? AND created_at <= ?",
    )
      .bind("expired", st, ungradedCutoff)
      .run();
  }
  await env.DB.prepare(
    "UPDATE jobs SET status = ?, claimed_at = NULL, claim_expires = NULL " +
      "WHERE status = ? AND claim_expires <= ?",
  )
    .bind("queued", "claimed", nowIso)
    .run();
}

async function jobCounts(env, pkgFull) {
  const { results } = await env.DB.prepare(
    "SELECT status FROM jobs WHERE pkg = ?",
  )
    .bind(pkgFull)
    .all();
  const counts = { total: results.length };
  for (const r of results) counts[r.status] = (counts[r.status] || 0) + 1;
  return counts;
}

async function packageMeta(env, row) {
  const full = `${row.pkg} v${row.version}`;
  return {
    pkg: full,
    version: row.version,
    content_sha256: row.content_sha256,
    status: row.status,
    trial: row.trial_json ? JSON.parse(row.trial_json) : null,
    jobs: await jobCounts(env, full),
    created_at: row.created_at,
  };
}

// ---------------------------------------------------------- Web Push
// RFC 8291 (aes128gcm content encryption) and RFC 8292 (VAPID),
// implemented with WebCrypto: ECDH P-256, HKDF-SHA-256, AES-128-GCM,
// ES256 JWT.

async function hkdf(ikm, salt, info, bytes) {
  const key = await crypto.subtle.importKey("raw", ikm, "HKDF", false, [
    "deriveBits",
  ]);
  const bits = await crypto.subtle.deriveBits(
    { name: "HKDF", hash: "SHA-256", salt, info },
    key,
    bytes * 8,
  );
  return new Uint8Array(bits);
}

async function vapidJwt(env, endpoint) {
  const aud = new URL(endpoint).origin;
  const header = base64url(enc(JSON.stringify({ typ: "JWT", alg: "ES256" })));
  const payload = base64url(
    enc(
      JSON.stringify({
        aud,
        exp: Math.floor(Date.now() / 1000) + 12 * 60 * 60,
        // RFC 8292 requires a contact URI as sub. The SPEC names no
        // contact setting, so a placeholder mailto is used.
        sub: "mailto:hw-grading@example.invalid",
      }),
    ),
  );
  const signingInput = `${header}.${payload}`;
  const pub = base64urlToBytes(env.VAPID_PUBLIC_KEY);
  const jwk = {
    kty: "EC",
    crv: "P-256",
    x: base64url(pub.slice(1, 33)),
    y: base64url(pub.slice(33, 65)),
    d: env.VAPID_PRIVATE_KEY,
  };
  const key = await crypto.subtle.importKey(
    "jwk",
    jwk,
    { name: "ECDSA", namedCurve: "P-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign(
    { name: "ECDSA", hash: "SHA-256" },
    key,
    enc(signingInput),
  );
  return `${signingInput}.${base64url(new Uint8Array(sig))}`;
}

async function encryptPushPayload(subscription, payloadText) {
  const uaPublic = base64urlToBytes(subscription.keys.p256dh);
  const authSecret = base64urlToBytes(subscription.keys.auth);
  const ephemeral = await crypto.subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveBits"],
  );
  const asPublic = new Uint8Array(
    await crypto.subtle.exportKey("raw", ephemeral.publicKey),
  );
  const uaKey = await crypto.subtle.importKey(
    "raw",
    uaPublic,
    { name: "ECDH", namedCurve: "P-256" },
    false,
    [],
  );
  const ecdhSecret = new Uint8Array(
    await crypto.subtle.deriveBits(
      { name: "ECDH", public: uaKey },
      ephemeral.privateKey,
      256,
    ),
  );
  const keyInfo = concatBytes(enc("WebPush: info"), new Uint8Array([0]), uaPublic, asPublic);
  const ikm = await hkdf(ecdhSecret, authSecret, keyInfo, 32);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const cek = await hkdf(
    ikm,
    salt,
    concatBytes(enc("Content-Encoding: aes128gcm"), new Uint8Array([0])),
    16,
  );
  const nonce = await hkdf(
    ikm,
    salt,
    concatBytes(enc("Content-Encoding: nonce"), new Uint8Array([0])),
    12,
  );
  // One record: payload, then the final-record delimiter 0x02.
  const plaintext = concatBytes(enc(payloadText), new Uint8Array([2]));
  const aesKey = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, [
    "encrypt",
  ]);
  const ciphertext = new Uint8Array(
    await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, aesKey, plaintext),
  );
  const rs = new Uint8Array(4);
  new DataView(rs.buffer).setUint32(0, 4096);
  return concatBytes(salt, rs, new Uint8Array([asPublic.length]), asPublic, ciphertext);
}

// Send the "result ready" push for a job. Fire-and-forget by contract:
// any failure is swallowed, except that a 404/410 from the push service
// clears the stored subscription (the endpoint is gone).
async function sendPush(env, job) {
  if (!job.push_json || !env.VAPID_PUBLIC_KEY || !env.VAPID_PRIVATE_KEY) return;
  let subscription;
  try {
    subscription = JSON.parse(job.push_json);
  } catch {
    return;
  }
  if (
    !subscription ||
    typeof subscription.endpoint !== "string" ||
    !subscription.keys ||
    typeof subscription.keys.p256dh !== "string" ||
    typeof subscription.keys.auth !== "string"
  ) {
    return;
  }
  try {
    const jwt = await vapidJwt(env, subscription.endpoint);
    const body = await encryptPushPayload(
      subscription,
      JSON.stringify({
        title: "HW Signing",
        body: "Your grade and critique are ready.",
      }),
    );
    const ttl = Math.max(
      0,
      Math.floor((Date.parse(job.expires_at) - Date.now()) / 1000),
    );
    const res = await fetch(subscription.endpoint, {
      method: "POST",
      headers: {
        authorization: `vapid t=${jwt}, k=${env.VAPID_PUBLIC_KEY}`,
        "content-encoding": "aes128gcm",
        "content-type": "application/octet-stream",
        ttl: String(ttl),
        urgency: "normal",
      },
      body,
    });
    if (res.status === 404 || res.status === 410) {
      await env.DB.prepare("UPDATE jobs SET push_json = NULL WHERE job_id = ?")
        .bind(job.job_id)
        .run();
    }
  } catch {
    // Push failure never fails the grading result call.
  }
}

// ------------------------------------------------------------ handlers

async function handleRoot(env) {
  const body = {
    service: "hw-grading",
    version: SERVICE_VERSION,
    storage: "d1",
  };
  if (env.VAPID_PUBLIC_KEY) body.vapid_public_key = env.VAPID_PUBLIC_KEY;
  return json(body);
}

async function handleYoutubeCheck(request, env) {
  const bad = requireSigning(env);
  if (bad) return bad;
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
  const token = await hmacBase64url(
    env.SIGNING_SECRET,
    `${videoId}\n${status}\n${checked_at}`,
  );
  return json({ video_id: videoId, status, checked_at, token, title });
}

// POST /stats/duration {pkg?, context?, audio_s, video_s} — one
// anonymous duration comparison from the student page: the page's
// audio duration and the YouTube player's duration for a link the
// student checked. No video ID, no link, no student information is
// accepted or stored; the row exists so the page's duration bands
// can be recalibrated from measured same-recording differences.
// Context is the flow the comparison came from ('send' at job
// creation, 'convert' at submission conversion); anything else is
// recorded as 'other'.
async function handleDurationStat(request, env) {
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const body = await readJson(request);
  if (!body || typeof body !== "object") {
    return json({ error: "invalid request body" }, 400);
  }
  const audioS = Number(body.audio_s);
  const videoS = Number(body.video_s);
  const validDur = (n) => Number.isFinite(n) && n > 0 && n <= 43200;
  if (!validDur(audioS) || !validDur(videoS)) {
    return json({ error: "invalid durations" }, 400);
  }
  const pkg = typeof body.pkg === "string" ? body.pkg.slice(0, 128) : "";
  const context = body.context === "send" || body.context === "convert"
    ? body.context : "other";
  const diff = Math.round((videoS - audioS) * 1000) / 1000;
  await env.DB.prepare(
    "INSERT INTO duration_stats " +
      "(created_at, pkg, context, audio_s, video_s, diff_s, abs_diff_s) " +
      "VALUES (?, ?, ?, ?, ?, ?, ?)",
  )
    .bind(new Date().toISOString(), pkg, context, audioS, videoS, diff,
      Math.abs(diff))
    .run();
  return json({ ok: true });
}

// GET /admin/duration-stats (ADMIN_TOKEN) — the stored comparisons
// summarised for threshold calibration: count, percentiles of the
// absolute difference, and how the rows fall against the page's
// current bands (pass at 1 s; the confirm tolerance of
// max(2 s, 2% of the audio); beyond).
async function handleDurationStats(request, env) {
  const badAuth = requireToken(request, env, "ADMIN_TOKEN");
  if (badAuth) return badAuth;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const { results } = await env.DB.prepare(
    "SELECT audio_s, abs_diff_s FROM duration_stats ORDER BY abs_diff_s",
  ).all();
  const rows = results || [];
  const abs = rows.map((r) => Number(r.abs_diff_s)).sort((a, b) => a - b);
  const pct = (p) => (abs.length
    ? abs[Math.min(abs.length - 1, Math.floor((p / 100) * abs.length))]
    : null);
  const bands = { pass_le_1s: 0, confirm_within_tolerance: 0, beyond_tolerance: 0 };
  for (const r of rows) {
    const a = Number(r.audio_s);
    const d = Number(r.abs_diff_s);
    if (d <= 1.0) bands.pass_le_1s += 1;
    else if (d <= Math.max(2, 0.02 * a)) bands.confirm_within_tolerance += 1;
    else bands.beyond_tolerance += 1;
  }
  return json({
    count: rows.length,
    abs_diff_s: abs.length
      ? { p50: pct(50), p90: pct(90), p95: pct(95), p99: pct(99), max: abs[abs.length - 1] }
      : null,
    bands,
  });
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

function validPushSubscription(p) {
  return (
    p &&
    typeof p === "object" &&
    typeof p.endpoint === "string" &&
    p.endpoint.startsWith("https://") &&
    p.endpoint.length <= 1024 &&
    p.keys &&
    typeof p.keys === "object" &&
    isText(p.keys.p256dh, 256) &&
    isText(p.keys.auth, 256)
  );
}

// The one live (non-expired) final job for a (package, audio
// fingerprint), or null. The jobs_one_final partial unique index in
// schema.sql enforces this invariant in the database; this lookup is
// the friendly pre-check and the post-race arbiter.
async function findLiveFinal(env, pkgFull, audioSha256) {
  return env.DB.prepare(
    "SELECT job_id FROM jobs WHERE pkg = ? AND audio_sha256 = ? " +
      "AND kind = ? AND status <> ?",
  )
    .bind(pkgFull, audioSha256, "final", "expired")
    .first();
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
    (body.kind !== "practice" && body.kind !== "final") ||
    typeof body.transcript !== "string" ||
    body.transcript.length < 1 ||
    body.transcript.length > MAX_TRANSCRIPT_CHARS ||
    !isHash(body.audio_sha256) ||
    !isHash(body.transcript_sha256) ||
    !validVersions(body.versions) ||
    typeof body.retrieval_code !== "string" ||
    !RETRIEVAL_CODE.test(body.retrieval_code) ||
    (body.push_subscription !== undefined &&
      body.push_subscription !== null &&
      !validPushSubscription(body.push_subscription))
  ) {
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
  await sweep(env, nowIso);

  const pkgRow = await getPackageRow(env, parsed.name, parsed.version);
  if (!pkgRow) return json({ error: "unknown package" }, 404);
  if (pkgRow.status !== "open") {
    return json({ error: "package is not open" }, 409);
  }
  if (
    !timingSafeEqual(
      pkgRow.content_sha256.toLowerCase(),
      body.pkg_content_sha256.toLowerCase(),
    )
  ) {
    return json({ error: "package content hash mismatch" }, 400);
  }

  // YouTube gate for final jobs. The check token is an HMAC over
  // video_id / status / checked_at, so the page returns all three;
  // a final job is accepted only for a token whose status is "ok"
  // and that is less than 24 h old.
  let youtubeStatus = "none";
  let youtubeVideoSha256 = null;
  if (body.kind === "final") {
    if (
      typeof body.youtube_video_id !== "string" ||
      !VIDEO_ID.test(body.youtube_video_id) ||
      !isText(body.youtube_token, 64) ||
      !isText(body.youtube_checked_at, 64) ||
      Number.isNaN(Date.parse(body.youtube_checked_at))
    ) {
      return json({ error: "final job requires a YouTube check token" }, 400);
    }
    const expected = await hmacBase64url(
      env.SIGNING_SECRET,
      `${body.youtube_video_id}\nok\n${body.youtube_checked_at}`,
    );
    if (!timingSafeEqual(expected, body.youtube_token)) {
      return json({ error: "YouTube check token invalid" }, 400);
    }
    const age = now.getTime() - Date.parse(body.youtube_checked_at);
    if (age < -5 * 60 * 1000 || age > YOUTUBE_TOKEN_MAX_AGE_MS) {
      return json({ error: "YouTube check token too old" }, 400);
    }
    youtubeStatus = "ok";
    youtubeVideoSha256 = await sha256Hex(body.youtube_video_id);
  }

  const codeLookup = await codeLookupFor(parsed.full, body.retrieval_code);
  const codeClash = await env.DB.prepare(
    "SELECT job_id FROM jobs WHERE pkg = ? AND code_lookup = ?",
  )
    .bind(parsed.full, codeLookup)
    .first();
  if (codeClash) {
    return json({ error: "retrieval code already used for this package" }, 409);
  }

  if (body.kind === "final") {
    const priorFinal = await findLiveFinal(
      env,
      parsed.full,
      body.audio_sha256.toLowerCase(),
    );
    if (priorFinal) {
      return json({ error: "a final job already exists for this recording" }, 409);
    }
  }

  const codeSalt = bytesToHex(crypto.getRandomValues(new Uint8Array(16)));
  const codeHash = await sha256Hex(`${codeSalt}\n${body.retrieval_code}`);
  const jobId = crypto.randomUUID();
  const expiresIso = new Date(now.getTime() + UNGRADED_TTL_MS).toISOString();
  try {
    await env.DB.prepare(
      "INSERT INTO jobs (job_id, pkg, retrieval_name, code_lookup, code_salt, code_hash, " +
        "kind, status, transcript, audio_sha256, transcript_sha256, " +
        "versions_json, youtube_status, youtube_video_sha256, completeness, " +
        "accuracy, critique, result_json, receipt, push_json, claimed_at, " +
        "claim_expires, created_at, graded_at, retrieved_at, expires_at) " +
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    )
      .bind(
        jobId,
        parsed.full,
        "",
        codeLookup,
        codeSalt,
        codeHash,
        body.kind,
        "queued",
        body.transcript,
        body.audio_sha256.toLowerCase(),
        body.transcript_sha256.toLowerCase(),
        JSON.stringify({
          webapp: body.versions.webapp,
          model: body.versions.model,
          glossary: body.versions.glossary,
        }),
        youtubeStatus,
        youtubeVideoSha256,
        null,
        null,
        null,
        null,
        null,
        body.push_subscription ? JSON.stringify(body.push_subscription) : null,
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
    // create won the race. Re-check which invariant fired so the error
    // names the right rule — the jobs_one_final partial index (one
    // live final per audio fingerprint) or the jobs_code_lookup index
    // (one job per retrieval code per package). (Review fix F2.)
    if (body.kind === "final") {
      const priorFinal = await findLiveFinal(
        env,
        parsed.full,
        body.audio_sha256.toLowerCase(),
      );
      if (priorFinal) {
        return json(
          { error: "a final job already exists for this recording" },
          409,
        );
      }
    }
    return json({ error: "retrieval code already used for this package" }, 409);
  }
  return json({ job_id: jobId, created_at: nowIso, expires_at: expiresIso });
}

// Shared auth for /jobs/status and /jobs/retrieved. Retrieval is by
// code only. The lookup hash finds the job; jobs created before the
// code-only change have no lookup value, so those are found by
// testing the salted hash of each of the package's remaining jobs.
// An unknown code and a wrong code deliberately return the identical
// 403 body. Returns the job row, or an error Response.
async function jobByRetrieval(env, body) {
  if (
    !body ||
    typeof body !== "object" ||
    typeof body.pkg !== "string" ||
    typeof body.retrieval_code !== "string"
  ) {
    return json({ error: "invalid retrieval code" }, 403);
  }
  const lookup = await codeLookupFor(body.pkg, body.retrieval_code);
  const row = await env.DB.prepare(
    "SELECT * FROM jobs WHERE pkg = ? AND code_lookup = ?",
  )
    .bind(body.pkg, lookup)
    .first();
  if (row) return row;
  const legacy = await env.DB.prepare("SELECT * FROM jobs WHERE pkg = ?")
    .bind(body.pkg)
    .all();
  for (const cand of legacy.results || []) {
    if (cand.code_lookup) continue;
    const codeHash = await sha256Hex(
      `${cand.code_salt}\n${body.retrieval_code}`,
    );
    if (timingSafeEqual(codeHash, cand.code_hash)) return cand;
  }
  return json({ error: "invalid retrieval code" }, 403);
}

// How many jobs are ahead of this one in the grading queue. The
// grading side claims jobs in created_at order across all packages
// (the /jobs/pending order), so the count is global: every job
// currently claimed (being graded), plus every queued job created
// earlier. For a claimed job, the jobs claimed before it.
async function queueAhead(env, row) {
  if (row.status === "claimed") {
    const r = await env.DB.prepare(
      "SELECT COUNT(*) AS n FROM jobs WHERE status = ? AND claimed_at < ?",
    )
      .bind("claimed", row.claimed_at)
      .first();
    return r ? r.n : 0;
  }
  const claimed = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM jobs WHERE status = ?",
  )
    .bind("claimed")
    .first();
  const earlier = await env.DB.prepare(
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
  await sweep(env, new Date().toISOString());
  const row = await jobByRetrieval(env, body);
  if (isErrorResponse(row)) return row;
  // The sweep above has already expired every job that is due, under
  // the ungraded cap or the graded expiry as its status requires, so
  // the stored status is the whole determination here.
  if (row.status === "expired") {
    return json({ status: "expired" });
  }
  const out = { status: row.status, expires_at: effectiveExpiresAt(row) };
  if (row.status === "queued" || row.status === "claimed") {
    out.queue_ahead = await queueAhead(env, row);
  }
  if (row.status === "ready" && row.result_json) {
    const bundle = JSON.parse(row.result_json);
    delete bundle.injection_flags;
    out.result = bundle;
  }
  return json(out);
}

// POST /jobs/finalize {pkg, retrieval_code, youtube_token,
// youtube_video_id, youtube_checked_at} — turn an existing job into
// the final (Canvas submission) job by attaching a YouTube check,
// verified exactly as at intake. Allowed in any live status; when the
// job is already graded, the stored result bundle is re-signed with
// the video hash (every other signed field, including the grading
// time, is unchanged), so the grade the student saw is the grade the
// audit verifies. The one-final-per-recording rule applies as at
// intake. The decision to submit is thus made after the grade is
// seen, with no second grading.
async function handleJobFinalize(request, env) {
  const badSecret = requireSigning(env);
  if (badSecret) return badSecret;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const body = await readJson(request);
  const now = new Date();
  await sweep(env, now.toISOString());
  const row = await jobByRetrieval(env, body);
  if (isErrorResponse(row)) return row;
  if (row.status === "expired") {
    return json({ error: "job expired" }, 410);
  }
  if (row.kind === "final") {
    return json({ error: "job is already a final submission" }, 409);
  }
  if (
    !body ||
    typeof body.youtube_video_id !== "string" ||
    !VIDEO_ID.test(body.youtube_video_id) ||
    !isText(body.youtube_token, 64) ||
    !isText(body.youtube_checked_at, 64) ||
    Number.isNaN(Date.parse(body.youtube_checked_at))
  ) {
    return json({ error: "finalize requires a YouTube check token" }, 400);
  }
  const expected = await hmacBase64url(
    env.SIGNING_SECRET,
    `${body.youtube_video_id}\nok\n${body.youtube_checked_at}`,
  );
  if (!timingSafeEqual(expected, body.youtube_token)) {
    return json({ error: "YouTube check token invalid" }, 400);
  }
  const age = now.getTime() - Date.parse(body.youtube_checked_at);
  if (age < -5 * 60 * 1000 || age > YOUTUBE_TOKEN_MAX_AGE_MS) {
    return json({ error: "YouTube check token too old" }, 400);
  }
  const priorFinal = await findLiveFinal(env, row.pkg, row.audio_sha256);
  if (priorFinal) {
    return json({ error: "a final job already exists for this recording" }, 409);
  }
  const videoSha = await sha256Hex(body.youtube_video_id);
  let receipt = row.receipt;
  let resultJson = row.result_json;
  if (row.status === "ready" && row.result_json) {
    const bundle = JSON.parse(row.result_json);
    bundle.youtube_video_sha256 = videoSha;
    receipt = await hmacBase64url(env.SIGNING_SECRET, gradeCanonical(bundle));
    bundle.receipt = receipt;
    resultJson = JSON.stringify(bundle);
  }
  try {
    await env.DB.prepare(
      "UPDATE jobs SET kind = ?, youtube_status = ?, " +
        "youtube_video_sha256 = ?, result_json = ?, receipt = ? " +
        "WHERE job_id = ?",
    )
      .bind("final", "ok", videoSha, resultJson, receipt, row.job_id)
      .run();
  } catch {
    return json({ error: "a final job already exists for this recording" }, 409);
  }
  return json({ ok: true, receipt });
}

async function handleJobRetrieved(request, env) {
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const body = await readJson(request);
  await sweep(env, new Date().toISOString());
  const row = await jobByRetrieval(env, body);
  if (isErrorResponse(row)) return row;
  if (row.status === "expired") {
    return json({ error: "job expired" }, 410);
  }
  if (!row.retrieved_at) {
    await env.DB.prepare("UPDATE jobs SET retrieved_at = ? WHERE job_id = ?")
      .bind(new Date().toISOString(), row.job_id)
      .run();
  }
  return json({ ok: true });
}

async function handlePending(request, env) {
  const badAuth = requireToken(request, env, "GRADING_TOKEN");
  if (badAuth) return badAuth;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const nowIso = new Date().toISOString();
  await sweep(env, nowIso);
  // The sweep has expired every due job, so a job still in status
  // queued is live — including a pre-2.4.1 job whose stored
  // expires_at (creation + 48 h) has passed while it waits.
  const { results } = await env.DB.prepare(
    "SELECT job_id, pkg, kind, created_at, transcript FROM jobs " +
      "WHERE status = ? ORDER BY created_at",
  )
    .bind("queued")
    .all();
  return json(
    results.map((r) => ({
      job_id: r.job_id,
      pkg: r.pkg,
      kind: r.kind,
      created_at: r.created_at,
      transcript_chars: r.transcript ? r.transcript.length : 0,
    })),
  );
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
  await sweep(env, now.toISOString());
  const row = await getJobRow(env, body.job_id);
  if (!row) return json({ error: "unknown job" }, 404);
  // After the sweep, a claimable job (queued, or claimed with an
  // expired lease) is exactly a job in status "queued".
  if (row.status !== "queued") {
    return json({ error: "job is not claimable" }, 409);
  }
  const claimExpires = new Date(now.getTime() + CLAIM_MINUTES * 60 * 1000);
  // The claim is this UPDATE, guarded on the job still being queued —
  // not the status check above, which a racing poller can pass at the
  // same moment. Only the first UPDATE matches status = 'queued'; a
  // loser sees changes === 0 and gets 409. (Review fix F1.)
  const upd = await env.DB.prepare(
    "UPDATE jobs SET status = ?, claimed_at = ?, claim_expires = ? " +
      "WHERE job_id = ? AND status = ?",
  )
    .bind(
      "claimed",
      now.toISOString(),
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
    ? await getPackageRow(env, parsed.name, parsed.version)
    : null;
  if (!pkgRow) return json({ error: "package record missing" }, 500);
  return json({
    job_id: row.job_id,
    kind: row.kind,
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

// Canonical signed text for a v2 grade (see header comment).
function gradeCanonical(f) {
  return [
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
    f.t,
  ].join("\n");
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
      !Array.isArray(body.injection_flags))
  ) {
    return json({ error: "invalid request body" }, 400);
  }
  const now = new Date();
  await sweep(env, now.toISOString());
  const row = await getJobRow(env, body.job_id);
  if (!row) return json({ error: "unknown job" }, 404);
  if (
    row.status !== "claimed" ||
    !row.claim_expires ||
    Date.parse(row.claim_expires) <= now.getTime()
  ) {
    return json({ error: "no live claim on this job" }, 409);
  }
  const parsed = parsePkgId(row.pkg);
  const pkgRow = parsed
    ? await getPackageRow(env, parsed.name, parsed.version)
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
    t,
  };
  bundle.receipt = await hmacBase64url(
    env.SIGNING_SECRET,
    gradeCanonical(bundle),
  );
  const stored = { ...bundle, injection_flags: body.injection_flags || [] };
  // Grading starts the job's remaining lifetime: it now expires
  // GRADED_TTL_MS after grading, replacing the ungraded cap.
  const gradedExpires = new Date(
    Date.parse(t) + GRADED_TTL_MS,
  ).toISOString();
  await env.DB.prepare(
    "UPDATE jobs SET status = ?, completeness = ?, accuracy = ?, " +
      "critique = ?, result_json = ?, receipt = ?, graded_at = ?, " +
      "expires_at = ?, claim_expires = NULL WHERE job_id = ?",
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
    )
    .run();
  await sendPush(env, { ...row, job_id: row.job_id, expires_at: gradedExpires });
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
  const expected = await hmacBase64url(env.SIGNING_SECRET, gradeCanonical(f));
  return json({ valid: timingSafeEqual(expected, body.receipt) });
}

// --------------------------------------------------------------- admin

async function handlePackageCreate(request, env) {
  const badAuth = requireToken(request, env, "ADMIN_TOKEN");
  if (badAuth) return badAuth;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const body = await readJson(request);
  if (
    !body ||
    typeof body !== "object" ||
    typeof body.pkg_name !== "string" ||
    !/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(body.pkg_name) ||
    typeof body.text !== "string" ||
    body.text.length < 1 ||
    body.text.length > MAX_PACKAGE_CHARS
  ) {
    return json({ error: "invalid request body" }, 400);
  }
  const contentSha256 = await sha256Hex(body.text);
  const dupe = await env.DB.prepare(
    "SELECT version FROM packages WHERE pkg = ? AND content_sha256 = ?",
  )
    .bind(body.pkg_name, contentSha256)
    .first();
  if (dupe) {
    return json({ error: "identical package text already stored" }, 409);
  }
  const maxRow = await env.DB.prepare(
    "SELECT MAX(version) AS max_version FROM packages WHERE pkg = ?",
  )
    .bind(body.pkg_name)
    .first();
  const version = (maxRow && maxRow.max_version ? maxRow.max_version : 0) + 1;
  const createdAt = new Date().toISOString();
  await env.DB.prepare(
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
  await sweep(env, new Date().toISOString());
  const { results } = await env.DB.prepare(
    "SELECT * FROM packages ORDER BY pkg, version",
  ).all();
  const out = [];
  for (const row of results) out.push(await packageMeta(env, row));
  return json(out);
}

async function handlePackageShow(request, env, pkgId) {
  const badAuth = requireToken(request, env, "ADMIN_TOKEN");
  if (badAuth) return badAuth;
  const badDb = requireDb(env);
  if (badDb) return badDb;
  const parsed = parsePkgId(pkgId);
  if (!parsed) return json({ error: "unknown package" }, 404);
  const row = await getPackageRow(env, parsed.name, parsed.version);
  if (!row) return json({ error: "unknown package" }, 404);
  const meta = await packageMeta(env, row);
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
  const row = await getPackageRow(env, parsed.name, parsed.version);
  if (!row) return json({ error: "unknown package" }, 404);
  const body = await readJson(request);
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
  await env.DB.prepare(
    "UPDATE packages SET status = ?, trial_json = ?, override_reason = ? " +
      "WHERE pkg = ? AND version = ?",
  )
    .bind(target, trialJson, overrideReason, parsed.name, parsed.version)
    .run();
  const updated = await getPackageRow(env, parsed.name, parsed.version);
  return json(await packageMeta(env, updated));
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
    if (request.method === "POST" && path === "/stats/duration") {
      return handleDurationStat(request, env);
    }
    if (request.method === "GET" && path === "/admin/duration-stats") {
      return handleDurationStats(request, env);
    }
    if (request.method === "POST" && path === "/jobs") {
      return handleJobCreate(request, env);
    }
    if (request.method === "POST" && path === "/jobs/status") {
      return handleJobStatus(request, env);
    }
    if (request.method === "POST" && path === "/jobs/retrieved") {
      return handleJobRetrieved(request, env);
    }
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
