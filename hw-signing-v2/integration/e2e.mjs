#!/usr/bin/env node
// HW Signing v2 end-to-end integration test.
//
// Drives the REAL components against each other, locally, no network
// beyond a loopback bridge:
//   - the real worker.js, loaded in Node, backed by a D1 shim (adapted
//     from worker/test.mjs), with fetch stubbed only for YouTube oEmbed
//     and the push service;
//   - the real pkg_admin.mjs and grade_jobs.mjs scripts (copied with
//     their skill folders to a temp dir so a test config.json can be
//     written; the scripts themselves are byte-identical), talking to
//     the Worker through a loopback HTTP bridge;
//   - the real webapp js/jobs.js (payload build/validate, submit,
//     status), js/package.js (submission.html) and js/zip.js (ZIP);
//   - the real audit app (audit.py check_package as a library call via
//     audit_check.py), its post_fn defaulting to real HTTP against the
//     bridge, i.e. the REAL worker /verify-grade.
//
// Prints a per-step PASS/FAIL summary; exits non-zero on any failure.
import http from "node:http";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileP = promisify(execFile);
import { cpSync, mkdtempSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const worker = (await import(path.join(ROOT, "worker", "worker.js"))).default;
const jobsMod = await import(path.join(ROOT, "webapp", "js", "jobs.js"));
const transcriptMod = await import(path.join(ROOT, "webapp", "js", "transcript.js"));
const pkgMod = await import(path.join(ROOT, "webapp", "js", "package.js"));
const zipMod = await import(path.join(ROOT, "webapp", "js", "zip.js"));

// ------------------------------------------------------------ D1 shim
// Adapted verbatim from worker/test.mjs (the statement shapes are the
// ones worker.js uses).
function createDb() {
  const tables = { packages: [], jobs: [] };
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
    if (mx) return [{ [mx[2]]: rows.length ? Math.max(...rows.map((r) => r[mx[1]])) : null }];
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
        if (tables.jobs.some((r) => r.job_id === row.job_id)) throw new Error("UNIQUE constraint failed: jobs.job_id");
        if (row.code_lookup != null &&
            tables.jobs.some((r) => r.pkg === row.pkg && r.code_lookup === row.code_lookup)) {
          throw new Error("UNIQUE constraint failed: jobs.pkg, jobs.code_lookup");
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
    throw new Error("unsupported statement: " + sql);
  }
  function prepare(sql) {
    let bound = [];
    const stmt = {
      bind(...a) { bound = a; return stmt; },
      async first() { const r = execSelect(sql, bound); return r.length ? r[0] : null; },
      async all() {
        if (/^\s*(INSERT|UPDATE)/i.test(sql)) { execWrite(sql, bound); return { results: [] }; }
        return { results: execSelect(sql, bound) };
      },
      async run() { const changes = execWrite(sql, bound); return { success: true, meta: { changes } }; },
    };
    return stmt;
  }
  return { prepare, _tables: tables };
}

// ------------------------------------------------------------ setup
const realFetch = globalThis.fetch.bind(globalThis);
globalThis.fetch = async (url, opts = {}) => {
  const u = String(url);
  if (u.startsWith("https://www.youtube.com/oembed")) {
    return new Response(JSON.stringify({ title: "t", author_name: "a" }), {
      status: 200, headers: { "content-type": "application/json" },
    });
  }
  if (u.startsWith("https://push.example")) return new Response("", { status: 201 });
  return realFetch(url, opts);
};

const vapidKeys = await crypto.subtle.generateKey(
  { name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
const vapidPubRaw = new Uint8Array(await crypto.subtle.exportKey("raw", vapidKeys.publicKey));
const vapidJwk = await crypto.subtle.exportKey("jwk", vapidKeys.privateKey);
const env = {
  DB: createDb(),
  SIGNING_SECRET: "e2e-signing-secret-0123456789abcdef",
  ADMIN_TOKEN: "e2e-admin-token-0123456789",
  GRADING_TOKEN: "e2e-grading-token-0123456789",
  VAPID_PUBLIC_KEY: Buffer.from(vapidPubRaw).toString("base64url"),
  VAPID_PRIVATE_KEY: vapidJwk.d,
};

// Loopback HTTP bridge: the skills' scripts and the audit's transport
// speak HTTP; the bridge hands each request to the real worker.fetch.
const bridge = http.createServer(async (req, res) => {
  try {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const body = Buffer.concat(chunks);
    const headers = {};
    for (const h of ["content-type", "authorization", "x-admin-token", "x-grading-token"]) {
      if (req.headers[h]) headers[h] = req.headers[h];
    }
    const wreq = new Request("http://127.0.0.1" + req.url, {
      method: req.method,
      headers,
      body: req.method === "GET" || req.method === "HEAD" ? undefined : body,
    });
    const wres = await worker.fetch(wreq, env);
    const text = await wres.text();
    res.writeHead(wres.status, { "content-type": wres.headers.get("content-type") || "application/json" });
    res.end(text);
  } catch (e) {
    res.writeHead(500, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: "bridge: " + e.message }));
  }
});
await new Promise((r) => bridge.listen(0, "127.0.0.1", r));
const BASE = "http://127.0.0.1:" + bridge.address().port;

const tmp = mkdtempSync(path.join(tmpdir(), "hw-signing-v2-e2e-"));
const enc = new TextEncoder();
const sha256 = (data) => createHash("sha256").update(data).digest("hex");

// NOTE: child processes must be awaited asynchronously. A blocking
// exec would freeze this process's event loop — and with it the
// loopback bridge the children are calling — deadlocking every call
// until the child's fetch times out.
async function runNode(script, args) {
  const { stdout } = await execFileP(process.execPath, [script, ...args], { encoding: "utf8" });
  return stdout;
}

// Skill copies with test configs (scripts byte-identical to staging).
const builderDir = path.join(tmp, "local-prompt-package-builder");
cpSync(path.join(ROOT, "skills", "local-prompt-package-builder"), builderDir, { recursive: true });
writeFileSync(path.join(builderDir, "config.json"),
  JSON.stringify({ worker: BASE, adminToken: env.ADMIN_TOKEN }));
const pollDir = path.join(tmp, "local-grading-poll");
cpSync(path.join(ROOT, "skills", "local-grading-poll"), pollDir, { recursive: true });
writeFileSync(path.join(pollDir, "config.json"),
  JSON.stringify({ worker: BASE, gradingToken: env.GRADING_TOKEN }));
const pkgAdmin = path.join(builderDir, "scripts", "pkg_admin.mjs");
const gradeJobs = path.join(pollDir, "scripts", "grade_jobs.mjs");

// ------------------------------------------------------------ fixtures
const VIDEO_ID = "abc123XYZ_-";
const WATCH_URL = "https://www.youtube.com/watch?v=" + VIDEO_ID;
const CHUNKS = [
  { start: 0, text: "Hello, this is the explanation of the grade distribution set-up." },
  { start: 65, text: "The count of ways uses the multinomial coefficient and Stirling's approximation." },
];
// The transcript the page sends is its canonical transcript: since
// webapp 2.4.2 each chunk line carries its [mm:ss] start marker.
const TRANSCRIPT = transcriptMod.canonicalTranscript(CHUNKS);
const CRITIQUE =
  "The set-up is stated clearly and the counting argument is exact.\n" +
  "The constraint equations aren't written out, and the Tom & Jerry <sic> remark is wrong.";

function makeWav(seconds = 2, rate = 16000) {
  const n = Math.floor(seconds * rate);
  const data = Buffer.alloc(44 + n * 2);
  data.write("RIFF", 0); data.writeUInt32LE(36 + n * 2, 4); data.write("WAVE", 8);
  data.write("fmt ", 12); data.writeUInt32LE(16, 16); data.writeUInt16LE(1, 20);
  data.writeUInt16LE(1, 22); data.writeUInt32LE(rate, 24); data.writeUInt32LE(rate * 2, 28);
  data.writeUInt16LE(2, 32); data.writeUInt16LE(16, 34);
  data.write("data", 36); data.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) {
    data.writeInt16LE(Math.round(12000 * Math.sin(2 * Math.PI * 440 * i / rate)), 44 + i * 2);
  }
  return new Uint8Array(data);
}
const WAV = makeWav();
const AUDIO_SHA = sha256(WAV);
const TRANSCRIPT_SHA = sha256(TRANSCRIPT);

