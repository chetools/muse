#!/usr/bin/env node
// Prompt-package administration for the HW Signing v2 grading worker.
// No dependencies (Node 18+).
//
//   node pkg_admin.mjs create <package-file>
//       Upload an approved package file as a new draft version. The
//       package name comes from the file's header line,
//       "# Prompt package (pkg: <name>)"; the Worker assigns the version
//       and the content SHA-256. Prints the Worker's record as JSON.
//   node pkg_admin.mjs list
//       Print every package version's metadata (no text) as JSON.
//   node pkg_admin.mjs show <pkg>
//       Print the full record of one version ("<name> v<version>"),
//       including its text, as JSON.
//   node pkg_admin.mjs trial <pkg> <completeness> <accuracy> [override-reason]
//       Record a trial result and move draft -> trialled. The Worker
//       enforces the gate: a trial below 5/5 and 5/5 is refused unless
//       an override reason is given here; the reason is stored on the
//       package.
//   node pkg_admin.mjs open <pkg> | close <pkg> | retire <pkg>
//       Move a package along its lifecycle (trialled -> open,
//       open -> closed, closed -> retired; draft -> retired allowed).
//   node pkg_admin.mjs link <pkg> <course> <asg> <page-base-url>
//       Print the student link for an open package:
//       <page-base-url>?w=<worker>&pkg=<pkg>&ph=<content sha-256>
//       &course=<course>&asg=<asg>, after verifying it: the link is
//       parsed back and every parameter recovered, and the package
//       record is fetched again to confirm status "open" and the hash.
//       Only the link is printed.
//
// Credentials come from config.json in the skill folder (one level up
// from this script): {worker, adminToken}. The token is sent only as
// the X-Admin-Token header to the configured worker; it is never
// printed, logged, or placed in a URL.
// Exit code 0 on success, 1 on any failure (message on stderr).
import { readFileSync } from "node:fs";

const USAGE =
  "usage: pkg_admin.mjs create <package-file> | list | show <pkg> | " +
  "trial <pkg> <completeness> <accuracy> [override-reason] | " +
  "open <pkg> | close <pkg> | retire <pkg> | " +
  "link <pkg> <course> <asg> <page-base-url>";

const cmd = process.argv[2];
const rest = process.argv.slice(3);

function fail(msg) {
  console.error(msg);
  process.exit(1);
}
if (!cmd) fail(USAGE);

let config;
try {
  config = JSON.parse(
    readFileSync(new URL("../config.json", import.meta.url), "utf8"),
  );
} catch {
  fail(
    "config.json is missing or unreadable in the skill folder. " +
      "Copy config.example.json to config.json and fill in the worker " +
      "address and the admin token.",
  );
}
const worker = String(config.worker || "").replace(/\/+$/, "");
const token = config.adminToken;
if (!worker || !token) {
  fail(
    'config.json is incomplete: it needs "worker" and "adminToken". ' +
      "Run the setup in this skill's SKILL.md again.",
  );
}

async function call(method, path, body) {
  let res;
  try {
    res = await fetch(worker + path, {
      method,
      headers: {
        "X-Admin-Token": token,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    fail("Could not reach the grading worker: " + e.message);
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    fail(
      "The grading worker refused the request (HTTP " + res.status + ")" +
        (data && data.error ? ": " + data.error : "") +
        ".",
    );
  }
  return data;
}

const pkgPath = (pkg) => "/admin/packages/" + encodeURIComponent(pkg);

function printJson(data) {
  console.log(JSON.stringify(data, null, 2));
}

if (cmd === "create") {
  const file = rest[0];
  if (!file) fail(USAGE);
  let text;
  try {
    text = readFileSync(file, "utf8");
  } catch {
    fail("Cannot read the package file: " + file);
  }
  // The package name comes from the header line,
  // "# Prompt package (pkg: <name>)". The Worker assigns the version, so
  // only the name is taken; a trailing version in a copied header is
  // ignored.
  const head = text.split("\n").slice(0, 10).join("\n");
  const m = head.match(/pkg:\s*([A-Za-z0-9][A-Za-z0-9-]*)/);
  if (!m) {
    fail(
      "No package name found in the file's header. The first lines must " +
        'carry a header of the form "# Prompt package (pkg: <name>)".',
    );
  }
  printJson(await call("POST", "/admin/packages", { pkg_name: m[1], text }));
} else if (cmd === "list") {
  printJson(await call("GET", "/admin/packages"));
} else if (cmd === "show") {
  if (!rest[0]) fail(USAGE);
  printJson(await call("GET", pkgPath(rest[0])));
} else if (cmd === "trial") {
  const [pkg, cRaw, aRaw, ...reasonParts] = rest;
  const completeness = Number(cRaw);
  const accuracy = Number(aRaw);
  if (
    !pkg ||
    !Number.isInteger(completeness) ||
    !Number.isInteger(accuracy) ||
    completeness < 0 ||
    completeness > 5 ||
    accuracy < 0 ||
    accuracy > 5
  ) {
    fail(
      "trial needs a package and two whole-number scores from 0 to 5: " +
        "trial <pkg> <completeness> <accuracy> [override-reason]",
    );
  }
  const body = {
    status: "trialled",
    trial: { completeness, accuracy },
  };
  const reason = reasonParts.join(" ").trim();
  if (reason) body.override_reason = reason;
  printJson(await call("POST", pkgPath(pkg) + "/status", body));
} else if (cmd === "open" || cmd === "close" || cmd === "retire") {
  if (!rest[0]) fail(USAGE);
  const status =
    cmd === "open" ? "open" : cmd === "close" ? "closed" : "retired";
  printJson(await call("POST", pkgPath(rest[0]) + "/status", { status }));
} else if (cmd === "link") {
  const [pkg, course, asg, pageBase] = rest;
  if (!pkg || !course || !asg || !pageBase) fail(USAGE);
  const rec = await call("GET", pkgPath(pkg));
  if (rec.status !== "open") {
    fail(
      'Package "' + pkg + '" is not open (status: ' + rec.status + "). " +
        "A student link is issued only for an open package.",
    );
  }
  if (!rec.content_sha256) {
    fail("The worker's record for \"" + pkg + '" carries no content hash.');
  }
  const params = new URLSearchParams({
    w: worker,
    pkg,
    ph: rec.content_sha256,
    course,
    asg,
  });
  const link = pageBase + "?" + params.toString();
  // Verify before printing: parse the link back and recover every
  // parameter, and confirm the record's status and hash once more.
  let parsed;
  try {
    parsed = new URL(link);
  } catch {
    fail("The built link does not parse as a URL; nothing was printed.");
  }
  const got = Object.fromEntries(
    ["w", "pkg", "ph", "course", "asg"].map((k) => [
      k,
      parsed.searchParams.get(k),
    ]),
  );
  const want = {
    w: worker,
    pkg,
    ph: rec.content_sha256,
    course,
    asg,
  };
  for (const k of Object.keys(want)) {
    if (got[k] !== want[k]) {
      fail(
        "Link verification failed: parameter " + k + " did not round-trip. " +
          "Nothing was printed.",
      );
    }
  }
  const confirm = await call("GET", pkgPath(pkg));
  if (confirm.status !== "open" || confirm.content_sha256 !== want.ph) {
    fail(
      "Link verification failed: the worker no longer reports \"" + pkg +
        '" as open with the same content hash. Nothing was printed.',
    );
  }
  console.log(link);
} else {
  fail(USAGE);
}
