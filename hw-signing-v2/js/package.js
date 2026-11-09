// HTML package assembly, format v2 (SPEC, Webapp section).
//
// The package is built at ZIP creation, at retrieval time, from the
// result bundle the grading Worker signed when the grade was posted:
//   { v, job_id, audio_sha256, transcript_sha256, pkg,
//     pkg_content_sha256, completeness, accuracy, critique,
//     critique_sha256, youtube_video_sha256, t, receipt }
// The page adds only what it holds locally and the Worker never
// stored: the YouTube link, the audio file name and duration, the
// transcript chunks, and the component versions.
//
// Markup contract (the v22 audit app parses exactly this; its
// VERIFICATION_LABELS extend v1's with the v2 lines):
//   <section id="summary">       clickable YouTube link; grades as
//                                <span data-grade="completeness"> /
//                                <span data-grade="accuracy">
//   <section id="grading">       transcript as <pre class="transcript">
//                                with one "[mm:ss] text" line per chunk,
//                                grades (same spans), critique as one
//                                <p class="critique"> holding the signed
//                                text exactly, empty <section id="audit">
//   <section id="verification">  a <dl> with the labels: Format version
//                                (value "2"), Job, Prompt package,
//                                Prompt package content SHA-256,
//                                Webapp version, Model version,
//                                Glossary version, YouTube link, Audio
//                                file, Audio duration, Audio SHA-256,
//                                Transcript SHA-256, Completeness,
//                                Accuracy, Critique SHA-256, YouTube
//                                video SHA-256, Graded at,
//                                Grade receipt.
// v2 packages carry NO v1 receipt and no Session line: the job ID and
// the grade receipt take their place. Transcript timestamps use total
// minutes ([75:20], never h:mm:ss) so the audit's timestamp stripping
// recovers each chunk text exactly and the recomputed transcript
// checksum matches the signed one.

export const FORMAT_VERSION = '2';
export const VERSIONS = {
  webapp: 'hw-signing-webapp 2.3.0',
  model: 'parakeet-tdt-0.6b-v2-int8',
  glossary: 'chemescribe-glossary-bundle ea2807d2',
};

