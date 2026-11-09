#!/usr/bin/env node
// Tests for scripts/pkg_admin.mjs against a local stub of the grading
// worker's /admin/packages endpoints, implementing the SPEC's
// transitions minimally (draft -> trialled gated on a 5/5 + 5/5 trial
// or an override reason; trialled -> open; open -> closed; closed or
// draft -> retired; identical text under one name rejected).
// No dependencies (Node 18+).
//   node scripts/pkg_admin.test.mjs
// The test writes a temporary config.json into the skill folder
// (restoring any real one afterwards) pointing at the stub, then runs
// the helper as a child process, as the skill's procedures do.
// Exit code 0 when every check passes, 1 otherwise.
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
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
const scriptUrl = new URL("scripts/pkg_admin.mjs", skillDir);
const TOKEN = "test-admin-token-7f3a";

const sha256 = (s) => createHash("sha256").update(s, "utf8").digest("hex");

// ---- stub worker -----------------------------------------------------
const store = new Map(); // pkg identifier -> record
const seenUrls = [];
const stub = createServer((req, res) => {
  seenUrls.push(req.url);
  const json = (code, obj) => {
    res.writeHead(code, { "Content-Type": "application/json" });
    res.end(JSON.stringify(obj));
  };
  if (req.headers["x-admin-token"] !== TOKEN) {
    return json(401, { error: "bad admin token" });
  }
  let body = "";
  req.on("data", (d) => (body += d));
  req.on("end", () => {
    const data = body ? JSON.parse(body) : {};
    const url = new URL(req.url, "http://stub");
    const parts = url.pathname.split("/").filter(Boolean); // admin/packages[/<pkg>[/status]]
    if (req.method === "POST" && url.pathname === "/admin/packages") {
      const { pkg_name, text } = data;
      const versions = [...store.values()].filter((r) => r.name === pkg_name);
      if (versions.some((r) => r.text === text)) {
        return json(400, { error: "identical text already stored" });
      }
      const version = versions.length
        ? Math.max(...versions.map((r) => r.version)) + 1
        : 1;
      const rec = {
        pkg: pkg_name + " v" + version,
        name: pkg_name,
        version,
        text,
        content_sha256: sha256(text),
        status: "draft",
        trial_json: null,
        override_reason: null,
        created_at: "2026-11-09T00:00:00Z",
      };
      store.set(rec.pkg, rec);
      return json(200, {
        pkg: rec.pkg,
        version,
        content_sha256: rec.content_sha256,
        status: "draft",
      });
    }
    if (req.method === "GET" && url.pathname === "/admin/packages") {
      return json(
        200,
        [...store.values()].map((r) => ({
          pkg: r.pkg,
          version: r.version,
          content_sha256: r.content_sha256,
          status: r.status,
          trial: r.trial_json
            ? {
                completeness: r.trial_json.completeness,
                accuracy: r.trial_json.accuracy,
              }
            : null,
          jobs: 0,
          created_at: r.created_at,
        })),
      );
    }
    if (parts.length >= 3 && parts[0] === "admin" && parts[1] === "packages") {
      const rec = store.get(decodeURIComponent(parts[2]));
      if (!rec) return json(404, { error: "no such package" });
      if (req.method === "GET" && parts.length === 3) {
        return json(200, {
          pkg: rec.pkg,
          version: rec.version,
          content_sha256: rec.content_sha256,
          status: rec.status,
          trial_json: rec.trial_json,
          override_reason: rec.override_reason,
          created_at: rec.created_at,
          text: rec.text,
        });
      }
      if (
        req.method === "POST" &&
        parts.length === 4 &&
        parts[3] === "status"
      ) {
        const to = data.status;
        const legal = {
          draft: ["trialled", "retired"],
          trialled: ["open"],
          open: ["closed"],
          closed: ["retired"],
          retired: [],
        }[rec.status];
        if (!legal.includes(to)) {
          return json(
            400,
            { error: "illegal transition " + rec.status + " -> " + to },
          );
        }
        if (to === "trialled") {
          const t = data.trial;
          if (!t) return json(400, { error: "trial result required" });
          const perfect = t.completeness === 5 && t.accuracy === 5;
          if (!perfect && !data.override_reason) {
            return json(400, {
              error:
                "trial below 5/5 and 5/5 requires a teacher override reason",
            });
          }
          rec.trial_json = t;
          rec.override_reason = data.override_reason || null;
        }
        rec.status = to;
        return json(200, { pkg: rec.pkg, status: rec.status });
      }
    }
    return json(404, { error: "no such route" });
  });
});
await new Promise((resolve) => stub.listen(0, "127.0.0.1", resolve));
const worker = "http://127.0.0.1:" + stub.address().port;