// ------------------------------------------------------------ step harness
const results = [];
async function step(name, fn) {
  try {
    const out = await fn();
    results.push([name, true, ""]);
    console.log("PASS", name);
    return out;
  } catch (e) {
    results.push([name, false, e.message]);
    console.log("FAIL", name, "-", e.message);
    return undefined;
  }
}
function assert(cond, msg) { if (!cond) throw new Error(msg || "assertion failed"); }

async function auditCheck(dir) {
  const { stdout } = await execFileP("python3", [
    path.join(HERE, "audit_check.py"),
    path.join(ROOT, "audit-app", "audit.py"),
    path.join(dir, "submission-audio.wav"),
    path.join(dir, "submission.html"),
    BASE,
  ], { encoding: "utf8" });
  return JSON.parse(stdout.trim().split("\n").pop());
}

async function unzipTo(zipBytes, dir) {
  mkdirSync(dir, { recursive: true });
  const zp = path.join(dir, "..", path.basename(dir) + ".zip");
  writeFileSync(zp, zipBytes);
  await execFileP("python3", ["-c",
    "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])",
    zp, dir]);
}

// ------------------------------------------------------------ the run
let pkgId, pkgHash, jobId, bundle, htmlText, zipBytes;

await step("admin: pkg_admin create (v2 fixture package)", async () => {
  const out = await runNode(pkgAdmin, ["create",
    path.join(ROOT, "webapp", "packages", "grade-distribution-pt1-v2.md")]);
  const rec = JSON.parse(out);
  assert(rec.pkg && rec.content_sha256, "create returned no pkg/hash: " + out);
  assert(rec.status === "draft", "new package is not draft: " + rec.status);
  pkgId = rec.pkg; pkgHash = rec.content_sha256;
});

