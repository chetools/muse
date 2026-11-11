// Page wiring, HW Signing v2. Browser only. All logic that can be
// pure lives in the sibling modules; this file holds page state and
// events.
//
// Privacy invariants held here:
// - the scrub field's contents are read only to scrub, and never enter
//   any export, storage, or network call;
// - nothing leaves the machine before the step-5 confirmation: the
//   job is the first network call carrying submission data, and it
//   carries the scrubbed transcript, fingerprints and versions — no
//   audio, no name, and no YouTube link;
// - browser storage holds only what the design settles: IndexedDB
//   caches the student's own recordings and corrected transcripts
//   (pre-scrub) on this machine, and localStorage holds the job
//   entries (retrieval code, labels, expiry, and the
//   YouTube link and its title kept locally for ZIP creation). The
//   transcript and the grades are never written to localStorage.

import { parseConfig, buildConfigLink } from './config.js';
import { sha256Hex } from './hash.js';
import {
  parseScrubWords, scrubChunks, scrubMetadata, canonicalTranscript,
  legacyCanonicalTranscript, findSuspects, formatDuration,
} from './transcript.js';
import {
  VERSIONS, AUDIO_FILE_NAME, assemblePackage, formatTranscriptTimestamp,
} from './package.js';
import { encodeWavPcm16, decodeFileTo16kMono, SAMPLE_RATE } from './media.js';
import { loadModel, transcribePcm, FILE_WINDOW_S } from './transcribe.js';
import { buildVocabulary } from './vocab.js';
import {
  cacheGet, cacheInit, cachePutChunk, cacheWindowDone, cacheComplete,
  cacheList, cacheDelete,
} from './cache.js';
import { fromCachedChunk, recordingFirstWords } from './cachekey.js';
import {
  parseYouTubeVideoId, canonicalWatchUrl, classifyDuration,
  verifyBundleContents,
  validateJobPayload, buildJobPayload, loadJobEntries, addJobEntry,
  removeJobEntry, saveJobEntries,
  requestYouTubeCheck, submitJob, fetchJobStatus, markJobRetrieved,
  finalizeJob, reportDurationStat,
} from './jobs.js';
import { buildZip, submissionZipName, ZIP_ENTRY_HTML, ZIP_ENTRY_AUDIO } from './zip.js';

const $ = (id) => document.getElementById(id);
const cfg = parseConfig(window.location.search);

let model = null;
let pcm = null;
let wavBytes = null;
let audioSha = null;
let durationS = 0;
let sourceName = '';
let chunks = [];            // pipeline chunks: {start, end, raw, corrected, ...}
let windowsDoneBase = 0;    // windows already cached before this run (resume)
let transcriptionComplete = false;
let confirmed = false;
let vocabulary = null;
let ytCheck = null;         // { videoId, token, checkedAt, title, audioSha256 } after an ok check
let ytDur = null;           // duration comparison for the step-6 check:
// { band, diffS, tolS, audioS, videoS } once the preview reports the
// video's length; null until then (treated as band 'unknown').
let finDur = null;          // the same, for the conversion panel
let ytApiPromise = null;
const readyBundles = new Map(); // "pkg|code" -> result bundle from /jobs/status
const jobStates = new Map();    // "pkg|code" -> {status, queue_ahead} last seen
const expandedJobs = new Set(); // "pkg|code" with grades shown (kept across refreshes)

// Errors belong beside the control that was used, in the part
// of the window on screen — not in one banner at the top of a
// long page (teacher's rule, 2026-11-09). The page's one error
// box moves: showError takes the control whose action failed
// and places the box directly after that control's row, then
// scrolls it into view if it is off screen. With no anchor, the
// box stays where it sits (at the top, for configuration errors
// at page load).
function showError(message, err, anchor) {
  const box = $('errBox');
  box.textContent = message;
  box.style.display = 'block';
  const host = anchor || (document.activeElement
    && document.activeElement !== document.body
    ? document.activeElement : null);
  if (host && host.isConnected && !box.contains(host)) {
    const row = host.closest('.row, .recrow, .jobrow') || host;
    if (row.parentNode) row.after(box);
  }
  if (box.scrollIntoView) box.scrollIntoView({ block: 'nearest' });
  if (err) console.error(err);
}
function clearError() { $('errBox').style.display = 'none'; }

function scrubWords() { return parseScrubWords($('scrubField').value); }
function scrubbed() { return scrubChunks(chunks, scrubWords()); }
function canonical() { return canonicalTranscript(scrubbed()); }
// There is no Practice/Final choice at send time: a job sent with a
// checked YouTube link is submission-ready when graded ("final"); a
// job sent without one can be turned into the submission afterwards
// (section 7), which is when most students decide.
function kind() { return ytCheck ? 'final' : 'practice'; }

// A link check stands only for the recording that was loaded when
// the check was made. Changing the recording — choosing another
// file, or restoring a saved one — voids it, because the checked
// video was compared with the previous recording's length and the
// job would otherwise carry the wrong video's token.
function clearYtCheck() {
  if (!ytCheck) return;
  ytCheck = null;
  ytDur = null;
  $('ytConfirmChk').checked = false;
  $('ytStatus').textContent =
    'The recording changed, so the earlier link check no longer stands. Check the link again.';
  refreshYtDurationUi();
  updateJobEnabled();
}

// Whether a checked link may be used, given its duration band and
// the student's explicit confirmation: 'pass' needs nothing;
// 'confirm' and 'unknown' need the played-and-confirmed tick;
// 'block' can never be used for this recording.
function durationGateOk(dur, confirmChk) {
  const band = dur ? dur.band : 'unknown';
  if (band === 'pass') return true;
  if (band === 'block') return false;
  return !!(confirmChk && confirmChk.checked);
}

// One anonymous duration statistic per (video, recording) pair is
// reported to the Worker, deduplicated in localStorage, so the
// duration bands can later be recalibrated from measured
// same-recording differences. Nothing about the video or the
// student is sent beyond the two durations and the package label.
const STATS_KEY = 'hw-signing.durationStats.v1';
function reportDurationOnce(context, audioSha256, videoId, audioS, videoS) {
  if (!cfg.worker || !(audioS > 0) || !(videoS > 0)) return;
  const key = videoId + '|' + (audioSha256 || '');
  let sent = [];
  try { sent = JSON.parse(localStorage.getItem(STATS_KEY) || '[]'); } catch { sent = []; }
  if (!Array.isArray(sent) || sent.includes(key)) return;
  sent.push(key);
  try { localStorage.setItem(STATS_KEY, JSON.stringify(sent.slice(-200))); } catch { /* full/blocked */ }
  reportDurationStat(cfg.worker, { pkg: cfg.pkg, context, audioS, videoS });
}

function downloadBlob(blob, name) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

