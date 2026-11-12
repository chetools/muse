// Tests for the hw-grading Worker (HW Signing v2), run locally in Node:
//   node test.mjs
// Exercises the Worker's fetch handler directly against an in-memory
// D1 shim implemented below, with a stubbed global fetch for the
// YouTube oEmbed calls and the push service. No network access.
import worker from "./worker.js";

// ------------------------------------------------------- D1 shim
// Minimal SQL engine covering exactly the statement shapes worker.js
// uses: INSERT with ?/NULL values; SELECT (*, column list, COUNT(*),
// MAX(col)) with AND-combined =, <>, <, <=, >, >=, IS [NOT] NULL
// conditions and ORDER BY; UPDATE ... SET col = ?/NULL ... WHERE ...;
// DELETE ... WHERE ... . INSERT also enforces the schema's uniqueness
// rules: the primary keys, UNIQUE(pkg, code_lookup) on jobs, the
// jobs_one_final partial unique index (one live final per pkg +
// audio fingerprint), the jobs_one_per_recording partial unique
// index (2.6.0: one live job of any kind per pkg + audio
// fingerprint), and the job_code_aliases primary key.
function createDb() {
  const tables = { packages: [], jobs: [], duration_stats: [], job_code_aliases: [] };

  function resolveToken(tok, args, ptr) {
    tok = tok.trim();
    if (tok === "?") return args[ptr.i++];
    if (/^NULL$/i.test(tok)) return null;
    if (/^'.*'$/.test(tok)) return tok.slice(1, -1);
    const n = Number(tok);
    return Number.isNaN(n) ? tok : n;
  }

  function evalConds(row, condStr, args, ptr) {
    if (!condStr) return true;
    return condStr.split(/\s+AND\s+/i).every((c) => {
      c = c.trim();
      let m = /^(\w+)\s+IS\s+NOT\s+NULL$/i.exec(c);
      if (m) return row[m[1]] !== null && row[m[1]] !== undefined;
      m = /^(\w+)\s+IS\s+NULL$/i.exec(c);
      if (m) return row[m[1]] === null || row[m[1]] === undefined;
      m = /^(\w+)\s*(=|<>|<=|>=|<|>)\s*(.+)$/.exec(c);
      if (!m) throw new Error("unsupported condition: " + c);
      const val = resolveToken(m[3], args, ptr);
      const rv = row[m[1]];
      switch (m[2]) {
        case "=": return rv === val;
        case "<>": return rv !== val;
        case "<": return rv !== null && rv !== undefined && rv < val;
        case "<=": return rv !== null && rv !== undefined && rv <= val;
        case ">": return rv !== null && rv !== undefined && rv > val;
        case ">=": return rv !== null && rv !== undefined && rv >= val;
      }
      return false;
    });
  }

  function execSelect(sql, args) {
    const m = /^SELECT\s+(.+?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+?))?(?:\s+ORDER\s+BY\s+(.+))?$/is.exec(sql.trim());
    if (!m) throw new Error("unsupported SELECT: " + sql);
    const [, list, table, where, order] = m;
    // Bind arguments are consumed per row: each row's condition
    // evaluation starts from a fresh pointer.
    let rows = tables[table].filter((r) => evalConds(r, where, args, { i: 0 }));
    if (order) {
      const terms = order.split(",").map((s) => s.trim());
      rows = [...rows].sort((a, b) => {
        for (const t of terms) {
          const [col, dir] = t.split(/\s+/);
          const desc = dir && dir.toUpperCase() === "DESC";
          if (a[col] < b[col]) return desc ? 1 : -1;
          if (a[col] > b[col]) return desc ? -1 : 1;
        }
        return 0;
      });
    }
    const agg = /^COUNT\(\*\)\s+AS\s+(\w+)$/i.exec(list.trim());
    if (agg) return [{ [agg[1]]: rows.length }];
    const mx = /^MAX\((\w+)\)\s+AS\s+(\w+)$/i.exec(list.trim());
    if (mx) {
      return [{ [mx[2]]: rows.length ? Math.max(...rows.map((r) => r[mx[1]])) : null }];
    }
    if (list.trim() === "*") return rows.map((r) => ({ ...r }));
    const cols = list.split(",").map((s) => s.trim());
    return rows.map((r) => {
      const o = {};
      for (const c of cols) o[c] = r[c];
      return o;
    });
  }

  function execWrite(sql, args) {
    sql = sql.trim();
    let m = /^INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)$/is.exec(sql);
    if (m) {
      const [, table, colStr, valStr] = m;
      const cols = colStr.split(",").map((s) => s.trim());
      const toks = valStr.split(",").map((s) => s.trim());
      const ptr = { i: 0 };
      const row = {};
      cols.forEach((c, i) => { row[c] = resolveToken(toks[i], args, ptr); });
      if (table === "jobs") {
        if (tables.jobs.some((r) => r.job_id === row.job_id)) {
          throw new Error("UNIQUE constraint failed: jobs.job_id");
        }
        if (row.code_lookup != null &&
            tables.jobs.some((r) => r.pkg === row.pkg && r.code_lookup === row.code_lookup)) {
          throw new Error("UNIQUE constraint failed: jobs.pkg, jobs.code_lookup");
        }
        // Partial unique index jobs_one_final (schema.sql): among
        // non-expired finals, (pkg, audio_sha256) is unique.
        if (row.kind === "final" && row.status !== "expired" &&
            tables.jobs.some((r) => r.kind === "final" && r.status !== "expired" &&
              r.pkg === row.pkg && r.audio_sha256 === row.audio_sha256)) {
          throw new Error("UNIQUE constraint failed: index 'jobs_one_final'");
        }
        // Partial unique index jobs_one_per_recording (2.6.0):
        // among non-expired jobs of any kind, (pkg, audio_sha256)
        // is unique.
        if (row.status !== "expired" &&
            tables.jobs.some((r) => r.status !== "expired" &&
              r.pkg === row.pkg && r.audio_sha256 === row.audio_sha256)) {
          throw new Error("UNIQUE constraint failed: index 'jobs_one_per_recording'");
        }
      }
      if (table === "job_code_aliases") {
        if (tables.job_code_aliases.some((r) => r.pkg === row.pkg && r.code_lookup === row.code_lookup)) {
          throw new Error("UNIQUE constraint failed: job_code_aliases.pkg, job_code_aliases.code_lookup");
        }
      }
      if (table === "packages") {
        if (tables.packages.some((r) => r.pkg === row.pkg && r.version === row.version)) {
          throw new Error("UNIQUE constraint failed: packages.pkg, packages.version");
        }
      }
      tables[table].push(row);
      return 1;
    }
    m = /^UPDATE\s+(\w+)\s+SET\s+(.+?)\s+WHERE\s+(.+)$/is.exec(sql);
    if (m) {
      const [, table, setStr, where] = m;
      const ptr = { i: 0 };
      const assigns = setStr.split(",").map((s) => {
        const am = /^(\w+)\s*=\s*(.+)$/.exec(s.trim());
        if (!am) throw new Error("unsupported SET: " + s);
        return [am[1], resolveToken(am[2], args, ptr)];
      });
      let changes = 0;
      for (const row of tables[table]) {
        const p2 = { i: ptr.i };
        if (evalConds(row, where, args, p2)) {
          for (const [c, v] of assigns) row[c] = v;
          changes++;
        }
      }
      return changes;
    }
    m = /^DELETE\s+FROM\s+(\w+)\s+WHERE\s+(.+)$/is.exec(sql);
    if (m) {
      const [, table, where] = m;
      const before = tables[table].length;
      tables[table] = tables[table].filter(
        (row) => !evalConds(row, where, args, { i: 0 }));
      return before - tables[table].length;
    }
    throw new Error("unsupported statement: " + sql);
  }

  function prepare(sql) {
    let bound = [];
    const stmt = {
      bind(...a) { bound = a; return stmt; },
      async first() {
        const r = execSelect(sql, bound);
        return r.length ? r[0] : null;
      },
      async all() {
        if (/^\s*(INSERT|UPDATE)/i.test(sql)) {
          execWrite(sql, bound);
          return { results: [] };
        }
        return { results: execSelect(sql, bound) };
      },
      async run() {
        const changes = execWrite(sql, bound);
        return { success: true, meta: { changes } };
      },
    };
    return stmt;
  }

  return { prepare, _tables: tables };
}

// ------------------------------------------------------- setup

const b64u = (u8) => Buffer.from(u8).toString("base64url");
const enc = (s) => new TextEncoder().encode(s);

function concatBytes(...parts) {
  let n = 0;
  for (const p of parts) n += p.length;
  const out = new Uint8Array(n);
  let off = 0;
  for (const p of parts) { out.set(p, off); off += p.length; }
  return out;
}

async function hkdf(ikm, salt, info, bytes) {
  const key = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "HKDF", hash: "SHA-256", salt, info }, key, bytes * 8);
  return new Uint8Array(bits);
}

async function sha256Hex(text) {
  const d = await crypto.subtle.digest("SHA-256", enc(text));
  return Buffer.from(d).toString("hex");
}

