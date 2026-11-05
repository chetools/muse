#!/usr/bin/env node
// Teacher helper for keypoints assignments. No dependencies (Node 18+).
//   node kp.mjs page         <server> <examId> <pageFile> <latexFile> <photos>
//       Upload the assignment page: the HTML fragment in pageFile, the LaTeX
//       source in latexFile, and the number of photographs the page combines.
//   node kp.mjs model-roster <server> <examId> <email> <name>
//       Enrol an email on the exam roster with the model-take role.
//   node kp.mjs model        <server> <examId>
//       Print the model take's record, including its sealed session code.
//   node kp.mjs audio        <server> <sessionCode> <outDir>
//       Download the sealed audio segments of a take into outDir as
//       slide-<n>.wav, and print a manifest (slide, title, file, sha256).
//   node kp.mjs key          <server> <examId> <keyFile>
//       Upload the approved answer key. keyFile is JSON:
//       {"points": [{"text": "...", "connection": "...", "points": 20}, ...]}
//       (a {"key": {"points": [...]}} file is also accepted). Uploading the
//       key is what opens the assignment to students.
// The page, model-roster, model and key commands are credentialed by the
// exam's audit token, taken from the environment variable KP_AUDIT_TOKEN.
// The token is never printed and never written to a file.
// Exit code 0 on success, 1 on any failure (message on stderr).
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";

const [mode, serverRaw, a, b, c, d] = process.argv.slice(2);
const MODES = ["page", "model-roster", "model", "audio", "key"];
if (!mode || !MODES.includes(mode) || !serverRaw || !a) {
  console.error("usage: kp.mjs page|model-roster|model|audio|key <server> <examId|sessionCode> [args]");
  process.exit(1);
}
const server = serverRaw.replace(/\/+$/, "");

function auditToken() {
  const t = process.env.KP_AUDIT_TOKEN || "";
  if (!t) {
    console.error("KP_AUDIT_TOKEN is not set. Set it to this exam's audit token in the command's environment (the token is never written to a file).");
    process.exit(1);
  }
  return t;
}

async function call(path, opts) {
  const res = await fetch(server + path, opts);
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && data.error) || ("HTTP " + res.status));
  return data;
}
const postAudit = (path, body) => call(path, { method: "POST",
  headers: { "Content-Type": "application/json", "X-Audit-Token": auditToken() },
  body: JSON.stringify(body) });
const getAudit = (path) => call(path, { headers: { "X-Audit-Token": auditToken() } });

try {
  if (mode === "page") {
    if (!b || !c || d === undefined) { console.error("page needs <pageFile> <latexFile> <photos>"); process.exit(1); }
    const pageHtml = readFileSync(b, "utf8");
    const latex = readFileSync(c, "utf8");
    const photos = Number(d);
    if (!Number.isInteger(photos) || photos < 0) { console.error("<photos> must be a non-negative integer (the number of photographs the page combines)"); process.exit(1); }
    const out = await postAudit("/k/page", { examId: a, pageHtml, latex, photos });
    console.log(JSON.stringify(out));
  } else if (mode === "model-roster") {
    if (!b) { console.error("model-roster needs <email> <name>"); process.exit(1); }
    const out = await postAudit("/k/model-roster", { examId: a, email: b, name: c || "Model take" });
    console.log(JSON.stringify(out));
  } else if (mode === "model") {
    const out = await getAudit("/k/model?exam=" + encodeURIComponent(a));
    console.log(JSON.stringify(out, null, 2));
  } else if (mode === "audio") {
    if (!b) { console.error("audio needs an output directory"); process.exit(1); }
    const packet = await call("/t/packet?session=" + encodeURIComponent(a));
    if (!packet.audio || !packet.audio.length) {
      console.error("This take has no sealed audio.");
      process.exit(1);
    }
    mkdirSync(b, { recursive: true });
    const manifest = [];
    for (const seg of packet.audio) {
      const res = await fetch(server + "/t/audio?session=" + encodeURIComponent(a) + "&slide=" + seg.slide);
      if (!res.ok) { const dd = await res.json().catch(() => null); throw new Error((dd && dd.error) || ("HTTP " + res.status)); }
      const buf = Buffer.from(await res.arrayBuffer());
      const name = "slide-" + seg.slide + ".wav";
      writeFileSync(b.replace(/\/+$/, "") + "/" + name, buf);
      manifest.push({ slide: seg.slide, title: seg.title || "", file: name, bytes: buf.length, sha256: seg.sha256 });
    }
    console.log(JSON.stringify({ audioFingerprint: packet.audioFingerprint, segments: manifest }, null, 2));
  } else if (mode === "key") {
    if (!b) { console.error("key needs a key file"); process.exit(1); }
    const parsed = JSON.parse(readFileSync(b, "utf8"));
    const points = Array.isArray(parsed.points) ? parsed.points
      : (parsed.key && Array.isArray(parsed.key.points) ? parsed.key.points : null);
    if (!points || !points.length) {
      console.error('The key file must be {"points": [{"text": "...", "connection": "...", "points": 20}, ...]}');
      process.exit(1);
    }
    const out = await postAudit("/k/key", { examId: a, key: { points } });
    console.log(JSON.stringify(out));
  }
} catch (e) {
  console.error(String(e && e.message || e));
  process.exit(1);
}