// --- Configuration display and teacher setup ---
function renderConfig() {
  const parts = [];
  if (cfg.course) parts.push('Course: ' + cfg.course);
  if (cfg.asg) parts.push('Assignment: ' + cfg.asg);
  if (cfg.pkg) parts.push('Prompt package: ' + cfg.pkg);
  if (cfg.ph) parts.push('Package content hash: ' + cfg.ph.slice(0, 12) + '…');
  if (cfg.worker) parts.push('Grading Worker: ' + cfg.worker);
  $('cfgLine').textContent = parts.length
    ? 'Configuration — ' + parts.join(' · ')
    : 'Configuration: none in this link. The teacher’s configured link sets the course, the prompt package, and the grading Worker.';
  if (cfg.setup) {
    $('setupSection').hidden = false;
    $('suWorker').value = cfg.worker || '';
    $('suPkg').value = cfg.pkg || '';
    $('suPh').value = cfg.ph || '';
    $('suCourse').value = cfg.course || '';
    $('suAsg').value = cfg.asg || '';
  }
}
$('suBuild').addEventListener('click', () => {
  const link = buildConfigLink(window.location.origin + window.location.pathname, {
    worker: $('suWorker').value.trim(),
    pkg: $('suPkg').value.trim(),
    ph: $('suPh').value.trim(),
    course: $('suCourse').value.trim(),
    asg: $('suAsg').value.trim(),
  });
  $('suLink').textContent = link;
});
$('suCopy').addEventListener('click', async () => {
  const link = $('suLink').textContent;
  if (link) { try { await navigator.clipboard.writeText(link); } catch { /* stays copyable by hand */ } }
});

// --- Model loading ---
const fileProgress = new Map();
function onDownloadProgress({ loaded, total, file }) {
  fileProgress.set(file, { loaded, total });
  let sumLoaded = 0, sumTotal = 0;
  for (const v of fileProgress.values()) { sumLoaded += v.loaded; sumTotal += v.total || 0; }
  if (sumTotal > 0) {
    $('loadProg').value = sumLoaded / sumTotal;
    $('loadStatus').textContent = 'Downloading ' + file + ' — ' +
      (sumLoaded / 1048576).toFixed(0) + ' MB of ' + (sumTotal / 1048576).toFixed(0) + ' MB…';
  }
}
$('loadBtn').addEventListener('click', async () => {
  clearError();
  $('loadBtn').disabled = true;
  $('loadProg').hidden = false;
  $('loadStatus').textContent = 'Downloading model files from Hugging Face…';
  try {
    model = await loadModel(onDownloadProgress);
    $('loadProg').value = 1;
    $('loadStatus').textContent = 'Model loaded. Transcription runs on WebAssembly, one thread.';
    updateRunEnabled();
  } catch (err) {
    $('loadStatus').textContent = 'Model did not load.';
    showError('The model could not be loaded. Check the connection and try again.', err, $('loadBtn'));
    $('loadBtn').disabled = false;
  }
});

// --- Media stage + cache ---
function updateRunEnabled() { $('runBtn').disabled = !(model && pcm); }

function setAudioMeta() {
  if (!audioSha) { $('audioMeta').textContent = ''; return; }
  $('audioMeta').textContent =
    (sourceName ? 'Source file: ' + scrubMetadata(sourceName, scrubWords()) + ' · ' : '') +
    'duration ' + durationS.toFixed(1) + ' s' +
    ' · extracted audio: ' + AUDIO_FILE_NAME +
    ' · SHA-256 ' + audioSha;
}

// Adopt a complete cache record as the current recording: WAV bytes
// from the stored blob, chunks from the store (pre-scrub; scrubbing
// re-derives the view), no transcription needed.
async function adoptCacheRecord(record, note) {
  chunks = (record.chunks || []).map(fromCachedChunk);
  windowsDoneBase = record.windows_done || 0;
  if (record.wavBlob) {
    wavBytes = new Uint8Array(await record.wavBlob.arrayBuffer());
  }
  durationS = record.duration_s || (wavBytes ? (wavBytes.length - 44) / 2 / SAMPLE_RATE : 0);
  transcriptionComplete = !!record.complete;
  $('mediaStatus').textContent = note;
  setAudioMeta();
  refreshDerived();
}

$('mediaFile').addEventListener('change', async (ev) => {
  clearError();
  clearYtCheck();
  const file = ev.target.files && ev.target.files[0];
  pcm = null; wavBytes = null; audioSha = null; durationS = 0;
  chunks = []; windowsDoneBase = 0;
  transcriptionComplete = false;
  confirmed = false; $('confirmChk').checked = false;
  updateRunEnabled();
  if (!file) { $('mediaStatus').textContent = 'No file chosen.'; return; }
  sourceName = file.name;
  $('mediaStatus').textContent = 'Reading the file…';
  try {
    pcm = await decodeFileTo16kMono(file);
    durationS = pcm.length / SAMPLE_RATE;
    wavBytes = encodeWavPcm16(pcm);
    audioSha = await sha256Hex(wavBytes);
    setAudioMeta();
    // Cache check: a hit restores the transcript with no transcription.
    const record = await cacheGet(audioSha, VERSIONS.model, VERSIONS.glossary)
      .catch(() => null);
    await cacheInit(audioSha, {
      model: VERSIONS.model, glossary: VERSIONS.glossary,
      wavBlob: new Blob([wavBytes], { type: 'audio/wav' }), duration_s: durationS,
      source_name: sourceName,
    }).catch(() => {});
    renderCacheList();
    if (record && record.complete && record.chunks && record.chunks.length) {
      await adoptCacheRecord({ ...record, wavBlob: new Blob([wavBytes], { type: 'audio/wav' }) },
        'Transcript restored from this computer — no transcription needed.');
    } else if (record && record.chunks && record.chunks.length) {
      chunks = record.chunks.map(fromCachedChunk);
      windowsDoneBase = record.windows_done || 0;
      $('mediaStatus').textContent =
        'Audio extracted on this device. An earlier run of this recording stopped partway; ' +
        'transcription will resume from ' + Math.round(100 * Math.min(1, (windowsDoneBase * FILE_WINDOW_S) / durationS)) + ' %.';
      updateRunEnabled();
      refreshDerived();
    } else {
      $('mediaStatus').textContent = 'Audio extracted on this device.';
      updateRunEnabled();
      refreshDerived();
    }
  } catch (err) {
    $('mediaStatus').textContent = 'That file could not be decoded.';
    showError('The chosen file could not be decoded as audio or video by this browser.', err, $('mediaFile'));
  }
});

