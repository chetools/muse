#!/usr/bin/env node
// Grading helper for keypoints assignments (explain-the-page takes). No
// dependencies (Node 18+).
//   node kpgrade.mjs packet   <server> <sessionCode>
//       Print the grading packet: exam, rubric (one element per key point,
//       named "Point 1", "Point 2", ..., with the key point's text and
//       connection carried in the element guidance), and the sealed audio
//       list. The packet is how the key reaches the grader — after sealing.
//   node kpgrade.mjs audio    <server> <sessionCode> <outDir>
//       Download the sealed audio segments listed in the packet into outDir
//       as slide-<n>.wav, and print a manifest (slide, title, file, sha256).
//       Transcribe these files, never a re-recording or a file handed over
//       in the chat.
//   node kpgrade.mjs key      <server> <sessionCode>
//       Print the structured answer key for this sealed take:
//       {points: [{text, connection, points}], totalPoints}. For grading
//       only — never show it to the student.
//   node kpgrade.mjs submit   <server> <sessionCode> <resultFile>
//       Upload {transcript, critique, grades} from the result file, where
//       the transcript is the corrected transcript made from the sealed
//       audio, the critique is the feedback to the student, and grades maps
//       "Point 1", "Point 2", ... to fractions 0..1. Every upload is
//       archived as an attempt. This flow has no final submission: no
//       "final" flag is ever sent.
//   node kpgrade.mjs standing <server> <sessionCode>
//       Print every attempt's score for this student and the standing
//       (best) grade.
// Exit code 0 on success, 1 on any failure (message on stderr).
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";

const [mode, serverRaw, sessionCode, file] = process.argv.slice(2);
if (!mode || !serverRaw || !sessionCode) {
  console.error("usage: kpgrade.mjs packet|audio|key|standing|submit <server> <sessionCode> [file|dir]");
  process.exit(1);
}
const server = serverRaw.replace(/\/+$/, "");

async function call(path, opts) {
  const res = await fetch(server + path, opts);
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && data.error) || ("HTTP " + res.status));
  return data;
}
const post = (path, body) => call(path, { method: "POST",
  headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const bySession = (path) => path + "?session=" + encodeURIComponent(sessionCode);

try {
  if (mode === "packet") {
    const d = await call(bySession("/t/packet"));
    console.log(JSON.stringify(d, null, 2));
  } else if (mode === "audio") {
    if (!file) { console.error("audio needs an output directory"); process.exit(1); }
    const packet = await call(bySession("/t/packet"));
    if (!packet.audio || !packet.audio.length) {
      console.error("This submission has no sealed audio.");
      process.exit(1);
    }
    mkdirSync(file, { recursive: true });
    const manifest = [];
    for (const seg of packet.audio) {
      const res = await fetch(server + "/t/audio?session=" + encodeURIComponent(sessionCode) + "&slide=" + seg.slide);
      if (!res.ok) { const d = await res.json().catch(() => null); throw new Error((d && d.error) || ("HTTP " + res.status)); }
      const buf = Buffer.from(await res.arrayBuffer());
      const name = "slide-" + seg.slide + ".wav";
      writeFileSync(file.replace(/\/+$/, "") + "/" + name, buf);
      manifest.push({ slide: seg.slide, title: seg.title || "", file: name, bytes: buf.length, sha256: seg.sha256 });
    }
    console.log(JSON.stringify({ audioFingerprint: packet.audioFingerprint, segments: manifest }, null, 2));
  } else if (mode === "key") {
    const d = await call(bySession("/k/key-session"));
    console.log(JSON.stringify(d, null, 2));
  } else if (mode === "standing") {
    const d = await call(bySession("/k/standing"));
    console.log(JSON.stringify(d, null, 2));
  } else if (mode === "submit") {
    if (!file) { console.error("submit needs a result file"); process.exit(1); }
    const result = JSON.parse(readFileSync(file, "utf8"));
    if (typeof result.transcript !== "string" || !result.transcript.trim()) {
      console.error('The result file must carry "transcript": the corrected transcript made from the sealed audio.');
      process.exit(1);
    }
    if (!result.critique || typeof result.grades !== "object" || result.grades === null) {
      console.error('The result file must be {"transcript": "...", "critique": "...", "grades": {"Point 1": 1, "Point 2": 0.5}}');
      process.exit(1);
    }
    const d = await post("/t/critique", { sessionCode, transcript: result.transcript,
      critique: result.critique, grades: result.grades });
    console.log(JSON.stringify(d));
  } else {
    console.error("unknown mode: " + mode);
    process.exit(1);
  }
} catch (e) {
  console.error(String(e && e.message || e));
  process.exit(1);
}
