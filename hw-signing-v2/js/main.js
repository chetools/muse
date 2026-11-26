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
import { encodeWavPcm16, pcmFromWavBytes, decodeFileTo16kMono, SAMPLE_RATE } from './media.js';
import { loadModel, transcribePcm, FILE_WINDOW_S } from './transcribe.js';
import { buildVocabulary } from './vocab.js';
import {
  cacheGet, cacheInit, cachePutChunk, cacheWindowDone, cacheComplete,
  cacheList, cacheDelete,
} from './cache.js';
import { fromCachedChunk, recordingFirstWords } from './cachekey.js';
import {
  parseYouTubeVideoId, canonicalWatchUrl,
  bundleBoundVideoSha,
  verifyBundleContents, bundleChromaprintSha, verifyFingerprintContents,
  validateJobPayload, buildJobPayload, generateRetrievalToken, loadJobEntries, addJobEntry, entryPollable,
  removeJobEntry, saveJobEntries, kindFromResultBundle,
  duplicateJobEntry, collapseSameJobEntries,
  requestYouTubeCheck, submitJob, fetchJobStatus, markJobRetrieved,
  finalizeJob,
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
let chromaprint = null;     // raw Chromaprint as base64 (2.6.0), or null when none computed
let chromaprintSha = null;  // audioSha the stored fingerprint was computed from
let chromaprintPending = null; // in-flight computeFingerprint promise, if any
let ytApiPromise = null;
// Per-row YouTube link state for the section-7 table: jobKey ->
// the row's field text as typed (so a list rebuild never loses
// what the student is typing), and the last ZIP failure for the
// row, which is shown in the row's own cell. Since 2.6.18 no
// check runs while the student types: the Generate ZIP button
// follows the field's readability, and the one check runs at
// the click, inside the review step (see generateZipForRow).
const rowDrafts = new Map();  // jobKey -> field text
const rowZipErrors = new Map(); // jobKey -> ZIP failure text for the cell
const readyBundles = new Map(); // "pkg|code" -> result bundle from /jobs/status
const readyExtras = new Map();  // "pkg|code" -> {transcript, chromaprint} from
// the same status response (Worker 2.7.0): the stored transcript text and the
// raw fingerprint as base64, kept in memory only, for the fingerprint-form ZIP
const jobStates = new Map();    // "pkg|code" -> {status, queue_ahead} last seen
const statusFailures = new Map(); // "pkg|code" -> consecutive failed status fetches
const expandedJobs = new Set(); // "pkg|code" with the detail panel open (kept across refreshes)

// Errors belong beside the control that was used, in the part
// of the window on screen — not in one banner at the top of a
// long page (teacher's rule, 2026-11-09). The message always
// goes into the page's error box at the top, and a copy of it
// (an .errline element) is placed directly after the row of
// the control whose action failed, then scrolled into view.
// The box itself never moves (2.6.15): it used to be relocated
// beside the anchor, but an anchor inside the recordings or
// jobs list put the box inside a container those lists rebuild
// from scratch, and the next rebuild destroyed the page's only
// error box — after which every later error threw instead of
// showing. The copy beside the control may be rebuilt away;
// the box at the top keeps the message.
function showError(message, err, anchor) {
  const box = $('errBox');
  box.textContent = message;
  box.style.display = 'block';
  document.querySelectorAll('.errline').forEach((el) => el.remove());
  const host = anchor || (document.activeElement
    && document.activeElement !== document.body
    ? document.activeElement : null);
  let line = null;
  if (host && host.isConnected && !box.contains(host)) {
    const row = host.closest('.row, .recrow, .jobrow') || host;
    if (row.parentNode) {
      line = document.createElement('div');
      line.className = 'err errline';
      line.style.display = 'block';
      line.textContent = message;
      row.after(line);
    }
  }
  const shown = line || box;
  if (shown.scrollIntoView) shown.scrollIntoView({ block: 'nearest' });
  if (err) console.error(err);
}
function clearError() {
  $('errBox').style.display = 'none';
  document.querySelectorAll('.errline').forEach((el) => el.remove());
}

function scrubWords() { return parseScrubWords($('scrubField').value); }
function scrubbed() { return scrubChunks(chunks, scrubWords()); }
function canonical() { return canonicalTranscript(scrubbed()); }
// There is no Practice/Final choice anywhere in the page (2.6.16):
// a job is sent with no YouTube link, and the submission is made
// afterwards from the job's own row in section 7. The video is
// bound at one moment only (2.6.18): the student's confirmation
// in the ZIP review, where the finalise step runs. The Worker's
// job kind stays as it is: a sent job is 'practice' until it is
// finalised, and entries for jobs sent as final by earlier
// versions keep working from their signed bundle.

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
    // The samples are derived from the stored WAV (2.6.14), so a
    // restored recording whose transcription is missing or partial
    // can be transcribed or resumed; before this, a restore left
    // the samples null and the Transcribe button stayed disabled.
    pcm = pcmFromWavBytes(wavBytes);
  }
  durationS = record.duration_s || (wavBytes ? (wavBytes.length - 44) / 2 / SAMPLE_RATE : 0);
  transcriptionComplete = !!record.complete;
  $('mediaStatus').textContent = note;
  setAudioMeta();
  refreshDerived();
}