// --- Saved recordings list ---
async function renderCacheList() {
  const box = $('cacheBox');
  let list = [];
  try { list = await cacheList(); } catch { list = []; }
  if (!list.length) { box.textContent = 'No recordings saved yet.'; return; }
  box.textContent = '';
  for (const entry of list) {
    const row = document.createElement('div');
    row.className = 'recrow';
    const when = entry.created_at ? new Date(entry.created_at).toLocaleString() : '';
    const meta = document.createElement('span');
    meta.className = 'recmeta';
    // Recognition aids first: the source file name and the
    // transcript's opening words (both scrubbed with the current
    // removal list, as everywhere they are shown) are what tell
    // several takes of one assignment apart.
    const words = scrubWords();
    const namePart = entry.source_name
      ? scrubMetadata(entry.source_name, words) + ' · ' : '';
    const wordsPart = entry.first_words
      ? ' · starts “' + scrubMetadata(entry.first_words, words) + '…”' : '';
    meta.textContent =
      namePart + when + ' · ' + formatDuration(entry.duration_s) + ' · ' +
      (entry.size_bytes / 1048576).toFixed(1) + ' MB · ' +
      (entry.complete ? 'transcribed' : 'partly transcribed (' + entry.chunks + ' pieces)') +
      ' · fingerprint ' + entry.audio_sha256.slice(0, 12) + '…' + wordsPart;
    row.append(meta);
    const restoreBtn = document.createElement('button');
    restoreBtn.textContent = 'Restore';
    restoreBtn.addEventListener('click', async () => {
      clearError();
      clearYtCheck();
      try {
        const record = await cacheGet(entry.audio_sha256, VERSIONS.model, VERSIONS.glossary);
        if (!record) { showError('That saved recording was made by an older model or glossary version and cannot be restored.', null, restoreBtn); return; }
        audioSha = entry.audio_sha256;
        sourceName = record.source_name || '';
        pcm = null;
        updateRunEnabled();
        await adoptCacheRecord(record, 'Recording restored from this computer.');
      } catch (err) { showError('The saved recording could not be restored.', err, restoreBtn); }
    });
    const delBtn = document.createElement('button');
    delBtn.textContent = 'Delete';
    delBtn.addEventListener('click', async () => {
      await cacheDelete(entry.audio_sha256).catch(() => {});
      renderCacheList();
    });
    row.append(restoreBtn, delBtn);
    box.append(row);
  }
}

// --- Scrub field: re-derive everything when it changes ---
$('scrubField').addEventListener('input', () => {
  confirmed = false;
  $('confirmChk').checked = false;
  setAudioMeta();
  refreshDerived();
  renderCacheList();
});

// --- Transcription (with chunk-level caching and resume) ---
$('runBtn').addEventListener('click', async () => {
  if (!model || !pcm) return;
  clearError();
  const resumeFrom = windowsDoneBase;
  if (!resumeFrom) chunks = [];
  transcriptionComplete = false;
  confirmed = false;
  $('confirmChk').checked = false;
  $('runBtn').disabled = true;
  $('runProg').hidden = false;
  $('runProg').value = durationS ? Math.min(1, (resumeFrom * FILE_WINDOW_S) / durationS) : 0;
  $('liveBox').hidden = false;
  $('runStatus').textContent = resumeFrom ? 'Resuming transcription…' : 'Transcribing…';
  const t0 = performance.now();
  let lastPct = Math.round(100 * $('runProg').value);
  const timer = setInterval(() => {
    $('runStatus').textContent = 'Transcribing… ' + lastPct +
      ' % of the audio · ' + Math.round((performance.now() - t0) / 1000) +
      ' s elapsed. The page may appear to pause while a piece is processed.';
  }, 1000);
  try {
    await transcribePcm(model, pcm, durationS, {
      startWindow: resumeFrom,
      onWindow: (done, total) => {
        if (total > 0) {
          lastPct = Math.round(100 * Math.min(1, done / total));
          $('runProg').value = Math.min(1, done / total);
        }
        const windows = Math.round(done / FILE_WINDOW_S);
        if (audioSha) cacheWindowDone(audioSha, windows).catch(() => {});
      },
      onChunk: (item, progress) => {
        chunks.push(item);
        if (audioSha) cachePutChunk(audioSha, item).catch(() => {});
        const s = scrubChunks([item], scrubWords())[0];
        $('liveRaw').textContent = s.raw;
        $('liveCorrected').textContent = s.text;
        if (progress && progress.total > 0) {
          $('runProg').value = Math.min(1, progress.done / progress.total);
          lastPct = Math.round(100 * Math.min(1, progress.done / progress.total));
          $('runStatus').textContent = 'Transcribing… ' + lastPct + ' % of the audio.';
        }
        refreshDerived();
      },
    });
    $('runProg').value = 1;
    transcriptionComplete = chunks.length > 0;
    if (transcriptionComplete && audioSha) {
      await cacheComplete(audioSha).catch(() => {});
      renderCacheList();
    }
    $('runStatus').textContent = chunks.length
      ? 'Done — ' + chunks.length + ' piece(s).'
      : 'The model returned no text for this recording.';
  } catch (err) {
    showError('Transcription failed or stopped partway. Pieces already shown are kept and saved; choosing the same file again resumes.', err, $('runBtn'));
    $('runStatus').textContent = '';
  } finally {
    clearInterval(timer);
    $('runBtn').disabled = false;
    refreshDerived();
  }
});

// --- Derived views: transcript, review list, job gating ---
function refreshDerived() {
  const sc = scrubbed();
  if (sc.length) {
    $('transcriptBox').textContent = sc
      .map((c) => '[' + formatTranscriptTimestamp(c.start) + '] ' + c.text)
      .join('\n');
    const words = scrubWords();
    $('scrubStatus').textContent = words.length
      ? 'Removal list active: ' + words.length + ' entr' + (words.length === 1 ? 'y' : 'ies') + '.'
      : '';
  } else {
    $('transcriptBox').textContent = 'The transcript will appear here.';
  }
  renderSuspects(sc);
  updateJobEnabled();
}

function renderSuspects(sc) {
  const box = $('suspectsBox');
  if (!sc.length) { box.textContent = 'No transcript yet.'; return; }
  if (!vocabulary) vocabulary = buildVocabulary();
  const suspects = findSuspects(sc, vocabulary.vocab, vocabulary.wordlist);
  if (!suspects.length) {
    box.textContent = 'No suspected identifiers found.';
    return;
  }
  box.textContent = suspects
    .map((s) => '“' + s.word + '” ×' + s.count + ' — ' + s.reason)
    .join('\n');
}

$('confirmChk').addEventListener('change', () => {
  confirmed = $('confirmChk').checked;
  updateJobEnabled();
});

// --- Job section ---
function updateJobEnabled() {
  const base = !!(cfg.worker && cfg.pkg && cfg.ph && transcriptionComplete && confirmed);
  // With a checked link, the duration gate also applies: a blocked
  // link disables Send until the link is fixed or cleared, and a
  // confirm-band link needs the student's explicit confirmation.
  const linkOk = !ytCheck || durationGateOk(ytDur, $('ytConfirmChk'));
  $('submitJobBtn').disabled = !(base && linkOk);
}
$('retrievalCode').addEventListener('input', updateJobEnabled);
$('ytConfirmChk').addEventListener('change', updateJobEnabled);

// The duration verdict for the step-6 link, in its own status line
// beside the preview, with the confirmation row shown exactly when
// the band requires it.
function refreshYtDurationUi() {
  const el = $('ytDurStatus');
  const row = $('ytConfirmRow');
  if (!ytCheck) { el.textContent = ''; row.hidden = true; return; }
  const band = ytDur ? ytDur.band : 'unknown';
  if (band === 'pass') {
    el.textContent = 'Lengths match: video ' + ytDur.videoS.toFixed(1) +
      ' s, audio ' + ytDur.audioS.toFixed(1) + ' s (difference ' +
      ytDur.diffS.toFixed(1) + ' s).';
    row.hidden = true;
  } else if (band === 'confirm') {
    el.textContent = 'The video runs ' + ytDur.videoS.toFixed(1) +
      ' s and the audio ' + ytDur.audioS.toFixed(1) + ' s — a difference of ' +
      ytDur.diffS.toFixed(1) + ' s. Play the preview above; if it is this ' +
      'recording, tick the confirmation below.';
    row.hidden = false;
  } else if (band === 'block') {
    el.textContent = 'The video runs ' + ytDur.videoS.toFixed(1) +
      ' s but the audio ' + ytDur.audioS.toFixed(1) + ' s — a difference of ' +
      ytDur.diffS.toFixed(1) + ' s, beyond the allowed ' + ytDur.tolS.toFixed(1) +
      ' s. This link cannot be used for this recording: enter the link for ' +
      'this recording, or clear the link to send for practice grading only.';
    row.hidden = true;
  } else {
    el.textContent = 'The preview has not reported the video’s length, so ' +
      'the lengths could not be compared. Play the preview above; if it is ' +
      'this recording, tick the confirmation below.';
    row.hidden = false;
  }
  updateJobEnabled();
}

