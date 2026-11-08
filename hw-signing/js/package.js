// Signing payload, signing call, and HTML package assembly. The assembly
// is a pure function; the signing call takes fetch as a parameter.
//
// Package markup contract (Stage 7 audit app, audit-app/README.md — the
// audit app parses exactly this):
//   <section id="summary">       clickable YouTube link; estimated grades
//                                as <span data-grade="completeness"> /
//                                <span data-grade="accuracy">
//   <section id="grading">       transcript as <pre class="transcript">
//                                with one "[mm:ss] text" line per chunk,
//                                estimated grades (same spans), per-point
//                                tally, critique, empty <section id="audit">
//   <section id="verification">  a <dl> with the fixed labels the audit
//                                app reads (VERIFICATION_LABELS in
//                                audit.py): Format version, Session,
//                                Prompt package, Webapp version, Model
//                                version, Glossary version, YouTube link,
//                                Audio file, Audio duration, Audio
//                                SHA-256, Transcript SHA-256, Signed at,
//                                Receipt.
// Transcript timestamps use total minutes ([75:20], never h:mm:ss) so the
// audit app's timestamp stripping recovers each chunk text exactly, and
// the checksum over the recovered canonical transcript (chunk texts
// joined by LF, no trailing LF) matches the transcript checksum.

import { normaliseWorkerBase } from './config.js';

export const FORMAT_VERSION = '1';
export const VERSIONS = {
  webapp: 'hw-signing-webapp 1.0.2',
  model: 'parakeet-tdt-0.6b-v2-int8',
  glossary: 'chemescribe-glossary-bundle ea2807d2',
};

export const AUDIO_FILE_NAME = 'submission-audio.wav';
export const PACKAGE_FILE_NAME = 'submission.html';

const SHA256_HEX = /^[0-9a-f]{64}$/;
const SESSION_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';

// Session code from random bytes. rngBytes(n) must return n bytes
// (defaults to crypto.getRandomValues); injected in tests.
export function generateSessionCode(rngBytes) {
  const get = rngBytes || ((n) => globalThis.crypto.getRandomValues(new Uint8Array(n)));
  const bytes = get(16);
  let code = '';
  for (const b of bytes) code += SESSION_ALPHABET[b % SESSION_ALPHABET.length];
  return 'SES-' + code;
}

// The exact payload of the plan's Interfaces section. Throws on any
// field that the signing Worker would reject.
export function buildSigningPayload({ session, audioSha256, transcriptSha256, pkg }) {
  const payload = {
    v: FORMAT_VERSION,
    session,
    audio_sha256: audioSha256,
    transcript_sha256: transcriptSha256,
    pkg,
    versions: { ...VERSIONS },
  };
  if (!payload.session || payload.session.length > 128) {
    throw new Error('session code missing or too long');
  }
  if (!SHA256_HEX.test(payload.audio_sha256 || '')) {
    throw new Error('audio fingerprint is not a SHA-256 hex value');
  }
  if (!SHA256_HEX.test(payload.transcript_sha256 || '')) {
    throw new Error('transcript checksum is not a SHA-256 hex value');
  }
  if (!payload.pkg || payload.pkg.length > 128) {
    throw new Error('prompt package identifier missing or too long');
  }
  return payload;
}