export const AUDIO_FILE_NAME = 'submission-audio.wav';
export const PACKAGE_FILE_NAME = 'submission.html';

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function unescapeHtml(s) {
  return String(s)
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&');
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

// Assemble the HTML package. Input:
// { youtubeLink, audioFileName, durationS, chunks: [{start, text}]
//   (scrubbed chunk texts), bundle: <Worker result bundle> }
// Audio is never embedded.
export function assemblePackage(input) {
  const bundle = input.bundle || {};
  const link = input.youtubeLink || '';
  const linkHtml = link
    ? '<a href="' + escapeHtml(link) + '">' + escapeHtml(link) + '</a>'
    : 'not provided';
  const grades =
    'Completeness: <span data-grade="completeness">' + bundle.completeness +
    '</span>/5 · Accuracy: <span data-grade="accuracy">' + bundle.accuracy +
    '</span>/5';
  const transcriptLines = (input.chunks || [])
    .map((c) => '[' + formatTranscriptTimestamp(c.start) + '] ' + oneLine(c.text))
    .join('\n');
  // The critique is emitted as ONE <p class="critique"> holding the
  // critique text exactly as signed (internal line breaks preserved):
  // the v22 audit recomputes critique_sha256 over that element's text,
  // so splitting, trimming or re-wrapping it here would break the
  // hash. pre-line keeps the line breaks visible when rendered.
  const critiqueHtml = '<p class="critique" style="white-space: pre-line">' +
    escapeHtml(bundle.critique || '') + '</p>';
  const duration = (Math.round((Number(input.durationS) || 0) * 10) / 10).toFixed(1);
  const ytVideoSha = bundle.youtube_video_sha256 || 'none';

  return '<!DOCTYPE html>\n' +
    '<html lang="en">\n<head>\n<meta charset="utf-8">\n' +
    '<title>Submission package</title>\n</head>\n<body>\n' +
    '<section id="summary">\n<h1>Summary</h1>\n' +
    '<p>YouTube: ' + linkHtml + '</p>\n' +
    '<p>Grades (predicted): ' + grades + '</p>\n</section>\n' +
    '<section id="grading">\n<h2>Grading</h2>\n' +
    '<h3>Transcript</h3>\n' +
    '<pre class="transcript">' + escapeHtml(transcriptLines) + '</pre>\n' +
    '<h3>Grades</h3>\n<p>' + grades + '</p>\n' +
    '<h3>Critique</h3>\n' + critiqueHtml + '\n' +
    '<section id="audit">\n<h3>Audit</h3>\n</section>\n</section>\n' +
    '<section id="verification">\n<h2>Verification</h2>\n' +
    '<p>Audio duration is a plain number of seconds (s).</p>\n<dl>\n' +
    '<dt>Format version</dt><dd>' + escapeHtml(FORMAT_VERSION) + '</dd>\n' +
    '<dt>Job</dt><dd>' + escapeHtml(bundle.job_id || '') + '</dd>\n' +
    '<dt>Prompt package</dt><dd>' + escapeHtml(bundle.pkg || '') + '</dd>\n' +
    '<dt>Prompt package content SHA-256</dt><dd>' + escapeHtml(bundle.pkg_content_sha256 || '') + '</dd>\n' +
    '<dt>Webapp version</dt><dd>' + escapeHtml(VERSIONS.webapp) + '</dd>\n' +
    '<dt>Model version</dt><dd>' + escapeHtml(VERSIONS.model) + '</dd>\n' +
    '<dt>Glossary version</dt><dd>' + escapeHtml(VERSIONS.glossary) + '</dd>\n' +
    '<dt>YouTube link</dt><dd>' + linkHtml + '</dd>\n' +
    '<dt>Audio file</dt><dd>' + escapeHtml(input.audioFileName) + '</dd>\n' +
    '<dt>Audio duration</dt><dd>' + duration + '</dd>\n' +
    '<dt>Audio SHA-256</dt><dd>' + escapeHtml(bundle.audio_sha256 || '') + '</dd>\n' +
    '<dt>Transcript SHA-256</dt><dd>' + escapeHtml(bundle.transcript_sha256 || '') + '</dd>\n' +
    '<dt>Completeness</dt><dd>' + escapeHtml(bundle.completeness) + '</dd>\n' +
    '<dt>Accuracy</dt><dd>' + escapeHtml(bundle.accuracy) + '</dd>\n' +
    '<dt>Critique SHA-256</dt><dd>' + escapeHtml(bundle.critique_sha256 || '') + '</dd>\n' +
    '<dt>YouTube video SHA-256</dt><dd>' + escapeHtml(ytVideoSha) + '</dd>\n' +
    '<dt>Graded at</dt><dd>' + escapeHtml(bundle.t || '') + '</dd>\n' +
    '<dt>Grade receipt</dt><dd>' + escapeHtml(bundle.receipt || '') + '</dd>\n' +
    '</dl>\n</section>\n</body>\n</html>\n';
}

// Read back what assemblePackage wrote — the verification <dl> as a
// label → value map (link values read as their href), the two grade
// spans, and the transcript lines. The audit app has its own parser;
// this one exists so the page's tests can round-trip the format and
// so the two parsers can be kept consistent.
export function parsePackageVerification(html) {
  const out = { verification: {}, completeness: null, accuracy: null, transcriptLines: [] };
  const text = String(html || '');
  const verif = text.slice(text.indexOf('<section id="verification">'));
  const pairRe = /<dt>([^<]+)<\/dt><dd>(.*?)<\/dd>/gs;
  for (const m of verif.matchAll(pairRe)) {
    const label = unescapeHtml(m[1]);
    const raw = m[2];
    const href = raw.match(/<a href="([^"]*)">/);
    out.verification[label] = href ? unescapeHtml(href[1]) : unescapeHtml(raw.replace(/<[^>]+>/g, ''));
  }
  const comp = text.match(/<span data-grade="completeness">(\d+)<\/span>/);
  const acc = text.match(/<span data-grade="accuracy">(\d+)<\/span>/);
  if (comp) out.completeness = Number(comp[1]);
  if (acc) out.accuracy = Number(acc[1]);
  const pre = text.match(/<pre class="transcript">(.*?)<\/pre>/s);
  if (pre) out.transcriptLines = unescapeHtml(pre[1]).split('\n');
  return out;
}
