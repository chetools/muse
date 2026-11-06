#!/usr/bin/env node
// Grading helper for sealed transcript exams. No dependencies (Node 18+).
//   node grade.mjs packet  <server> <sessionCode>
//       Print the grading packet: exam prompt, rubric, the sealed transcript
//       (text-sealed takes) or the sealed audio list (audio-sealed takes).
//   node grade.mjs audio   <server> <sessionCode> <outDir>
//       Download the sealed audio segments listed in the packet into outDir
//       as slide-<n>.wav, and print a manifest (slide, title, file, sha256).
//       For audio-sealed takes: transcribe these files, never a re-recording.
//   node grade.mjs verify  <server> <sessionCode> <transcriptFile>
//       Check a transcript file against the sealed master copy on the server.
//       Text-sealed takes only (audio takes have no master text to compare).
//   node grade.mjs submit  <server> <sessionCode> <resultFile>
//       Upload {critique, grades} — plus {transcript} for audio-sealed takes,
//       where the transcript is the one made from the downloaded sealed audio.
//       Add "final": true when the student marks this attempt as their final
//       submission; practice attempts (the default) are unlimited.
//       For text-sealed takes the transcript is fetched from the server at
//       submit time, so what is graded is always the sealed text.
// Exit code 0 on success, 1 on any failure (message on stderr).
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";

const [mode, serverRaw, sessionCode, file] = process.argv.slice(2);
if (!mode || !serverRaw || !sessionCode) {
  console.error("usage: grade.mjs packet|audio|verify|submit <server> <sessionCode> [file|dir]");
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

try {
  if (mode === "packet") {
    const d = await call("/t/packet?session=" + encodeURIComponent(sessionCode));
    console.log(JSON.stringify(d, null, 2));
  } else if (mode === "audio") {
    if (!file) { console.error("audio needs an output directory"); process.exit(1); }
    const packet = await call("/t/packet?session=" + encodeURIComponent(sessionCode));
    if (!packet.audio || !packet.audio.length) {
      console.error("This submission has no sealed audio (it is a text-sealed take; use the packet transcript).");
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
  } else if (mode === "verify") {
    if (!file) { console.error("verify needs a transcript file"); process.exit(1); }
    const transcript = readFileSync(file, "utf8");
    const d = await post("/t/verify", { sessionCode, transcript });
    console.log(JSON.stringify(d));
    if (!d.match) { console.error("The transcript does not match the sealed master copy."); process.exit(1); }
  } else if (mode === "submit") {
    if (!file) { console.error("submit needs a result file"); process.exit(1); }
    const result = JSON.parse(readFileSync(file, "utf8"));
    if (!result.critique || typeof result.grades !== "object" || result.grades === null) {
      console.error('The result file must be {"critique": "...", "grades": {"Element": 0.0}}');
      process.exit(1);
    }
    const packet = await call("/t/packet?session=" + encodeURIComponent(sessionCode));
    const transcript = packet.transcript || result.transcript;
    if (!transcript) {
      console.error('This is an audio-sealed take: the result file must also carry "transcript", the transcript made from the sealed audio (see the audio mode).');
      process.exit(1);
    }
    const d = await post("/t/critique", { sessionCode, transcript,
      critique: result.critique, grades: result.grades, final: result.final === true });
    console.log(JSON.stringify(d));
  } else {
    console.error("unknown mode: " + mode);
    process.exit(1);
  }
} catch (e) {
  console.error(String(e && e.message || e));
  process.exit(1);
}
