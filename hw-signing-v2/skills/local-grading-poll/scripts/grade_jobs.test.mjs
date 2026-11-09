#!/usr/bin/env node
// Tests for scripts/grade_jobs.mjs against a local stub of the grading
// worker's /grading endpoints. No dependencies (Node 18+).
//   node scripts/grade_jobs.test.mjs
// The test writes a temporary config.json into the skill folder
// (restoring any real one afterwards) pointing at the stub, then runs
// the helper as a child process, as the skill's procedures do.
// Exit code 0 when every check passes, 1 otherwise.
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import {
  readFileSync,
  writeFileSync,
  rmSync,
  existsSync,
  mkdtempSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const skillDir = new URL("../", import.meta.url);
const configUrl = new URL("config.json", skillDir);
const scriptUrl = new URL("scripts/grade_jobs.mjs", skillDir);
const TOKEN = "test-grading-token-9c41";

const CLAIM = {
  job_id: "job-1",
  kind: "final",
  transcript: "[0:00 - 0:25] The widget flows because...",
  audio_sha256: "a".repeat(64),
  transcript_sha256: "b".repeat(64),
  versions: { webapp: "hw-signing-webapp 2.0.0", model: "m", glossary: "g" },
  package: {
    pkg: "widget-flow v1",
    text: "# Prompt package (pkg: widget-flow v1)\n...",
    content_sha256: "c".repeat(64),
  },
};
const PENDING = [
  {
    job_id: "job-1",
    pkg: "widget-flow v1",
    kind: "final",
    created_at: "2026-11-09T10:00:00Z",
    transcript_chars: 4200,
  },
  {
    job_id: "job-2",
    pkg: "widget-flow v1",
    kind: "practice",
    created_at: "2026-11-09T10:01:00Z",
    transcript_chars: 3100,
  },
];

let resultBody = null;
const seenUrls = [];
const stub = createServer((req, res) => {
  seenUrls.push(req.url);
  const json = (code, obj) => {
    res.writeHead(code, { "Content-Type": "application/json" });
    res.end(JSON.stringify(obj));
  };
  if (req.headers["x-grading-token"] !== TOKEN) {
    return json(401, { error: "bad grading token" });
  }
  let body = "";
  req.on("data", (d) => (body += d));
  req.on("end", () => {
    const data = body ? JSON.parse(body) : {};
    if (req.method === "GET" && req.url === "/grading/pending") {
      return json(200, PENDING);
    }
    if (req.method === "POST" && req.url === "/grading/claim") {
      if (data.job_id === "job-1") return json(200, CLAIM);
      if (data.job_id === "job-2") {
        return json(409, { error: "job already claimed" });
      }
      return json(404, { error: "no such job" });
    }
    if (req.method === "POST" && req.url === "/grading/result") {
      resultBody = data;
      return json(200, { ok: true, receipt: "stub-receipt" });
    }
    return json(404, { error: "no such route" });
  });
});
await new Promise((resolve) => stub.listen(0, "127.0.0.1", resolve));
const worker = "http://127.0.0.1:" + stub.address().port;

let passed = 0,
  failed = 0;
function check(name, ok, detail) {
  if (ok) {
    passed++;
    console.log("PASS  " + name);
  } else {
    failed++;
    console.log("FAIL  " + name + (detail ? " — " + detail : ""));
  }
}
const allOutput = [];
function run(args) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [scriptUrl.pathname, ...args], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "",
      stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("error", (e) =>
      resolve({ status: 1, stdout, stderr: stderr + String(e) }),
    );
    child.on("close", (code) => {
      allOutput.push(stdout, stderr);
      resolve({ status: code === null ? 1 : code, stdout, stderr });
    });
  });
}

const savedConfig = existsSync(configUrl)
  ? readFileSync(configUrl, "utf8")
  : null;
writeFileSync(
  configUrl,
  JSON.stringify({ worker, gradingToken: TOKEN }) + "\n",
  "utf8",
);
const work = mkdtempSync(join(tmpdir(), "grade-jobs-test-"));

try {
  // list.
  let r = await run(["list"]);
  check("list exits 0", r.status === 0, r.stderr);
  const pending = JSON.parse(r.stdout);
  check(
    "list returns both pending jobs",
    Array.isArray(pending) &&
      pending.length === 2 &&
      pending[0].job_id === "job-1" &&
      pending[0].pkg === "widget-flow v1",
    r.stdout,
  );

  // claim round trip: claim JSON lands in the --out file.
  const claimFile = join(work, "claim-job-1.json");
  r = await run(["claim", "job-1", "--out", claimFile]);
  check("claim exits 0", r.status === 0, r.stderr);
  const claimOnDisk = JSON.parse(readFileSync(claimFile, "utf8"));
  check(
    "claim file holds the package text and transcript",
    claimOnDisk.job_id === "job-1" &&
      claimOnDisk.transcript === CLAIM.transcript &&
      claimOnDisk.package.text === CLAIM.package.text &&
      claimOnDisk.package.content_sha256 === CLAIM.package.content_sha256,
  );
  check(
    "claim stdout is a summary without the transcript",
    !r.stdout.includes("widget flows"),
    r.stdout,
  );

  // 409: another claim holds job-2.
  const claim2 = join(work, "claim-job-2.json");
  r = await run(["claim", "job-2", "--out", claim2]);
  check("claim on a held job exits non-zero", r.status !== 0);
  check(
    "409 is reported as an existing claim",
    /already claimed/.test(r.stderr),
    r.stderr,
  );
  check("no claim file is written on a 409", !existsSync(claim2));

  // result round trip: the file's fields plus the job_id reach the stub.
  const resultFile = join(work, "result-job-1.json");
  writeFileSync(
    resultFile,
    JSON.stringify({
      completeness: 5,
      accuracy: 4,
      critique: "Complete on counting; one sign error in the Stirling step.",
      injection_flags: [{ pattern: "ignore instructions", at: "[03:12]" }],
    }),
    "utf8",
  );
  r = await run(["result", "job-1", resultFile]);
  check("result exits 0", r.status === 0, r.stderr);
  check(
    "worker answer is printed",
    JSON.parse(r.stdout).receipt === "stub-receipt",
    r.stdout,
  );
  check(
    "result body carries job_id and the structured fields",
    resultBody &&
      resultBody.job_id === "job-1" &&
      resultBody.completeness === 5 &&
      resultBody.accuracy === 4 &&
      resultBody.critique.startsWith("Complete on counting") &&
      Array.isArray(resultBody.injection_flags) &&
      resultBody.injection_flags[0].at === "[03:12]",
    JSON.stringify(resultBody),
  );

  // token hygiene.
  check(
    "grading token never appears in any output",
    !allOutput.join("").includes(TOKEN),
  );
  check(
    "grading token never appears in a requested URL",
    !seenUrls.some((u) => u.includes(TOKEN)),
  );
} finally {
  if (savedConfig === null) rmSync(configUrl, { force: true });
  else writeFileSync(configUrl, savedConfig, "utf8");
  rmSync(work, { recursive: true, force: true });
  stub.close();
}

console.log("\n" + passed + " passed, " + failed + " failed");
process.exit(failed ? 1 : 0);
