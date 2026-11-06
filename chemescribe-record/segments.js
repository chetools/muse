// Segment assembly and display helpers for the raw transcript.
// Pure functions, unit-tested in node (tests-record.mjs in the build
// folder). A segment is {start: seconds from the start of the audio,
// text: string}. This page applies no corrections, so a segment's text
// is the recogniser's raw output, exactly as returned.

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

export function wordCount(text) {
  const m = String(text || '').trim().match(/\S+/g);
  return m ? m.length : 0;
}

// The full raw transcript: the pieces' texts, trimmed, joined with a
// single space. Empty pieces contribute nothing.
export function assembleSegments(segments) {
  const clean = (segments || []).filter((s) => s && s.text && s.text.trim());
  return clean.map((s) => s.text.trim()).join(' ');
}

// Start times of the fixed-length windows a file is cut into before
// transcription: [0, windowS, 2*windowS, ...], always at least one
// window, the count being ceil(totalSeconds / windowS).
export function windowStarts(totalSeconds, windowS) {
  const n = Math.max(1, Math.ceil((Number(totalSeconds) || 0) / windowS));
  const starts = [];
  for (let w = 0; w < n; w++) starts.push(w * windowS);
  return starts;
}

// Recording timer display: whole seconds as M:SS (H:MM:SS past an hour).
export function formatClock(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  if (s >= 3600) return Math.floor(s / 3600) + ':' + mm + ':' + ss;
  return Math.floor(s / 60) + ':' + ss;
}