// POST the payload to <worker>/sign; returns { t, receipt }.
export async function requestSignature(workerBase, payload, fetchFn) {
  const base = normaliseWorkerBase(workerBase);
  if (!base) throw new Error('no signing Worker address configured');
  const doFetch = fetchFn || globalThis.fetch;
  const res = await doFetch(base + '/sign', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('signing Worker answered HTTP ' + res.status);
  const data = await res.json();
  if (!data || typeof data.t !== 'string' || typeof data.receipt !== 'string') {
    throw new Error('signing Worker response carried no t/receipt');
  }
  return { t: data.t, receipt: data.receipt };
}

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

// [mm:ss] with total minutes, zero-padded to two digits (can exceed 59).
export function formatTranscriptTimestamp(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const mm = String(Math.floor(s / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  return mm + ':' + ss;
}

function oneLine(text) {
  return String(text || '').replace(/\s+/g, ' ').trim();
}

// Assemble the HTML package in the plan's section order. Input:
// { youtubeLink, audioFileName, durationS, audioSha256, transcriptSha256,
//   pkg, session, t, receipt,
//   chunks: [{ start, text }] (scrubbed chunk texts),
//   result: { completeness, accuracy, tally: [{label, score, passage}],
//             critique } }
// Audio is never embedded.
export function assemblePackage(input) {
  const link = input.youtubeLink || '';
  const linkHtml = link
    ? '<a href="' + escapeHtml(link) + '">' + escapeHtml(link) + '</a>'
    : 'not provided';
  const grades =
    'Completeness: <span data-grade="completeness">' + input.result.completeness +
    '</span>/5 · Accuracy: <span data-grade="accuracy">' + input.result.accuracy +
    '</span>/5';
  const transcriptLines = (input.chunks || [])
    .map((c) => '[' + formatTranscriptTimestamp(c.start) + '] ' + oneLine(c.text))
    .join('\n');
  const tallyItems = input.result.tally
    .map((t) => '<li>' + escapeHtml(t.label) + ': ' + escapeHtml(t.score) +
      ' — &ldquo;' + escapeHtml(t.passage) + '&rdquo;</li>')
    .join('\n');
  const critiqueParas = String(input.result.critique || '')
    .split(/\n+/).map((l) => l.trim()).filter(Boolean)
    .map((l) => '<p>' + escapeHtml(l) + '</p>').join('\n');
  const duration = (Math.round((Number(input.durationS) || 0) * 10) / 10).toFixed(1);

  return '<!DOCTYPE html>\n' +
    '<html lang="en">\n<head>\n<meta charset="utf-8">\n' +
    '<title>Submission package</title>\n</head>\n<body>\n' +
    '<section id="summary">\n<h1>Summary</h1>\n' +
    '<p>YouTube: ' + linkHtml + '</p>\n' +
    '<p>Estimated grades (predicted): ' + grades + '</p>\n</section>\n' +
    '<section id="grading">\n<h2>Grading</h2>\n' +
    '<h3>Transcript</h3>\n' +
    '<pre class="transcript">' + escapeHtml(transcriptLines) + '</pre>\n' +
    '<h3>Estimated grades</h3>\n<p>' + grades + '</p>\n' +
    '<h3>Per-point tally</h3>\n<ul>\n' + tallyItems + '\n</ul>\n' +
    '<h3>Critique</h3>\n' + critiqueParas + '\n' +
    '<section id="audit">\n<h3>Audit</h3>\n</section>\n</section>\n' +
    '<section id="verification">\n<h2>Verification</h2>\n' +
    '<p>Audio duration is a plain number of seconds (s).</p>\n<dl>\n' +
    '<dt>Format version</dt><dd>' + escapeHtml(FORMAT_VERSION) + '</dd>\n' +
    '<dt>Session</dt><dd>' + escapeHtml(input.session) + '</dd>\n' +
    '<dt>Prompt package</dt><dd>' + escapeHtml(input.pkg) + '</dd>\n' +
    '<dt>Webapp version</dt><dd>' + escapeHtml(VERSIONS.webapp) + '</dd>\n' +
    '<dt>Model version</dt><dd>' + escapeHtml(VERSIONS.model) + '</dd>\n' +
    '<dt>Glossary version</dt><dd>' + escapeHtml(VERSIONS.glossary) + '</dd>\n' +
    '<dt>YouTube link</dt><dd>' + linkHtml + '</dd>\n' +
    '<dt>Audio file</dt><dd>' + escapeHtml(input.audioFileName) + '</dd>\n' +
    '<dt>Audio duration</dt><dd>' + duration + '</dd>\n' +
    '<dt>Audio SHA-256</dt><dd>' + escapeHtml(input.audioSha256) + '</dd>\n' +
    '<dt>Transcript SHA-256</dt><dd>' + escapeHtml(input.transcriptSha256) + '</dd>\n' +
    '<dt>Signed at</dt><dd>' + escapeHtml(input.t) + '</dd>\n' +
    '<dt>Receipt</dt><dd>' + escapeHtml(input.receipt) + '</dd>\n' +
    '</dl>\n</section>\n</body>\n</html>\n';
}
