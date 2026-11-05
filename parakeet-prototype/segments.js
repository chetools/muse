// Segment assembly and timestamp formatting for the transcript.
// Pure functions, unit-tested in node (tests-v3.mjs in the build folder).
// A segment is {start: seconds from the start of the audio, text: string}.
// Segment start times come only from the transcription itself: in
// recording mode, samples already transcribed divided by the sample rate;
// in file mode, the start of each chunk returned by transcribeLongAudio
// with returnTimestamps enabled (see vendor/parakeet/src/long_audio.js,
// which returns chunks of {text, timestamp: [start, end]}).

export function formatTimestamp(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  if (s >= 3600) return Math.floor(s / 3600) + ':' + mm + ':' + ss;
  return mm + ':' + ss;
}

export function assembleSegments(segments, { timestamps = false } = {}) {
  const clean = (segments || []).filter((s) => s && s.text && s.text.trim());
  if (timestamps) {
    return clean.map((s) => '[' + formatTimestamp(s.start) + '] ' + s.text.trim()).join('\n');
  }
  return clean.map((s) => s.text.trim()).join(' ');
}