// The same verdict for the conversion panel's link.
function refreshFinDurationUi() {
  const el = $('finDurStatus');
  const row = $('finConfirmRow');
  if (!finCheck) { el.textContent = ''; row.hidden = true; updateFinConfirmEnabled(); return; }
  const band = finDur ? finDur.band : 'unknown';
  if (band === 'pass') {
    el.textContent = 'Lengths match: video ' + finDur.videoS.toFixed(1) +
      ' s, audio ' + finDur.audioS.toFixed(1) + ' s (difference ' +
      finDur.diffS.toFixed(1) + ' s).';
    row.hidden = true;
  } else if (band === 'confirm') {
    el.textContent = 'The video runs ' + finDur.videoS.toFixed(1) +
      ' s and the selected job’s audio ' + finDur.audioS.toFixed(1) +
      ' s — a difference of ' + finDur.diffS.toFixed(1) + ' s. Play the ' +
      'preview above; if it is that job’s recording, tick the confirmation below.';
    row.hidden = false;
  } else if (band === 'block') {
    el.textContent = 'The video runs ' + finDur.videoS.toFixed(1) +
      ' s but the selected job’s audio ' + finDur.audioS.toFixed(1) +
      ' s — a difference of ' + finDur.diffS.toFixed(1) + ' s, beyond the ' +
      'allowed ' + finDur.tolS.toFixed(1) + ' s. This link cannot be used ' +
      'for this job.';
    row.hidden = true;
  } else {
    el.textContent = 'The preview has not reported the video’s length, so ' +
      'the lengths could not be compared. Play the preview above; if it is ' +
      'the selected job’s recording, tick the confirmation below.';
    row.hidden = false;
  }
  updateFinConfirmEnabled();
}

function updateFinConfirmEnabled() {
  $('finConfirmBtn').disabled =
    !(finCheck && durationGateOk(finDur, $('finConfirmChk')));
}
$('finConfirmChk').addEventListener('change', updateFinConfirmEnabled);

// YouTube: the link invalidates any earlier check when it changes.
$('ytLink').addEventListener('input', () => {
  ytCheck = null;
  ytDur = null;
  $('ytConfirmChk').checked = false;
  $('ytStatus').textContent = '';
  $('ytPlayerWrap').hidden = true;
  refreshYtDurationUi();
  updateJobEnabled();
});

function loadYouTubeApi() {
  if (window.YT && window.YT.Player) return Promise.resolve(window.YT);
  if (ytApiPromise) return ytApiPromise;
  ytApiPromise = new Promise((resolve, reject) => {
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      if (prev) prev();
      resolve(window.YT);
    };
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    tag.onerror = () => reject(new Error('the YouTube player could not be loaded'));
    document.head.append(tag);
  });
  return ytApiPromise;
}

// Preview the video in the embedded player and compare its duration
// with the relevant audio's — the loaded recording for the send form,
// the selected job's audio for the conversion panel. The comparison
// result goes to onDuration(videoS|null) once the player reports a
// length, or after a wait of about 12 s with none: classifyDuration
// turns it into the pass / confirm / block bands the send and
// conversion flows gate on. A true acoustic fingerprint comparison
// cannot run here, because the browser cannot read the video's audio
// track (YouTube serves it only inside its own player); sameness of
// recording is established by the teacher audit's acoustic
// cross-check on the submitted ZIP. A preview failure (embedding
// disabled, sign-in required) leaves the band 'unknown', which the
// gate treats as needing the student's played-and-confirmed tick;
// the Worker reachability check remains a requirement throughout.
const ytPlayers = {};
const durWatches = new Map(); // player element id -> interval timer
function watchPlayerDuration(playerId, onDuration) {
  if (durWatches.has(playerId)) clearInterval(durWatches.get(playerId));
  let tries = 0;
  const timer = setInterval(() => {
    tries += 1;
    let d = 0;
    try {
      const p = ytPlayers[playerId];
      d = p && p.getDuration ? p.getDuration() : 0;
    } catch { d = 0; }
    if (d > 0 || tries >= 24) {
      clearInterval(timer);
      durWatches.delete(playerId);
      onDuration(d > 0 ? d : null);
    }
  }, 500);
  durWatches.set(playerId, timer);
}
async function previewYouTube(videoId, els, onDuration) {
  try {
    const YT = await loadYouTubeApi();
    $(els.wrap).hidden = false;
    if (ytPlayers[els.player]) {
      ytPlayers[els.player].loadVideoById(videoId);
    } else {
      ytPlayers[els.player] = new YT.Player(els.player, {
        width: '480', height: '270', videoId,
        events: {
          onError: () => {
            $(els.status).textContent +=
              ' The preview could not play this video here (it may have embedding turned off); the link check above is what counts.';
          },
        },
      });
    }
    if (onDuration) watchPlayerDuration(els.player, onDuration);
  } catch { if (onDuration) onDuration(null); /* preview is best-effort */ }
}

$('ytCheckBtn').addEventListener('click', async () => {
  clearError();
  const url = $('ytLink').value.trim();
  const videoId = parseYouTubeVideoId(url);
  if (!videoId) {
    $('ytStatus').textContent = 'That does not look like a YouTube video link.';
    return;
  }
  if (!cfg.worker) {
    $('ytStatus').textContent = 'The teacher’s configured link is needed to check the link.';
    return;
  }
  $('ytStatus').textContent = 'Checking…';
  ytCheck = null;
  ytDur = null;
  $('ytConfirmChk').checked = false;
  refreshYtDurationUi();
  try {
    const res = await requestYouTubeCheck(cfg.worker, canonicalWatchUrl(videoId));
    if (res.status === 'ok' && res.video_id === videoId && res.token) {
      // The check is bound to the recording loaded right now: its
      // fingerprint travels with the check, and changing the
      // recording voids the check (clearYtCheck).
      ytCheck = {
        videoId, token: res.token, checkedAt: res.checked_at,
        title: res.title || '', audioSha256: audioSha,
      };
      $('ytStatus').textContent = 'Link checks out: the video is reachable (Unlisted or Public).' +
        (res.title ? ' Video title: “' + res.title + '”.' : '');
    } else {
      $('ytStatus').textContent =
        'YouTube reports this video as private or missing. Set it to Unlisted or Public and check again.';
    }
  } catch (err) {
    $('ytStatus').textContent = 'The check could not be completed. Try again.';
    console.error(err);
  }
  refreshYtDurationUi();
  if (ytCheck) {
    const checkedSha = ytCheck.audioSha256;
    previewYouTube(videoId,
      { wrap: 'ytPlayerWrap', player: 'ytPlayer', status: 'ytStatus' },
      (videoS) => {
        if (!ytCheck || ytCheck.videoId !== videoId) return; // stale
        const cls = classifyDuration(durationS, videoS || 0);
        ytDur = { ...cls, audioS: durationS, videoS };
        refreshYtDurationUi();
        if (videoS) reportDurationOnce('send', checkedSha, videoId, durationS, videoS);
      });
  }
  updateJobEnabled();
});

