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
  VERSIONS, AUDIO_FILE_NAME, FINGERPRINT_FILE_NAME, assemblePackage,
  chunksFromCanonical, formatTranscriptTimestamp,
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
  verifyBundleContents, bundleChromaprintSha, verifyFingerprintContents,
  validateJobPayload, buildJobPayload, generateRetrievalToken, loadJobEntries, addJobEntry,
  removeJobEntry, saveJobEntries, kindFromResultBundle,
  duplicateJobEntry, collapseSameJobEntries,
  requestYouTubeCheck, submitJob, fetchJobStatus, markJobRetrieved,
  finalizeJob, reportDurationStat,
} from './jobs.js';
import { computeFingerprint } from './fingerprint.js';
import { decodeRawFingerprint } from './fingerprint.js';
import { buildZipAsync, submissionZipName, ZIP_ENTRY_HTML, ZIP_ENTRY_AUDIO } from './zip.js';

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
let vocabulary = null;
let ytCheck = null;         // { videoId, token, checkedAt, title, audioSha256 } after an ok check
let chromaprint = null;     // raw Chromaprint as base64 (2.6.0), or null when none computed
let chromaprintSha = null;  // audioSha the stored fingerprint was computed from
let chromaprintPending = null; // in-flight computeFingerprint promise, if any
let ytDur = null;           // duration comparison for the step-6 check:
// { band, diffS, tolS, audioS, videoS } once the preview reports the
// video's length; null until then (treated as band 'unknown').
let finDur = null;          // the same, for the conversion panel
let ytApiPromise = null;
const readyBundles = new Map(); // "pkg|code" -> result bundle from /jobs/status
const readyExtras = new Map();  // "pkg|code" -> {transcript, chromaprint} from
// the same status response (Worker 2.7.0): the stored transcript text and the
// raw fingerprint as base64, kept in memory only, for the fingerprint-form ZIP
const jobStates = new Map();    // "pkg|code" -> {status, queue_ahead} last seen
const statusFailures = new Map(); // "pkg|code" -> consecutive failed status fetches
const expandedJobs = new Set(); // "pkg|code" with the detail panel open (kept across refreshes)

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
  $('ytStatus').textContent =
    'Recording changed: the earlier link check no longer stands. Paste the link to check it again.';
  refreshYtDurationUi();
  updateJobEnabled();
}