async function hmacB64u(secret, text) {
  const key = await crypto.subtle.importKey("raw", enc(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc(text));
  return Buffer.from(sig).toString("base64url");
}

// VAPID keys (worker's identity) and a user-agent push subscription.
const vapidKeys = await crypto.subtle.generateKey(
  { name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
const vapidPubRaw = new Uint8Array(await crypto.subtle.exportKey("raw", vapidKeys.publicKey));
const vapidJwk = await crypto.subtle.exportKey("jwk", vapidKeys.privateKey);

const uaKeys = await crypto.subtle.generateKey(
  { name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
const uaPubRaw = new Uint8Array(await crypto.subtle.exportKey("raw", uaKeys.publicKey));
const uaAuth = crypto.getRandomValues(new Uint8Array(16));
const pushSub = {
  endpoint: "https://push.example.test/send/ua1",
  keys: { p256dh: b64u(uaPubRaw), auth: b64u(uaAuth) },
};
const pushSubGone = {
  endpoint: "https://push.example.test/send/gone",
  keys: { p256dh: b64u(uaPubRaw), auth: b64u(uaAuth) },
};

// Stubbed fetch: YouTube oEmbed and the push service. No network.
const pushRequests = [];
globalThis.fetch = async (url, opts = {}) => {
  const u = String(url);
  if (u.startsWith("https://www.youtube.com/oembed")) {
    const decoded = decodeURIComponent(u);
    if (decoded.includes("private0001")) return new Response("no", { status: 404 });
    return new Response(JSON.stringify({ title: "x", author_name: "y" }), {
      status: 200, headers: { "content-type": "application/json" },
    });
  }
  if (u.startsWith("https://push.example.test/")) {
    pushRequests.push({ url: u, opts });
    if (u.includes("gone")) return new Response("", { status: 410 });
    return new Response("", { status: 201 });
  }
  throw new Error("unexpected fetch in test: " + u);
};

const db = createDb();
const env = {
  DB: db,
  SIGNING_SECRET: "test-signing-secret-0123456789abcdef",
  ADMIN_TOKEN: "test-admin-token-0123456789",
  GRADING_TOKEN: "test-grading-token-0123456789",
  VAPID_PUBLIC_KEY: b64u(vapidPubRaw),
  VAPID_PRIVATE_KEY: vapidJwk.d,
};

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; console.log("PASS", name); }
  else { fail++; console.log("FAIL", name); }
}

async function call(path, { method = "POST", body, token, e = env } = {}) {
  const headers = { "content-type": "application/json" };
  if (token) headers.authorization = "Bearer " + token;
  const req = new Request("https://hw-grading.test" + path, {
    method,
    headers,
    body: body === undefined || method === "GET" ? undefined : JSON.stringify(body),
  });
  const res = await worker.fetch(req, e);
  const text = await res.text();
  let parsed = null;
  try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
  return { status: res.status, body: parsed, headers: res.headers };
}

async function callH(path, { method = "POST", body, headers = {} } = {}) {
  const req = new Request("https://hw-grading.test" + path, {
    method,
    headers: { "content-type": "application/json", ...headers },
    body: body === undefined || method === "GET" ? undefined : JSON.stringify(body),
  });
  const res = await worker.fetch(req, env);
  const text = await res.text();
  let parsed = null;
  try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
  return { status: res.status, body: parsed, headers: res.headers };
}

const ADMIN = env.ADMIN_TOKEN;
const GRADING = env.GRADING_TOKEN;
const AUDIO_SHA = "a".repeat(64);
const AUDIO2_SHA = "b".repeat(64);
const AUDIO3_SHA = "c".repeat(64);
const AUDIO_FINAL_SHA = "1".repeat(64);
const AUDIO4_SHA = "d".repeat(64);
// The Worker verifies transcript_sha256 against the transcript at
// intake (review fix F3), so the fixture hash is the genuine SHA-256
// of the fixture transcript string.
const JOB_TRANSCRIPT = "This is my explanation of the thing, in full sentences.";
const TRANS_SHA = await sha256Hex(JOB_TRANSCRIPT);
const VERSIONS = { webapp: "hw-signing-webapp 2.0.0", model: "parakeet-tdt-0.6b-v2-int8", glossary: "bundle-1" };
const PKG_TEXT = [
  "pkg: test-package",
  "",
  "## Homework description",
  "Explain the thing, part 1 only.",
  "",
  "## Lecture transcript portions",
  "Lecture words about the thing.",
  "",
  "## Grading basis",
  "Holistic completeness and accuracy, 0-5 each.",
].join("\n");
const PKG_TEXT_V2 = PKG_TEXT + "\nRevised basis line for version 2.\n";

// ------------------------------------------------------- health / CORS
{
  const r = await call("/", { method: "GET" });
  check("health: hw-grading with d1 storage", r.status === 200 &&
    r.body.service === "hw-grading" && r.body.storage === "d1");
  check("health: vapid public key included when configured",
    r.body.vapid_public_key === env.VAPID_PUBLIC_KEY);
  const bare = { ...env };
  delete bare.VAPID_PUBLIC_KEY;
  const r2 = await call("/", { method: "GET", e: bare });
  check("health: vapid key omitted when not configured",
    r2.status === 200 && !("vapid_public_key" in r2.body));
}
{
  const req = new Request("https://hw-grading.test/jobs", { method: "OPTIONS" });
  const res = await worker.fetch(req, env);
  const text = await res.text();
  check("OPTIONS preflight returns 204 with CORS headers and no body",
    res.status === 204 && text === "" &&
    res.headers.get("access-control-allow-origin") === "*" &&
    (res.headers.get("access-control-allow-headers") || "").includes("authorization"));
}

// ------------------------------------------------------- packages
const pkgHash1 = await sha256Hex(PKG_TEXT);
const pkgHash2 = await sha256Hex(PKG_TEXT_V2);
let r = await call("/admin/packages", { body: { pkg_name: "test-package", text: PKG_TEXT } });
check("admin without token rejected", r.status === 401);
r = await call("/admin/packages", { body: { pkg_name: "test-package", text: PKG_TEXT }, token: "wrong" });
check("admin with wrong token rejected", r.status === 401);
r = await call("/admin/packages", { body: { pkg_name: "test-package", text: PKG_TEXT }, token: ADMIN });
check("package v1 created as draft", r.status === 200 &&
  r.body.pkg === "test-package v1" && r.body.version === 1 &&
  r.body.content_sha256 === pkgHash1 && r.body.status === "draft");
r = await call("/admin/packages", { body: { pkg_name: "test-package", text: PKG_TEXT }, token: ADMIN });
check("identical package text rejected", r.status === 409);
r = await call("/admin/packages", { body: { pkg_name: "test-package", text: PKG_TEXT_V2 }, token: ADMIN });
check("revised text creates v2", r.status === 200 && r.body.version === 2 &&
  r.body.content_sha256 === pkgHash2 && r.body.status === "draft");
r = await call("/admin/packages", { method: "GET", token: ADMIN });
check("package list has both versions, metadata only", r.status === 200 &&
  Array.isArray(r.body) && r.body.length === 2 &&
  r.body.every((p) => !("text" in p)) &&
  r.body[0].pkg === "test-package v1" && r.body[0].jobs.total === 0);
r = await call("/admin/packages/" + encodeURIComponent("test-package v1"), { method: "GET", token: ADMIN });
check("package show returns full text", r.status === 200 && r.body.text === PKG_TEXT);

// Text slicing (2.3.0): slices counted in code points reassemble
// the full text exactly; the unparameterised show above is
// unchanged.
{
  const full = Array.from(PKG_TEXT);
  let joined = "";
  let offset = 0;
  for (;;) {
    const s = await call(
      "/admin/packages/" + encodeURIComponent("test-package v1")
        + "?text_offset=" + offset + "&text_length=10",
      { method: "GET", token: ADMIN });
    check("slice at offset " + offset + " reports the total",
      s.status === 200 && s.body.text_total === full.length &&
        s.body.text_offset === offset);
    joined += s.body.text;
    offset += Array.from(s.body.text).length;
    if (offset >= full.length) break;
  }
  check("slices reassemble the package text exactly",
    joined === PKG_TEXT);
  let s = await call(
    "/admin/packages/" + encodeURIComponent("test-package v1")
      + "?text_offset=0&text_length=20001",
    { method: "GET", token: ADMIN });
  check("slice length above the cap rejected", s.status === 400);
  s = await call(
    "/admin/packages/" + encodeURIComponent("test-package v1")
      + "?text_offset=-1&text_length=10",
    { method: "GET", token: ADMIN });
  check("negative slice offset rejected", s.status === 400);
  s = await call(
    "/admin/packages/" + encodeURIComponent("test-package v1")
      + "?text_offset=0&text_length=10",
    { method: "GET" });
  check("slice without admin token rejected", s.status === 401);
}

// Dedicated token headers (the teacher skills' scripts send these
// instead of Authorization: Bearer) must work on both route families.
r = await callH("/admin/packages", { method: "GET", headers: { "x-admin-token": ADMIN } });
check("admin route accepts X-Admin-Token header", r.status === 200 && Array.isArray(r.body));
r = await callH("/admin/packages", { method: "GET", headers: { "x-admin-token": "wrong" } });
check("admin route rejects wrong X-Admin-Token", r.status === 401);
r = await callH("/grading/pending", { method: "GET", headers: { "x-grading-token": GRADING } });
check("grading route accepts X-Grading-Token header", r.status === 200 && Array.isArray(r.body));
r = await callH("/grading/pending", { method: "GET", headers: { "x-grading-token": "wrong" } });
check("grading route rejects wrong X-Grading-Token", r.status === 401);
r = await callH("/grading/pending", { method: "GET", headers: { "x-admin-token": ADMIN } });
check("admin token does not open grading routes via its header", r.status === 401);

// Status transitions and the trial gate (on v1)
const pkgPath = "/admin/packages/" + encodeURIComponent("test-package v1") + "/status";
r = await call(pkgPath, { body: { status: "open" }, token: ADMIN });
check("draft cannot jump to open", r.status === 409);
r = await call(pkgPath, { body: { status: "trialled" }, token: ADMIN });
check("trialled without trial rejected", r.status === 400);
r = await call(pkgPath, { body: { status: "trialled", trial: { completeness: 4, accuracy: 5 } }, token: ADMIN });
check("trial below 5/5 without override rejected", r.status === 400);
r = await call(pkgPath, { body: { status: "trialled", trial: { completeness: 5, accuracy: 5 } }, token: ADMIN });
check("trial 5/5 moves to trialled", r.status === 200 && r.body.status === "trialled" &&
  r.body.trial.completeness === 5 && r.body.trial.accuracy === 5);
r = await call(pkgPath, { body: { status: "open" }, token: ADMIN });
check("trialled moves to open", r.status === 200 && r.body.status === "open");

// Override path and closing (on v2)
const pkg2Path = "/admin/packages/" + encodeURIComponent("test-package v2") + "/status";
r = await call(pkg2Path, { body: { status: "trialled", trial: { completeness: 4, accuracy: 5 }, override_reason: "HW requires a derivation beyond the lecture" }, token: ADMIN });
check("trial below 5/5 with override accepted", r.status === 200 && r.body.status === "trialled");
r = await call("/admin/packages/" + encodeURIComponent("test-package v2"), { method: "GET", token: ADMIN });
check("override reason stored on package", r.body.override_reason === "HW requires a derivation beyond the lecture");
r = await call(pkg2Path, { body: { status: "open" }, token: ADMIN });
check("v2 opens", r.status === 200 && r.body.status === "open");
r = await call(pkg2Path, { body: { status: "retired" }, token: ADMIN });
check("open cannot jump to retired", r.status === 409);
r = await call(pkg2Path, { body: { status: "closed" }, token: ADMIN });
check("open moves to closed", r.status === 200 && r.body.status === "closed");

// draft -> retired directly (throwaway package)
r = await call("/admin/packages", { body: { pkg_name: "throwaway", text: "draft text" }, token: ADMIN });
check("throwaway draft created", r.status === 200);
r = await call("/admin/packages/" + encodeURIComponent("throwaway v1") + "/status", { body: { status: "retired" }, token: ADMIN });
check("draft moves directly to retired", r.status === 200 && r.body.status === "retired");

// ------------------------------------------------------- youtube check
const ytOk = await call("/youtube-check", { body: { url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" } });
check("youtube-check ok for a public video", ytOk.status === 200 &&
  ytOk.body.video_id === "dQw4w9WgXcQ" && ytOk.body.status === "ok");
{
  const expected = await hmacB64u(env.SIGNING_SECRET,
    `${ytOk.body.video_id}\n${ytOk.body.status}\n${ytOk.body.checked_at}`);
  check("youtube token is the HMAC of id/status/checked_at", ytOk.body.token === expected);
}
const ytShort = await call("/youtube-check", { body: { url: "https://youtu.be/dQw4w9WgXcQ?t=3" } });
check("youtu.be form parses", ytShort.status === 200 && ytShort.body.video_id === "dQw4w9WgXcQ");
const ytShorts = await call("/youtube-check", { body: { url: "https://www.youtube.com/shorts/dQw4w9WgXcQ" } });
check("shorts form parses", ytShorts.status === 200 && ytShorts.body.video_id === "dQw4w9WgXcQ");
const ytPriv = await call("/youtube-check", { body: { url: "https://www.youtube.com/watch?v=private0001" } });
check("youtube-check reports private_or_missing on oEmbed 404",
  ytPriv.status === 200 && ytPriv.body.status === "private_or_missing");
const ytBad = await call("/youtube-check", { body: { url: "https://example.com/watch?v=dQw4w9WgXcQ" } });
check("non-YouTube URL rejected", ytBad.status === 400);
const ytBadId = await call("/youtube-check", { body: { url: "https://www.youtube.com/watch?v=tooshort" } });
check("bad video id rejected", ytBadId.status === 400);
check("youtube-check returns the video title for recognition, stores nothing",
  ytOk.body.title === "x" && ytPriv.body.title === null &&
  !("title" in (db._tables.jobs[0] || {})));

// ------------------------------------------------------- duration stats
const stat1 = await call("/stats/duration", {
  body: { pkg: "test-package v1", context: "send", audio_s: 600, video_s: 600.4 },
});
check("duration stat accepted", stat1.status === 200 && stat1.body.ok === true);
await call("/stats/duration", {
  body: { pkg: "test-package v1", context: "convert", audio_s: 600, video_s: 601.5 },
});
await call("/stats/duration", {
  body: { pkg: "test-package v1", context: "whatever", audio_s: 100, video_s: 120 },
});
check("duration stats stored with computed differences, unknown context normalised",
  db._tables.duration_stats.length === 3 &&
  Math.abs(db._tables.duration_stats[0].diff_s - 0.4) < 1e-9 &&
  db._tables.duration_stats[2].context === "other" &&
  !("video_id" in db._tables.duration_stats[0]));
const statBad = await call("/stats/duration", {
  body: { audio_s: -5, video_s: 100 },
});
check("duration stat rejects invalid durations", statBad.status === 400 &&
  db._tables.duration_stats.length === 3);
const statNoAuth = await call("/admin/duration-stats", { method: "GET" });
check("duration stats summary requires the admin token", statNoAuth.status === 401);
const statSum = await call("/admin/duration-stats", {
  method: "GET", token: env.ADMIN_TOKEN,
});
check("duration stats summary: count, percentiles, band split",
  statSum.status === 200 && statSum.body.count === 3 &&
  Math.abs(statSum.body.abs_diff_s.max - 20) < 1e-9 &&
  statSum.body.bands.pass_le_1s === 1 &&
  statSum.body.bands.confirm_within_tolerance === 1 &&
  statSum.body.bands.beyond_tolerance === 1);

// ------------------------------------------------------- job creation
const jobBase = {
  pkg: "test-package v1",
  pkg_content_sha256: pkgHash1,
  kind: "practice",
  transcript: JOB_TRANSCRIPT,
  audio_sha256: AUDIO_SHA,
  transcript_sha256: TRANS_SHA,
  versions: VERSIONS,
  retrieval_code: "correcthorsebattery7",
};
r = await call("/jobs", { body: jobBase });
check("practice job created queued with 7-day ungraded expiry", r.status === 200 &&
  typeof r.body.job_id === "string" &&
  Date.parse(r.body.expires_at) - Date.parse(r.body.created_at) === 7 * 24 * 3600 * 1000);
const practiceJob = r.body.job_id;

r = await call("/jobs", { body: { ...jobBase, retrieval_code: "short99" } });
check("retrieval code under 8 characters rejected at creation", r.status === 400);

r = await call("/jobs", { body: { ...jobBase, retrieval_code: "bad code" } });
check("retrieval code with spaces rejected", r.status === 400);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "" } });
check("empty retrieval code rejected", r.status === 400);
r = await call("/jobs", { body: { ...jobBase, audio_sha256: AUDIO2_SHA } });
check("duplicate retrieval code for the package rejected", r.status === 409);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "redfox99", pkg_content_sha256: "f".repeat(64) } });
check("package content hash mismatch rejected", r.status === 400);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "redfox99", pkg: "nope v1" } });
check("unknown package rejected", r.status === 404);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "redfox99", pkg: "test-package v2", pkg_content_sha256: pkgHash2 } });
check("job against a closed package rejected", r.status === 409);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "redfox99", transcript: "" } });
check("empty transcript rejected", r.status === 400);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "redfox99", audio_sha256: "xyz" } });
check("non-hex audio hash rejected", r.status === 400);