$('submitJobBtn').addEventListener('click', async () => {
  clearError();
  $('submitJobBtn').disabled = true;
  $('jobStatus').textContent = 'Preparing…';
  try {
    if (ytCheck && ytCheck.audioSha256 !== audioSha) {
      throw new Error('the YouTube link was checked against a different recording. Check the link again for this recording.');
    }
    if (ytCheck && !durationGateOk(ytDur, $('ytConfirmChk'))) {
      throw new Error(ytDur && ytDur.band === 'block'
        ? 'the checked video’s length differs from this recording’s by more than the allowed tolerance. Enter the link for this recording, or clear the link to send for practice grading only.'
        : 'play the preview and tick the confirmation that the checked video is this recording, or clear the link to send without it.');
    }
    const transcript = canonical();
    const transcriptSha = await sha256Hex(transcript);
    const payload = buildJobPayload({
      pkg: cfg.pkg,
      pkgContentSha256: cfg.ph,
      kind: kind(),
      transcript,
      audioSha256: audioSha,
      transcriptSha256: transcriptSha,
      versions: VERSIONS,
      retrievalCode: $('retrievalCode').value,
      youtubeToken: ytCheck ? ytCheck.token : null,
      youtubeVideoId: ytCheck ? ytCheck.videoId : null,
      youtubeCheckedAt: ytCheck ? ytCheck.checkedAt : null,
    });
    const check = validateJobPayload(payload);
    if (!check.ok) throw new Error(check.reason);
    $('jobStatus').textContent = 'Sending for grading…';
    const res = await submitJob(cfg.worker, payload);
    addJobEntry({
      pkg: cfg.pkg,
      course: cfg.course,
      asg: cfg.asg,
      retrieval_code: payload.retrieval_code,
      kind: payload.kind,
      youtube_link: payload.kind === 'final' ? $('ytLink').value.trim() : '',
      youtube_title: payload.kind === 'final' && ytCheck ? ytCheck.title : '',
      youtube_checked_at: payload.kind === 'final' && ytCheck ? ytCheck.checkedAt : '',
      created_at: res.created_at,
      expires_at: res.expires_at,
    });
    $('jobStatus').textContent =
      'Sent' + (payload.kind === 'final'
        ? ' with the checked link — submission-ready as soon as it is graded.'
        : ' — when the grade is back, turn it into your Canvas submission from the list below.') +
      ' The list below updates every 5 seconds while this page is open. ' +
      'An ungraded job is kept for 7 days; once graded, the grade is kept for 48 hours.';
    renderJobs();
  } catch (err) {
    showError('Sending for grading failed: ' + err.message, err, $('submitJobBtn'));
    // The reason also goes in the status line beside the button,
    // where the student is looking. Nothing is recorded in the
    // job list for a failed send.
    $('jobStatus').textContent = 'Sending failed: ' + err.message;
  } finally {
    updateJobEnabled();
  }
});

// --- Retrieval: jobs list, grades reveal, ZIP download ---
function jobKey(pkg, code) { return pkg + '|' + code; }

async function wavBytesForBundle(bundle) {
  if (wavBytes && audioSha === bundle.audio_sha256) return wavBytes;
  const record = await cacheGet(bundle.audio_sha256, VERSIONS.model, VERSIONS.glossary)
    .catch(() => null);
  if (record && record.wavBlob) {
    return new Uint8Array(await record.wavBlob.arrayBuffer());
  }
  return null;
}

// Verified submission parts, per job, held between the review step
// and the download step: jobKey -> { receipt, parts, lines }.
const zipReviews = new Map();

// Verify everything that will go into the ZIP against the signed
// result bundle, before anything is packaged:
// - the WAV is the recording the job was graded on: it is fetched by
//   the bundle's audio fingerprint and its SHA-256 is recomputed
//   over the exact bytes to be packaged;
// - the transcript is built from THAT recording's own cached chunks
//   (never from whatever transcript happens to be on the page) and
//   its canonical checksum must equal the signed transcript_sha256 —
//   a different removal list in step 3 is the usual cause of a
//   mismatch, and the error says so;
// - the critique's SHA-256 must equal the signed critique_sha256;
// - the locally kept YouTube link's video ID must hash to the
//   bundle's signed youtube_video_sha256.
// Returns the verified parts, or null with the error shown beside
// the button that was used.
async function verifySubmissionParts(entry, bundle, anchor) {
  const record = await cacheGet(bundle.audio_sha256, VERSIONS.model, VERSIONS.glossary)
    .catch(() => null);
  const wav = await wavBytesForBundle(bundle);
  if (!wav || !record) {
    showError('The audio for this job is not on this computer. The job’s ' +
      'recording has fingerprint ' + bundle.audio_sha256.slice(0, 12) + '… — ' +
      'choose that recording’s file in step 2, or restore it from the saved ' +
      'recordings list there, then try again.', null, anchor);
    return null;
  }
  if (!record.chunks || !record.chunks.length) {
    showError('The transcript pieces for this job’s recording are not on ' +
      'this computer, so the packaged transcript cannot be verified against ' +
      'the graded one. Restore the recording in step 2 (fingerprint ' +
      bundle.audio_sha256.slice(0, 12) + '…) and try again.', null, anchor);
    return null;
  }
  const scrubbedChunks = scrubChunks(
    record.chunks.map(fromCachedChunk), scrubWords());
  const [wavSha, markedSha, legacySha, critiqueSha] = await Promise.all([
    sha256Hex(wav),
    sha256Hex(canonicalTranscript(scrubbedChunks)),
    sha256Hex(legacyCanonicalTranscript(scrubbedChunks)),
    sha256Hex(bundle.critique || ''),
  ]);
  // A bundle graded before 2.4.2 was signed over the markerless
  // canonical form; accept that form for such a bundle, and the
  // current marked form otherwise. Either way the hash must equal
  // the signed checksum exactly.
  const transcriptSha = legacySha === bundle.transcript_sha256
    ? legacySha : markedSha;
  const failures = verifyBundleContents(bundle, {
    wavSha256: wavSha, transcriptSha256: transcriptSha,
    critiqueSha256: critiqueSha,
  });
  if (failures.includes('audio')) {
    showError('The audio on this computer does not match the audio this ' +
      'job was graded on (fingerprint mismatch). Restore the recording ' +
      'with fingerprint ' + bundle.audio_sha256.slice(0, 12) + '… in step 2 ' +
      'and try again.', null, anchor);
    return null;
  }
  if (failures.includes('transcript')) {
    showError('The transcript that would be packaged does not match the ' +
      'transcript that was graded (checksum mismatch). The usual cause is ' +
      'the removal list in step 3: re-enter the same names and words you ' +
      'used when you sent this job, then try again.', null, anchor);
    return null;
  }
  if (failures.includes('critique')) {
    showError('The critique in the grade record does not match its signed ' +
      'checksum, so nothing was packaged. Retrieve the job again and retry.',
    null, anchor);
    return null;
  }
  // The HTML's YouTube link comes from local keeping only; cross-check
  // it against the signed bundle: the SHA-256 of its video ID must
  // equal the bundle's youtube_video_sha256.
  const link = entry.youtube_link || '';
  const videoId = parseYouTubeVideoId(link);
  if (!videoId) {
    showError('The YouTube link kept on this browser is missing. Re-enter it in step 6 and download again from the job list after re-checking.', null, anchor);
    return null;
  }
  const videoIdSha = await sha256Hex(videoId);
  if (bundle.youtube_video_sha256 && bundle.youtube_video_sha256 !== videoIdSha) {
    showError('The YouTube link kept on this browser is not the video that was checked for this job.', null, anchor);
    return null;
  }
  return { wav, scrubbedChunks, record, videoId };
}