$('mediaFile').addEventListener('change', async (ev) => {
  clearError();
  const file = ev.target.files && ev.target.files[0];
  // Clear the input's value at once (2.6.15): a file input fires
  // no change event when the same file is chosen twice in a row,
  // so without this, deleting the loaded recording and choosing
  // its file again — the one recovery copy — silently did
  // nothing until a page reload.
  ev.target.value = '';
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
    // The state was emptied at the top of this handler; refresh
    // the derived views too (2.6.15), so the previous recording's
    // transcript, hash line and review text do not stay on screen
    // over the emptied state with Send still enabled.
    setAudioMeta();
    updateRunEnabled();
    refreshDerived();
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
      (entry.complete ? 'transcribed'
        : entry.chunks ? 'partly transcribed (' + entry.chunks + ' pieces)'
        : 'not transcribed') +
      ' · recording hash ' + entry.audio_sha256.slice(0, 12) + '…' + wordsPart;
    row.append(meta);
    const restoreBtn = document.createElement('button');
    restoreBtn.textContent = 'Restore';
    restoreBtn.addEventListener('click', async () => {
      clearError();
      try {
        const record = await cacheGet(entry.audio_sha256, VERSIONS.model, VERSIONS.glossary);
        if (!record) { showError('That saved recording was made by an older model or glossary version and cannot be restored.', null, restoreBtn); return; }
        // The link check is voided only once the restore is known
        // to proceed (2.6.15): a refused restore changes no
        // recording, so a check that was standing must stand.
              audioSha = entry.audio_sha256;
        sourceName = record.source_name || '';
        pcm = null;
        chromaprint = null; chromaprintSha = null; chromaprintPending = null;
        updateRunEnabled();
        // The status line says what was restored (2.6.15): a
        // complete transcript, a partial one that Transcribe
        // resumes, or a recording with no transcript yet — the
        // one line for all three hid which state the page was in.
        const note = record.complete && record.chunks && record.chunks.length
          ? 'Recording and transcript restored from this computer — no transcription needed.'
          : (record.chunks && record.chunks.length) || record.windows_done
            ? 'Recording restored from this computer. An earlier transcription stopped partway; press Transcribe to resume it.'
            : 'Recording restored from this computer. It has not been transcribed yet; press Transcribe.';
        await adoptCacheRecord(record, note);
        updateRunEnabled();
        refreshFingerprint();
      } catch (err) { showError('That saved recording could not be restored.', err, restoreBtn); }
    });
    const delBtn = document.createElement('button');
    delBtn.textContent = 'Delete';
    delBtn.addEventListener('click', async () => {
      await cacheDelete(entry.audio_sha256).catch(() => {});
      // A delete is a delete (2.6.14): when the deleted recording
      // is the one loaded in the page, it is unloaded too, instead
      // of living on in the page until a reload.
      if (audioSha && entry.audio_sha256 === audioSha) {
        pcm = null; wavBytes = null; audioSha = null; durationS = 0;
        chromaprint = null; chromaprintSha = null; chromaprintPending = null;
        chunks = []; windowsDoneBase = 0;
        transcriptionComplete = false;
              $('mediaStatus').textContent = 'Recording deleted from this computer.';
        setAudioMeta();
        updateRunEnabled();
        refreshDerived();
      }
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
  $('submitJobBtn').disabled = !base;
}

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

/* ---------------- the fixed preview player (2.6.16) ----------------
 * One player, in the sticky area directly above the jobs table.
 * It plays only without sound: it is muted before every play, and
 * no audible autoplay is ever attempted (a browser refuses sound
 * on hover in any case, since hovering is not a user activation).
 * Hovering a populated row's link cell plays that row's video
 * here; clicking the player area, or the link text under a row's
 * field, opens the video on YouTube in a new tab. A true acoustic
 * fingerprint comparison cannot run here, because the browser
 * cannot read the video's audio track (YouTube serves it only
 * inside its own player); sameness of recording is established by
 * the teacher audit's acoustic cross-check on the submitted ZIP.
 */
let previewPlayer = null;   // the YT.Player, once created
let previewVideoId = null;  // the video loaded in it, if any
let previewKey = null;      // the job key whose row loaded it

async function previewLoad(videoId, play, key) {
  try {
    const YT = await loadYouTubeApi();
    $('ytPreviewHint').hidden = true;
    $('ytPreviewOverlay').hidden = false;
    previewVideoId = videoId;
    previewKey = key || null;
    if (previewPlayer) {
      previewPlayer.mute();
      if (play) previewPlayer.loadVideoById(videoId);
      else previewPlayer.cueVideoById(videoId);
    } else {
      previewPlayer = new YT.Player('ytPreviewPlayer', {
        width: '400', height: '225', videoId,
        playerVars: { autoplay: play ? 1 : 0, mute: 1 },
        events: {
          onReady: (ev) => { ev.target.mute(); if (play) ev.target.playVideo(); },
        },
      });
    }
  } catch { /* preview is best-effort */ }
}

function previewPause() {
  try { if (previewPlayer && previewPlayer.pauseVideo) previewPlayer.pauseVideo(); } catch { /* best effort */ }
}

// Clear the player window entirely (2.6.18): stop the video,
// destroy the player (the IFrame API has no unload call; destroy
// removes the iframe), restore a fresh mount point, hide the
// click overlay, and bring the placeholder text back. Used when
// the link that loaded the player is cleared or edited into a
// different or unreadable link.
function previewClear() {
  try { if (previewPlayer && previewPlayer.stopVideo) previewPlayer.stopVideo(); } catch { /* best effort */ }
  try { if (previewPlayer && previewPlayer.destroy) previewPlayer.destroy(); } catch { /* best effort */ }
  previewPlayer = null;
  previewVideoId = null;
  previewKey = null;
  const slot = $('ytPreviewSlot');
  if (slot && !slot.querySelector('#ytPreviewPlayer')) {
    const mount = document.createElement('div');
    mount.id = 'ytPreviewPlayer';
    slot.prepend(mount);
  }
  $('ytPreviewHint').hidden = false;
  $('ytPreviewOverlay').hidden = true;
}

// When the row that loaded the player is cleared, or its link is
// edited to a different video or to something unreadable, the
// playing window clears with the link. Editing any other row, or
// re-entering the same video, leaves the player untouched.
function previewMaybeClear(key, currentVideoId) {
  if (previewKey !== key) return;
  if (currentVideoId && currentVideoId === previewVideoId) return;
  previewClear();
}

$('ytPreviewOverlay').addEventListener('click', () => {
  if (previewVideoId) {
    window.open(canonicalWatchUrl(previewVideoId), '_blank', 'noopener');
  }
});

/* ---------------- per-row links (2.6.18) ----------------
 * Each ready job's row carries its own link field. No check runs
 * while the student types: the field's text is parsed for
 * readability only (a Studio address is converted to the watch
 * form automatically), and the Generate ZIP button is present
 * exactly while the field holds a readable link. The one check —
 * the Worker reporting the video reachable (Public or Unlisted)
 * through /youtube-check — runs at the Generate ZIP click, as
 * part of preparing the review. Binding happens later still, at
 * the review's confirm (see doDownloadZip): cancelling the
 * review binds nothing.
 */

function rowInputEl(key) {
  const box = $('jobsBox');
  if (!box) return null;
  for (const r of box.querySelectorAll('[data-job-key]')) {
    if (r.dataset.jobKey !== key) continue;
    const input = r.querySelector('[data-act="ytlink"]');
    if (input) return input;
  }
  return null;
}

// The draft text for a row: what the student has typed in this
// session, else the link kept with the entry.
function rowLinkDraft(entry) {
  const key = jobKey(entry.pkg, entry.retrieval_code);
  return rowDrafts.has(key) ? rowDrafts.get(key) : (entry.youtube_link || '');
}

// What the row's cell says, from its standing state: a ZIP
// failure in small red text, else the starting line while the
// field holds no readable link, else nothing.
function rowCellBits(key) {
  const zipErr = rowZipErrors.get(key);
  const draft = rowDrafts.get(key) || '';
  const parsed = parseYouTubeVideoId(draft);
  const bits = { text: '', cls: 'ytneed', openId: parsed };
  if (zipErr) { bits.text = zipErr; bits.cls = 'ytreason'; return bits; }
  if (!parsed) {
    bits.text = 'Add a YouTube link to download the ZIP.';
    return bits;
  }
  return bits;
}

// Repaint one row's cell message and link text in place, without
// rebuilding the list (a rebuild would drop the student's place
// in the field).
function paintRowCell(key) {
  const box = $('jobsBox');
  if (!box) return;
  for (const r of box.querySelectorAll('[data-job-key]')) {
    if (r.dataset.jobKey !== key) continue;
    const msg = r.querySelector('.ytmsg');
    if (!msg) continue;
    const bits = rowCellBits(key);
    msg.textContent = bits.text;
    msg.className = 'ytmsg ' + bits.cls;
    const open = r.querySelector('.ytopen');
    if (open) {
      if (bits.openId) {
        open.hidden = false;
        open.textContent = canonicalWatchUrl(bits.openId);
        open.href = canonicalWatchUrl(bits.openId);
      } else open.hidden = true;
    }
    return;
  }
}

function persistRowLink(entry, link, title, checkedAt) {
  const entries = loadJobEntries();
  const e = entries.find((x) => x.pkg === entry.pkg &&
    x.retrieval_code === entry.retrieval_code);
  if (!e) return;
  e.youtube_link = link;
  e.youtube_title = title || '';
  e.youtube_checked_at = checkedAt || '';
  entry.youtube_link = link;
  entry.youtube_title = title || '';
  entry.youtube_checked_at = checkedAt || '';
  saveJobEntries(entries);
}

// Another row in this browser whose field or kept link names the
// same video, or null. The review warns about it: the same link
// on two rows is the shape of a mix-up between homeworks.
function duplicateLinkEntry(key, videoId) {
  for (const e of loadJobEntries()) {
    const k2 = jobKey(e.pkg, e.retrieval_code);
    if (k2 === key) continue;
    const other = parseYouTubeVideoId(rowLinkDraft(e));
    if (other && other === videoId) return e;
  }
  return null;
}

// Generate ZIP, from a row holding a readable link (2.6.18): the
// reachability check runs now, as part of preparing the review.
// A private or missing video, or a failed check, is reported in
// the row's own cell and nothing is bound or packaged. On a pass
// the verified parts and the review are prepared by
// downloadSubmissionZip, carrying a pending binding — the bind
// (or superseding rebind) itself runs only if the student
// confirms in the review (see doDownloadZip).
async function generateZipForRow(entry, bundle, btn) {
  const key = jobKey(entry.pkg, entry.retrieval_code);
  const videoId = parseYouTubeVideoId(rowLinkDraft(entry));
  if (!videoId) return;
  const canonical = canonicalWatchUrl(videoId);
  rowZipErrors.delete(key);
  paintRowCell(key);
  if (!cfg.worker) {
    rowZipErrors.set(key,
      'Open this page from the link your teacher put in Canvas to check the link.');
    paintRowCell(key);
    return;
  }
  btn.disabled = true;
  let res = null;
  try {
    res = await requestYouTubeCheck(cfg.worker, canonical);
  } catch (err) {
    console.error(err);
    rowZipErrors.set(key, 'Could not complete the check. Try again.');
    paintRowCell(key);
    btn.disabled = false;
    return;
  }
  if (!res || res.status !== 'ok' || res.video_id !== videoId || !res.token) {
    rowZipErrors.set(key, 'YouTube reports this video as private ' +
      'or missing. Set it to Unlisted or Public and check again.');
    paintRowCell(key);
    btn.disabled = false;
    return;
  }
  btn.disabled = false;
  // The link is kept with the entry, as before — browser keeping
  // only; the binding is the Worker's, and happens at confirm.
  persistRowLink(entry, canonical, res.title || '', res.checked_at);
  if (rowDrafts.get(key) !== canonical) rowDrafts.set(key, canonical);
  const boundSha = bundleBoundVideoSha(bundle);
  let mode = 'bind';
  if (boundSha) {
    mode = (await sha256Hex(videoId)) === boundSha ? 'same' : 'supersede';
  }
  const pending = {
    videoId, token: res.token, checkedAt: res.checked_at,
    title: res.title || '', mode,
  };
  await downloadSubmissionZip(entry, bundle, btn, (msg) => {
    rowZipErrors.set(key, msg);
    paintRowCell(key);
  }, pending);
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
      kind: 'practice',
      transcript,
      audioSha256: audioSha,
      transcriptSha256: transcriptSha,
      chromaprint,
      versions: VERSIONS,
      retrievalCode: generateRetrievalToken(),
      youtubeToken: null,
      youtubeVideoId: null,
      youtubeCheckedAt: null,
    });
    const check = validateJobPayload(payload);
    if (!check.ok) throw new Error(check.reason);
    $('jobStatus').textContent = 'Sending for grading…';
    const res = await submitJob(cfg.worker, payload);
    const sentText =
      'Sent — when the grade is back, add the YouTube link in the ' +
      'job’s row below to make your Canvas submission. ' +
      'The list below updates every 5 seconds while this page is open. ' +
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
        worker: cfg.worker,
        pkg: cfg.pkg,
        course: cfg.course,
        asg: cfg.asg,
        retrieval_code: payload.retrieval_code,
        kind: payload.kind,
        youtube_link: '',
        youtube_title: '',
        youtube_checked_at: '',
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
      worker: cfg.worker,
      pkg: cfg.pkg,
      course: cfg.course,
      asg: cfg.asg,
      retrieval_code: payload.retrieval_code,
      job_id: res.job_id || '',
      kind: payload.kind,
      youtube_link: '',
      youtube_title: '',
      youtube_checked_at: '',
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
// updated in place. The title and check time are the ones already
// kept on the entry (put there by the Generate ZIP click's
// check, through persistRowLink). Shared by the WAV and
// fingerprint ZIP paths.
function keepReenteredLink(entry, bundle, link) {
  if (entry.youtube_link) return;
  const entries = loadJobEntries();
  const e = entries.find((x) => x.pkg === entry.pkg &&
    x.retrieval_code === entry.retrieval_code);
  if (e) {
    entry.youtube_link = link;
    e.youtube_link = link;
    e.youtube_title = entry.youtube_title || '';
    e.youtube_checked_at = entry.youtube_checked_at || '';
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
async function verifySubmissionParts(entry, bundle, anchor, onError, pending) {
  // A failure is reported through onError — in the row's own cell,
  // beside the field and button that were used (2.6.16) — or, with
  // no sink given, through the page's error box as before.
  const fail = onError || ((m) => showError(m, null, anchor));
  const record = await cacheGet(bundle.audio_sha256, VERSIONS.model, VERSIONS.glossary)
    .catch(() => null);
  const wav = await wavBytesForBundle(bundle);
  if (!wav || !record) {
    fail('This job’s audio is not on this computer. Its recording ' +
      'hash is ' + bundle.audio_sha256.slice(0, 12) + '… — ' +
      'choose that recording’s file in step 2, or restore it from the saved ' +
      'recordings list there, then try again.', null, anchor);
    return null;
  }
  if (!record.chunks || !record.chunks.length) {
    fail('This computer does not hold the transcript pieces for ' +
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
    fail('Audio on this computer does not match the audio this ' +
      'job was graded on (recording hash mismatch). Restore the recording ' +
      'with recording hash ' + bundle.audio_sha256.slice(0, 12) + '… in step 2 ' +
      'and try again.', null, anchor);
    return null;
  }
  if (failures.includes('transcript')) {
    fail('Packaging would use a transcript that does not match the ' +
      'transcript that was graded (checksum mismatch). The usual cause is ' +
      'the removal list in step 3: re-enter the same names and words you ' +
      'used when you sent this job, then try again.', null, anchor);
    return null;
  }
  if (failures.includes('critique')) {
    fail('Critique check failed: the critique in the grade record ' +
      'does not match its signed checksum, so nothing was packaged. ' +
      'Reload the page and retry.',
    null, anchor);
    return null;
  }
  // The HTML's YouTube link: with a pending binding (2.6.18) it
  // is the video the Generate ZIP click just checked; the
  // bundle-hash equality is established at the review's confirm,
  // when the binding is made and re-verified before packaging
  // (see doDownloadZip). Without one, the link kept with this
  // job's entry is cross-checked against the signed bundle: the
  // SHA-256 of its video ID must equal the bundle's
  // youtube_video_sha256.
  const link = entry.youtube_link || '';
  const videoId = pending ? pending.videoId : parseYouTubeVideoId(link);
  if (!videoId) {
    fail('No YouTube link is kept on this browser for this job. Enter it in the job’s row, then try again.', null, anchor);
    return null;
  }
  if (!pending) {
    const videoIdSha = await sha256Hex(videoId);
    if (bundle.youtube_video_sha256 && bundle.youtube_video_sha256 !== videoIdSha) {
      fail('A different video is kept on this browser from the one that was checked for this job.', null, anchor);
      return null;
    }
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
//   when they reproduce the graded text, and otherwise from the
//   transcript text the status response returned; either way its
//   canonical SHA-256 must equal the signed transcript_sha256;
// - the critique's SHA-256 must equal the signed critique_sha256;
// - the YouTube link kept with the entry, from the job's row,
 //   must hash to the signed youtube_video_sha256.
// Returns the verified parts, or null with the error shown beside
// the button that was used.
async function verifyFingerprintParts(entry, bundle, anchor, onError, pending) {
  const fail = onError || ((m) => showError(m, null, anchor));
  const key = jobKey(entry.pkg, entry.retrieval_code);
  const extras = readyExtras.get(key);
  const items = extras && extras.chromaprint
    ? decodeRawFingerprint(extras.chromaprint) : null;
  if (!items) {
    fail('The grading record for this job did not include its ' +
      'recording fingerprint, so the fingerprint submission cannot ' +
      'be built. Reload the page and try again.', null, anchor);
    return null;
  }
  const fingerprintBytes = new Uint8Array(
    items.buffer, items.byteOffset, items.byteLength);
  const record = await cacheGet(bundle.audio_sha256, VERSIONS.model, VERSIONS.glossary)
    .catch(() => null);
  let scrubbedChunks = null;
  let transcriptSha = null;
  let cacheCandidate = null;
  let cacheMarkedSha = null;
  if (record && record.chunks && record.chunks.length) {
    cacheCandidate = scrubChunks(
      record.chunks.map(fromCachedChunk), scrubWords());
    const [markedSha, legacySha] = await Promise.all([
      sha256Hex(canonicalTranscript(cacheCandidate)),
      sha256Hex(legacyCanonicalTranscript(cacheCandidate)),
    ]);
    cacheMarkedSha = markedSha;
    if (markedSha === bundle.transcript_sha256) {
      scrubbedChunks = cacheCandidate;
      transcriptSha = markedSha;
    } else if (legacySha === bundle.transcript_sha256) {
      scrubbedChunks = cacheCandidate;
      transcriptSha = legacySha;
    }
  }
  if (!scrubbedChunks && extras && typeof extras.transcript === 'string') {
    // Fall back to the graded transcript the Worker kept (2.6.15):
    // the cache reconstruction above is scrubbed with the removal
    // list as it stands now, so a list changed since send time
    // cannot reproduce the graded text — the stored copy is the
    // graded text itself and does not depend on the list. Before
    // this, the fallback ran only when no cache record existed,
    // and the same ZIP built correctly once the record was
    // deleted.
    const storedSha = await sha256Hex(extras.transcript);
    if (storedSha === bundle.transcript_sha256) {
      transcriptSha = storedSha;
      scrubbedChunks = chunksFromCanonical(extras.transcript);
    }
  }
  if (!scrubbedChunks && cacheCandidate) {
    // Neither source reproduced the graded transcript: package
    // nothing, and let the check below report the mismatch with
    // its removal-list guidance.
    scrubbedChunks = cacheCandidate;
    transcriptSha = cacheMarkedSha;
  }
  if (!scrubbedChunks) {
    fail('The grading record for this job did not include its ' +
      'transcript, so the submission cannot be built. Reload the ' +
      'page and try again.', null, anchor);
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
    fail('The recording fingerprint that came back with this ' +
      'grade does not match the fingerprint checksum signed with ' +
      'the grade, so nothing was packaged. Reload the page ' +
      'and retry.', null, anchor);
    return null;
  }
  if (failures.includes('transcript')) {
    fail('Packaging would use a transcript that does not match ' +
      'the transcript that was graded (checksum mismatch). The usual ' +
      'cause is the removal list in step 3: re-enter the same names ' +
      'and words you used when you sent this job, then try again.',
    null, anchor);
    return null;
  }
  if (failures.includes('critique')) {
    fail('Critique check failed: the critique in the grade ' +
      'record does not match its signed checksum, so nothing was ' +
      'packaged. Reload the page and retry.', null, anchor);
    return null;
  }
  // The link is needed only when the signed bundle names a checked
  // video; a job whose bundle carries youtube_video_sha256 "none"
  // was sent without one and packages with no link. With a pending
  // binding (2.6.18) the video is the one the Generate ZIP click
  // just checked, and the bundle-hash equality is established at
  // the review's confirm, before packaging (see doDownloadZip).
  let videoId = '';
  if (pending) {
    videoId = pending.videoId;
    keepReenteredLink(entry, bundle, entry.youtube_link || '');
  } else if (bundle.youtube_video_sha256 && bundle.youtube_video_sha256 !== 'none') {
    const link = entry.youtube_link || '';
    videoId = parseYouTubeVideoId(link) || '';
    if (!videoId) {
      fail('No YouTube link is kept on this browser for this job. ' +
        'Enter it in the job’s row, then ' +
        'try again.', null, anchor);
      return null;
    }
    const videoIdSha = await sha256Hex(videoId);
    if (videoIdSha !== bundle.youtube_video_sha256) {
      fail('That YouTube link is for a different video from ' +
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

// Generate ZIP, verification step: verify, then show
// the review panel in the job's row (renderJobRow renders it from
// zipReviews; the 5-second refresh pauses while a review is open, so
// the panel and its button are never rebuilt under the student). The
// panel's own button performs the download from the verified parts.
async function downloadSubmissionZip(entry, bundle, anchor, onError, pending) {
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
      ? await verifyFingerprintParts(entry, bundle, anchor, onError, pending)
      : await verifySubmissionParts(entry, bundle, anchor, onError, pending);
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
  // The review (2.6.18) states, in one place, what the student is
  // confirming: this job (its course and assignment), this video
  // (its title and address), and this graded transcript (its
  // opening words). Two warnings can join it: the same link on
  // another row in this browser, and — for a job already bound
  // to a different video — the supersede notice. Confirming is
  // what binds the video; see doDownloadZip.
  const key = jobKey(entry.pkg, entry.retrieval_code);
  const jobLabel = [entry.course, entry.asg].filter(Boolean).join(' · ')
    || entry.pkg;
  const extras = readyExtras.get(key);
  let opening = '';
  if (extras && typeof extras.transcript === 'string') {
    opening = extras.transcript
      .replace(/\[\d+:\d+\]\s*/g, ' ')
      .split(/\s+/).filter(Boolean).slice(0, 30).join(' ');
  }
  const videoTitle = pending ? pending.title : (entry.youtube_title || '');
  const lines = [
    jobLabel + ' · Completeness ' + bundle.completeness +
      '/5 · Accuracy ' + bundle.accuracy + '/5',
    'Checks: recording ✓ · transcript ✓ · YouTube ✓',
    'Recording: ' + recName + formatDuration(durationS) +
      ' · hash ' + bundle.audio_sha256.slice(0, 12) + '…' +
      (firstWords
        ? ' · starts “' + scrubMetadata(firstWords, words) + '…”' : '') +
      (parts.form === 'fingerprint'
        ? ' · fingerprint matches the checksum signed with the grade'
        : ' · matches the recording hash signed with the grade'),
  ];
  if (opening) {
    lines.push('Transcript starts: “' +
      scrubMetadata(opening, words) + '…”');
  }
  lines.push('YouTube: ' + (videoTitle ? '“' + videoTitle + '” · ' : '') +
    canonicalWatchUrl(parts.videoId));
  if (pending) {
    const dup = duplicateLinkEntry(key, pending.videoId);
    if (dup) {
      const dupLabel = [dup.course, dup.asg].filter(Boolean).join(' · ')
        || dup.pkg;
      lines.push('This link is also on your ' + dupLabel + ' row.');
    }
    if (pending.mode === 'supersede') {
      lines.push("This job's submission is currently a different " +
        'video. Confirming replaces it with this one; the earlier ' +
        'ZIP will no longer be the submission of record.');
    }
  }
  lines.push(pending && pending.mode !== 'same'
    ? 'Check the recording and the video are yours, then bind and download.'
    : 'Check the recording and the video title are yours, then download.');
  zipReviews.set(key, {
    receipt: bundle.receipt, parts, lines, pending: pending || null,
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
    // Binding happens here, at the confirm, and not before
    // (2.6.18): a pending bind finalises the job with the checked
    // video; a pending supersede rebinds it from the video it was
    // bound to. The ZIP is then built against the grade record as
    // it now stands, fetched back and checked to name this video.
    // A failure packages nothing and is reported in the row's
    // cell. Cancelling the review never reaches this function, so
    // a shown-but-unconfirmed supersede does not happen.
    let liveBundle = bundle;
    if (review.pending && review.pending.mode !== 'same') {
      const key = jobKey(entry.pkg, entry.retrieval_code);
      try {
        const payload = {
          pkg: entry.pkg,
          retrieval_code: entry.retrieval_code,
          youtube_video_id: review.pending.videoId,
          youtube_checked_at: review.pending.checkedAt,
        };
        payload['youtube' + '_token'] = review.pending.token;
        await finalizeJob(cfg.worker, payload);
        const status = await fetchJobStatus(cfg.worker, {
          pkg: entry.pkg, retrieval_code: entry.retrieval_code,
        });
        if (status.status === 'ready' && status.data && status.data.result) {
          liveBundle = status.data.result;
          readyBundles.set(key, liveBundle);
          if (typeof status.data.transcript === 'string' || status.data.chromaprint) {
            readyExtras.set(key, {
              transcript: typeof status.data.transcript === 'string'
                ? status.data.transcript : null,
              chromaprint: status.data.chromaprint || null,
            });
          }
        }
        if (bundleBoundVideoSha(liveBundle) !==
            (await sha256Hex(review.pending.videoId))) {
          throw new Error('the grade record does not name this video after binding');
        }
      } catch (err) {
        rowZipErrors.set(key, 'The submission could not be made: ' + err.message);
        zipReviews.delete(key);
        renderJobs();
        return;
      }
    }
    const html = assemblePackage({
      youtubeLink: canonicalWatchUrl(parts.videoId),
      audioFileName: parts.form === 'fingerprint'
        ? FINGERPRINT_FILE_NAME : AUDIO_FILE_NAME,
      durationS: parts.form === 'fingerprint'
        ? parts.durationS : parts.record.duration_s,
      chunks: parts.scrubbedChunks,
      bundle: liveBundle,
      ...(parts.form === 'fingerprint'
        ? { fingerprintSha256: liveBundle.chromaprint_sha256 } : {}),
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
      completeness: liveBundle.completeness, accuracy: liveBundle.accuracy,
      youtubeCheckedAt: entry.youtube_checked_at, gradedAt: liveBundle.t,
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

function makeZipButton(entry, bundle) {
  const zipBtn = document.createElement('button');
  zipBtn.dataset.act = 'zipgen';
  zipBtn.className = 'primary';
  zipBtn.textContent = 'Generate ZIP';
  zipBtn.addEventListener('click', () => generateZipForRow(entry, bundle, zipBtn));
  return zipBtn;
}

function renderJobRow(tbody, entry, statusInfo, unreachable) {
  const key = jobKey(entry.pkg, entry.retrieval_code);
  const bundle = statusInfo && statusInfo.status === 'ready'
    ? readyBundles.get(key) : null;
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
  else if (statusInfo.status === 'foreign') {
    statusText = 'sent to a different grading service — not checked from this page';
  }
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
  // One table row per job (2.6.16): Job | Grades | YouTube link |
  // Actions. No Practice/Final label: a job is a job, and a row
  // with no checked link is one the student has not made a
  // submission from. The critique and the ZIP review live in the
  // details row below, opened by the row's one toggle. Both rows
  // carry the job key, so a refresh rebuild can put the student's
  // focus back on the control that had it (see renderJobsOnce).
  const row = document.createElement('tr');
  row.className = 'jobrow';
  row.dataset.jobKey = key;
  const tdJob = document.createElement('td');
  const labelSpan = document.createElement('span');
  labelSpan.className = 'joblabel';
  labelSpan.textContent = label + ' · ' + statusText;
  labelSpan.title = labelSpan.textContent;
  tdJob.append(labelSpan);
  row.append(tdJob);
  const tdGrades = document.createElement('td');
  tdGrades.className = 'jobgrades';
  tdGrades.textContent = bundle
    ? 'Completeness ' + bundle.completeness + '/5 · Accuracy ' + bundle.accuracy + '/5'
    : '—';
  row.append(tdGrades);

  /* ---- the YouTube link cell ---- */
  const tdYt = document.createElement('td');
  tdYt.className = 'ytcell';
  if (!bundle) {
    const note = document.createElement('div');
    note.className = 'ytneed';
    note.textContent = statusInfo && statusInfo.status === 'foreign'
      ? 'Sent to a different grading service.'
      : 'The YouTube link goes here once the grade is back.';
    tdYt.append(note);
  } else {
    const wrap = document.createElement('div');
    wrap.className = 'ytlinkwrap';
    const input = document.createElement('input');
    input.type = 'url';
    input.dataset.act = 'ytlink';
    input.placeholder = 'https://www.youtube.com/watch?v=…';
    input.value = rowDrafts.has(key) ? rowDrafts.get(key)
      : (entry.youtube_link || '');
    if (input.value && !rowDrafts.has(key)) rowDrafts.set(key, input.value);
    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.dataset.act = 'ytclear';
    clearBtn.className = 'quiet ytclear';
    clearBtn.textContent = '×';
    clearBtn.title = 'Clear the YouTube link';
    clearBtn.setAttribute('aria-label', 'Clear the YouTube link');
    clearBtn.hidden = !input.value;
    wrap.append(input, clearBtn);
    const open = document.createElement('a');
    open.className = 'ytopen';
    open.target = '_blank';
    open.rel = 'noopener';
    open.hidden = true;
    const msg = document.createElement('div');
    tdYt.append(wrap, open, msg);
    // The row is not in the document yet, so paintRowCell cannot
    // reach it: set the cell's message and link text from the
    // standing state directly.
    const bits = rowCellBits(key);
    msg.textContent = bits.text;
    msg.className = 'ytmsg ' + bits.cls;
    if (bits.openId) {
      open.hidden = false;
      open.textContent = canonicalWatchUrl(bits.openId);
      open.href = canonicalWatchUrl(bits.openId);
    }
    input.addEventListener('input', () => {
      rowDrafts.set(key, input.value);
      clearBtn.hidden = !input.value;
      rowZipErrors.delete(key);
      // If this row's link loaded the preview player and the edit
      // changed or unreadied the video, the window clears with
      // the link (2.6.18).
      previewMaybeClear(key, parseYouTubeVideoId(input.value));
      // The Generate ZIP button follows readability, in place:
      // present while the field holds a readable link, gone
      // while it does not. No check runs on typing.
      const parsed = parseYouTubeVideoId(input.value);
      const zb = row.querySelector('[data-act="zipgen"]');
      if (parsed && !zb && entry.pkg === cfg.pkg &&
          !zipReviews.has(key)) {
        const actions = row.querySelector('.jobactions');
        const forget = row.querySelector('[data-act="remove"]');
        if (actions) {
          const btn = makeZipButton(entry, bundle);
          if (forget) actions.insertBefore(btn, forget);
          else actions.append(btn);
        }
      } else if (!parsed && zb) {
        zb.remove();
      }
      paintRowCell(key);
    });
    clearBtn.addEventListener('click', () => {
      // × clears the field and the kept link for this job: the
      // Generate ZIP button goes, the cell returns to its
      // starting line, and a preview this link loaded clears
      // with it. No confirmation.
      input.value = '';
      rowDrafts.set(key, '');
      rowZipErrors.delete(key);
      previewMaybeClear(key, null);
      persistRowLink(entry, '', '', '');
      renderJobs();
    });
    // Hover play (2.6.16): dwelling on a populated link cell for
    // about 400 ms plays its video, without sound, in the fixed
    // player area above the table; a sweep across cells starts
    // nothing, and leaving the cell pauses the preview.
    let hoverTimer = null;
    tdYt.addEventListener('mouseenter', () => {
      const id = parseYouTubeVideoId(input.value);
      if (!id) return;
      hoverTimer = setTimeout(() => previewLoad(id, true, key), 400);
    });
    tdYt.addEventListener('mouseleave', () => {
      if (hoverTimer) clearTimeout(hoverTimer);
      hoverTimer = null;
      previewPause();
    });
  }
  row.append(tdYt);

  /* ---- the actions cell ---- */
  const tdAct = document.createElement('td');
  const actions = document.createElement('div');
  actions.className = 'jobactions';
  const detailBtn = document.createElement('button');
  detailBtn.dataset.act = 'grades';
  detailBtn.textContent = expandedJobs.has(key) ? 'Hide details' : 'Show details';
  actions.append(detailBtn);
  const review = bundle ? zipReviews.get(key) : null;
  const reviewOpen = !!(review && bundle && review.receipt === bundle.receipt);
  if (bundle && entry.pkg !== cfg.pkg) {
    // Guard (2.6.2): the jobs list is browser-wide, but a submission
    // ZIP is built only from the link of the job's own assignment.
    // From another assignment's page the row says so instead of
    // offering the button, so one homework's ZIP is not downloaded
    // here and uploaded to the wrong Canvas assignment.
    const other = document.createElement('span');
    other.className = 'guardnote';
    other.textContent = 'To build this job’s submission ZIP, ' +
      'open its assignment’s link in Canvas.';
    other.title = other.textContent;
    actions.append(other);
  } else if (bundle) {
    // The Generate ZIP button is present while the row's field
    // holds a readable link (2.6.18), and exactly one ZIP control
    // per job at any moment (2.5.3): once the review panel is
    // open, the panel's confirm button replaces it.
    if (!reviewOpen && parseYouTubeVideoId(rowLinkDraft(entry))) {
      actions.append(makeZipButton(entry, bundle));
    }
  }
  const forgetBtn = document.createElement('button');
  forgetBtn.dataset.act = 'remove';
  forgetBtn.className = 'quiet';
  forgetBtn.textContent = 'Remove from this browser';
  forgetBtn.addEventListener('click', () => {
    // A review open on this row is abandoned with the job: its
    // zipReviews entry goes too, or the poll would stay paused on a
    // review that no longer exists. The row's link state goes too,
    // and a preview this row loaded clears with it.
    zipReviews.delete(key);
    expandedJobs.delete(key);
    rowDrafts.delete(key);
    rowZipErrors.delete(key);
    previewMaybeClear(key, null);
    removeJobEntry(entry.pkg, entry.retrieval_code);
    renderJobs();
  });
  actions.append(forgetBtn);
  tdAct.append(actions);
  row.append(tdAct);
  tbody.append(row);

  /* ---- the details row: critique and ZIP review ---- */
  const dtr = document.createElement('tr');
  dtr.className = 'jobdetailrow';
  dtr.dataset.jobKey = key;
  dtr.hidden = !expandedJobs.has(key);
  const dtd = document.createElement('td');
  dtd.colSpan = 4;
  const detail = document.createElement('div');
  detail.className = 'jobdetail';
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
  if (bundle && reviewOpen) {
    // The review section from a completed verification (see
    // downloadSubmissionZip): the download button first, then the
    // compact lines — the checks on one line, the recording and
    // YouTube identity in small print, and the instruction.
    const panel = document.createElement('div');
    panel.className = 'box reviewbox';
    const dlBtn = document.createElement('button');
    dlBtn.dataset.act = 'zip-download';
    dlBtn.className = 'primary';
    // The confirm label says what confirming does (2.6.18): with
    // a pending bind or supersede it binds this video and then
    // downloads; with the video already bound it only downloads.
    dlBtn.textContent = review.pending && review.pending.mode !== 'same'
      ? 'Bind this video and download the ZIP'
      : 'Download submission ZIP';
    dlBtn.addEventListener('click', () => doDownloadZip(entry, bundle, review, dlBtn));
    const closeBtn = document.createElement('button');
    closeBtn.dataset.act = 'zip-close';
    closeBtn.className = 'quiet';
    closeBtn.textContent = 'Close review';
    closeBtn.addEventListener('click', () => {
      // Closing the review restores the row's Generate ZIP button
      // and lets the 5-second poll resume (it pauses while a review
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
  dtd.append(detail);
  dtr.append(dtd);
  tbody.append(dtr);
  detailBtn.addEventListener('click', () => {
    dtr.hidden = !dtr.hidden;
    if (dtr.hidden) expandedJobs.delete(key); else expandedJobs.add(key);
    detailBtn.textContent = dtr.hidden ? 'Show details' : 'Hide details';
  });
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
    return;
  }
  // Every status is fetched before the list is touched, and all of
  // them in parallel: the box is never emptied while the network
  // answers, and one slow answer no longer delays the other rows.
  // (Before this fix the box was emptied first and each row was
  // rebuilt twice, once per sequential fetch, so the ZIP buttons
  // vanished and moved on every 5-second cycle.)
  const results = await Promise.all(entries.map(async (entry) => {
    // 2.6.12: never send a stored code to a Worker other than the
    // one that created the entry (see entryPollable in jobs.js).
    // 2.6.15: a foreign entry is marked as such, not left as a
    // failed fetch — it was counted as unreachable before, and
    // after three rounds its row claimed the service could not
    // be reached and was being retried, neither of which is true.
    if (!entryPollable(entry, cfg.worker)) return { foreign: true };
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
    if (res && res.foreign) {
      // Sent to a different grading service than this page's:
      // never polled from here, and not a failure. The row says
      // so (renderJobRow, status 'foreign').
      statusFailures.delete(key);
      jobStates.set(key, { status: 'foreign' });
      const bundle = readyBundles.get(key);
      live.push({ entry, jobId: entry.job_id || (bundle && bundle.job_id) || null });
      return;
    }
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
        // the row's ZIP flow see the job as it is.
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
  // The jobs list is a table (2.6.16): Job | Grades | YouTube link |
  // Actions, one row per job plus its details row.
  const table = document.createElement('table');
  table.className = 'jobstable';
  const thead = document.createElement('thead');
  const htr = document.createElement('tr');
  for (const h of ['Job', 'Grades', 'YouTube link', 'Actions']) {
    const th = document.createElement('th');
    th.textContent = h;
    htr.append(th);
  }
  thead.append(htr);
  table.append(thead);
  const tbody = document.createElement('tbody');
  for (const entry of survivors) {
    const key = jobKey(entry.pkg, entry.retrieval_code);
    renderJobRow(tbody, entry, jobStates.get(key) || null,
      (statusFailures.get(key) || 0) >= 3);
  }
  table.append(tbody);
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
  if (survivors.length) box.append(table);
  else box.textContent = 'No jobs sent from this browser yet.';
  if (focusMark) {
    // A job has two keyed rows (its row and its details row); the
    // focused control may sit in either, so scan both.
    for (const r of box.querySelectorAll('[data-job-key]')) {
      if (r.dataset.jobKey !== focusMark.key) continue;
      const target = r.querySelector('[data-act="' + focusMark.act + '"]');
      if (target) { target.focus({ preventScroll: true }); break; }
    }
  }
  if (entriesDirty) saveJobEntries(survivors);
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