await step("admin: pkg_admin trial 5/5 then open", async () => {
  const t = JSON.parse(await runNode(pkgAdmin, ["trial", pkgId, "5", "5"]));
  assert(t.status === "trialled", "trial did not move to trialled: " + t.status);
  const o = JSON.parse(await runNode(pkgAdmin, ["open", pkgId]));
  assert(o.status === "open", "package did not open: " + o.status);
});

let ytCheck;
await step("youtube-check through the real Worker (oEmbed stubbed 200)", async () => {
  const res = await realFetch(BASE + "/youtube-check", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ url: WATCH_URL }),
  });
  ytCheck = await res.json();
  assert(res.status === 200, "youtube-check HTTP " + res.status);
  assert(ytCheck.status === "ok" && ytCheck.video_id === VIDEO_ID && ytCheck.token,
    "unexpected check result: " + JSON.stringify(ytCheck));
});

await step("webapp jobs.js builds and validates the practice payload (no link at send)", async () => {
  const payload = jobsMod.buildJobPayload({
    pkg: pkgId, pkgContentSha256: pkgHash, kind: "practice",
    transcript: TRANSCRIPT, audioSha256: AUDIO_SHA, transcriptSha256: TRANSCRIPT_SHA,
    versions: pkgMod.VERSIONS,
    retrievalCode: "e2ecode1234",
  });
  const v = jobsMod.validateJobPayload(payload);
  assert(v.ok, "payload failed webapp validation: " + v.reason);
  assert(!("youtube_video_id" in payload), "practice payload carries youtube fields");
  return payload;
}).then((p) => { step.payload = p; });