// First click on a ready final job's ZIP button: verify, then show
// the review panel in the job's row (renderJobRow renders it from
// zipReviews, so it survives the 5-second list refresh). The panel's
// own button performs the download from the verified parts.
async function downloadSubmissionZip(entry, bundle, anchor) {
  clearError();
  const parts = await verifySubmissionParts(entry, bundle, anchor);
  if (!parts) return;
  const words = scrubWords();
  const label = [entry.course, entry.asg].filter(Boolean).join(' · ') || entry.pkg;
  const recName = parts.record.source_name
    ? scrubMetadata(parts.record.source_name, words) + ' · ' : '';
  const firstWords = recordingFirstWords(parts.record.chunks);
  const lines = [
    label + ' — ' + entry.pkg,
    'Grades: Completeness ' + bundle.completeness + '/5 · Accuracy ' +
      bundle.accuracy + '/5',
    'Recording: ' + recName + formatDuration(parts.record.duration_s) +
      ' · fingerprint ' + bundle.audio_sha256.slice(0, 12) + '…' +
      (firstWords
        ? ' · starts “' + scrubMetadata(firstWords, words) + '…”' : ''),
    'Audio: matches the fingerprint signed with the grade ✓',
    'Transcript: matches the checksum signed with the grade ✓',
    'YouTube: ' + (entry.youtube_title ? '“' + entry.youtube_title + '” · ' : '') +
      canonicalWatchUrl(parts.videoId) +
      ' · the video checked for this job ✓',
    'Check the recording and the video title are yours, then download.',
  ];
  zipReviews.set(jobKey(entry.pkg, entry.retrieval_code), {
    receipt: bundle.receipt, parts, lines,
  });
  renderJobs();
}

async function doDownloadZip(entry, bundle, review, anchor) {
  const { parts } = review;
  const html = assemblePackage({
    youtubeLink: canonicalWatchUrl(parts.videoId),
    audioFileName: AUDIO_FILE_NAME,
    durationS: parts.record.duration_s,
    chunks: parts.scrubbedChunks,
    bundle,
  });
  const zip = buildZip([
    { name: ZIP_ENTRY_HTML, data: new TextEncoder().encode(html) },
    { name: ZIP_ENTRY_AUDIO, data: parts.wav },
  ]);
  downloadBlob(zip, submissionZipName({
    course: entry.course, asg: entry.asg,
    completeness: bundle.completeness, accuracy: bundle.accuracy,
    youtubeCheckedAt: entry.youtube_checked_at, gradedAt: bundle.t,
  }));
  zipReviews.delete(jobKey(entry.pkg, entry.retrieval_code));
  try {
    await markJobRetrieved(cfg.worker, {
      pkg: entry.pkg, retrieval_code: entry.retrieval_code,
    });
  } catch { /* the ZIP is already in the student's hands */ }
  removeJobEntry(entry.pkg, entry.retrieval_code);
  renderJobs();
}

function renderJobRow(container, entry, statusInfo) {
  const row = document.createElement('div');
  row.className = 'jobrow';
  const label = [entry.course, entry.asg].filter(Boolean).join(' · ') || entry.pkg;
  let statusText;
  if (statusInfo === null) statusText = 'checking…';
  else if (statusInfo.status === 'forbidden') statusText = 'not found under this code';
  else if (statusInfo.status === 'ready') statusText = 'ready';
  else if (statusInfo.status === 'claimed') statusText = 'being graded now';
  else if (statusInfo.status === 'queued') {
    const ahead = statusInfo.queue_ahead;
    statusText = typeof ahead === 'number'
      ? (ahead === 0 ? 'waiting — next in the grading queue'
        : 'waiting — ' + ahead + (ahead === 1 ? ' job' : ' jobs') + ' ahead')
      : 'waiting';
  } else statusText = statusInfo.status;
  row.append(document.createTextNode(
    label + ' (' + entry.kind + '): ' + statusText + ' '));
  if (statusInfo && statusInfo.status === 'ready') {
    const bundle = readyBundles.get(jobKey(entry.pkg, entry.retrieval_code));
    const key = jobKey(entry.pkg, entry.retrieval_code);
    const showBtn = document.createElement('button');
    showBtn.textContent = expandedJobs.has(key) ? 'Hide grades and critique' : 'Show grades and critique';
    const detail = document.createElement('div');
    detail.hidden = !expandedJobs.has(key);
    if (bundle) {
      detail.innerHTML = '';
      const p = document.createElement('p');
      p.textContent = 'Completeness: ' + bundle.completeness + '/5 · Accuracy: ' +
        bundle.accuracy + '/5';
      const rec = document.createElement('p');
      rec.textContent = 'Recording fingerprint: ' +
        (bundle.audio_sha256 || '').slice(0, 12) + '…' +
        (entry.youtube_title ? ' · YouTube: “' + entry.youtube_title + '”' : '');

      const crit = document.createElement('div');
      crit.className = 'box';
      // The critique is a numbered list, one point per line:
      // keep the line breaks when it is shown (the submission
      // HTML does the same with white-space: pre-line).
      crit.style.whiteSpace = 'pre-line';
      crit.textContent = bundle.critique || '';
      detail.append(p, rec, crit);
    }
    showBtn.addEventListener('click', () => {
      detail.hidden = !detail.hidden;
      if (detail.hidden) expandedJobs.delete(key); else expandedJobs.add(key);
      showBtn.textContent = detail.hidden ? 'Show grades and critique' : 'Hide grades and critique';
    });
    row.append(showBtn, detail);
    if (entry.kind === 'final' && bundle) {
      const zipBtn = document.createElement('button');
      zipBtn.className = 'primary';
      zipBtn.textContent = 'Review and download submission ZIP';
      zipBtn.addEventListener('click', () => downloadSubmissionZip(entry, bundle, zipBtn));
      row.append(document.createTextNode(' '), zipBtn);
      // The review panel from a completed verification (see
      // downloadSubmissionZip): every item that will be packaged,
      // identified and checked, with the actual download button.
      const review = zipReviews.get(key);
      if (review && review.receipt === bundle.receipt) {
        const panel = document.createElement('div');
        panel.className = 'box';
        for (const line of review.lines) {
          const p = document.createElement('p');
          p.textContent = line;
          panel.append(p);
        }
        const dlBtn = document.createElement('button');
        dlBtn.className = 'primary';
        dlBtn.textContent = 'Download submission ZIP';
        dlBtn.addEventListener('click', () => doDownloadZip(entry, bundle, review, dlBtn));
        panel.append(dlBtn);
        row.append(panel);
      }
    }
    // No per-row conversion button: the conversion panel's picker is
    // the single route to turning a graded job into the submission.
  }
  const forgetBtn = document.createElement('button');
  forgetBtn.textContent = 'Remove from this browser';
  forgetBtn.addEventListener('click', () => {
    removeJobEntry(entry.pkg, entry.retrieval_code);
    renderJobs();
  });
  row.append(document.createTextNode(' '), forgetBtn);
  container.append(row);
}