// Whether a checked link may be used, given its duration band
// (2.6.8: no played-preview confirmation — the length comparison
// is the check). 'pass' and 'confirm' are within the tolerance and
// may be used; 'unknown' (the preview reported no length) may be
// used, because the Worker reachability check is the requirement
// and sameness of recording is established by the teacher audit's
// acoustic cross-check on the submitted ZIP; 'block' can never be
// used for this recording.
function durationGateOk(dur) {
  const band = dur ? dur.band : 'unknown';
  return band !== 'block';
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
  // Small version indicator under the title, so a screenshot or a
  // shared screen shows which release the student is running. The
  // text is the same version string the submission package carries.
  $('appVersion').textContent = VERSIONS.webapp;
  const parts = [];
  if (cfg.course) parts.push('Course: ' + cfg.course);
  if (cfg.asg) parts.push('Assignment: ' + cfg.asg);
  if (cfg.pkg) parts.push('Prompt package: ' + cfg.pkg);
  $('cfgLine').textContent = parts.length
    ? 'Configuration — ' + parts.join(' · ')
    : 'Configuration: none in this link. The teacher’s configured link sets the course, the prompt package, and the grading service.';
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
// The model loads automatically when the page opens (2.6.4); the
// button remains only as the retry after a failed load, and in
// teacher setup mode, where nothing loads on its own.
let modelLoading = false;
async function startModelLoad() {
  if (model || modelLoading) return;
  modelLoading = true;
  clearError();
  $('loadBtn').hidden = true;
  $('loadProg').hidden = false;
  $('loadStatus').textContent = 'Loading model…';
  try {
    model = await loadModel(onDownloadProgress);
    $('loadProg').hidden = true;
    $('loadStatus').textContent = 'Model loaded.';
    updateRunEnabled();
  } catch (err) {
    $('loadProg').hidden = true;
    $('loadStatus').textContent = 'Model did not load.';
    $('loadBtn').hidden = false;
    showError('Model loading failed. Check the connection and try again.', err, $('loadBtn'));
  } finally {
    modelLoading = false;
  }
}
$('loadBtn').addEventListener('click', startModelLoad);

// --- Media stage + cache ---
function updateRunEnabled() { $('runBtn').disabled = !(model && pcm); }

function setAudioMeta() {
  if (!audioSha) { $('audioMeta').textContent = ''; return; }
  $('audioMeta').textContent =
    (sourceName ? 'Source file: ' + scrubMetadata(sourceName, scrubWords()) + ' · ' : '') +
    'duration ' + durationS.toFixed(1) + ' s' +
    ' · extracted audio: ' + AUDIO_FILE_NAME +
    ' · recording hash (SHA-256) ' + audioSha;
}

// Compute the Chromaprint (2.6.0) once from the normalised WAV's own
// int16 samples — the same samples the audio SHA-256 is computed
// over — and keep it in state for the job payload. Runs in the
// background after normalisation; a failure leaves chromaprint null
// and the job is sent without it. Never awaited by the media stage:
// the submit handler awaits the in-flight promise, if any, before
// building the payload.
async function refreshFingerprint() {
  if (!wavBytes || wavBytes.length <= 44 || !audioSha) return;
  if (audioSha === chromaprintSha) return;
  if (chromaprintPending) { await chromaprintPending; return; }
  const sha = audioSha;
  const samples = new Int16Array(
    wavBytes.buffer, wavBytes.byteOffset + 44, (wavBytes.length - 44) / 2);
  const p = computeFingerprint(samples);
  chromaprintPending = p;
  const res = await p;
  if (chromaprintPending !== p) return; // superseded by a newer recording
  chromaprintPending = null;
  if (sha !== audioSha) return; // the recording changed meanwhile
  chromaprint = res ? res.rawBase64 : null;
  chromaprintSha = sha;
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
  chromaprint = null; chromaprintSha = null; chromaprintPending = null;
  chunks = []; windowsDoneBase = 0;
  transcriptionComplete = false;
  updateRunEnabled();
  if (!file) { $('mediaStatus').textContent = 'No file chosen.'; return; }
  sourceName = file.name;
  $('mediaStatus').textContent = 'Reading the file…';
  try {
    pcm = await decodeFileTo16kMono(file, () => {
      $('mediaStatus').textContent =
        'This browser could not read that file directly, so the audio is being extracted another way…';
    });
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
    refreshFingerprint();
  } catch (err) {
    $('mediaStatus').textContent = 'That file could not be decoded.';
    showError('This browser could not decode the chosen file as audio or video.', err, $('mediaFile'));
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
      ' · recording hash ' + entry.audio_sha256.slice(0, 12) + '…' + wordsPart;
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
        chromaprint = null; chromaprintSha = null; chromaprintPending = null;
        updateRunEnabled();
        await adoptCacheRecord(record, 'Recording restored from this computer.');
        refreshFingerprint();
      } catch (err) { showError('That saved recording could not be restored.', err, restoreBtn); }
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
      ' s elapsed; the page may appear to pause while a piece is processed.';
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
      : 'No text came back from the model for this recording.';
  } catch (err) {
    showError('Transcription failed or stopped partway. Pieces already shown are kept and saved; choosing the same file again resumes.', err, $('runBtn'));
    $('runStatus').textContent = '';
  } finally {
    clearInterval(timer);
    $('runProg').hidden = true;
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
    $('transcriptBox').textContent = 'Your transcript will appear here.';
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

// --- Job section ---
function updateJobEnabled() {
  const base = !!(cfg.worker && cfg.pkg && cfg.ph && transcriptionComplete);
  // With a checked link, the duration gate also applies: a blocked
  // link (length beyond the tolerance) disables Send until the link
  // is fixed or cleared.
  const linkOk = !ytCheck || durationGateOk(ytDur);
  $('submitJobBtn').disabled = !(base && linkOk);
}

// The duration verdict for the step-6 link, in its own status line
// beside the preview (2.6.8: a statement, not a gate — within the
// tolerance the link may be used, beyond it it may not).
function refreshYtDurationUi() {
  const el = $('ytDurStatus');
  if (!ytCheck) { el.textContent = ''; return; }
  const band = ytDur ? ytDur.band : 'unknown';
  if (band === 'pass') {
    el.textContent = 'Lengths match: video ' + ytDur.videoS.toFixed(1) +
      ' s, audio ' + ytDur.audioS.toFixed(1) + ' s (difference ' +
      ytDur.diffS.toFixed(1) + ' s).';
  } else if (band === 'confirm') {
    el.textContent = 'Video ' + ytDur.videoS.toFixed(1) +
      ' s, audio ' + ytDur.audioS.toFixed(1) + ' s — a difference of ' +
      ytDur.diffS.toFixed(1) + ' s, within the allowed ' +
      ytDur.tolS.toFixed(1) + ' s.';
  } else if (band === 'block') {
    el.textContent = 'Video ' + ytDur.videoS.toFixed(1) +
      ' s, audio ' + ytDur.audioS.toFixed(1) + ' s — a difference of ' +
      ytDur.diffS.toFixed(1) + ' s, beyond the allowed ' + ytDur.tolS.toFixed(1) +
      ' s. This link cannot be used for this recording: enter the link for ' +
      'this recording, or clear the link and send without it.';
  } else {
    el.textContent = 'No length has been reported by the preview, so ' +
      'the lengths could not be compared. The link check above is what counts.';
  }
  updateJobEnabled();
}

// The same verdict for the conversion panel's link.
function refreshFinDurationUi() {
  const el = $('finDurStatus');
  if (!finCheck) { el.textContent = ''; updateFinConfirmEnabled(); return; }
  const band = finDur ? finDur.band : 'unknown';
  if (band === 'pass') {
    el.textContent = 'Lengths match: video ' + finDur.videoS.toFixed(1) +
      ' s, audio ' + finDur.audioS.toFixed(1) + ' s (difference ' +
      finDur.diffS.toFixed(1) + ' s).';
  } else if (band === 'confirm') {
    el.textContent = 'Video ' + finDur.videoS.toFixed(1) +
      ' s, selected job’s audio ' + finDur.audioS.toFixed(1) +
      ' s — a difference of ' + finDur.diffS.toFixed(1) + ' s, within the ' +
      'allowed ' + finDur.tolS.toFixed(1) + ' s.';
  } else if (band === 'block') {
    el.textContent = 'Video ' + finDur.videoS.toFixed(1) +
      ' s, selected job’s audio ' + finDur.audioS.toFixed(1) +
      ' s — a difference of ' + finDur.diffS.toFixed(1) + ' s, beyond the ' +
      'allowed ' + finDur.tolS.toFixed(1) + ' s. This link cannot be used ' +
      'for this job.';
  } else {
    el.textContent = 'No length has been reported by the preview, so ' +
      'the lengths could not be compared. The link check above is what counts.';
  }
  updateFinConfirmEnabled();
}

function updateFinConfirmEnabled() {
  $('finConfirmBtn').disabled =
    !(finCheck && durationGateOk(finDur));
}

// YouTube: the link invalidates any earlier check when it changes,
// and a recognisable link is checked by itself (2.6.8) — the check
// runs after a short pause following the last keystroke, so typing
// a link does not fire a check per character, and pasting fires one.
let ytCheckTimer = null;
let ytCheckBusy = false;
let ytCheckRearms = 0;
$('ytLink').addEventListener('input', () => {
  ytCheck = null;
  ytDur = null;
  ytCheckRearms = 0;
  $('ytStatus').textContent = '';
  $('ytPlayerWrap').hidden = true;
  refreshYtDurationUi();
  updateJobEnabled();
  if (ytCheckTimer) clearTimeout(ytCheckTimer);
  ytCheckTimer = setTimeout(runYtCheck, 700);
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
// conversion flows gate on (only 'block' bars use). A true acoustic
// fingerprint comparison cannot run here, because the browser
// cannot read the video's audio track (YouTube serves it only
// inside its own player); sameness of recording is established by
// the teacher audit's acoustic cross-check on the submitted ZIP. A
// preview failure (embedding disabled, sign-in required) leaves the
// band 'unknown', which does not bar use; the Worker reachability
// check remains a requirement throughout.
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

async function runYtCheck() {
  const url = $('ytLink').value.trim();
  const videoId = parseYouTubeVideoId(url);
  if (!videoId) return;
  if (ytCheckBusy) {
    // A check for an earlier link is still in flight; its result
    // will be discarded as stale. Re-arm so this link is checked
    // once that flight ends, instead of never being checked. The
    // re-arms are capped: a flight that never settles must not
    // leave a timer running with nothing on screen.
    if (ytCheckRearms >= 40) {
      $('ytStatus').textContent = 'The link check is taking a long time; edit the link to try again.';
      return;
    }
    ytCheckRearms += 1;
    $('ytStatus').textContent = 'Checking…';
    if (ytCheckTimer) clearTimeout(ytCheckTimer);
    ytCheckTimer = setTimeout(runYtCheck, 700);
    return;
  }
  if (ytCheck && ytCheck.videoId === videoId) return; // already checked
  ytCheckRearms = 0;
  if (!cfg.worker) {
    $('ytStatus').textContent = 'Open this page from the link your teacher put in Canvas to check the link.';
    return;
  }
  ytCheckBusy = true;
  $('ytStatus').textContent = 'Checking…';
  try {
    const res = await requestYouTubeCheck(cfg.worker, canonicalWatchUrl(videoId));
    if ($('ytLink').value.trim() !== url) return; // replaced while checking
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
    $('ytStatus').textContent = 'Could not complete the check. Try again.';
    console.error(err);
  } finally {
    ytCheckBusy = false;
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
}

// The queue state or grades of a duplicate response, for the
// status line, when no alias was created and so no job row exists to
// show them. Uses only the phrasings the jobs list already uses.
function duplicateStatusText(res) {
  if (res.status === 'ready' && res.result) {
    return 'Completeness: ' + res.result.completeness + '/5 · Accuracy: ' +
      res.result.accuracy + '/5';
  }
  if (res.status === 'claimed') return 'being graded now';
  if (res.status === 'queued') {
    const ahead = res.queue_ahead;
    return typeof ahead === 'number'
      ? (ahead === 0 ? 'waiting — next in the grading queue'
        : 'waiting — ' + ahead + (ahead === 1 ? ' job' : ' jobs') + ' ahead')
      : 'waiting';
  }
  return res.status || '';
}

$('submitJobBtn').addEventListener('click', async () => {
  clearError();
  $('submitJobBtn').disabled = true;
  $('jobStatus').textContent = 'Preparing…';
  try {
    if (ytCheck && ytCheck.audioSha256 !== audioSha) {
      throw new Error('the YouTube link was checked against a different recording. Check the link again for this recording.');
    }
    if (ytCheck && !durationGateOk(ytDur)) {
      throw new Error('the checked video’s length differs from this recording’s by more than the allowed tolerance. Enter the link for this recording, or clear the link and send without it.');
    }
    const transcript = canonical();
    const transcriptSha = await sha256Hex(transcript);
    // The fingerprint is computed in the background after
    // normalisation; wait for it here so the job carries it when it
    // is ready. A failure leaves chromaprint null and the job is
    // sent without it.
    if (chromaprintPending) await chromaprintPending;
    const payload = buildJobPayload({
      pkg: cfg.pkg,
      pkgContentSha256: cfg.ph,
      kind: kind(),
      transcript,
      audioSha256: audioSha,
      transcriptSha256: transcriptSha,
      chromaprint,
      versions: VERSIONS,
      retrievalCode: generateRetrievalToken(),
      youtubeToken: ytCheck ? ytCheck.token : null,
      youtubeVideoId: ytCheck ? ytCheck.videoId : null,
      youtubeCheckedAt: ytCheck ? ytCheck.checkedAt : null,
    });
    const check = validateJobPayload(payload);
    if (!check.ok) throw new Error(check.reason);
    $('jobStatus').textContent = 'Sending for grading…';
    const res = await submitJob(cfg.worker, payload);
    const sentText =
      'Sent' + (payload.kind === 'final'
        ? ' with the checked link — submission-ready as soon as it is graded.'
        : ' — when the grade is back, turn it into your Canvas submission from the list below.') +
      ' The list below updates every 5 seconds while this page is open. ' +
      'An ungraded job is kept for 7 days; once graded, the grade is kept for 180 days.';
    if (res.duplicate) {
      // The recording already has a live job under this prompt
      // package version: no new job was created. The entry is filed
      // under the submitted code (the alias), so the existing job
      // renders through the normal jobs-list path below — queue
      // state while queued or claimed, grades and critique when
      // ready — and finalize and ZIP work from it exactly as from
      // the original entry. When no alias was created the code does
      // not retrieve this job, so no entry is stored under it and
      // the grade or queue state from the response is shown in the
      // status line instead.
      const aliasEntry = duplicateJobEntry(res, {
        pkg: cfg.pkg,
        course: cfg.course,
        asg: cfg.asg,
        retrieval_code: payload.retrieval_code,
        kind: payload.kind,
        youtube_link: payload.kind === 'final' ? $('ytLink').value.trim() : '',
        youtube_title: payload.kind === 'final' && ytCheck ? ytCheck.title : '',
        youtube_checked_at: payload.kind === 'final' && ytCheck ? ytCheck.checkedAt : '',
      });
      if (aliasEntry) {
        addJobEntry(aliasEntry);
        const key = jobKey(cfg.pkg, payload.retrieval_code);
        jobStates.set(key, { status: res.status, queue_ahead: res.queue_ahead });
        if (res.result) readyBundles.set(key, res.result);
        $('jobStatus').textContent = duplicateStatusText(res);
      } else {
        $('jobStatus').textContent = duplicateStatusText(res);
      }
      renderJobs();
      return;
    }
    addJobEntry({
      pkg: cfg.pkg,
      course: cfg.course,
      asg: cfg.asg,
      retrieval_code: payload.retrieval_code,
      job_id: res.job_id || '',
      kind: payload.kind,
      youtube_link: payload.kind === 'final' ? $('ytLink').value.trim() : '',
      youtube_title: payload.kind === 'final' && ytCheck ? ytCheck.title : '',
      youtube_checked_at: payload.kind === 'final' && ytCheck ? ytCheck.checkedAt : '',
      created_at: res.created_at,
      expires_at: res.expires_at,
    });
    $('jobStatus').textContent = sentText;
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

// Live status for the two slow ZIP steps (2.4.6): a labelled native
// progress element placed directly after the button that started
// the step. The jobs refresh is paused while either step runs
// (zipBusy) and while a review is open (zipReviews), so the element
// is never rebuilt out from under the student. When a step finishes
// the element is removed: the verification step's outcome is the
// review panel, and the download step's outcome is the downloaded
// file plus the brief completion line above the jobs list.
function showZipStatus(anchor, text) {
  clearZipStatus(anchor);
  const box = document.createElement('div');
  box.className = 'zipstatus';
  const bar = document.createElement('progress');
  bar.style.width = '100%';
  const label = document.createElement('div');
  label.textContent = text;
  box.append(bar, label);
  anchor.after(box);
  return { box, bar, label };
}

function clearZipStatus(anchor) {
  const row = anchor.closest('.jobrow') || anchor.parentElement;
  if (row) for (const el of row.querySelectorAll('.zipstatus')) el.remove();
}

// Keep a re-entered YouTube link with the job's stored entry, so
// the next click does not need it again. Only a stored entry is
// updated in place. The
// title and check time come from the step-6 check when it was made
// for this job's recording. Shared by the WAV and fingerprint ZIP
// paths.
function keepReenteredLink(entry, bundle, link) {
  if (entry.youtube_link) return;
  // Keep the re-entered link with the entry so the next click does
  // not need it again.
  const entries = loadJobEntries();
  const e = entries.find((x) => x.pkg === entry.pkg &&
    x.retrieval_code === entry.retrieval_code);
  if (e) {
    entry.youtube_link = link;
    e.youtube_link = link;
    if (ytCheck && ytCheck.audioSha256 === bundle.audio_sha256) {
      entry.youtube_title = ytCheck.title || '';
      entry.youtube_checked_at = ytCheck.checkedAt;
      e.youtube_title = ytCheck.title || '';
      e.youtube_checked_at = ytCheck.checkedAt;
    }
    saveJobEntries(entries);
  }
}

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
    showError('This job’s audio is not on this computer. Its recording ' +
      'hash is ' + bundle.audio_sha256.slice(0, 12) + '… — ' +
      'choose that recording’s file in step 2, or restore it from the saved ' +
      'recordings list there, then try again.', null, anchor);
    return null;
  }
  if (!record.chunks || !record.chunks.length) {
    showError('This computer does not hold the transcript pieces for ' +
      'this job’s recording, so the packaged transcript cannot be verified ' +
      'against the graded one. Restore the recording in step 2 (recording ' +
      'hash ' + bundle.audio_sha256.slice(0, 12) + '…) and try again.', null, anchor);
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
    showError('Audio on this computer does not match the audio this ' +
      'job was graded on (recording hash mismatch). Restore the recording ' +
      'with recording hash ' + bundle.audio_sha256.slice(0, 12) + '… in step 2 ' +
      'and try again.', null, anchor);
    return null;
  }
  if (failures.includes('transcript')) {
    showError('Packaging would use a transcript that does not match the ' +
      'transcript that was graded (checksum mismatch). The usual cause is ' +
      'the removal list in step 3: re-enter the same names and words you ' +
      'used when you sent this job, then try again.', null, anchor);
    return null;
  }
  if (failures.includes('critique')) {
    showError('Critique check failed: the critique in the grade record ' +
      'does not match its signed checksum, so nothing was packaged. ' +
      'Retrieve the job again and retry.',
    null, anchor);
    return null;
  }
  // The HTML's YouTube link comes from local keeping only; cross-check
  // it against the signed bundle: the SHA-256 of its video ID must
  // equal the bundle's youtube_video_sha256. A stored entry normally
  // carries the link from send time, but an alias entry filed for an
  // existing final job by a practice resubmission has none — no link
  // was sent — so fall back to the link field in step 6, which the
  // student re-enters there. The signed check below still proves it
  // is the video checked for this job.
  const link = entry.youtube_link || $('ytLink').value.trim() || '';
  const videoId = parseYouTubeVideoId(link);
  if (!videoId) {
    showError('No YouTube link is kept on this browser. Re-enter it in step 6 and download again from the job list after re-checking.', null, anchor);
    return null;
  }
  const videoIdSha = await sha256Hex(videoId);
  if (bundle.youtube_video_sha256 && bundle.youtube_video_sha256 !== videoIdSha) {
    showError('A different video is kept on this browser from the one that was checked for this job.', null, anchor);
    return null;
  }
  keepReenteredLink(entry, bundle, link);
  return { form: 'wav', wav, scrubbedChunks, record, videoId };
}

// The fingerprint form's verification (2.6.0): the same discipline
// as verifySubmissionParts, over the contents this form packages —
// no audio is read on this computer at all, which is what lets a
// job retrieved on a fresh computer (no local entry, no recording)
// build its ZIP here.
// - the fingerprint bytes are the ones the status response returned
//   with the grade, and their SHA-256 must equal the signed
//   chromaprint_sha256 in the bundle;
// - the transcript comes from this recording's own cached chunks
//   when this computer holds them, and otherwise from the
//   transcript text the status response returned; either way its
//   canonical SHA-256 must equal the signed transcript_sha256;
// - the critique's SHA-256 must equal the signed critique_sha256;
// - the YouTube link (the entry's kept link, or the one in the
//   step-6 field) must hash to the signed youtube_video_sha256.
// Returns the verified parts, or null with the error shown beside
// the button that was used.
async function verifyFingerprintParts(entry, bundle, anchor) {
  const key = jobKey(entry.pkg, entry.retrieval_code);
  const extras = readyExtras.get(key);
  const items = extras && extras.chromaprint
    ? decodeRawFingerprint(extras.chromaprint) : null;
  if (!items) {
    showError('The grading record for this job did not include its ' +
      'recording fingerprint, so the fingerprint submission cannot ' +
      'be built. Retrieve the job again and try again.', null, anchor);
    return null;
  }
  const fingerprintBytes = new Uint8Array(
    items.buffer, items.byteOffset, items.byteLength);
  const record = await cacheGet(bundle.audio_sha256, VERSIONS.model, VERSIONS.glossary)
    .catch(() => null);
  let scrubbedChunks = null;
  let transcriptSha = null;
  if (record && record.chunks && record.chunks.length) {
    scrubbedChunks = scrubChunks(
      record.chunks.map(fromCachedChunk), scrubWords());
    const [markedSha, legacySha] = await Promise.all([
      sha256Hex(canonicalTranscript(scrubbedChunks)),
      sha256Hex(legacyCanonicalTranscript(scrubbedChunks)),
    ]);
    transcriptSha = legacySha === bundle.transcript_sha256
      ? legacySha : markedSha;
  } else if (extras && typeof extras.transcript === 'string') {
    transcriptSha = await sha256Hex(extras.transcript);
    scrubbedChunks = chunksFromCanonical(extras.transcript);
  }
  if (!scrubbedChunks) {
    showError('The grading record for this job did not include its ' +
      'transcript, so the submission cannot be built. Retrieve the ' +
      'job again and try again.', null, anchor);
    return null;
  }
  const [fingerprintSha, critiqueSha] = await Promise.all([
    sha256Hex(fingerprintBytes),
    sha256Hex(bundle.critique || ''),
  ]);
  const failures = verifyFingerprintContents(bundle, {
    fingerprintSha256: fingerprintSha, transcriptSha256: transcriptSha,
    critiqueSha256: critiqueSha,
  });
  if (failures.includes('fingerprint')) {
    showError('The recording fingerprint that came back with this ' +
      'grade does not match the fingerprint checksum signed with ' +
      'the grade, so nothing was packaged. Retrieve the job again ' +
      'and retry.', null, anchor);
    return null;
  }
  if (failures.includes('transcript')) {
    showError('Packaging would use a transcript that does not match ' +
      'the transcript that was graded (checksum mismatch). The usual ' +
      'cause is the removal list in step 3: re-enter the same names ' +
      'and words you used when you sent this job, then try again.',
    null, anchor);
    return null;
  }
  if (failures.includes('critique')) {
    showError('Critique check failed: the critique in the grade ' +
      'record does not match its signed checksum, so nothing was ' +
      'packaged. Retrieve the job again and retry.', null, anchor);
    return null;
  }
  // The link is needed only when the signed bundle names a checked
  // video; a job whose bundle carries youtube_video_sha256 "none"
  // was sent without one and packages with no link.
  let videoId = '';
  if (bundle.youtube_video_sha256 && bundle.youtube_video_sha256 !== 'none') {
    const link = entry.youtube_link || $('ytLink').value.trim() || '';
    videoId = parseYouTubeVideoId(link) || '';
    if (!videoId) {
      showError('No YouTube link is kept on this browser. Enter the ' +
        'link for this recording in step 6 above, then download ' +
        'again — it is checked against the signed grade record ' +
        'before anything is packaged.', null, anchor);
      return null;
    }
    const videoIdSha = await sha256Hex(videoId);
    if (videoIdSha !== bundle.youtube_video_sha256) {
      showError('That YouTube link is for a different video from ' +
        'the one that was checked for this job.', null, anchor);
      return null;
    }
    keepReenteredLink(entry, bundle, link);
  }
  // The packaged duration: the locally held recording's duration
  // when this computer has it, otherwise the fingerprint's own
  // length — one item per 0.124 s of audio.
  const durationS = record && record.duration_s
    ? record.duration_s : items.length * 0.124;
  return {
    form: 'fingerprint', fingerprintBytes, scrubbedChunks, record,
    videoId, durationS,
  };
}

// First click on a ready final job's ZIP button: verify, then show
// the review panel in the job's row (renderJobRow renders it from
// zipReviews; the 5-second refresh pauses while a review is open, so
// the panel and its button are never rebuilt under the student). The
// panel's own button performs the download from the verified parts.
async function downloadSubmissionZip(entry, bundle, anchor) {
  clearError();
  zipBusy = true;
  anchor.disabled = true;
  const status = showZipStatus(anchor,
    bundleChromaprintSha(bundle)
      ? 'Verifying the fingerprint and the transcript against the ' +
        'signed grade record…'
      : 'Verifying the recording and the transcript against the ' +
        'signed grade record… This can take a minute on a long ' +
        'recording.');
  let parts = null;
  try {
    // Let the status paint before the verification hashes begin.
    await new Promise((resolve) => setTimeout(resolve, 0));
    // The signed bundle decides the ZIP form (2.6.0): a real signed
    // chromaprint_sha256 means the fingerprint form, verified
    // without reading any audio; anything else is the WAV form.
    parts = bundleChromaprintSha(bundle)
      ? await verifyFingerprintParts(entry, bundle, anchor)
      : await verifySubmissionParts(entry, bundle, anchor);
  } finally {
    zipBusy = false;
    anchor.disabled = false;
    status.box.remove();
  }
  if (!parts) return;
  const words = scrubWords();
  const recName = parts.record && parts.record.source_name
    ? scrubMetadata(parts.record.source_name, words) + ' · ' : '';
  const firstWords = parts.record
    ? recordingFirstWords(parts.record.chunks) : '';
  const durationS = parts.form === 'fingerprint'
    ? parts.durationS : parts.record.duration_s;
  // Compact review lines (2.6.7): the row and panel already carry
  // the label and the grades, so the review states only what the
  // verification established — the three checks on one line, the
  // recording and YouTube identity in small print, and the
  // instruction. No verified fact is dropped: the recording line
  // still names the file, the duration, the hash, the opening words
  // and which signed checksum the audio matched.
  const lines = [
    'Checks: recording ✓ · transcript ✓ · YouTube ✓',
    'Recording: ' + recName + formatDuration(durationS) +
      ' · hash ' + bundle.audio_sha256.slice(0, 12) + '…' +
      (firstWords
        ? ' · starts “' + scrubMetadata(firstWords, words) + '…”' : '') +
      (parts.form === 'fingerprint'
        ? ' · fingerprint matches the checksum signed with the grade'
        : ' · matches the recording hash signed with the grade'),
    'YouTube: ' + (entry.youtube_title ? '“' + entry.youtube_title + '” · ' : '') +
      canonicalWatchUrl(parts.videoId),
    'Check the recording and the video title are yours, then download.',
  ];
  zipReviews.set(jobKey(entry.pkg, entry.retrieval_code), {
    receipt: bundle.receipt, parts, lines,
  });
  // The review renders inside the job's panel: open the panel so
  // the student sees it at once.
  expandedJobs.add(jobKey(entry.pkg, entry.retrieval_code));
  renderJobs();
}

async function doDownloadZip(entry, bundle, review, anchor) {
  zipBusy = true;
  anchor.disabled = true;
  const status = showZipStatus(anchor, 'Building the submission ZIP…');
  try {
    const { parts } = review;
    const html = assemblePackage({
      youtubeLink: canonicalWatchUrl(parts.videoId),
      audioFileName: parts.form === 'fingerprint'
        ? FINGERPRINT_FILE_NAME : AUDIO_FILE_NAME,
      durationS: parts.form === 'fingerprint'
        ? parts.durationS : parts.record.duration_s,
      chunks: parts.scrubbedChunks,
      bundle,
      ...(parts.form === 'fingerprint'
        ? { fingerprintSha256: bundle.chromaprint_sha256 } : {}),
    });
    const zip = await buildZipAsync([
      { name: ZIP_ENTRY_HTML, data: new TextEncoder().encode(html) },
      parts.form === 'fingerprint'
        ? { name: FINGERPRINT_FILE_NAME, data: parts.fingerprintBytes }
        : { name: ZIP_ENTRY_AUDIO, data: parts.wav },
    ], (done, total) => {
      status.bar.max = total;
      status.bar.value = done;
      status.label.textContent = 'Building the submission ZIP… ' +
        (total ? Math.floor((done / total) * 100) : 100) + '%';
    });
    const zipName = submissionZipName({
      course: entry.course, asg: entry.asg,
      completeness: bundle.completeness, accuracy: bundle.accuracy,
      youtubeCheckedAt: entry.youtube_checked_at, gradedAt: bundle.t,
    });
    downloadBlob(zip, zipName);
    $('zipDone').textContent = 'Done — ' + zipName +
      ' has been downloaded. Upload that file to Canvas. ' +
      'The job stays in the list below, so you can download ' +
      'the ZIP again if you need to.';
    zipReviews.delete(jobKey(entry.pkg, entry.retrieval_code));
    try {
      await markJobRetrieved(cfg.worker, {
        pkg: entry.pkg, retrieval_code: entry.retrieval_code,
      });
    } catch { /* the ZIP is already in the student's hands */ }
    // The job entry is kept (2.6.6): before this, a download removed
    // the row, the list flipped to "No jobs sent from this browser
    // yet" under the Done line, and a student whose Canvas upload
    // failed had to retrieve the job by its recovery code before
    // they could build the ZIP again. The Worker keeps a graded job
    // for 180 days and the render drops the row when the Worker
    // reports it expired, so a kept row costs nothing; "Remove from
    // this browser" remains the student's own way to clear it.
    renderJobs();
  } finally {
    zipBusy = false;
    anchor.disabled = false;
    status.box.remove();
  }
}

function renderJobRow(container, entry, statusInfo, unreachable) {
  const row = document.createElement('div');
  row.className = 'jobrow';
  // The row and each of its controls carry stable identities, so a
  // refresh rebuild can put the student's focus back on the control
  // that had it (see renderJobsOnce) instead of dropping it.
  row.dataset.jobKey = jobKey(entry.pkg, entry.retrieval_code);
  const label = [entry.course, entry.asg].filter(Boolean).join(' · ') || entry.pkg;
  let statusText;
  if (statusInfo === null && unreachable) {
    // The status fetch has failed three rounds running: say so,
    // instead of leaving the row at "checking…" indefinitely. The
    // poll keeps retrying, and the row returns to its real status
    // on the first answer that gets through.
    statusText = 'can’t reach the grading service — retrying';
  }
  else if (statusInfo === null) statusText = 'checking…';
  else if (statusInfo.status === 'forbidden') statusText = 'Job not found.';
  else if (statusInfo.status === 'ready') statusText = 'ready';
  else if (statusInfo.status === 'claimed') statusText = 'being graded now';
  else if (statusInfo.status === 'queued') {
    const ahead = statusInfo.queue_ahead;
    statusText = typeof ahead === 'number'
      ? (ahead === 0 ? 'waiting — next in the grading queue'
        : 'waiting — ' + ahead + (ahead === 1 ? ' job' : ' jobs') + ' ahead')
      : 'waiting';
  } else statusText = statusInfo.status;
  // One line per job (2.6.7): the line carries the label, the kind
  // in plain words (Final or Practice), the status, the grades when
  // ready, the panel toggle, and the one primary button; the label
  // takes the slack and shortens with an ellipsis. Everything else —
  // the critique, the ZIP review, Remove — lives
  // in the single panel below the line, so a collapsed job is
  // exactly one line. That a final job's link was checked is carried
  // by the YouTube check in the ZIP review, not by the label.
  const line = document.createElement('div');
  line.className = 'jobline';
  const labelSpan = document.createElement('span');
  labelSpan.className = 'joblabel';
  labelSpan.textContent =
    label + ' · ' + (entry.kind === 'final' ? 'Final' : 'Practice') +
    ' · ' + statusText;
  labelSpan.title = labelSpan.textContent;
  line.append(labelSpan);
  const key = jobKey(entry.pkg, entry.retrieval_code);
  const bundle = statusInfo && statusInfo.status === 'ready'
    ? readyBundles.get(key) : null;
  if (bundle) {
    const grades = document.createElement('span');
    grades.className = 'jobgrades';
    grades.textContent = 'Completeness ' + bundle.completeness +
      '/5 · Accuracy ' + bundle.accuracy + '/5';
    line.append(grades);
  }
  const detail = document.createElement('div');
  detail.className = 'jobdetail';
  detail.hidden = !expandedJobs.has(key);
  const detailBtn = document.createElement('button');
  detailBtn.dataset.act = 'grades';
  detailBtn.textContent = 'Show details';
  if (expandedJobs.has(key)) detailBtn.textContent = 'Hide details';
  detailBtn.addEventListener('click', () => {
    detail.hidden = !detail.hidden;
    if (detail.hidden) expandedJobs.delete(key); else expandedJobs.add(key);
    detailBtn.textContent = detail.hidden ? 'Show details' : 'Hide details';
  });
  line.append(detailBtn);
  row.append(line);
  if (bundle && entry.kind === 'practice' && entry.pkg === cfg.pkg) {
    // A graded practice job (no link was given at send time): the
    // place to add the link is on the job itself (2.6.10). The button takes the student
    // to the conversion panel below the list, with this job
    // selected and the link field focused — the panel is where the
    // check and the conversion run, as before.
    const linkBtn = document.createElement('button');
    linkBtn.dataset.act = 'addlink';
    linkBtn.className = 'primary';
    linkBtn.textContent = 'Add a YouTube link — make this your submission';
    linkBtn.addEventListener('click', () => {
      refreshFinPanel(key);
      $('finPanel').scrollIntoView({ block: 'nearest' });
      $('finLink').focus({ preventScroll: true });
    });
    detail.append(linkBtn);
  }
  if (bundle) {
    // The critique is a numbered list, one point per line: keep the
    // line breaks when it is shown (the submission HTML does the
    // same with white-space: pre-line).
    const crit = document.createElement('div');
    crit.className = 'box';
    crit.style.whiteSpace = 'pre-line';
    crit.textContent = bundle.critique || '';
    detail.append(crit);
  }
  if (statusInfo && statusInfo.status === 'ready') {
    if (entry.kind === 'final' && bundle && entry.pkg !== cfg.pkg) {
      // Guard (2.6.2): the jobs list is browser-wide, but a submission
      // ZIP is built only from the link of the job's own assignment.
      // From another assignment's page the row says so instead of
      // offering the button, so one homework's ZIP is not downloaded
      // here and uploaded to the wrong Canvas assignment.
      const other = document.createElement('span');
      other.className = 'guardnote';
      other.textContent = 'To build this job\u2019s submission ZIP, ' +
        'open its assignment\u2019s link in Canvas.';
      other.title = other.textContent;
      line.append(other);
    } else if (entry.kind === 'final' && bundle) {
      // Exactly one ZIP button per job at any moment (2.5.3): before
      // verification the row's button is the Review button; once the
      // review panel is open, the panel's Download button REPLACES
      // it — the Review button is not rendered alongside the panel.
      // (Before this fix both were shown together, and students
      // counted the still-visible Review button as a second,
      // non-working "generate ZIP" button.)
      const review = zipReviews.get(key);
      const reviewOpen = !!(review && review.receipt === bundle.receipt);
      if (!reviewOpen) {
        const zipBtn = document.createElement('button');
        zipBtn.dataset.act = 'zip-review';
        zipBtn.className = 'primary';
        zipBtn.textContent = 'Review and download';
        zipBtn.addEventListener('click', () => downloadSubmissionZip(entry, bundle, zipBtn));
        line.append(zipBtn);
      } else {
        // The review section from a completed verification (see
        // downloadSubmissionZip), inside the job's one panel: the
        // download button first, then the compact lines — the checks
        // on one line, the recording and YouTube identity in small
        // print, and the instruction.
        const panel = document.createElement('div');
        panel.className = 'box reviewbox';
        const dlBtn = document.createElement('button');
        dlBtn.dataset.act = 'zip-download';
        dlBtn.className = 'primary';
        dlBtn.textContent = 'Download submission ZIP';
        dlBtn.addEventListener('click', () => doDownloadZip(entry, bundle, review, dlBtn));
        const closeBtn = document.createElement('button');
        closeBtn.dataset.act = 'zip-close';
        closeBtn.className = 'quiet';
        closeBtn.textContent = 'Close review';
        closeBtn.addEventListener('click', () => {
          // Closing the review restores the row's Review button and
          // lets the 5-second poll resume (it pauses while a review
          // is open).
          zipReviews.delete(key);
          renderJobs();
        });
        const btnRow = document.createElement('div');
        btnRow.className = 'houserow';
        btnRow.append(dlBtn, closeBtn);
        panel.append(btnRow);
        review.lines.forEach((text, i) => {
          const p = document.createElement('p');
          if (i > 0 && i < review.lines.length - 1) p.className = 'small';
          p.textContent = text;
          panel.append(p);
        });
        detail.append(panel);
      }
    }
    // The conversion itself runs in the panel below the list; a
    // practice job's panel above carries the button that leads
    // there (2.6.10).
  }
  const forgetBtn = document.createElement('button');
  forgetBtn.dataset.act = 'remove';
  forgetBtn.className = 'quiet';
  forgetBtn.textContent = 'Remove from this browser';
  forgetBtn.addEventListener('click', () => {
    // A review open on this row is abandoned with the job: its
    // zipReviews entry goes too, or the poll would stay paused on a
    // review that no longer exists.
    zipReviews.delete(key);
    expandedJobs.delete(key);
    removeJobEntry(entry.pkg, entry.retrieval_code);
    renderJobs();
  });
  // Housekeeping sits at the foot of the panel (2.6.7): Remove is
  // not part of the job's one line.
  const houseRow = document.createElement('div');
  houseRow.className = 'houserow';
  houseRow.append(forgetBtn);
  detail.append(houseRow);
  row.append(detail);
  container.append(row);
}

// Rendering is serialised: every caller shares the one in-flight
// render, so a timer tick can never start a second rebuild while a
// click-triggered render (ZIP verification, send, remove) is still
// running, and two renders never interleave their DOM writes.
let renderJobsPromise = null;
function renderJobs() {
  if (renderJobsPromise) return renderJobsPromise;
  renderJobsPromise = (async () => {
    try { await renderJobsOnce(); }
    finally { renderJobsPromise = null; }
  })();
  return renderJobsPromise;
}

async function renderJobsOnce() {
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
  // Every status is fetched before the list is touched, and all of
  // them in parallel: the box is never emptied while the network
  // answers, and one slow answer no longer delays the other rows.
  // (Before this fix the box was emptied first and each row was
  // rebuilt twice, once per sequential fetch, so the ZIP buttons
  // vanished and moved on every 5-second cycle.)
  const results = await Promise.all(entries.map(async (entry) => {
    try {
      return await fetchJobStatus(cfg.worker, {
        pkg: entry.pkg, retrieval_code: entry.retrieval_code,
      });
    } catch { /* offline or Worker error: keep the entry, render last known */ return null; }
  }));
  let entriesDirty = false;
  const live = []; // { entry, jobId } for entries the Worker still holds
  entries.forEach((entry, i) => {
    const key = jobKey(entry.pkg, entry.retrieval_code);
    const res = results[i];
    if (res && res.status === 'expired') {
      // The Worker has deleted the job; drop the entry and its row,
      // and any ZIP review open on it, so the poll is not left
      // paused on a review that no longer exists.
      entriesDirty = true;
      readyBundles.delete(key);
      readyExtras.delete(key);
      jobStates.delete(key);
      statusFailures.delete(key);
      zipReviews.delete(key);
      return;
    }
    if (!res) {
      // The status fetch failed (offline, or the service address
      // blocked in this browser): count it, so the row can say the
      // service cannot be reached instead of sitting at "checking…"
      // with no explanation (2.6.9).
      statusFailures.set(key, (statusFailures.get(key) || 0) + 1);
    }
    if (res) {
      statusFailures.delete(key);
      // The Worker reports the job's current expiry (7 days while
      // ungraded, 180 days after grading); keep the stored entry in
      // step with it.
      if (res.data && res.data.expires_at &&
          entry.expires_at !== res.data.expires_at) {
        entry.expires_at = res.data.expires_at;
        entriesDirty = true;
      }
      if (res.status === 'ready' && res.data && res.data.result) {
        readyBundles.set(key, res.data.result);
        // The same response carries the stored transcript and
        // fingerprint (Worker 2.7.0) for the fingerprint-form ZIP
        // path; an older Worker sends neither, and the WAV path
        // then governs, exactly as before.
        if (typeof res.data.transcript === 'string' || res.data.chromaprint) {
          readyExtras.set(key, {
            transcript: typeof res.data.transcript === 'string'
              ? res.data.transcript : null,
            chromaprint: res.data.chromaprint || null,
          });
        }
        // The ready bundle is authoritative for the job's kind: an
        // alias entry filed while the job was still queued carries
        // the submitted kind, which may not be the existing job's
        // kind. Correct it from the bundle so the ZIP button and
        // the conversion panel see the job as it is.
        const trueKind = kindFromResultBundle(res.data.result);
        if (entry.kind !== trueKind) {
          entry.kind = trueKind;
          entriesDirty = true;
        }
      }
      jobStates.set(key, {
        status: res.status,
        queue_ahead: res.data ? res.data.queue_ahead : undefined,
      });
    }
    const bundle = readyBundles.get(key);
    live.push({ entry, jobId: entry.job_id || (bundle && bundle.job_id) || null });
  });
  // One row per underlying job (2.5.3): entries filed under
  // different retrieval codes can all retrieve the same job (the
  // Worker's duplicate/alias path), and each such entry used to
  // render its own row with its own ZIP button — only the entry
  // carrying the locally kept YouTube link could actually build
  // the ZIP. Collapse them to the single most usable entry, merge
  // its locally kept link fields from the others, and persist the
  // collapsed list so the duplicates do not return on the next
  // visit. A ZIP review open on a collapsed-away entry moves to
  // the surviving entry's key (same job, same receipt).
  // collapseSameJobEntries fills in a missing job_id from the ready
  // bundle; note any such entry first, so the filled value is
  // persisted and later visits know the job's identity at once.
  if (live.some(({ entry, jobId }) => jobId && !entry.job_id)) {
    entriesDirty = true;
  }
  const kept = collapseSameJobEntries(live);
  if (kept.length !== live.length) {
    entriesDirty = true;
    const keptKeys = new Set(kept.map(({ entry }) =>
      jobKey(entry.pkg, entry.retrieval_code)));
    for (const { entry, jobId } of live) {
      const key = jobKey(entry.pkg, entry.retrieval_code);
      if (keptKeys.has(key)) continue;
      const review = zipReviews.get(key);
      if (review) {
        zipReviews.delete(key);
        const target = kept.find((k) => k.jobId && k.jobId === jobId);
        if (target) {
          const tKey = jobKey(target.entry.pkg, target.entry.retrieval_code);
          if (!zipReviews.has(tKey)) zipReviews.set(tKey, review);
        }
      }
      readyBundles.delete(key);
      readyExtras.delete(key);
      jobStates.delete(key);
      statusFailures.delete(key);
    }
  }
  const survivors = kept.map(({ entry }) => entry);
  const frag = document.createDocumentFragment();
  for (const entry of survivors) {
    const holder = document.createElement('div');
    const key = jobKey(entry.pkg, entry.retrieval_code);
    renderJobRow(holder, entry, jobStates.get(key) || null,
      (statusFailures.get(key) || 0) >= 3);
    frag.append(holder);
  }
  // One synchronous swap, after every fetch has settled: no painted
  // frame ever shows an empty or half-built list, and a button's
  // position never moves while its row is being rebuilt.
  // The swap replaces the row elements, which would drop the
  // student's focus to the page body: note the focused control
  // (its row's job key and its action) before the swap and put the
  // focus back on the matching control in the rebuilt row. The
  // grades panel survives a rebuild the same way, through
  // expandedJobs.
  const ae = document.activeElement;
  let focusMark = null;
  if (ae && ae.dataset && ae.dataset.act && box.contains(ae)) {
    const holderRow = ae.closest('[data-job-key]');
    if (holderRow) focusMark = { key: holderRow.dataset.jobKey, act: ae.dataset.act };
  }
  box.textContent = '';
  if (survivors.length) box.append(frag);
  else box.textContent = 'No jobs sent from this browser yet.';
  if (focusMark) {
    for (const r of box.querySelectorAll('[data-job-key]')) {
      if (r.dataset.jobKey !== focusMark.key) continue;
      const target = r.querySelector('[data-act="' + focusMark.act + '"]');
      if (target) target.focus({ preventScroll: true });
      break;
    }
  }
  if (entriesDirty) saveJobEntries(survivors);
  refreshFinPanel();
}

// The jobs list refreshes itself every 5 seconds while the page is
// open, so a waiting student sees the queue move and the grade arrive
// without reloading — no notification is needed. A poll is skipped
// while the tab is hidden, while a ZIP verification or download is
// running (zipBusy), or while a ZIP review panel is open
// (zipReviews) — a rebuild would destroy the review being read.
// Focus inside the list no longer skips a poll (2.6.6): a clicked
// button keeps the focus, so the old rule blocked every later update
// for as long as the student left the focus there, and the row sat
// at "being graded now" after the grade had arrived. A rebuild is
// safe for a focused student instead: the swap is synchronous, and
// renderJobsOnce restores the focus to the same control in the
// rebuilt row, with the grades panel kept as it was.
let zipBusy = false;
async function refreshJobs() {
  if (document.hidden) return;
  if (zipBusy || zipReviews.size) return;
  try { await renderJobs(); } catch { /* the next tick retries */ }
}
setInterval(refreshJobs, 5000);

// --- Conversion: turn a graded job into the Canvas submission ---
let finCheck = null;
let finPrevSelKey = null;

function conversionCandidates() {
  const out = [];
  for (const entry of loadJobEntries()) {
    const key = jobKey(entry.pkg, entry.retrieval_code);
    const st = jobStates.get(key);
    const bundle = readyBundles.get(key);
    if (entry.pkg !== cfg.pkg) continue; // guard (2.6.2): this assignment only
    if (entry.kind === 'practice' && st && st.status === 'ready' && bundle) {
      out.push({ entry, bundle });
    }
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
      c.bundle.accuracy + '/5 · recording hash ' +
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
  $('finConfirmBtn').disabled = true;
  $('finStatus').textContent = '';
  $('finDone').textContent = '';
  $('finPlayerWrap').hidden = true;
  refreshFinDurationUi();
}
$('finJobSel').addEventListener('change', finResetCheck);
// As in step 6 (2.6.8): the link invalidates any earlier check when
// it changes, and a recognisable link is checked by itself after a
// short pause.
let finCheckTimer = null;
let finCheckBusy = false;
let finCheckRearms = 0;
$('finLink').addEventListener('input', () => {
  finCheck = null;
  finDur = null;
  finCheckRearms = 0;
  $('finConfirmBtn').disabled = true;
  $('finPlayerWrap').hidden = true;
  refreshFinDurationUi();
  if (finCheckTimer) clearTimeout(finCheckTimer);
  finCheckTimer = setTimeout(runFinCheck, 700);
});

async function runFinCheck() {
  const cand = finSelected();
  if (!cand) return;
  const url = $('finLink').value.trim();
  const videoId = parseYouTubeVideoId(url);
  if (!videoId) return;
  if (finCheckBusy) {
    // As in step 6: re-arm so the replacement link is checked once
    // the in-flight check for the earlier link ends, capped so a
    // flight that never settles leaves a message, not a timer.
    if (finCheckRearms >= 40) {
      $('finStatus').textContent = 'The link check is taking a long time; edit the link to try again.';
      return;
    }
    finCheckRearms += 1;
    $('finStatus').textContent = 'Checking…';
    if (finCheckTimer) clearTimeout(finCheckTimer);
    finCheckTimer = setTimeout(runFinCheck, 700);
    return;
  }
  if (finCheck && finCheck.videoId === videoId) return; // already checked
  finCheckRearms = 0;
  if (!cfg.worker) {
    $('finStatus').textContent = 'Open this page from the link your teacher put in Canvas to check the link.';
    return;
  }
  finCheckBusy = true;
  $('finStatus').textContent = 'Checking…';
  try {
    const res = await requestYouTubeCheck(cfg.worker, canonicalWatchUrl(videoId));
    if ($('finLink').value.trim() !== url) return; // replaced while checking
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
    $('finStatus').textContent = 'Could not complete the check. Try again.';
    console.error(err);
  } finally {
    finCheckBusy = false;
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
}

$('finConfirmBtn').addEventListener('click', async () => {
  const cand = finSelected();
  if (!cand || !finCheck) return;
  if (finCheck.jobKey !== jobKey(cand.entry.pkg, cand.entry.retrieval_code)) {
    $('finDone').textContent = 'Link check mismatch: it was made for a different job. Check the link again.';
    return;
  }
  if (!durationGateOk(finDur)) {
    $('finDone').textContent = 'Checked video and this job’s audio differ in length by more than the allowed tolerance. Enter the link for this job’s recording.';
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
    finCheck = null;
    $('finDone').textContent = 'Converted. Download the submission ZIP from the job’s row above.';
    await renderJobs();
  } catch (err) {
    $('finDone').textContent = 'Converting failed: ' + err.message;
    $('finConfirmBtn').disabled = false;
  }
});

renderConfig();
refreshDerived();
renderCacheList();
renderJobs();
if (cfg.setup) {
  $('loadBtn').hidden = false;
  $('loadStatus').textContent = 'Model not loaded.';
} else {
  startModelLoad();
}