// Final jobs and the YouTube gate
const finalBase = {
  ...jobBase, kind: "final", retrieval_code: "finalone9",
  audio_sha256: AUDIO_FINAL_SHA,
  youtube_token: ytOk.body.token, youtube_video_id: ytOk.body.video_id,
  youtube_checked_at: ytOk.body.checked_at,
};
r = await call("/jobs", { body: { ...jobBase, kind: "final", retrieval_code: "finalx99", audio_sha256: AUDIO_FINAL_SHA } });
check("final job without a YouTube token rejected", r.status === 400);
r = await call("/jobs", {
  body: {
    ...finalBase, retrieval_code: "finalx99",
    youtube_token: ytPriv.body.token, youtube_video_id: ytPriv.body.video_id,
    youtube_checked_at: ytPriv.body.checked_at,
  },
});
check("final job with a private_or_missing token rejected", r.status === 400);
{
  const old = new Date(Date.now() - 25 * 3600 * 1000).toISOString();
  const staleToken = await hmacB64u(env.SIGNING_SECRET, `dQw4w9WgXcQ\nok\n${old}`);
  r = await call("/jobs", {
    body: { ...finalBase, retrieval_code: "finalx99", youtube_token: staleToken, youtube_checked_at: old },
  });
  check("final job with a token older than 24 h rejected", r.status === 400);
}
r = await call("/jobs", { body: finalBase });
check("final job with a valid ok token created", r.status === 200);
const finalJob = r.body.job_id;
{
  const row = db._tables.jobs.find((j) => j.job_id === finalJob);
  const expectVideoHash = await sha256Hex("dQw4w9WgXcQ");
  check("final job stores only the video ID hash and ok status",
    row.youtube_status === "ok" && row.youtube_video_sha256 === expectVideoHash);
}
r = await call("/jobs", { body: { ...finalBase, retrieval_code: "finaltwo9" } });
check("second final job for one audio fingerprint returns the existing final as a duplicate",
  r.status === 200 && r.body.duplicate === true && r.body.job_id === finalJob &&
  r.body.status === "queued" && r.body.queue_ahead === 1 && r.body.alias_created === true &&
  r.body.pkg === "test-package v1");
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "practicetwo9" } });
check("second practice job for the same fingerprint returns the existing practice job as a duplicate",
  r.status === 200 && r.body.duplicate === true && r.body.job_id === practiceJob &&
  r.body.status === "queued" && r.body.queue_ahead === 0 && r.body.alias_created === true);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "practicethree9", audio_sha256: AUDIO4_SHA } });