await step("POST /jobs through the webapp submitJob (real Worker)", async () => {
  const res = await jobsMod.submitJob(BASE, step.payload);
  assert(res.job_id, "no job_id returned");
  jobId = res.job_id;
});

await step("grade_jobs list shows the job; claim returns transcript + package", async () => {
  const list = JSON.parse(await runNode(gradeJobs, ["list"]));
  assert(list.some((j) => j.job_id === jobId), "job not in pending list");
  const claimFile = path.join(tmp, "claim.json");
  await runNode(gradeJobs, ["claim", jobId, "--out", claimFile]);
  const claim = JSON.parse(readFileSync(claimFile, "utf8"));
  assert(claim.transcript === TRANSCRIPT, "claim transcript differs");
  assert(claim.package && claim.package.content_sha256 === pkgHash, "claim package hash differs");
});

await step("grade_jobs result posts the simulated sub-agent result (4/5, tricky critique)", async () => {
  const rf = path.join(tmp, "result.json");
  writeFileSync(rf, JSON.stringify({
    completeness: 4, accuracy: 5, critique: CRITIQUE, injection_flags: [],
  }));
  const out = JSON.parse(await runNode(gradeJobs, ["result", jobId, rf]));
  assert(out.ok === true && out.receipt, "result not accepted: " + JSON.stringify(out));
});

await step("retrieval via webapp fetchJobStatus returns the signed bundle under `result`", async () => {
  const st = await jobsMod.fetchJobStatus(BASE, {
    pkg: pkgId, retrieval_code: "e2ecode1234",
  });
  assert(st.status === "ready", "job not ready: " + st.status);
  assert(st.data && st.data.result, "status body carries no `result` bundle");
  bundle = st.data.result;
  assert(bundle.completeness === 4 && bundle.accuracy === 5, "bundle grades differ");
  assert(bundle.critique === CRITIQUE, "bundle critique differs from posted critique");
  assert(bundle.pkg_content_sha256 === pkgHash, "bundle pkg hash differs");
  assert(bundle.youtube_video_sha256 === "none", "practice bundle should carry no video hash");
});

await step("finalize via webapp finalizeJob turns the graded job into the submission", async () => {
  const finPayload = { pkg: pkgId, retrieval_code: "e2ecode1234" };
  finPayload["youtube" + "_token"] = ytCheck.token;
  finPayload.youtube_video_id = ytCheck.video_id;
  finPayload.youtube_checked_at = ytCheck.checked_at;
  const out = await jobsMod.finalizeJob(BASE, finPayload);
  assert(out.ok === true && out.receipt, "finalize not accepted: " + JSON.stringify(out));
  const st = await jobsMod.fetchJobStatus(BASE, {
    pkg: pkgId, retrieval_code: "e2ecode1234",
  });
  assert(st.status === "ready" && st.data && st.data.result, "job not ready after finalize");
  bundle = st.data.result;
  const expectHash = sha256(VIDEO_ID);
  assert(bundle.youtube_video_sha256 === expectHash, "finalized bundle lacks the video hash");
  assert(bundle.receipt === out.receipt, "finalized receipt differs from status bundle");
  assert(bundle.completeness === 4 && bundle.accuracy === 5 && bundle.critique === CRITIQUE,
    "finalize changed the grade content");
});

await step("webapp package.js builds submission.html; zip.js builds submission.zip", async () => {
  htmlText = pkgMod.assemblePackage({
    youtubeLink: WATCH_URL, audioFileName: "submission-audio.wav",
    durationS: 67, chunks: CHUNKS, bundle,
  });
  zipBytes = zipMod.buildZipBytes([
    { name: "submission.html", data: enc.encode(htmlText) },
    { name: "submission-audio.wav", data: WAV },
  ]);
  const again = zipMod.buildZipBytes([
    { name: "submission.html", data: enc.encode(htmlText) },
    { name: "submission-audio.wav", data: WAV },
  ]);
  assert(Buffer.from(zipBytes).equals(Buffer.from(again)), "ZIP is not deterministic");
});

