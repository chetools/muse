#!/usr/bin/env node
// Tests for scripts/watch.mjs against a local stub of the course server's
// /w/poll and /w/pending endpoints. No dependencies (Node 18+).
//   node tests/watch-skill-test.mjs
// The test writes a temporary watch-config.json into the skill folder
// (restoring any real one afterwards) pointing at the stub, then runs the
// helper as a child process, as the skill's procedures do.
// Exit code 0 when every check passes, 1 otherwise.
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, rmSync, existsSync } from "node:fs";

const skillDir = new URL("../", import.meta.url);
const configUrl = new URL("watch-config.json", skillDir);
const watchUrl = new URL("scripts/watch.mjs", skillDir);

const TAKES = [
  { examId: "exam-1", title: "Rachford-Rice page", sessionCode: "SEAL-AAA",
    status: "audio_sealed", sealedAt: "2026-11-06T11:00:00Z" },
  { examId: "exam-2", title: "Ponchon-Savarit page", sessionCode: "SEAL-BBB",
    status: "sealed", sealedAt: "2026-11-06T11:05:00Z" },
];

const stub = createServer((req, res) => {
  const json = (code, obj) => {
    res.writeHead(code, { "Content-Type": "application/json" });
    res.end(JSON.stringify(obj));
  };
  if (req.url === "/w/poll") {
    if (req.headers["x-poll-key"] !== "test-poll-key") return json(401, { error: "Bad poll key." });
    return json(200, { pending: TAKES.length });
  }
  if (req.url === "/w/pending") {
    if (req.headers["x-watch-token"] !== "test-token") return json(401, { error: "Bad watch token." });
    return json(200, { takes: TAKES });
  }
  return json(404, { error: "No such route." });
});
await new Promise((resolve) => stub.listen(0, "127.0.0.1", resolve));
const server = "http://127.0.0.1:" + stub.address().port;

let passed = 0, failed = 0;
function check(name, ok, detail) {
  if (ok) { passed++; console.log("PASS  " + name); }
  else { failed++; console.log("FAIL  " + name + (detail ? " — " + detail : "")); }
}
// Async spawn, never spawnSync: the stub server lives in this same process,
// so blocking its event loop would deadlock the child's fetch.
function runWatch(mode) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [watchUrl.pathname, mode], { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "", stderr = "";
    child.stdout.on("data", (d) => { stdout += d; });
    child.stderr.on("data", (d) => { stderr += d; });
    child.on("error", (e) => resolve({ status: 1, stdout, stderr: stderr + String(e) }));
    child.on("close", (code) => resolve({ status: code === null ? 1 : code, stdout, stderr }));
  });
}
function writeConfig(obj) {
  if (obj === null) rmSync(configUrl, { force: true });
  else writeFileSync(configUrl, JSON.stringify(obj));
}

const hadConfig = existsSync(configUrl);
const savedConfig = hadConfig ? readFileSync(configUrl) : null;
try {
  writeConfig({ server, token: "test-token", pollKey: "test-poll-key" });

  const poll = await runWatch("poll");
  check("poll exits 0", poll.status === 0, poll.stderr);
  let pollData = null;
  try { pollData = JSON.parse(poll.stdout); } catch { /* counted below */ }
  check("poll prints the stub's pending count", !!pollData && pollData.pending === 2,
    "stdout: " + poll.stdout);

  const pending = await runWatch("pending");
  check("pending exits 0", pending.status === 0, pending.stderr);
  let pendingData = null;
  try { pendingData = JSON.parse(pending.stdout); } catch { /* counted below */ }
  check("pending prints the takes list", !!pendingData && Array.isArray(pendingData.takes) &&
    pendingData.takes.length === 2, "stdout: " + pending.stdout);
  check("pending takes carry session codes and statuses", !!pendingData &&
    pendingData.takes[0].sessionCode === "SEAL-AAA" && pendingData.takes[0].status === "audio_sealed" &&
    pendingData.takes[1].sessionCode === "SEAL-BBB" && pendingData.takes[1].status === "sealed");

  writeConfig({ server, token: "wrong-token", pollKey: "wrong-key" });
  const badPoll = await runWatch("poll");
  check("poll exits non-zero on a 401 stub", badPoll.status !== 0, "exit: " + badPoll.status);
  const badPending = await runWatch("pending");
  check("pending exits non-zero on a 401 stub", badPending.status !== 0, "exit: " + badPending.status);
  check("401 message names the revocation plainly", /revoked or regenerated/.test(badPending.stderr),
    "stderr: " + badPending.stderr);

  writeConfig(null);
  const noConfig = await runWatch("pending");
  check("missing config exits non-zero", noConfig.status !== 0, "exit: " + noConfig.status);
  check("missing config message names watch-config.json", /watch-config\.json is missing/.test(noConfig.stderr),
    "stderr: " + noConfig.stderr);
} finally {
  if (hadConfig) writeFileSync(configUrl, savedConfig);
  else rmSync(configUrl, { force: true });
  stub.close();
}

console.log(passed + " passed, " + failed + " failed");
process.exit(failed ? 1 : 0);