check("practice job for a different fingerprint created",
  r.status === 200 && !r.body.duplicate && typeof r.body.job_id === "string");
const thirdPracticeJob = r.body.job_id;

// ------------------------------------------------------- code hashing / status auth
{
  const row = db._tables.jobs.find((j) => j.job_id === practiceJob);
  const expected = await sha256Hex(`${row.code_salt}\ncorrecthorsebattery7`);
  check("retrieval code stored as salted SHA-256",
    !!row.code_salt && row.code_hash === expected && !JSON.stringify(row).includes("correct horse"));
}
const wrongCode = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "wrongcode9" } });
const unknownCode = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "nosuchcode9" } });
check("wrong code returns 403", wrongCode.status === 403);
check("unknown code returns the identical 403 body",
  unknownCode.status === 403 && JSON.stringify(unknownCode.body) === JSON.stringify(wrongCode.body));
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "correcthorsebattery7" } });
check("status with correct code reports queued", r.status === 200 && r.body.status === "queued");
check("queued status carries a jobs-ahead count", Number.isInteger(r.body.queue_ahead) && r.body.queue_ahead >= 0);
// Queue order is global FIFO by created_at (the /grading/pending
// order): at this point the queued jobs are, in order, the practice
// job, the final job, and the second practice job, and none is claimed.
check("first queued job has 0 jobs ahead", r.body.queue_ahead === 0);
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "finalone9" } });
check("second queued job has 1 job ahead", r.status === 200 && r.body.queue_ahead === 1);
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "practicethree9" } });
check("third queued job has 2 jobs ahead", r.status === 200 && r.body.queue_ahead === 2);

// A job created before 2.4.1 with a short code remains retrievable:
// lookup does not re-validate length. Simulate the old row by
// pointing its lookup hash at a 6-character code.
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "legacycode9", audio_sha256: "6".repeat(64) } });
const legacyJob = r.body.job_id;
{
  const row = db._tables.jobs.find((j) => j.job_id === legacyJob);
  row.code_lookup = await sha256Hex("test-package v1\ntiny9x");
}
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "tiny9x" } });
check("pre-2.4.1 short code still retrieves its job", r.status === 200 && r.body.status === "queued");

// ------------------------------------------------------- grading flow
r = await call("/grading/pending", { method: "GET" });
check("pending without grading token rejected", r.status === 401);
r = await call("/grading/pending", { method: "GET", token: GRADING });
check("pending lists queued jobs with transcript sizes", r.status === 200 &&
  Array.isArray(r.body) &&
  r.body.some((j) => j.job_id === practiceJob && j.transcript_chars === jobBase.transcript.length) &&
  r.body.some((j) => j.job_id === finalJob && j.kind === "final"));

r = await call("/grading/result", {
  token: GRADING,
  body: { job_id: finalJob, completeness: 5, accuracy: 5, critique: "Fine." },
});
check("result without a live claim rejected", r.status === 409);

r = await call("/grading/claim", { token: GRADING, body: { job_id: practiceJob } });
check("claim returns transcript and full package", r.status === 200 &&
  r.body.transcript === jobBase.transcript &&
  r.body.package.text === PKG_TEXT &&
  r.body.package.content_sha256 === pkgHash1 &&
  r.body.versions.model === VERSIONS.model);
r = await call("/grading/claim", { token: GRADING, body: { job_id: practiceJob } });
check("second claim while the lease is live rejected", r.status === 409);
r = await call("/grading/pending", { method: "GET", token: GRADING });
check("claimed job leaves the pending list", r.status === 200 &&
  !r.body.some((j) => j.job_id === practiceJob));

r = await call("/grading/result", {
  token: GRADING,
  body: { job_id: practiceJob, completeness: 6, accuracy: 5, critique: "Too high." },
});
check("score above 5 rejected", r.status === 400);
r = await call("/grading/result", {
  token: GRADING,
  body: { job_id: practiceJob, completeness: 4, accuracy: 5, critique: "" },
});
check("empty critique rejected", r.status === 400);

// ------------------------------------------------------- push + signed result
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "pushone9", audio_sha256: AUDIO2_SHA, push_subscription: pushSub } });
check("job with a push subscription created", r.status === 200);
const pushJob = r.body.job_id;
await call("/grading/claim", { token: GRADING, body: { job_id: pushJob } });
const pushesBefore = pushRequests.length;
r = await call("/grading/result", {
  token: GRADING,
  body: {
    job_id: pushJob, completeness: 4, accuracy: 5,
    critique: "Covered most of it. The derivation step was missing.",
    injection_flags: [{ pattern: "instruction-like text", at_s: 42 }],
  },
});
check("result accepted and returns a receipt", r.status === 200 && r.body.ok === true &&
  /^[A-Za-z0-9_-]{43}$/.test(r.body.receipt));
const pushReceipt = r.body.receipt;
check("exactly one push was sent", pushRequests.length === pushesBefore + 1);

async function decryptPush(req) {
  const bodyBytes = new Uint8Array(req.opts.body);
  const salt = bodyBytes.slice(0, 16);
  const idlen = bodyBytes[20];
  const serverPub = bodyBytes.slice(21, 21 + idlen);
  const ciphertext = bodyBytes.slice(21 + idlen);
  const serverKey = await crypto.subtle.importKey("raw", serverPub, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const secret = new Uint8Array(await crypto.subtle.deriveBits({ name: "ECDH", public: serverKey }, uaKeys.privateKey, 256));
  const keyInfo = concatBytes(enc("WebPush: info"), new Uint8Array([0]), uaPubRaw, serverPub);
  const ikm = await hkdf(secret, uaAuth, keyInfo, 32);
  const cek = await hkdf(ikm, salt, concatBytes(enc("Content-Encoding: aes128gcm"), new Uint8Array([0])), 16);
  const nonce = await hkdf(ikm, salt, concatBytes(enc("Content-Encoding: nonce"), new Uint8Array([0])), 12);
  const aesKey = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["decrypt"]);
  const plain = new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: nonce }, aesKey, ciphertext));
  let end = plain.length;
  while (end > 0 && plain[end - 1] === 0) end--;
  if (plain[end - 1] !== 2) throw new Error("final record delimiter missing");
  return new TextDecoder().decode(plain.slice(0, end - 1));
}
{
  const req = pushRequests[pushRequests.length - 1];
  check("push headers: vapid auth, aes128gcm, urgency normal, ttl within job life",
    req.opts.headers["content-encoding"] === "aes128gcm" &&
    req.opts.headers.urgency === "normal" &&
    req.opts.headers.authorization.startsWith("vapid t=") &&
    req.opts.headers.authorization.includes("k=" + env.VAPID_PUBLIC_KEY) &&
    Number(req.opts.headers.ttl) > 0 && Number(req.opts.headers.ttl) <= 180 * 24 * 3600);
  const auth = req.opts.headers.authorization;
  const jwt = auth.slice("vapid t=".length, auth.indexOf(","));
  const [h, p, s] = jwt.split(".");
  const sigOk = await crypto.subtle.verify(
    { name: "ECDSA", hash: "SHA-256" }, vapidKeys.publicKey,
    Buffer.from(s, "base64url"), enc(`${h}.${p}`));
  const claims = JSON.parse(Buffer.from(p, "base64url").toString());
  check("VAPID JWT verifies against the public key and names the push origin",
    sigOk && claims.aud === "https://push.example.test" && claims.exp > Date.now() / 1000);
  const payloadText = await decryptPush(req);
  check("push payload decrypts (RFC 8291 self-decrypt) to the ready message",
    payloadText === JSON.stringify({ title: "HW Signing", body: "Your grade and critique are ready." }));
}

// Result bundle through /jobs/status, then /verify-grade round trip
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "pushone9" } });
check("status ready returns the result bundle without injection flags",
  r.status === 200 && r.body.status === "ready" && r.body.result &&
  r.body.result.receipt === pushReceipt &&
  r.body.result.completeness === 4 && r.body.result.accuracy === 5 &&
  r.body.result.youtube_video_sha256 === "none" &&
  !("injection_flags" in r.body.result));