await step("audit check_package on the unzipped package: internally_consistent, grade receipt ok", async () => {
  const dir = path.join(tmp, "pkg-good");
  await unzipTo(zipBytes, dir);
  const chk = await auditCheck(dir);
  assert(chk.format_ok === true, "format_ok false: " + JSON.stringify(chk));
  assert(chk.audio_fingerprint_ok === true, "audio check failed: " + JSON.stringify(chk));
  assert(chk.transcript_checksum_ok === true, "transcript check failed: " + JSON.stringify(chk));
  assert(chk.critique_ok === true, "critique check failed: " + JSON.stringify(chk));
  assert(chk.youtube_id_ok === true, "youtube id check failed: " + JSON.stringify(chk));
  assert(chk.grade_receipt_ok === true, "grade receipt failed against the real Worker: " + JSON.stringify(chk));
  assert(chk.internally_consistent === true, "not internally consistent: " + JSON.stringify(chk));
});

await step("tamper (i): completeness span 4→5 fails the grade check", async () => {
  const bad = htmlText.replaceAll(
    '<span data-grade="completeness">4</span>', '<span data-grade="completeness">5</span>');
  assert(bad !== htmlText, "span replacement did not apply");
  const zb = zipMod.buildZipBytes([
    { name: "submission.html", data: enc.encode(bad) },
    { name: "submission-audio.wav", data: WAV },
  ]);
  const dir = path.join(tmp, "pkg-tamper-grade");
  await unzipTo(zb, dir);
  const chk = await auditCheck(dir);
  assert(chk.internally_consistent === false, "tampered grade accepted");
  assert(chk.grade_receipt_ok === false, "grade receipt still verifies with a tampered grade");
  assert(chk.critique_ok === true && chk.audio_fingerprint_ok === true,
    "failure is not isolated to the grade check: " + JSON.stringify(chk));
});

await step("tamper (ii): one critique word changed fails the critique check", async () => {
  const bad = htmlText.replace("argument is exact", "argument is wrong");
  assert(bad !== htmlText, "critique replacement did not apply");
  const zb = zipMod.buildZipBytes([
    { name: "submission.html", data: enc.encode(bad) },
    { name: "submission-audio.wav", data: WAV },
  ]);
  const dir = path.join(tmp, "pkg-tamper-critique");
  await unzipTo(zb, dir);
  const chk = await auditCheck(dir);
  assert(chk.internally_consistent === false, "tampered critique accepted");
  assert(chk.critique_ok === false, "critique hash still matches after a word change");
  assert(chk.grade_receipt_ok === true && chk.audio_fingerprint_ok === true,
    "failure is not isolated to the critique check: " + JSON.stringify(chk));
});

await step("tamper (iii): one WAV byte flipped fails the audio check", async () => {
  const badWav = new Uint8Array(WAV);
  badWav[100] = badWav[100] ^ 0xff;
  const zb = zipMod.buildZipBytes([
    { name: "submission.html", data: enc.encode(htmlText) },
    { name: "submission-audio.wav", data: badWav },
  ]);
  const dir = path.join(tmp, "pkg-tamper-audio");
  await unzipTo(zb, dir);
  const chk = await auditCheck(dir);
  assert(chk.internally_consistent === false, "tampered audio accepted");
  assert(chk.audio_fingerprint_ok === false, "audio fingerprint still matches after a byte flip");
  assert(chk.critique_ok === true && chk.grade_receipt_ok === true,
    "failure is not isolated to the audio check: " + JSON.stringify(chk));
});

// ------------------------------------------------------------ summary
bridge.close();
const failed = results.filter((r) => !r[1]);
console.log("");
console.log("e2e summary: " + (results.length - failed.length) + "/" + results.length + " steps passed");
for (const [name, ok, msg] of results) {
  console.log((ok ? "PASS " : "FAIL ") + name + (ok ? "" : " - " + msg));
}
console.log("work dir: " + tmp);
process.exit(failed.length ? 1 : 0);