// ---- harness ----------------------------------------------------------
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
  JSON.stringify({ worker, adminToken: TOKEN }) + "\n",
  "utf8",
);

const work = mkdtempSync(join(tmpdir(), "pkg-admin-test-"));
const pkgText =
  "# Prompt package (pkg: widget-flow v1)\n\nStatus: test fixture.\n\n" +
  "## Homework description\n\nExplain the widget.\n\n" +
  "## Lecture transcript portions\n\nWidgets flow.\n\n" +
  "## Grading basis\n\nHolistic.\n";
const pkgFile = join(work, "widget-flow.md");
writeFileSync(pkgFile, pkgText, "utf8");
const pkgText2 = pkgText.replace("widget-flow v1", "gadget-flow v1");
const pkgFile2 = join(work, "gadget-flow.md");
writeFileSync(pkgFile2, pkgText2, "utf8");

try {
  // create: name parsed from the header line (version ignored), draft.
  let r = await run(["create", pkgFile]);
  check("create exits 0", r.status === 0, r.stderr);
  let rec = JSON.parse(r.stdout);
  check(
    "create returns server-assigned pkg id and hash",
    rec.pkg === "widget-flow v1" &&
      rec.status === "draft" &&
      rec.content_sha256 === sha256(pkgText),
    r.stdout,
  );

  // identical text under the same name is refused.
  r = await run(["create", pkgFile]);
  check("duplicate create exits non-zero", r.status !== 0);

  // list: metadata only.
  r = await run(["list"]);
  const list = JSON.parse(r.stdout);
  check(
    "list shows the draft without its text",
    Array.isArray(list) &&
      list.length === 1 &&
      list[0].pkg === "widget-flow v1" &&
      !("text" in list[0]),
    r.stdout,
  );

  // show: full record with text.
  r = await run(["show", "widget-flow v1"]);
  rec = JSON.parse(r.stdout);
  check("show returns the full text", rec.text === pkgText);

  // trial gate: 4/5 without an override reason is refused...
  r = await run(["trial", "widget-flow v1", "4", "5"]);
  check("trial 4/5 without override exits non-zero", r.status !== 0);
  r = await run(["show", "widget-flow v1"]);
  check(
    "package stays draft after refused trial",
    JSON.parse(r.stdout).status === "draft",
  );

  // ...and accepted with one, the reason stored.
  r = await run([
    "trial",
    "widget-flow v1",
    "4",
    "5",
    "Part 2 derivation is beyond the lecture by design.",
  ]);
  check("trial 4/5 with override exits 0", r.status === 0, r.stderr);
  r = await run(["show", "widget-flow v1"]);
  rec = JSON.parse(r.stdout);
  check(
    "override reason and trial are recorded",
    rec.status === "trialled" &&
      rec.override_reason ===
        "Part 2 derivation is beyond the lecture by design." &&
      rec.trial_json.completeness === 4,
    r.stdout,
  );

  // a perfect trial needs no override (second package).
  await run(["create", pkgFile2]);
  r = await run(["trial", "gadget-flow v1", "5", "5"]);
  check("trial 5/5 without override exits 0", r.status === 0, r.stderr);

  // open, then link.
  r = await run(["open", "widget-flow v1"]);
  check("open exits 0", r.status === 0, r.stderr);
  const pageBase = "https://chetools.github.io/muse/hw-signing/";
  r = await run([
    "link",
    "widget-flow v1",
    "CHE1234",
    "HW1",
    pageBase,
  ]);
  check("link exits 0", r.status === 0, r.stderr);
  const linkLine = r.stdout.trim();
  const u = new URL(linkLine);
  check(
    "link parses back with every parameter",
    linkLine.split("\n").length === 1 &&
      u.origin + u.pathname === pageBase &&
      u.searchParams.get("w") === worker &&
      u.searchParams.get("pkg") === "widget-flow v1" &&
      u.searchParams.get("ph") === sha256(pkgText) &&
      u.searchParams.get("course") === "CHE1234" &&
      u.searchParams.get("asg") === "HW1",
    linkLine,
  );

  // close, then link is refused; retire from closed.
  r = await run(["close", "widget-flow v1"]);
  check("close exits 0", r.status === 0, r.stderr);
  r = await run(["link", "widget-flow v1", "CHE1234", "HW1", pageBase]);
  check("link for a closed package exits non-zero", r.status !== 0);
  r = await run(["retire", "widget-flow v1"]);
  check("retire exits 0", r.status === 0, r.stderr);
  r = await run(["show", "widget-flow v1"]);
  check(
    "package is retired",
    JSON.parse(r.stdout).status === "retired",
  );

  // token hygiene.
  check(
    "admin token never appears in any output",
    !allOutput.join("").includes(TOKEN),
  );
  check(
    "admin token never appears in a requested URL",
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