const bundle = r.body.result;
r = await call("/verify-grade", { body: bundle });
check("verify-grade accepts the signed bundle", r.status === 200 && r.body.valid === true);
for (const [name, mod] of [
  ["completeness", { completeness: 5 }],
  ["accuracy", { accuracy: 4 }],
  ["critique hash", { critique_sha256: "e".repeat(64) }],
  ["audio fingerprint", { audio_sha256: "f".repeat(64) }],
  ["transcript fingerprint", { transcript_sha256: "d".repeat(64) }],
  ["package content hash", { pkg_content_sha256: "0".repeat(64) }],
  ["time", { t: "2020-01-01T00:00:00.000Z" }],
]) {
  const rr = await call("/verify-grade", { body: { ...bundle, ...mod } });
  check("verify-grade rejects tampered " + name, rr.status === 200 && rr.body.valid === false);
}
{
  const row = db._tables.jobs.find((j) => j.job_id === pushJob);
  check("injection flags are stored on the job record for the audit",
    JSON.stringify(JSON.parse(row.result_json).injection_flags) ===
    JSON.stringify([{ pattern: "instruction-like text", at_s: 42 }]));
}

// Retrieved marking
r = await call("/jobs/retrieved", { body: { pkg: "test-package v1", retrieval_code: "pushone9" } });
check("retrieved call succeeds", r.status === 200 && r.body.ok === true);
{
  const row = db._tables.jobs.find((j) => j.job_id === pushJob);
  check("retrieved_at is marked", typeof row.retrieved_at === "string");
}

// Push subscription gone (410) is cleared, result still succeeds
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "pushgone9", audio_sha256: AUDIO3_SHA, push_subscription: pushSubGone } });
const goneJob = r.body.job_id;
await call("/grading/claim", { token: GRADING, body: { job_id: goneJob } });
r = await call("/grading/result", {
  token: GRADING,
  body: { job_id: goneJob, completeness: 3, accuracy: 3, critique: "Partial." },
});
check("result succeeds even when the push endpoint is gone", r.status === 200 && r.body.ok === true);
{
  const row = db._tables.jobs.find((j) => j.job_id === goneJob);
  check("subscription returning 410 is cleared from the job", row.push_json === null);
}

// ------------------------------------------------------- claim lease expiry
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "leaseone9", audio_sha256: "9".repeat(64) } });
const leaseJob = r.body.job_id;
r = await call("/grading/claim", { token: GRADING, body: { job_id: leaseJob } });
check("lease job claimed", r.status === 200);
{
  const row = db._tables.jobs.find((j) => j.job_id === leaseJob);
  row.claim_expires = new Date(Date.now() - 1000).toISOString();
}
r = await call("/grading/pending", { method: "GET", token: GRADING });
check("job with an expired claim returns to pending", r.status === 200 &&
  r.body.some((j) => j.job_id === leaseJob));
r = await call("/grading/claim", { token: GRADING, body: { job_id: leaseJob } });
check("job with an expired claim can be claimed again", r.status === 200);

// ------------------------------------------------ job expiry (2.4.1)
// An ungraded job survives past 48 h: simulate a pre-2.4.1 queued job
// created 49 h ago whose stored expires_at (creation + 48 h) is past.
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "weekend99", audio_sha256: "8".repeat(64) } });
const weekendJob = r.body.job_id;
{
  const row = db._tables.jobs.find((j) => j.job_id === weekendJob);
  const created = Date.now() - 49 * 3600 * 1000;
  row.created_at = new Date(created).toISOString();
  row.expires_at = new Date(created + 48 * 3600 * 1000).toISOString();
}
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "weekend99" } });
check("queued job aged 49 h is not expired", r.status === 200 && r.body.status === "queued");
{
  const row = db._tables.jobs.find((j) => j.job_id === weekendJob);
  check("queued status reports the 7-day ungraded expiry", r.status === 200 &&
    Date.parse(r.body.expires_at) - Date.parse(row.created_at) === 7 * 24 * 3600 * 1000);
}
r = await call("/grading/pending", { method: "GET", token: GRADING });
check("queued job aged 49 h is still pending", r.status === 200 &&
  r.body.some((j) => j.job_id === weekendJob));
{
  const row = db._tables.jobs.find((j) => j.job_id === weekendJob);
  check("queued job aged 49 h keeps its transcript", row.transcript === jobBase.transcript);
}
// Grading it starts the 180-day graded lifetime.
r = await call("/grading/claim", { token: GRADING, body: { job_id: weekendJob } });
check("queued job aged 49 h can be claimed", r.status === 200);
r = await call("/grading/result", {
  token: GRADING,
  body: { job_id: weekendJob, completeness: 5, accuracy: 4, critique: "Graded after the weekend." },
});
check("result for the aged job succeeds", r.status === 200 && r.body.ok === true);
{
  const row = db._tables.jobs.find((j) => j.job_id === weekendJob);
  check("grading resets expiry to graded_at + 180 days",
    Date.parse(row.expires_at) - Date.parse(row.graded_at) === 180 * 24 * 3600 * 1000);
  check("grading nulls the transcript text but keeps its hash",
    row.transcript === null && row.transcript_sha256 === TRANS_SHA);
}
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "weekend99" } });
check("ready status reports the graded expiry", r.status === 200 && r.body.status === "ready" &&
  Date.parse(r.body.expires_at) - Date.now() <= 180 * 24 * 3600 * 1000);
// An ungraded job past the 7-day cap does expire.
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "staleone99", audio_sha256: "7".repeat(64) } });
const staleJob = r.body.job_id;
{
  const row = db._tables.jobs.find((j) => j.job_id === staleJob);
  const created = Date.now() - 8 * 24 * 3600 * 1000;
  row.created_at = new Date(created).toISOString();
  row.expires_at = new Date(created + 7 * 24 * 3600 * 1000).toISOString();
}
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "staleone99" } });
check("ungraded job aged 8 days reports status expired", r.status === 200 && r.body.status === "expired");
{
  const row = db._tables.jobs.find((j) => j.job_id === staleJob);
  check("expiry deletes the transcript and result",
    row.status === "expired" && row.transcript === null && row.result_json === null);
}
r = await call("/grading/pending", { method: "GET", token: GRADING });
check("expired job is not pending", r.status === 200 &&
  !r.body.some((j) => j.job_id === staleJob));
// A job graded before 2.6.0 (stored expires_at = graded_at + 48 h,
// here in the past) is governed by graded_at + 180 days, not the
// stored value: graded 10 h ago, it is still live.
{
  const row = db._tables.jobs.find((j) => j.job_id === weekendJob);
  row.graded_at = new Date(Date.now() - 10 * 3600 * 1000).toISOString();
  row.expires_at = new Date(Date.now() - 1000).toISOString();
}
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "weekend99" } });
check("pre-2.6.0 graded job is governed by graded_at, not the stored expiry",
  r.status === 200 && r.body.status === "ready" &&
  Date.parse(r.body.expires_at) - Date.now() > 179 * 24 * 3600 * 1000);
// A graded job expires 180 days after grading.
{
  const row = db._tables.jobs.find((j) => j.job_id === weekendJob);
  row.graded_at = new Date(Date.now() - 181 * 24 * 3600 * 1000).toISOString();
  row.expires_at = new Date(Date.now() - 1000).toISOString();
}
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "weekend99" } });
check("graded job past its graded expiry reports expired", r.status === 200 && r.body.status === "expired");
{
  const row = db._tables.jobs.find((j) => j.job_id === weekendJob);
  check("graded expiry deletes the result",
    row.status === "expired" && row.result_json === null);
}

// Final-job uniqueness versus an expired final: an expired final no
// longer blocks a fresh final for the same fingerprint.
{
  const row = db._tables.jobs.find((j) => j.job_id === finalJob);
  // Past every governing expiry: the stored graded expiry, and the
  // 7-day ungraded cap measured from an 8-day-old creation.
  row.created_at = new Date(Date.now() - 8 * 24 * 3600 * 1000).toISOString();
  row.expires_at = new Date(Date.now() - 1000).toISOString();
  await call("/grading/pending", { method: "GET", token: GRADING }); // runs the sweep
  const rr = await call("/jobs", { body: { ...finalBase, retrieval_code: "finalthree9" } });
  check("expired final frees the fingerprint for a new final", rr.status === 200);
}

// ------------------------------------------------------- review fixes F1–F3
// F1: the claim is the guarded UPDATE, not the preceding status
// check — two pollers racing one job cannot both win.
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "raceclaim9", audio_sha256: "7".repeat(64) } });
check("F1 setup: race target job created", r.status === 200);
const raceJob = r.body.job_id;
{
  const [c1, c2] = await Promise.all([
    call("/grading/claim", { token: GRADING, body: { job_id: raceJob } }),
    call("/grading/claim", { token: GRADING, body: { job_id: raceJob } }),
  ]);
  const statuses = [c1.status, c2.status].sort((a, b) => a - b);
  check("F1: concurrent claims — exactly one wins, the loser gets 409",
    statuses[0] === 200 && statuses[1] === 409);
  const winner = c1.status === 200 ? c1 : c2;
  check("F1: the winning claim received the transcript",
    winner.body.transcript === JOB_TRANSCRIPT);
}