async function renderJobs() {
  const box = $('jobsBox');
  // The stored expires_at is a cache, not the authority: an entry
  // written before 2.4.1 carries creation + 48 h, while the Worker
  // now keeps an ungraded job for 7 days. Entries are therefore NOT
  // pruned on the stored value here; every entry is asked about, and
  // an entry is dropped only when the Worker reports the job expired
  // (or the list is saved back with the corrected expiry, below).
  const entries = loadJobEntries();
  if (!entries.length) {
    box.textContent = 'No jobs sent from this browser yet.';
    refreshFinPanel();
    return;
  }
  box.textContent = '';
  let entriesDirty = false;
  const survivors = [];
  for (const entry of entries) {
    const key = jobKey(entry.pkg, entry.retrieval_code);
    let res = null;
    try {
      res = await fetchJobStatus(cfg.worker, {
        pkg: entry.pkg, retrieval_code: entry.retrieval_code,
      });
    } catch { /* offline or Worker error: keep the entry, render last known */ }
    if (res && res.status === 'expired') {
      // The Worker has deleted the job; drop the entry and its row.
      entriesDirty = true;
      readyBundles.delete(key);
      jobStates.delete(key);
      continue;
    }
    survivors.push(entry);
    const holder = document.createElement('div');
    box.append(holder);
    renderJobRow(holder, entry, jobStates.get(key) || null);
    if (res) {
      // The Worker reports the job's current expiry (7 days while
      // ungraded, 48 hours after grading); keep the stored entry in
      // step with it.
      if (res.data && res.data.expires_at &&
          entry.expires_at !== res.data.expires_at) {
        entry.expires_at = res.data.expires_at;
        entriesDirty = true;
      }
      if (res.status === 'ready' && res.data && res.data.result) {
        readyBundles.set(key, res.data.result);
      }
      jobStates.set(key, {
        status: res.status,
        queue_ahead: res.data ? res.data.queue_ahead : undefined,
      });
      holder.textContent = '';
      renderJobRow(holder, entry, jobStates.get(key));
    }
  }
  if (!survivors.length && entries.length) {
    box.textContent = 'No jobs sent from this browser yet.';
  }
  if (entriesDirty) saveJobEntries(survivors);
  refreshFinPanel();
}

// The jobs list refreshes itself every 5 seconds while the page is
// open, so a waiting student sees the queue move and the grade arrive
// without reloading — no notification is needed. Refreshes pause
// while the tab is hidden and never overlap.
let jobsRefreshInFlight = false;
async function refreshJobs() {
  if (jobsRefreshInFlight || document.hidden) return;
  jobsRefreshInFlight = true;
  try { await renderJobs(); } catch { /* the next tick retries */ }
  jobsRefreshInFlight = false;
}
setInterval(refreshJobs, 5000);

// --- Conversion: turn a graded job into the Canvas submission ---
let finCheck = null;
let finManualEntry = null;
let finPrevSelKey = null;

function conversionCandidates() {
  const out = [];
  for (const entry of loadJobEntries()) {
    const key = jobKey(entry.pkg, entry.retrieval_code);
    const st = jobStates.get(key);
    const bundle = readyBundles.get(key);
    if (entry.kind === 'practice' && st && st.status === 'ready' && bundle) {
      out.push({ entry, bundle });
    }
  }
  if (finManualEntry && finManualEntry.kind === 'practice') {
    const key = jobKey(finManualEntry.pkg, finManualEntry.retrieval_code);
    const bundle = readyBundles.get(key);
    if (bundle) out.push({ entry: finManualEntry, bundle });
  }
  return out;
}

function refreshFinPanel(preferKey) {
  const panel = $('finPanel');
  if (!panel) return;
  const cands = conversionCandidates();
  if (!cands.length) { panel.hidden = true; finPrevSelKey = null; return; }
  panel.hidden = false;
  const sel = $('finJobSel');
  const prev = preferKey || sel.value;
  sel.textContent = '';
  for (const c of cands) {
    const opt = document.createElement('option');
    opt.value = jobKey(c.entry.pkg, c.entry.retrieval_code);
    const label = [c.entry.course, c.entry.asg].filter(Boolean).join(' · ') || c.entry.pkg;
    opt.textContent = label +
      ' — Completeness ' + c.bundle.completeness + '/5, Accuracy ' +
      c.bundle.accuracy + '/5 · recording ' +
      (c.bundle.audio_sha256 || '').slice(0, 8) + '…' +
      (c.bundle.t ? ' — graded ' + new Date(c.bundle.t).toLocaleString() : '');
    sel.append(opt);
  }
  const latest = cands[cands.length - 1];
  sel.value = cands.some((c) => jobKey(c.entry.pkg, c.entry.retrieval_code) === prev)
    ? prev : jobKey(latest.entry.pkg, latest.entry.retrieval_code);
  // The picker is rebuilt on every jobs-list refresh, so it tracks
  // graded jobs being added or removed at once. If a rebuild changed
  // which job is selected (the selected job was removed, so the
  // latest took its place), a link check already made was for a
  // different job and no longer stands — the select's own change
  // event does not fire for a programmatic change.
  if (finPrevSelKey !== null && sel.value !== finPrevSelKey) finResetCheck();
  finPrevSelKey = sel.value;
}

function finSelected() {
  const key = $('finJobSel').value;
  return conversionCandidates().find(
    (c) => jobKey(c.entry.pkg, c.entry.retrieval_code) === key) || null;
}

async function finJobAudioDurationS(cand) {
  if (audioSha && audioSha === cand.bundle.audio_sha256 && durationS > 0) return durationS;
  const record = await cacheGet(cand.bundle.audio_sha256, VERSIONS.model, VERSIONS.glossary)
    .catch(() => null);
  return record && record.duration_s ? record.duration_s : 0;
}

function finResetCheck() {
  finCheck = null;
  finDur = null;
  $('finConfirmChk').checked = false;
  $('finConfirmBtn').disabled = true;
  $('finStatus').textContent = '';
  $('finDone').textContent = '';
  $('finPlayerWrap').hidden = true;
  refreshFinDurationUi();
}
$('finJobSel').addEventListener('change', finResetCheck);
$('finLink').addEventListener('input', () => {
  finCheck = null;
  finDur = null;
  $('finConfirmChk').checked = false;
  $('finConfirmBtn').disabled = true;
  $('finPlayerWrap').hidden = true;
  refreshFinDurationUi();
});

