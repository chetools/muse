// Suggested YouTube chapters from chunk start times. Pure functions.
//
// YouTube description form: first chapter at 00:00, at least 3 chapters,
// at least 10 s between chapter starts. Chapters are taken from chunk
// starts; when chunk starts alone cannot give 3 chapters, the recording
// is divided into thirds. Returns an array of { start, title } (start in
// seconds), or null when no valid list exists (recording too short).

import { formatClock } from './transcript.js';

const MIN_GAP_S = 10;

function chapterTitle(text) {
  const words = String(text || '').replace(/\s+/g, ' ').trim().split(' ')
    .filter(Boolean).slice(0, 6);
  let title = words.join(' ');
  if (title.length > 60) title = title.slice(0, 60).trim();
  return title;
}

export function generateChapters(chunks, durationS) {
  const duration = Number(durationS) || 0;
  const clean = (chunks || [])
    .filter((c) => c && Number.isFinite(c.start))
    .slice()
    .sort((a, b) => a.start - b.start);
  if (!clean.length || duration < 3 * MIN_GAP_S) return null;

  const starts = [0];
  for (const c of clean) {
    const s = Math.floor(c.start);
    if (s > 0 && s - starts[starts.length - 1] >= MIN_GAP_S && s < duration) {
      starts.push(s);
    }
  }
  if (starts.length < 3) {
    // Fall back to thirds of the recording, snapped to chunk starts when
    // one is near and keeps the spacing rule.
    for (const target of [duration / 3, (2 * duration) / 3]) {
      if (starts.length >= 3) break;
      const t = Math.floor(target);
      let candidate = t;
      const near = clean
        .map((c) => Math.floor(c.start))
        .filter((s) => Math.abs(s - t) <= 5)
        .sort((a, b) => Math.abs(a - t) - Math.abs(b - t))[0];
      if (near !== undefined) candidate = near;
      if (candidate - starts[starts.length - 1] >= MIN_GAP_S
          && duration - candidate >= 0) {
        starts.push(candidate);
      }
    }
    starts.sort((a, b) => a - b);
  }
  if (starts.length < 3) return null;

  const titleAt = (s, i) => {
    const chunk = clean.find((c) => Math.abs(c.start - s) < 1) || clean[0];
    const title = chunk ? chapterTitle(chunk.text) : '';
    return title || 'Section ' + (i + 1);
  };
  return starts.map((s, i) => ({ start: s, title: titleAt(s, i) }));
}

export function chaptersText(chapters) {
  if (!chapters) return '';
  return chapters
    .map((c) => formatClock(c.start) + ' ' + c.title)
    .join('\n');
}