// F3: a transcript hash that does not match the transcript is
// rejected at intake, not signed later.
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "hashliar9", transcript_sha256: "e".repeat(64) } });
check("F3: job whose transcript hash does not match its transcript rejected",
  r.status === 400 && /transcript/i.test((r.body && r.body.error) || ""));

// F2: one live job per audio fingerprint, enforced by the
// jobs_one_per_recording partial unique index — two concurrent jobs
// under different retrieval names cannot both land, and the loser
// is told it is a duplicate of the winner (2.6.0: the duplicate
// response, not a 409).
{
  const raceFinal = { ...finalBase, retrieval_code: "racefinala9", audio_sha256: "5".repeat(64) };
  const [f1, f2] = await Promise.all([
    call("/jobs", { body: raceFinal }),
    call("/jobs", { body: { ...raceFinal, retrieval_code: "racefinalb9" } }),
  ]);
  const winner = f1.body && f1.body.duplicate ? f2 : f1;
  const loser = f1.body && f1.body.duplicate ? f1 : f2;
  check("F2: concurrent finals for one fingerprint — exactly one is created, the loser gets the duplicate",
    f1.status === 200 && f2.status === 200 &&
    winner.body && !winner.body.duplicate && typeof winner.body.job_id === "string" &&
    loser.body && loser.body.duplicate === true &&
    loser.body.job_id === winner.body.job_id && loser.body.alias_created === true);
  const rows = db._tables.jobs.filter(
    (j) => j.audio_sha256 === "5".repeat(64) && j.kind === "final");
  check("F2: exactly one final row is stored for the fingerprint", rows.length === 1);
}

// ------------------------------------------------------- fail closed
{
  const noSecret = { ...env };
  delete noSecret.SIGNING_SECRET;
  const r1 = await call("/verify-grade", { body: bundle, e: noSecret });
  const r2 = await call("/youtube-check", { body: { url: "https://youtu.be/dQw4w9WgXcQ" }, e: noSecret });
  const r3 = await call("/jobs", { body: jobBase, e: noSecret });
  check("no signing secret: verify-grade fails closed", r1.status === 500);
  check("no signing secret: youtube-check fails closed", r2.status === 500);
  check("no signing secret: job creation fails closed", r3.status === 500);
  const noAdmin = { ...env };
  delete noAdmin.ADMIN_TOKEN;
  const r4 = await call("/admin/packages", { method: "GET", e: noAdmin });
  check("no admin token configured: admin route fails closed", r4.status === 500);
  const noGrading = { ...env };
  delete noGrading.GRADING_TOKEN;
  const r5 = await call("/grading/pending", { method: "GET", e: noGrading });
  check("no grading token configured: grading route fails closed", r5.status === 500);
}

// ------------------------------------------------------- finalize (turn a graded job into the submission)
{
  const finBody = {
    pkg: "test-package v1", retrieval_code: "pushone9",
    youtube_video_id: "dQw4w9WgXcQ",
    youtube_token: ytOk.body.token,
    youtube_checked_at: ytOk.body.checked_at,
  };
  r = await call("/jobs/finalize", { body: { ...finBody, retrieval_code: "wrongcode9" } });
  check("finalize with wrong code returns 403", r.status === 403);
  r = await call("/jobs/finalize", { body: { ...finBody, youtube_token: "bogus" } });
  check("finalize with a bad YouTube token rejected", r.status === 400);
  const before = db._tables.jobs.find((j) => j.job_id === pushJob);
  const oldReceipt = before.receipt;
  r = await call("/jobs/finalize", { body: finBody });
  check("finalize of a graded practice job succeeds", r.status === 200 && r.body.ok === true);
  const after = db._tables.jobs.find((j) => j.job_id === pushJob);
  const bundle2 = JSON.parse(after.result_json);
  const expectHash = await sha256Hex("dQw4w9WgXcQ");
  check("finalize sets kind final and the video hash everywhere",
    after.kind === "final" && after.youtube_video_sha256 === expectHash &&
    bundle2.youtube_video_sha256 === expectHash && after.receipt !== oldReceipt &&
    bundle2.receipt === after.receipt && bundle2.t === JSON.parse(before.result_json).t);
  const { injection_flags, ...verifyBody } = bundle2;
  r = await call("/verify-grade", { body: verifyBody });
  check("re-signed bundle verifies after finalize", r.status === 200 && r.body.valid === true);
  r = await call("/jobs/finalize", { body: finBody });
  check("finalize of an already-final job rejected", r.status === 409);
  // Under 2.6.0 a job for a fingerprint with a live final is a
  // duplicate of that final, not a new job: the live final for
  // AUDIO_FINAL_SHA is the one created after the first final
  // expired (finalthree9), not the expired finalJob row.
  const liveFinal = db._tables.jobs.find(
    (j) => j.audio_sha256 === AUDIO_FINAL_SHA && j.kind === "final" && j.status !== "expired");
  r = await call("/jobs", { body: { ...finalBase, retrieval_code: "finconflict9" } });
  check("job for a fingerprint with a live final returns the final as a duplicate",
    r.status === 200 && r.body.duplicate === true && r.body.job_id === liveFinal.job_id);
  r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "finconflict9" } });
  check("alias code for the duplicate retrieves the final job",
    r.status === 200 && r.body.status === "queued");
  // Finalize's own one-final guard still applies when a final
  // already exists for the recording: set it up by direct row
  // edit, since POST /jobs can no longer create the second job.
  r = await call("/jobs", { body: { ...jobBase, retrieval_code: "finpractice9", audio_sha256: "e5".repeat(32) } });
  check("practice job for the finalize-conflict recording created",
    r.status === 200 && !r.body.duplicate);
  r = await call("/jobs", { body: { ...finalBase, retrieval_code: "finother999", audio_sha256: "f6".repeat(32) } });
  check("second final job for the finalize-conflict setup created",
    r.status === 200 && !r.body.duplicate);
  const finOtherJob = r.body.job_id;
  {
    const row = db._tables.jobs.find((j) => j.job_id === finOtherJob);
    row.audio_sha256 = "e5".repeat(32);
  }
  r = await call("/jobs/finalize", { body: { ...finBody, retrieval_code: "finpractice9" } });
  check("finalize blocked when a final already exists for the recording", r.status === 409);
}

// ------------------------------------------------------- replacement check
// A job sent under an issued link for one version is graded under
// the newest open version of the same package name (worker 2.5.0).
const RP_TEXT_1 = PKG_TEXT + "\nReplacement package, version 1.\n";
const RP_TEXT_2 = PKG_TEXT + "\nReplacement package, version 2.\n";
const RP_TEXT_3 = PKG_TEXT + "\nReplacement package, version 3.\n";
const rpHash1 = await sha256Hex(RP_TEXT_1);
const rpHash2 = await sha256Hex(RP_TEXT_2);
async function rpStatus(id, body) {
  return call("/admin/packages/" + encodeURIComponent(id) + "/status",
    { body, token: ADMIN });
}
r = await call("/admin/packages", { body: { pkg_name: "replace-package", text: RP_TEXT_1 }, token: ADMIN });
check("replacement package v1 created", r.status === 200 && r.body.version === 1);
await rpStatus("replace-package v1", { status: "trialled", trial: { completeness: 5, accuracy: 5 } });
r = await rpStatus("replace-package v1", { status: "open" });
check("replacement package v1 opens", r.status === 200 && r.body.status === "open");
const rpBase = { ...jobBase, pkg: "replace-package v1", pkg_content_sha256: rpHash1 };
r = await call("/jobs", { body: { ...rpBase, retrieval_code: "rpfirst001", audio_sha256: "2a".repeat(32) } });
check("no newer open version: job stays on the requested version",
  r.status === 200 && r.body.pkg === "replace-package v1");
r = await call("/admin/packages", { body: { pkg_name: "replace-package", text: RP_TEXT_2 }, token: ADMIN });
check("replacement package v2 created as draft", r.status === 200 && r.body.version === 2);
r = await call("/jobs", { body: { ...rpBase, retrieval_code: "rpsecond02", audio_sha256: "2b".repeat(32) } });
check("newer version still draft: job stays on the requested version",
  r.status === 200 && r.body.pkg === "replace-package v1");
await rpStatus("replace-package v2", { status: "trialled", trial: { completeness: 5, accuracy: 5 } });
r = await rpStatus("replace-package v2", { status: "open" });
check("replacement package v2 opens", r.status === 200 && r.body.status === "open");
r = await call("/jobs", { body: { ...rpBase, retrieval_code: "rpthird003", audio_sha256: "2c".repeat(32) } });
check("newer open version: job resolves to it at intake",
  r.status === 200 && r.body.pkg === "replace-package v2");
const rpJob = r.body.job_id;
check("job row stored under the resolved version",
  db._tables.jobs.find((j) => j.job_id === rpJob).pkg === "replace-package v2");
r = await call("/grading/pending", { method: "GET", token: GRADING });
check("pending list names the resolved version",
  r.body.some((j) => j.job_id === rpJob && j.pkg === "replace-package v2"));
r = await call("/grading/claim", { token: GRADING, body: { job_id: rpJob } });
check("claim returns the resolved version's text and hash",
  r.status === 200 && r.body.package.pkg === "replace-package v2" &&
  r.body.package.text === RP_TEXT_2 && r.body.package.content_sha256 === rpHash2);