$('finCheckBtn').addEventListener('click', async () => {
  clearError();
  const cand = finSelected();
  if (!cand) return;
  const videoId = parseYouTubeVideoId($('finLink').value.trim());
  if (!videoId) {
    $('finStatus').textContent = 'That does not look like a YouTube video link.';
    return;
  }
  if (!cfg.worker) {
    $('finStatus').textContent = 'The teacher’s configured link is needed to check the link.';
    return;
  }
  $('finStatus').textContent = 'Checking…';
  finCheck = null;
  finDur = null;
  $('finConfirmChk').checked = false;
  refreshFinDurationUi();
  try {
    const res = await requestYouTubeCheck(cfg.worker, canonicalWatchUrl(videoId));
    if (res.status === 'ok' && res.video_id === videoId && res.token) {
      finCheck = {
        videoId, tok: res.token, checkedAt: res.checked_at,
        title: res.title || '',
        jobKey: jobKey(cand.entry.pkg, cand.entry.retrieval_code),
      };
      $('finStatus').textContent = 'Link checks out: the video is reachable (Unlisted or Public).' +
        (res.title ? ' Video title: “' + res.title + '”.' : '');
    } else {
      $('finStatus').textContent =
        'YouTube reports this video as private or missing. Set it to Unlisted or Public and check again.';
    }
  } catch (err) {
    $('finStatus').textContent = 'The check could not be completed. Try again.';
    console.error(err);
  }
  refreshFinDurationUi();
  if (finCheck) {
    const dur = await finJobAudioDurationS(cand);
    if (!dur) {
      $('finStatus').textContent +=
        ' Load this job’s recording in step 2 to compare the video length with its audio.';
    }
    const checkedSha = cand.bundle.audio_sha256;
    previewYouTube(videoId,
      { wrap: 'finPlayerWrap', player: 'finPlayer', status: 'finStatus' },
      (videoS) => {
        if (!finCheck || finCheck.videoId !== videoId) return; // stale
        const cls = classifyDuration(dur, videoS || 0);
        finDur = { ...cls, audioS: dur, videoS };
        refreshFinDurationUi();
        if (videoS) reportDurationOnce('convert', checkedSha, videoId, dur, videoS);
      });
  }
});

$('finConfirmBtn').addEventListener('click', async () => {
  const cand = finSelected();
  if (!cand || !finCheck) return;
  if (finCheck.jobKey !== jobKey(cand.entry.pkg, cand.entry.retrieval_code)) {
    $('finDone').textContent = 'The link check was made for a different job. Check the link again.';
    return;
  }
  if (!durationGateOk(finDur, $('finConfirmChk'))) {
    $('finDone').textContent = finDur && finDur.band === 'block'
      ? 'The checked video’s length differs from this job’s audio by more than the allowed tolerance. Enter the link for this job’s recording.'
      : 'Play the preview and tick the confirmation that the checked video is this job’s recording.';
    return;
  }
  $('finConfirmBtn').disabled = true;
  $('finDone').textContent = 'Converting…';
  try {
    const payload = {
      pkg: cand.entry.pkg,
      retrieval_code: cand.entry.retrieval_code,
      youtube_video_id: finCheck.videoId,
      youtube_checked_at: finCheck.checkedAt,
    };
    payload['youtube' + '_token'] = finCheck.tok;
    await finalizeJob(cfg.worker, payload);
    if (cand.entry.manual) {
      cand.entry.kind = 'final';
      cand.entry.youtube_link = $('finLink').value.trim();
      cand.entry.youtube_title = finCheck.title || '';
      cand.entry.youtube_checked_at = finCheck.checkedAt;
    } else {
      const entries = loadJobEntries();
      const e = entries.find((x) => x.pkg === cand.entry.pkg &&
        x.retrieval_code === cand.entry.retrieval_code);
      if (e) {
        e.kind = 'final';
        e.youtube_link = $('finLink').value.trim();
        e.youtube_title = finCheck.title || '';
        e.youtube_checked_at = finCheck.checkedAt;
        saveJobEntries(entries);
      }
    }
    finCheck = null;
    $('finDone').textContent = 'Converted. Download the submission ZIP from the job’s row above.';
    await renderJobs();
  } catch (err) {
    $('finDone').textContent = 'Converting failed: ' + err.message;
    $('finConfirmBtn').disabled = false;
  }
});

// Manual retrieval (different browser): status by typed code
// against the configured package. On ready, the same rendering is
// used, with a synthetic entry; the ZIP path then needs the audio on
// this computer, as the section text states.
$('manualBtn').addEventListener('click', async () => {
  clearError();
  const code = $('manualCode').value;
  const box = $('manualBox');
  box.hidden = true;
  if (!cfg.worker || !cfg.pkg) {
    $('manualStatus').textContent = 'Open this assignment’s configured link to retrieve.';
    return;
  }
  $('manualStatus').textContent = 'Checking…';
  try {
    const res = await fetchJobStatus(cfg.worker, {
      pkg: cfg.pkg, retrieval_code: code,
    });
    if (res.status === 'forbidden') {
      $('manualStatus').textContent = 'No job under that code.';
      return;
    }
    $('manualStatus').textContent = 'Status: ' + res.status +
      (res.data && typeof res.data.queue_ahead === 'number' && res.status === 'queued'
        ? ' — ' + res.data.queue_ahead + (res.data.queue_ahead === 1 ? ' job' : ' jobs') + ' ahead in the grading queue.'
        : '.');
    if (res.status === 'ready' && res.data && res.data.result) {
      const entry = {
        pkg: cfg.pkg, course: cfg.course, asg: cfg.asg,
        retrieval_code: code,
        kind: res.data.result.youtube_video_sha256 && res.data.result.youtube_video_sha256 !== 'none'
          ? 'final' : 'practice',
        youtube_link: '',
        created_at: '', expires_at: (res.data && res.data.expires_at) || '',
      };
      // A final job retrieved manually needs its YouTube link for the
      // HTML; it is not stored anywhere off the original browser, so
      // the student enters it in step 6 and the row reads the live
      // entry at click time (the signed video hash check in
      // downloadSubmissionZip verifies it is the checked video).
      readyBundles.set(jobKey(entry.pkg, entry.retrieval_code), res.data.result);
      entry.manual = true;
      if (entry.kind === 'practice') {
        finManualEntry = entry;
        jobStates.set(jobKey(entry.pkg, entry.retrieval_code), { status: 'ready' });
        refreshFinPanel(jobKey(entry.pkg, entry.retrieval_code));
      }
      entry.youtube_link = $('ytLink').value.trim();
      $('ytLink').addEventListener('input', () => {
        entry.youtube_link = $('ytLink').value.trim();
      });
      box.hidden = false;
      box.textContent = '';
      const note = document.createElement('p');
      note.className = 'note';
      note.textContent = entry.kind === 'final'
        ? 'Final job. Enter the YouTube link in step 6 (it is checked against the signed record when the ZIP is built), then use Review and download submission ZIP here.'
        : 'Practice job.';
      box.append(note);
      renderJobRow(box, entry, 'ready');
    }
  } catch (err) {
    $('manualStatus').textContent = 'The check could not be completed. Try again.';
    console.error(err);
  }
});

renderConfig();
refreshDerived();
renderCacheList();
renderJobs();