r = await call("/jobs/status", { body: { pkg: "replace-package v1", retrieval_code: "rpthird003" } });
check("status lookup under the old link still finds the resolved job",
  r.status === 200 && r.body.status === "claimed");
r = await call("/jobs", { body: { ...rpBase, retrieval_code: "rpthird003", audio_sha256: "2d".repeat(32) } });
check("same code under the old link again rejected after resolution", r.status === 409);
r = await call("/jobs", { body: { ...rpBase, retrieval_code: "rpfourth04", pkg_content_sha256: "f".repeat(64) } });
check("wrong hash for the requested version rejected despite a newer open version",
  r.status === 400);
r = await rpStatus("replace-package v1", { status: "closed" });
check("replacement package v1 closes", r.status === 200 && r.body.status === "closed");
r = await call("/jobs", { body: { ...rpBase, retrieval_code: "rpfifth005", audio_sha256: "2e".repeat(32) } });
check("requested version closed, newer open: old link still resolves",
  r.status === 200 && r.body.pkg === "replace-package v2");
r = await call("/admin/packages", { body: { pkg_name: "replace-package", text: RP_TEXT_3 }, token: ADMIN });
check("replacement package v3 created as draft", r.status === 200 && r.body.version === 3);
r = await call("/jobs", { body: { ...rpBase, retrieval_code: "rpsixth006", audio_sha256: "2f".repeat(32) } });
check("newest version draft: resolution stops at the newest open version",
  r.status === 200 && r.body.pkg === "replace-package v2");
r = await call("/jobs", { body: { ...rpBase, pkg: "replace-package v2", pkg_content_sha256: rpHash2, retrieval_code: "rpseventh7", audio_sha256: "3a".repeat(32) } });
check("job sent under the newest link stays on it",
  r.status === 200 && r.body.pkg === "replace-package v2");

// ------------------------------------------------------- dedup (2.6.0)
function fpBase64(items) {
  const buf = Buffer.alloc(items.length * 4);
  items.forEach((v, i) => buf.writeUInt32LE(v >>> 0, i * 4));
  return buf.toString("base64");
}
function makeFp(seed, n = 100) {
  let x = seed >>> 0;
  const out = [];
  for (let i = 0; i < n; i++) {
    x = (Math.imul(x, 1664525) + 1013904223) >>> 0;
    out.push(x);
  }
  return out;
}
const FP_A = makeFp(12345, 100);
const FP_A64 = fpBase64(FP_A);
const FP_B = FP_A.map((v, i) => (i % 10 === 0 ? v ^ 1 : v)); // a few bits flipped: similarity ~0.998
const FP_C = makeFp(999, 100); // unrelated recording: similarity ~0.5
const FP_D = makeFp(31337, 80);
const FP_E = makeFp(4242, 90);
const FP_F = makeFp(5151, 60);
const FP_A_SHIFTED = [...makeFp(777, 3), ...FP_A];

r = await call("/", { method: "GET" });
check("health: version is 2.6.0", r.status === 200 && r.body.version === "2.6.0");

// Duplicate of a graded job returns the same bundle (practice and
// final), and the submitted kind / YouTube token are ignored.
const DEDUP_A = "a1".repeat(32);
const DEDUP_B = "b2".repeat(32);
const DEDUP_C = "c3".repeat(32);
const DEDUP_D = "d4".repeat(32);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "deduppa01", audio_sha256: DEDUP_A, chromaprint: FP_A64 } });
check("dedup setup: practice job with a fingerprint created", r.status === 200 && !r.body.duplicate);
const dedupJob = r.body.job_id;
{
  const row = db._tables.jobs.find((j) => j.job_id === dedupJob);
  check("fingerprint stored on the job row", row.chromaprint === FP_A64);
}
await call("/grading/claim", { token: GRADING, body: { job_id: dedupJob } });
r = await call("/grading/result", {
  token: GRADING,
  body: { job_id: dedupJob, completeness: 4, accuracy: 5, critique: "Dedup graded critique." },
});
check("dedup setup: graded job returns a receipt", r.status === 200 && r.body.ok === true);
const dedupReceipt = r.body.receipt;
{
  const row = db._tables.jobs.find((j) => j.job_id === dedupJob);
  check("transcript nulling (a): graded job row transcript is NULL",
    row.transcript === null);
  check("transcript nulling (b): graded job keeps transcript_sha256 and the fingerprint",
    row.transcript_sha256 === TRANS_SHA && row.chromaprint === FP_A64);
  check("graded expires_at is graded_at + 180 days",
    Date.parse(row.expires_at) - Date.parse(row.graded_at) === 180 * 24 * 3600 * 1000);
}
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "deduppb02", audio_sha256: DEDUP_A, chromaprint: FP_A64 } });
check("duplicate practice job returns the same graded bundle",
  r.status === 200 && r.body.duplicate === true && r.body.job_id === dedupJob &&
  r.body.status === "ready" && r.body.result && r.body.result.completeness === 4 &&
  r.body.result.accuracy === 5 && r.body.result.receipt === dedupReceipt &&
  r.body.result.critique === "Dedup graded critique." && r.body.alias_created === true &&
  Date.parse(r.body.expires_at) - Date.parse(r.body.result.t) <= 180 * 24 * 3600 * 1000);
r = await call("/jobs", { body: { ...jobBase, kind: "final", retrieval_code: "deduppc03", audio_sha256: DEDUP_A, chromaprint: FP_A64 } });
check("duplicate final job without a YouTube token still returns the duplicate (kind and token ignored)",
  r.status === 200 && r.body.duplicate === true && r.body.job_id === dedupJob);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "deduppd04", audio_sha256: DEDUP_B, chromaprint: FP_A64 } });
check("same fingerprint under a different audio hash is a duplicate (Chromaprint path)",
  r.status === 200 && r.body.duplicate === true && r.body.job_id === dedupJob);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "deduppe05", audio_sha256: DEDUP_C, chromaprint: fpBase64(FP_A_SHIFTED) } });
check("fingerprint shifted by 3 items is a duplicate (offset search)",
  r.status === 200 && r.body.duplicate === true && r.body.job_id === dedupJob);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "deduppf06", audio_sha256: DEDUP_D, chromaprint: fpBase64(FP_C) } });
check("different fingerprint is a new job", r.status === 200 && !r.body.duplicate);
const dedupOtherJob = r.body.job_id;
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "deduppg07", audio_sha256: DEDUP_A, pkg: "replace-package v2", pkg_content_sha256: rpHash2 } });
check("same audio under a different package is a new job (dedup is per package)",
  r.status === 200 && !r.body.duplicate);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "dedupph08", audio_sha256: DEDUP_D, chromaprint: fpBase64(FP_C) } });
check("duplicate of a queued job carries queue_ahead",
  r.status === 200 && r.body.duplicate === true && r.body.job_id === dedupOtherJob &&
  r.body.status === "queued" && Number.isInteger(r.body.queue_ahead));
// Alias retrieval: the alias code finds the graded job by status,
// and a code already used by a different job is not aliased.
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "deduppb02" } });
check("transcript nulling (b): alias status returns the result bundle for the graded job",
  r.status === 200 && r.body.status === "ready" && r.body.result &&
  r.body.result.receipt === dedupReceipt);
r = await call("/jobs/retrieved", { body: { pkg: "test-package v1", retrieval_code: "deduppb02" } });
check("alias code marks the job retrieved", r.status === 200 && r.body.ok === true);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "deduppf06", audio_sha256: DEDUP_A, chromaprint: FP_A64 } });
check("duplicate with a code already used by a different job: no alias created, duplicate still returned",
  r.status === 200 && r.body.duplicate === true && r.body.job_id === dedupJob &&
  r.body.alias_created === false);
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "deduppf06" } });
check("code used by another job still retrieves that job, not the duplicate",
  r.status === 200 && r.body.status === "queued");
r = await call("/jobs/finalize", {
  body: {
    pkg: "test-package v1", retrieval_code: "deduppb02",
    youtube_video_id: "dQw4w9WgXcQ",
    youtube_token: ytOk.body.token,
    youtube_checked_at: ytOk.body.checked_at,
  },
});
check("alias code finalizes the graded job", r.status === 200 && r.body.ok === true);
{
  const row = db._tables.jobs.find((j) => j.job_id === dedupJob);
  check("finalize via alias sets kind final on the original job",
    row.kind === "final" && row.youtube_status === "ok");
}

// Transcript nulling (c): a queued job still returns its transcript
// on claim; grading it then nulls the transcript.
r = await call("/grading/claim", { token: GRADING, body: { job_id: dedupOtherJob } });
check("transcript nulling (c): queued job returns its transcript on claim",
  r.status === 200 && r.body.transcript === JOB_TRANSCRIPT);
r = await call("/grading/result", {
  token: GRADING,
  body: { job_id: dedupOtherJob, completeness: 3, accuracy: 4, critique: "Queued claim transcript check." },
});
check("transcript nulling (c): result for the claimed job succeeds", r.status === 200 && r.body.ok === true);
{
  const row = db._tables.jobs.find((j) => j.job_id === dedupOtherJob);
  check("transcript nulling (c): transcript is NULL after grading",
    row.transcript === null && row.transcript_sha256 === TRANS_SHA);
}

// Same audio under a new prompt version re-grades.
const RG_TEXT_1 = PKG_TEXT + "\nRegrade package, version 1.\n";
const RG_TEXT_2 = PKG_TEXT + "\nRegrade package, version 2.\n";
const rgHash1 = await sha256Hex(RG_TEXT_1);
const rgHash2 = await sha256Hex(RG_TEXT_2);
r = await call("/admin/packages", { body: { pkg_name: "regrade-package", text: RG_TEXT_1 }, token: ADMIN });
check("regrade package v1 created", r.status === 200 && r.body.version === 1);
await rpStatus("regrade-package v1", { status: "trialled", trial: { completeness: 5, accuracy: 5 } });
r = await rpStatus("regrade-package v1", { status: "open" });
check("regrade package v1 opens", r.status === 200 && r.body.status === "open");
const REGRADE_A = "a9".repeat(32);
const rgBase = { ...jobBase, pkg: "regrade-package v1", pkg_content_sha256: rgHash1, audio_sha256: REGRADE_A, chromaprint: FP_A64 };
r = await call("/jobs", { body: { ...rgBase, retrieval_code: "regradea1" } });
check("regrade setup: job under v1 created", r.status === 200 && r.body.pkg === "regrade-package v1");
const regradeV1Job = r.body.job_id;
await call("/grading/claim", { token: GRADING, body: { job_id: regradeV1Job } });
r = await call("/grading/result", {
  token: GRADING,
  body: { job_id: regradeV1Job, completeness: 5, accuracy: 5, critique: "First version grade." },
});
check("regrade setup: v1 job graded", r.status === 200 && r.body.ok === true);
r = await call("/admin/packages", { body: { pkg_name: "regrade-package", text: RG_TEXT_2 }, token: ADMIN });
check("regrade package v2 created", r.status === 200 && r.body.version === 2);
await rpStatus("regrade-package v2", { status: "trialled", trial: { completeness: 5, accuracy: 5 } });
r = await rpStatus("regrade-package v2", { status: "open" });
check("regrade package v2 opens", r.status === 200 && r.body.status === "open");
r = await call("/jobs", { body: { ...rgBase, retrieval_code: "regradeb2" } });
check("same audio under a new prompt version is a new job, resolved to v2",
  r.status === 200 && !r.body.duplicate && r.body.pkg === "regrade-package v2");
const regradeV2Job = r.body.job_id;
await call("/grading/claim", { token: GRADING, body: { job_id: regradeV2Job } });
r = await call("/grading/result", {
  token: GRADING,
  body: { job_id: regradeV2Job, completeness: 3, accuracy: 4, critique: "Second version grade." },
});
check("regrade: v2 job graded with its own grade", r.status === 200 && r.body.ok === true);
r = await call("/jobs/status", { body: { pkg: "regrade-package v1", retrieval_code: "regradeb2" } });
check("regrade: status under the old link returns the v2 grade",
  r.status === 200 && r.body.status === "ready" && r.body.result &&
  r.body.result.completeness === 3 && r.body.result.critique === "Second version grade.");
r = await call("/jobs", { body: { ...rgBase, retrieval_code: "regradec3" } });
check("same audio under v2 again is a duplicate of the v2 job",
  r.status === 200 && r.body.duplicate === true && r.body.job_id === regradeV2Job);

// Bad, oversize and missing fingerprints are ignored, never reject.
const BADFP = "!!!not-base64!!!";
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "badfp001", audio_sha256: "b1".repeat(32) } });
check("missing fingerprint: job created normally", r.status === 200 && !r.body.duplicate);
{
  const row = db._tables.jobs.find((j) => j.job_id === r.body.job_id);
  check("missing fingerprint stored as NULL", row.chromaprint === null || row.chromaprint === undefined);
}
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "badfp002", audio_sha256: "c1".repeat(32), chromaprint: BADFP } });
check("malformed fingerprint: job created normally", r.status === 200 && !r.body.duplicate);
{
  const row = db._tables.jobs.find((j) => j.job_id === r.body.job_id);
  check("malformed fingerprint stored as NULL", row.chromaprint === null);
}
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "badfp003", audio_sha256: "c2".repeat(32), chromaprint: Buffer.from([1, 2, 3]).toString("base64") } });
check("fingerprint of 3 bytes (not a whole item): job created normally", r.status === 200 && !r.body.duplicate);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "badfp004", audio_sha256: "c4".repeat(32), chromaprint: fpBase64(makeFp(42, 20001)) } });
check("oversize fingerprint (20001 items): job created normally", r.status === 200 && !r.body.duplicate);
{
  const row = db._tables.jobs.find((j) => j.job_id === r.body.job_id);
  check("oversize fingerprint stored as NULL", row.chromaprint === null);
}
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "badfp005", audio_sha256: "c5".repeat(32), chromaprint: "" } });
check("empty fingerprint: job created normally", r.status === 200 && !r.body.duplicate);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "badfp006", audio_sha256: "c6".repeat(32), chromaprint: BADFP } });
check("same bad fingerprint on a different recording is not a duplicate",
  r.status === 200 && !r.body.duplicate);

// Expired jobs allow fresh grading, and the sweep deletes aliases.
const EXP_A = "d1".repeat(32);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "expa0001", audio_sha256: EXP_A, chromaprint: fpBase64(FP_D) } });
check("expiry setup: ungraded job created", r.status === 200 && !r.body.duplicate);
{
  const row = db._tables.jobs.find((j) => j.job_id === r.body.job_id);
  const created = Date.now() - 8 * 24 * 3600 * 1000;
  row.created_at = new Date(created).toISOString();
  row.expires_at = new Date(created + 7 * 24 * 3600 * 1000).toISOString();
}
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "expa0001" } });
check("ungraded job aged 8 days reports expired", r.status === 200 && r.body.status === "expired");
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "expa0002", audio_sha256: EXP_A, chromaprint: fpBase64(FP_D) } });
check("expired ungraded job frees the fingerprint for a fresh job",
  r.status === 200 && !r.body.duplicate);
const EXP_B = "d2".repeat(32);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "expb0001", audio_sha256: EXP_B, chromaprint: fpBase64(FP_E) } });
check("expiry setup: graded job created", r.status === 200 && !r.body.duplicate);
const expBJob = r.body.job_id;
await call("/grading/claim", { token: GRADING, body: { job_id: expBJob } });
r = await call("/grading/result", {
  token: GRADING,
  body: { job_id: expBJob, completeness: 4, accuracy: 4, critique: "Expiry test grade." },
});
check("expiry setup: job graded", r.status === 200 && r.body.ok === true);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "expb0002", audio_sha256: EXP_B, chromaprint: fpBase64(FP_E) } });
check("duplicate of the graded job returns its bundle and creates an alias",
  r.status === 200 && r.body.duplicate === true && r.body.job_id === expBJob && r.body.alias_created === true);
{
  const row = db._tables.jobs.find((j) => j.job_id === expBJob);
  row.graded_at = new Date(Date.now() - 181 * 24 * 3600 * 1000).toISOString();
  row.expires_at = new Date(Date.now() - 1000).toISOString();
}
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "expb0001" } });
check("graded job past 180 days reports expired", r.status === 200 && r.body.status === "expired");
{
  const row = db._tables.jobs.find((j) => j.job_id === expBJob);
  check("graded expiry deletes the result and the alias is swept",
    row.status === "expired" && row.result_json === null &&
    !db._tables.job_code_aliases.some((a) => a.job_id === expBJob));
}
r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "expb0002" } });
check("alias code stops retrieving once the job has expired", r.status === 403);
r = await call("/jobs", { body: { ...jobBase, retrieval_code: "expb0003", audio_sha256: EXP_B, chromaprint: fpBase64(FP_E) } });
check("expired graded job frees the fingerprint for fresh grading",
  r.status === 200 && !r.body.duplicate);

// Race safety (2.6.0): two concurrent creates for the same
// fingerprint and version — exactly one job, the loser gets the
// duplicate response.
{
  const RACE_A = "e1".repeat(32);
  const raceBody = { ...jobBase, retrieval_code: "racea001", audio_sha256: RACE_A, chromaprint: fpBase64(FP_F) };
  const [r1, r2] = await Promise.all([
    call("/jobs", { body: raceBody }),
    call("/jobs", { body: { ...raceBody, retrieval_code: "raceb002" } }),
  ]);
  const winner = r1.body && r1.body.duplicate ? r2 : r1;
  const loser = r1.body && r1.body.duplicate ? r1 : r2;
  check("race: concurrent creates for one fingerprint — exactly one job, loser gets the duplicate",
    r1.status === 200 && r2.status === 200 &&
    winner.body && !winner.body.duplicate && typeof winner.body.job_id === "string" &&
    loser.body && loser.body.duplicate === true &&
    loser.body.job_id === winner.body.job_id && loser.body.alias_created === true);
  const rows = db._tables.jobs.filter(
    (j) => j.audio_sha256 === RACE_A && j.pkg === "test-package v1" && j.status !== "expired");
  check("race: exactly one live row is stored for the fingerprint", rows.length === 1);
  r = await call("/jobs/status", { body: { pkg: "test-package v1", retrieval_code: "raceb002" } });
  check("race: the loser's code retrieves the winning job via its alias",
    r.status === 200 && r.body.status === "queued");
}

// Unknown route
r = await call("/nope", { method: "GET" });
check("unknown route is 404", r.status === 404);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
