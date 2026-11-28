// Page wiring, HW Signing v2. Browser only. All logic that can be
// pure lives in the sibling modules; this file holds page state and
// events.
//
// Privacy invariants held here:
// - the scrub field's contents are read only to scrub, and never enter
//   any export, storage, or network call;
// - nothing leaves the machine before the step-4 confirmation: the
//   job is the first network call carrying submission data, and it
//   carries the scrubbed transcript, fingerprints and versions — no
//   audio, no name, and no YouTube link;
// - browser storage holds only what the design settles: IndexedDB
//   caches the student's own recordings and corrected transcripts
//   (pre-scrub) on this machine, and localStorage holds the job
//   entries (retrieval code, labels, expiry, the
//   YouTube link and its title kept locally for ZIP creation, and
//   — since 2.8.0 — the removal selections made at send time,
//   stored as positions only: an entry index and appearance
//   ordinals, never the removal field's contents). The
//   transcript and the grades are never written to localStorage.

import { parseConfig, buildConfigLink } from './config.js';
import { sha256Hex } from './hash.js';
import {
  parseScrubWords, scrubChunks, scrubChunksSelective, scrubMetadata,
  canonicalTranscript, formatDuration,
  entryAppearances, PICKER_THRESHOLD,
} from './transcript.js';
import {
  buildSketch, buildWordCounts, addedWords, ADDED_WORDS_THRESHOLD,
} from './sketch.js';
import { solvePow, powBucket, POW_FALLBACK_BITS } from './pow.js';
import {
  VERSIONS, AUDIO_FILE_NAME, FINGERPRINT_FILE_NAME, assemblePackage,
  chunksFromCanonical, formatTranscriptTimestamp,
} from './package.js';
import { encodeWavPcm16, pcmFromWavBytes, decodeFileTo16kMono, SAMPLE_RATE } from './media.js';
import { loadModel, transcribePcm, FILE_WINDOW_S } from './transcribe.js';
import {
  cacheGet, cacheInit, cachePutChunk, cacheWindowDone, cacheComplete,
  cacheList, cacheDelete,
  cacheAddSentSketch, cacheSentSketches, cacheExtendSketchExpiry,
} from './cache.js';
import { fromCachedChunk } from './cachekey.js';
import {
  parseYouTubeVideoId, canonicalWatchUrl,
  bundleChromaprintSha, verifyFingerprintContents,
  validateJobPayload, buildJobPayload, generateRetrievalToken, loadJobEntries, addJobEntry, entryPollable,
  removeJobEntry, saveJobEntries,
  collapseSameJobEntries,
  requestYouTubeCheck, submitJob, fetchJobStatus, fetchWorkerInfo,
  finalizeJob,
} from './jobs.js';
import { computeFingerprint } from './fingerprint.js';
import { decodeRawFingerprint } from './fingerprint.js';
import { buildZipAsync, submissionZipName, ZIP_ENTRY_HTML } from './zip.js';

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
let transcriptionRunId = null; // the cache record's run identifier (2.8.0)
// A2 picker state (2.8.0): removal entry text -> the set of
// appearance ordinals the student has chosen to remove. An entry
// absent from the map is at its default: the first offered
// appearance is chosen. Only ordinals are ever kept — never the
// entry's text in any storage (the map is memory only).
const pickerSelections = new Map();
let pickerSignature = '';
// Submission preparation state (2.8.0; see pow.js): solved tokens
// by bucket, the in-flight search, the Worker's difficulty, and
// the offset between the Worker's clock and this machine's (the
// bucket is reckoned on the Worker's time, from its root
// response). None of this is named or explained on the page.
const powTokens = new Map(); // bucket -> { key, nonce }
let powSolving = null;       // { key, bucket, signal }
let powBits = POW_FALLBACK_BITS;
let serverOffsetMs = 0;
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
const rowCheckedInfo = new Map(); // jobKey -> {videoId, title, opening} from
// the row's passed reachability check (2.7.0): the link cell then
// shows the video title and the transcript's opening words — the
// identity the removed ZIP review panel used to show, now in the
// row — and the canonical watch address is built from the video
// ID the Worker returned, not from the page's own parse.
const readyBundles = new Map(); // "pkg|code" -> result bundle from /jobs/status
const readyExtras = new Map();  // "pkg|code" -> {transcript, chromaprint,
// injection_flags} from the same status response (Worker 2.7.0; the
// flags since Worker 2.9.0): the stored transcript text, the raw
// fingerprint as base64, and the grader's injection flags, kept in
// memory only, for the fingerprint-form ZIP
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

// A2 (2.8.0; threshold 1 since 2.8.1): a removal entry that
// appears more than PICKER_THRESHOLD times in the corrected
// transcript is applied selectively — only the appearances the
// student picked are removed (see renderPicker). Returns
// entry -> appearances.
function pickerEntries() {
  const out = new Map();
  if (!chunks.length) return out;
  for (const w of scrubWords()) {
    const apps = entryAppearances(chunks, w);
    if (apps.length > PICKER_THRESHOLD) out.set(w, apps);
  }
  return out;
}

// The appearances the picker offers: the first three and the
// last two.
function offeredOrdinals(apps) {
  const ords = apps.map((a) => a.ordinal);
  return ords.length <= 5 ? ords : [...ords.slice(0, 3), ...ords.slice(-2)];
}

// The ordinals chosen for removal: the student's stored choice,
// or the default — the first offered appearance.
function pickerRemovedOrdinals(entry) {
  return pickerSelections.get(entry) || new Set([0]);
}

function scrubbed() {
  const selective = pickerEntries();
  const ordinary = scrubWords().filter((w) => !selective.has(w));
  let stage = chunks;
  for (const [w] of selective) {
    stage = scrubChunksSelective(stage, w, pickerRemovedOrdinals(w));
  }
  return scrubChunks(stage, ordinary);
}

// The picker itself, under the removal list: one block per
// repeated entry, offering the first three and last
// two appearances with their surrounding words. Rebuilt only
// when the offered set changes, so toggling a choice never
// rebuilds the block being clicked.
function renderPicker() {
  const box = $('scrubPicker');
  if (!box) return;
  const selective = pickerEntries();
  const sig = [...selective.entries()]
    .map(([w, apps]) => w + ':' + apps.length).join('|');
  if (sig === pickerSignature) return;
  pickerSignature = sig;
  box.textContent = '';
  for (const [entry, apps] of selective) {
    const wrap = document.createElement('div');
    wrap.className = 'box';
    const head = document.createElement('p');
    head.className = 'note';
    head.textContent = '“' + entry + '” appears ' + apps.length +
      ' times in the transcript. Choose which appearances to remove — only the chosen ones are removed:';
    wrap.append(head);
    const removed = pickerRemovedOrdinals(entry);
    for (const ord of offeredOrdinals(apps)) {
      const label = document.createElement('label');
      label.style.display = 'block';
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = removed.has(ord);
      cb.addEventListener('change', () => {
        const set = new Set(pickerRemovedOrdinals(entry));
        if (cb.checked) set.add(ord); else set.delete(ord);
        pickerSelections.set(entry, set);
        refreshDerived();
      });
      label.append(cb, document.createTextNode(' …' + apps[ord].phrase + '…'));
      wrap.append(label);
    }
    box.append(wrap);
  }
}

// The removal selections as they stand, for the job entry stored
// at send time: entry index into the removal list, and the
// appearance ordinals removed. Positions only — the removal
// field's contents never enter storage.
function currentRemovalSelections() {
  const selective = pickerEntries();
  const out = [];
  scrubWords().forEach((entry, idx) => {
    if (selective.has(entry)) {
      out.push({
        entry_index: idx,
        appearances_removed: [...pickerRemovedOrdinals(entry)].sort((a, b) => a - b),
      });
    }
  });
  return out;
}

// ------------------------------------------------------------
// Background submission preparation (2.8.0; pow.js). The search
// runs while the student reviews the transcript, keyed to the
// exact transcript, recording and run; a change to any of them
// abandons the search and starts another. Nothing about the
// mechanism is named on the page.

function powKey(tSha) {
  return audioSha + '|' + tSha + '|' + (transcriptionRunId || '');
}

async function kickPow() {
  if (!cfg.worker || !audioSha || !transcriptionComplete || !chunks.length) return;
  const transcript = canonical();
  if (!transcript) return;
  const tSha = await sha256Hex(transcript);
  const key = powKey(tSha);
  const bucket = powBucket(Date.now() + serverOffsetMs);
  const have = powTokens.get(bucket);
  if (have && have.key === key) return;
  if (powSolving && powSolving.key === key && powSolving.bucket === bucket) return;
  if (powSolving) powSolving.signal.aborted = true;
  const signal = { aborted: false };
  powSolving = { key, bucket, signal };
  const res = await solvePow({
    audioSha256: audioSha, transcriptSha256: tSha,
    runId: transcriptionRunId || '', bucket, bits: powBits, signal,
  });
  if (powSolving && powSolving.signal === signal) powSolving = null;
  if (res && !signal.aborted) {
    powTokens.set(bucket, { key, nonce: res.nonce });
    const nowBucket = powBucket(Date.now() + serverOffsetMs);
    for (const b of powTokens.keys()) {
      if (b < nowBucket - 1) powTokens.delete(b);
    }
  }
}

// The solved token for this exact submission: the current
// bucket's, or the previous bucket's when the search finished
// just before the bucket turned (the Worker accepts both, so a
// completed token is submitted, never discarded). Waits — with
// the plain status line beside the Send button — for a search
// already running; returns null when none arrives in time, and
// the send then proceeds without one.
async function awaitPowToken(tSha) {
  const key = powKey(tSha);
  const pick = () => {
    const bucket = powBucket(Date.now() + serverOffsetMs);
    for (const b of [bucket, bucket - 1]) {
      const t = powTokens.get(b);
      if (t && t.key === key) return { bucket: b, nonce: t.nonce };
    }
    return null;
  };
  let token = pick();
  if (token) return token;
  void kickPow();
  const deadline = Date.now() + 120000;
  while (Date.now() < deadline) {
    $('jobStatus').textContent =
      'Preparing your submission — this takes a short while…';
    await new Promise((r) => setTimeout(r, 300));
    token = pick();
    if (token) return token;
    if (!powSolving) void kickPow();
  }
  return null;
}
function canonical() { return canonicalTranscript(scrubbed()); }
// There is no Practice/Final choice anywhere in the page, and
// no job kind is sent (2.7.0): a job is sent with no YouTube
// link, and the submission is made afterwards from the job's own
// row in section 6. No video is bound to a job: the row's
// Generate ZIP click finalises the job — marking it final, with
// no video attached — and the ZIP carries the row's link as
// package data. The entry's local finalised flag records that
// this browser's finalize call succeeded.

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
  }
}
// The model loads automatically when the page opens (2.6.4).
// There is no model section (2.6.20): while it loads, only the
// progress bar shows; when it has loaded, the bar goes and
// nothing replaces it. The button appears only after a failed
// load, as the retry, beside the one-line failure note; in
// teacher setup mode, where nothing loads on its own, it is
// the manual load button.
let modelLoading = false;
async function startModelLoad() {
  if (model || modelLoading) return;
  modelLoading = true;
  clearError();
  $('loadBtn').hidden = true;
  $('loadProg').hidden = false;
  $('loadStatus').textContent = '';
  try {
    model = await loadModel(onDownloadProgress);
    $('loadProg').hidden = true;
    updateRunEnabled();
  } catch (err) {
    console.error(err);
    $('loadProg').hidden = true;
    $('loadStatus').textContent = 'Model did not load. Check the connection and try again.';
    $('loadBtn').textContent = 'Retry';
    $('loadBtn').hidden = false;
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

// Compute the Chromaprint once from the normalised WAV's own
// int16 samples — the same samples the audio SHA-256 is computed
// over — and keep it in state for the job payload. Runs in the
// background after normalisation; a failure leaves chromaprint
// null, and since 2.7.0 the submit handler then blocks the send:
// a job is never sent without its fingerprint. Never awaited by
// the media stage: the submit handler awaits the in-flight
// promise, if any, before building the payload.
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
  transcriptionRunId = record.transcription_run_id || null;
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
  transcriptionRunId = null;
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
    // The record after init holds the run identifier (minted on
    // creation or reset, kept on resume); adopt it for the send.
    if (!record) {
      const fresh = await cacheGet(audioSha, VERSIONS.model, VERSIONS.glossary)
        .catch(() => null);
      transcriptionRunId = fresh ? (fresh.transcription_run_id || null) : null;
    } else {
      transcriptionRunId = record.transcription_run_id || null;
    }
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
// The last list fetched from IndexedDB is kept in memory
// (cacheListMemory): re-rendering for a scrub-field change uses
// the memory copy, so typing in the scrub field never re-reads
// IndexedDB per keystroke (2.7.0).
let cacheListMemory = [];

async function renderCacheList() {
  let list = [];
  try { list = await cacheList(); } catch { list = []; }
  cacheListMemory = list;
  renderCacheRows(list);
}

function renderCacheRows(list) {
  const box = $('cacheBox');
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
        transcriptionRunId = null;
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

// --- Scrub field: re-derive the scrubbed views when it changes ---
// Per keystroke (2.7.0) only the scrubbed views re-derive, and
// the recordings list re-renders from the in-memory list, with
// no IndexedDB re-read.
$('scrubField').addEventListener('input', () => {
  setAudioMeta();
  refreshDerived();
  renderCacheRows(cacheListMemory);
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
  renderPicker();
  void kickPow();
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
  updateJobEnabled();
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
// A link added or replaced in a row plays in the viewing area
// at once (2.6.20), without waiting for a hover: the commit is
// the field holding a readable video different from the one the
// field held before. If another row's video was showing, the
// area updates to this one. Clearing keeps the clearing
// behaviour below.
function previewOnLinkCommit(key, videoId) {
  if (!videoId) return;
  if (previewKey === key && previewVideoId === videoId) return;
  previewLoad(videoId, true, key);
}

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

/* ---------------- per-row links (2.6.18; no binding, 2.6.19) ----------------
 * Each ready job's row carries its own link field. No check runs
 * while the student types: the field's text is parsed for
 * readability only (a Studio address is converted to the watch
 * form automatically), and the Generate ZIP button is present
 * exactly while the field holds a readable link. The one check —
 * the Worker reporting the video reachable (Public or Unlisted)
 * through /youtube-check — runs at the Generate ZIP click, as
 * part of the one-click Generate ZIP flow. No video is bound
 * to the job: the click finalises the job (marking it final)
 * and downloads the ZIP carrying the row's link (see
 * generateZipForRow).
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
// failure in small red text, else — once the row's check has
// passed — the video title and the transcript's opening words
// (the identity the ZIP review panel used to show, in the row
// since 2.7.0), else the starting line while the field holds no
// readable link, else nothing. The open link's address is built
// from the video ID the Worker returned at the check once a
// check has run, and from the page's parse only before that.
function rowCellBits(key) {
  const zipErr = rowZipErrors.get(key);
  const draft = rowDrafts.get(key) || '';
  const parsed = parseYouTubeVideoId(draft);
  const checked = rowCheckedInfo.get(key);
  const bits = { text: '', cls: 'ytneed', openId: checked ? checked.videoId : parsed };
  if (zipErr) { bits.text = zipErr; bits.cls = 'ytreason'; return bits; }
  if (checked) {
    bits.cls = 'ytok';
    bits.text = (checked.title ? '\u201c' + checked.title + '\u201d' : 'Video checked') +
      (checked.opening ? ' \u00b7 starts \u201c' + checked.opening + '\u2026\u201d' : '');
    return bits;
  }
  if (!parsed) {
    bits.text = 'Necessary for ZIP generation';
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

// Generate ZIP, from a row holding a readable link (2.7.0): one
// click does the whole flow — the Worker's reachability check
// runs now; on a pass the row's cell shows the video title and
// the transcript's opening words, the job is finalised, its
// status is re-fetched, and the fingerprint-form ZIP is packaged
// and downloaded (see packageSubmissionZip). There is no review
// panel. A private or missing video, a failed check, or any
// later failure is reported in the row's own cell in small red
// text and nothing is packaged. No video is bound to the job:
// the ZIP carries the row's checked link as package data, and
// the canonical watch address is built from the video ID the
// Worker returned, not from the page's parse.
async function generateZipForRow(entry, bundle, btn) {
  const key = jobKey(entry.pkg, entry.retrieval_code);
  const videoId = parseYouTubeVideoId(rowLinkDraft(entry));
  if (!videoId) return;
  rowZipErrors.delete(key);
  paintRowCell(key);
  if (!cfg.worker) {
    rowZipErrors.set(key,
      'Open this page from the link your teacher put in Canvas to check the link.');
    paintRowCell(key);
    return;
  }
  const fail = (msg) => {
    rowZipErrors.set(key, msg);
    paintRowCell(key);
  };
  btn.disabled = true;
  zipBusy = true;
  try {
    let res = null;
    try {
      res = await requestYouTubeCheck(cfg.worker, canonicalWatchUrl(videoId));
    } catch (err) {
      console.error(err);
      fail('Could not complete the check. Try again.');
      return;
    }
    if (!res || res.status !== 'ok') {
      fail('YouTube reports this video as private ' +
        'or missing. Set it to Unlisted or Public and check again.');
      return;
    }
    const checkedId = res.video_id || videoId;
    const canonical = canonicalWatchUrl(checkedId);
    // The link is kept with the entry, as before — browser keeping
    // only. It is package data: the ZIP is built with this link.
    persistRowLink(entry, canonical, res.title || '', res.checked_at);
    previewOnLinkCommit(key, checkedId);
    if (rowDrafts.get(key) !== canonical) rowDrafts.set(key, canonical);
    paintRowCell(key);
    // Finalise the job in this browser: the call is idempotent
    // (a job that already stands final returns the same success).
    // On success the entry's finalised flag is set and kept.
    let liveBundle = bundle;
    try {
      await finalizeJob(cfg.worker, {
        pkg: entry.pkg,
        retrieval_code: entry.retrieval_code,
      });
      markEntryFinalised(entry);
      const st = await fetchJobStatus(cfg.worker, {
        pkg: entry.pkg, retrieval_code: entry.retrieval_code,
      });
      if (st.status === 'ready' && st.data && st.data.result) {
        liveBundle = st.data.result;
        readyBundles.set(key, liveBundle);
        if (typeof st.data.transcript === 'string' || st.data.chromaprint) {
          readyExtras.set(key, {
            transcript: typeof st.data.transcript === 'string'
              ? st.data.transcript : null,
            chromaprint: st.data.chromaprint || null,
            injection_flags: Array.isArray(st.data.injection_flags)
              ? st.data.injection_flags : null,
          });
        }
      }
    } catch (err) {
      fail('The submission could not be made: ' + err.message);
      return;
    }
    // The check has passed: the row now shows the video title and
    // the graded transcript's opening words.
    const extras = readyExtras.get(key);
    let opening = '';
    if (extras && typeof extras.transcript === 'string') {
      opening = extras.transcript
        .replace(/\[\d+:\d+\]\s*/g, ' ')
        .split(/\s+/).filter(Boolean).slice(0, 30).join(' ');
    }
    rowCheckedInfo.set(key, {
      videoId: checkedId,
      title: res.title || '',
      opening: opening ? scrubMetadata(opening, scrubWords()) : '',
    });
    paintRowCell(key);
    const pending = { videoId: checkedId, title: res.title || '' };
    await packageSubmissionZip(entry, liveBundle, btn, fail, pending);
  } finally {
    zipBusy = false;
    btn.disabled = false;
  }
}

// Record that this browser finalised the job: the entry's
// finalised flag is set on the entry object and on its stored
// copy (2.7.0).
function markEntryFinalised(entry) {
  entry.finalised = true;
  const entries = loadJobEntries();
  const e = entries.find((x) => x.pkg === entry.pkg &&
    x.retrieval_code === entry.retrieval_code);
  if (e) {
    e.finalised = true;
    saveJobEntries(entries);
  }
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
    // Component A (2.8.0): refuse a send that adds fewer than
    // ADDED_WORDS_THRESHOLD words to a version already sent for
    // this package from this recording on this machine. The
    // comparison is against the stored sketches (sketch.js); the
    // refusal is plain language, beside the Send button, and
    // nothing is sent.
    {
      const sketches = await cacheSentSketches(audioSha, cfg.pkg).catch(() => []);
      if (sketches.length) {
        const counts = await buildWordCounts(transcript);
        const nearDuplicate = sketches.some(
          (sk) => addedWords(counts, sk) < ADDED_WORDS_THRESHOLD);
        if (nearDuplicate) {
          const msg = 'This version is almost the same as one you ' +
            'already sent for this homework, so it was not sent. ' +
            'To send again, change more of the explanation — or ' +
            'record it again and transcribe the new recording.';
          showError(msg, null, $('submitJobBtn'));
          $('jobStatus').textContent = msg;
          return;
        }
      }
    }
    // The fingerprint is computed in the background after
    // normalisation; wait for it here. Since 2.7.0 a fingerprint
    // failure BLOCKS the send: without a fingerprint no
    // fingerprint-form submission ZIP could ever be built from
    // the job. The error lands beside
    // the Send control through the catch below (showError with
    // the button as anchor, and the status line beside it).
    if (chromaprintPending) await chromaprintPending;
    if (!chromaprint) {
      throw new Error('This recording could not be fingerprinted, ' +
        'so it cannot be sent. Choose the recording file again, ' +
        'then send once it has been read.');
    }
    // The background preparation (pow.js) has normally finished
    // while the student reviewed the transcript; wait for it if
    // it has not. The wait is the plain status line beside the
    // button; nothing about the mechanism is named.
    const pow = await awaitPowToken(transcriptSha);
    const payload = buildJobPayload({
      pkg: cfg.pkg,
      pkgContentSha256: cfg.ph,
      transcript,
      audioSha256: audioSha,
      transcriptSha256: transcriptSha,
      chromaprint,
      versions: VERSIONS,
      retrievalCode: generateRetrievalToken(),
      runId: transcriptionRunId,
      pow,
    });
    const check = validateJobPayload(payload);
    if (!check.ok) throw new Error(check.reason);
    $('jobStatus').textContent = 'Sending for grading…';
    const res = await submitJob(cfg.worker, payload);
    const sentText =
      'Sent — when the grade is back, add the YouTube link in the ' +
      'job’s row below to make your Canvas submission.';
    // The send happened (a job was created, or the Worker
    // answered that this exact submission already stands):
    // snapshot the as-sent transcript's sketch for the
    // near-duplicate check on later sends (Component A). The
    // sketch is stored in the recording's cache record with the
    // job's expiry; failures here never block the send's outcome.
    cacheAddSentSketch(audioSha, {
      pkg: cfg.pkg,
      sketch: await buildSketch(transcript).catch(() => null),
      expires_at: res.expires_at,
    }).catch(() => {});
    if (res.duplicate) {
      // This exact submission (same recording, same transcript,
      // same transcription run) already stands as a live job: no
      // new job was created, and the submitted code does not
      // retrieve the existing job — no entry is stored for it.
      // The queue state or grades from the response are shown in
      // the status line beside the button; the existing job's own
      // row in the list below is where it is followed.
      $('jobStatus').textContent =
        'Already sent — this exact version is already in for ' +
        'grading. ' + duplicateStatusText(res);
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
      finalised: false,
      youtube_link: '',
      youtube_title: '',
      youtube_checked_at: '',
      created_at: res.created_at,
      expires_at: res.expires_at,
      // The A2 removal selections made at this send (positions
      // only; see currentRemovalSelections).
      removal_selections: currentRemovalSelections(),
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

// Live status for the ZIP build (2.4.6): a labelled native
// progress element placed directly after the button that started
// the step. The jobs refresh is paused while the step runs
// (zipBusy), so the element is never rebuilt out from under the
// student. When the step finishes the element is removed: the
// outcome is the downloaded file plus the brief completion line
// above the jobs list.
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
// check, through persistRowLink).
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

// Verify the one thing that is still re-hashed before packaging
// (2.7.0): the fingerprint bytes held locally (decoded from the
// status response) against the signed chromaprint_sha256. The
// critique is not re-hashed, and Worker-supplied parts are not
// re-hashed: the packaged transcript is the as-sent text the
// Worker returns with the grade — never a re-scrub of this
// computer's cached chunks under the current removal list
// (2.8.0: the removal list may have changed since the send, and
// a re-scrub would package a transcript that was never graded).
// The packaged transcript is the graded text the
// status response returned, parsed back into chunks; when the
// Worker sent none, packaging fails with the message below —
// there is no fallback to this computer's cached chunks. There
// is no audio ZIP form: a job whose bundle carries no signed
// fingerprint hash cannot be packaged. The YouTube link is not verified against
// the bundle: no video is bound to the job.
// Returns the verified parts, or null with the error shown in
// the row's cell through onError.
async function verifyFingerprintParts(entry, bundle, anchor, onError, pending) {
  const fail = onError || ((m) => showError(m, null, anchor));
  if (!bundleChromaprintSha(bundle)) {
    fail('This job has no recording fingerprint in its grade ' +
      'record, so a submission ZIP cannot be built for it.', null, anchor);
    return null;
  }
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
  const fingerprintSha = await sha256Hex(fingerprintBytes);
  const failures = verifyFingerprintContents(bundle, {
    fingerprintSha256: fingerprintSha,
  });
  if (failures.includes('fingerprint')) {
    fail('The recording fingerprint that came back with this ' +
      'grade does not match the fingerprint checksum signed with ' +
      'the grade, so nothing was packaged. Reload the page ' +
      'and retry.', null, anchor);
    return null;
  }
  const record = await cacheGet(bundle.audio_sha256, VERSIONS.model, VERSIONS.glossary)
    .catch(() => null);
  // The packaged transcript is the as-sent text the Worker
  // returned (2.8.0): there is no fallback to the cached chunks.
  const scrubbedChunks = extras && typeof extras.transcript === 'string'
    ? chunksFromCanonical(extras.transcript)
    : null;
  if (!scrubbedChunks) {
    fail('The grading record for this job did not include its ' +
      'transcript, so the submission cannot be built. Reload the ' +
      'page and try again.', null, anchor);
    return null;
  }
  // The HTML's YouTube link: with a checked video pending it is
  // the video the Generate ZIP click just checked; without one it
  // is the link kept with this job's entry.
  const link = entry.youtube_link || '';
  const videoId = pending ? pending.videoId : parseYouTubeVideoId(link);
  if (!videoId) {
    fail('No YouTube link is kept on this browser for this job. Enter it in the job\u2019s row, then try again.', null, anchor);
    return null;
  }
  keepReenteredLink(entry, bundle, link);
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

// Package and download, the last step of the Generate ZIP click
// (2.7.0): verify the fingerprint, build the fingerprint-form
// ZIP from the grade record as it now stands (liveBundle, fetched
// back after the finalize), download it, and mark the job
// retrieved. A failure packages nothing and is reported in the
// row's cell through onError.
async function packageSubmissionZip(entry, liveBundle, anchor, onError, pending) {
  const status = showZipStatus(anchor,
    'Verifying the fingerprint against the signed grade record…');
  let parts = null;
  try {
    // Let the status paint before the verification hash begins.
    await new Promise((resolve) => setTimeout(resolve, 0));
    parts = await verifyFingerprintParts(entry, liveBundle, anchor, onError, pending);
  } finally {
    status.box.remove();
  }
  if (!parts) return;
  const build = showZipStatus(anchor, 'Building the submission ZIP…');
  try {
    const zipExtras = readyExtras.get(jobKey(entry.pkg, entry.retrieval_code));
    const html = assemblePackage({
      youtubeLink: canonicalWatchUrl(parts.videoId),
      audioFileName: FINGERPRINT_FILE_NAME,
      durationS: parts.durationS,
      chunks: parts.scrubbedChunks,
      bundle: liveBundle,
      fingerprintSha256: liveBundle.chromaprint_sha256,
      // The grader's injection flags, copied from the status
      // response into the package (2.8.0): the audit app reads
      // them from the package; it does not scan itself.
      injectionFlags: zipExtras && Array.isArray(zipExtras.injection_flags)
        ? zipExtras.injection_flags : undefined,
    });
    const zip = await buildZipAsync([
      { name: ZIP_ENTRY_HTML, data: new TextEncoder().encode(html) },
      { name: FINGERPRINT_FILE_NAME, data: parts.fingerprintBytes },
    ], (done, total) => {
      build.bar.max = total;
      build.bar.value = done;
      build.label.textContent = 'Building the submission ZIP… ' +
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
    // The job entry is kept (2.6.6): a download does not remove
    // the row, so the ZIP can be downloaded again; "Remove from
    // this browser" remains the student's own way to clear it.
    renderJobs();
  } finally {
    build.box.remove();
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
      const prevParsed = parseYouTubeVideoId(rowDrafts.get(key) || '');
      rowDrafts.set(key, input.value);
      clearBtn.hidden = !input.value;
      rowZipErrors.delete(key);
      rowCheckedInfo.delete(key);
      // A link added or replaced in the row plays in the viewing
      // area at once (2.6.20). If this row's link loaded the
      // player and the edit unreadied it, the window clears with
      // the link (2.6.18).
      const nowParsed = parseYouTubeVideoId(input.value);
      if (nowParsed && nowParsed !== prevParsed) {
        previewOnLinkCommit(key, nowParsed);
      } else if (!nowParsed) {
        previewMaybeClear(key, null);
      }
      // The Generate ZIP button follows readability, in place:
      // present while the field holds a readable link, gone
      // while it does not. No check runs on typing.
      const parsed = parseYouTubeVideoId(input.value);
      const zb = row.querySelector('[data-act="zipgen"]');
      if (parsed && !zb && entry.pkg === cfg.pkg) {
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
      rowCheckedInfo.delete(key);
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
      // The timer re-validates when it fires (2.6.20): a row
      // rebuilt, cleared or edited within the dwell must not
      // resurrect the video it no longer holds.
      hoverTimer = setTimeout(() => {
        if (!document.contains(input)) return;
        if (parseYouTubeVideoId(input.value) !== id) return;
        previewLoad(id, true, key);
      }, 400);
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
    // holds a readable link (2.6.18): parseYouTubeVideoId gates
    // the button's presence only — the one reachability check
    // runs at the click.
    if (parseYouTubeVideoId(rowLinkDraft(entry))) {
      actions.append(makeZipButton(entry, bundle));
    }
  }
  const forgetBtn = document.createElement('button');
  forgetBtn.dataset.act = 'remove';
  forgetBtn.className = 'quiet';
  forgetBtn.textContent = 'Remove from this browser';
  forgetBtn.addEventListener('click', () => {
    // The row's link and check state go with the job, and a
    // preview this row loaded clears with it.
    expandedJobs.delete(key);
    rowDrafts.delete(key);
    rowZipErrors.delete(key);
    rowCheckedInfo.delete(key);
    previewMaybeClear(key, null);
    removeJobEntry(entry.pkg, entry.retrieval_code);
    renderJobs();
  });
  actions.append(forgetBtn);
  tdAct.append(actions);
  row.append(tdAct);
  tbody.append(row);

  /* ---- the details row: critique ---- */
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
    if (lastJobsFingerprint !== '') {
      box.textContent = 'No jobs sent from this browser yet.';
      lastJobsFingerprint = '';
    }
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
      // The Worker has deleted the job; drop the entry and its row.
      entriesDirty = true;
      readyBundles.delete(key);
      readyExtras.delete(key);
      jobStates.delete(key);
      statusFailures.delete(key);
      rowCheckedInfo.delete(key);
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
        // path; an older Worker sends neither.
        if (typeof res.data.transcript === 'string' || res.data.chromaprint) {
          readyExtras.set(key, {
            transcript: typeof res.data.transcript === 'string'
              ? res.data.transcript : null,
            chromaprint: res.data.chromaprint || null,
            injection_flags: Array.isArray(res.data.injection_flags)
              ? res.data.injection_flags : null,
          });
        }
        // The job stands graded: its sketches' horizon becomes
        // the graded one (180 days) in the recording's record.
        if (res.data.result && res.data.result.audio_sha256) {
          cacheExtendSketchExpiry(res.data.result.audio_sha256,
            entry.pkg, res.data.expires_at).catch(() => {});
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
  // visit.
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
    for (const { entry } of live) {
      const key = jobKey(entry.pkg, entry.retrieval_code);
      if (keptKeys.has(key)) continue;
      readyBundles.delete(key);
      readyExtras.delete(key);
      jobStates.delete(key);
      statusFailures.delete(key);
    }
  }
  const survivors = kept.map(({ entry }) => entry);
  // Poll rebuild skip (2.7.0): when the fetched states match the
  // rendered states — the per-entry status/grades fingerprint
  // below — the table is not rebuilt at all, so a poll with
  // nothing changed causes no focus churn. Entry bookkeeping
  // (expiry, collapse) above has already run and is persisted.
  const renderedFp = jobsRenderFingerprint(survivors);
  if (renderedFp === lastJobsFingerprint) {
    if (entriesDirty) saveJobEntries(survivors);
    return;
  }
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
  lastJobsFingerprint = renderedFp;
  if (entriesDirty) saveJobEntries(survivors);
}

// The fingerprint of what the jobs table renders for these
// entries: per entry, its label fields, its kept link, its
// finalised flag, its last-seen status and queue position, its
// unreachable flag, and its ready bundle's grades, critique and
// receipt. Draft text typed in a row is excluded: the input
// handler paints those changes in place.
let lastJobsFingerprint = null;
function jobsRenderFingerprint(survivors) {
  return survivors.map((entry) => {
    const key = jobKey(entry.pkg, entry.retrieval_code);
    const st = jobStates.get(key);
    const b = readyBundles.get(key);
    return [
      key, entry.course || '', entry.asg || '',
      entry.youtube_link || '', entry.finalised ? '1' : '0',
      st ? st.status : '', st && st.queue_ahead != null ? st.queue_ahead : '',
      (statusFailures.get(key) || 0) >= 3 ? 'unreachable' : '',
      b ? [b.completeness, b.accuracy, b.critique || '', b.receipt || ''].join('/') : '',
    ].join('|');
  }).join('\n');
}

// The jobs list refreshes itself every 5 seconds while the page is
// open, so a waiting student sees the queue move and the grade arrive
// without reloading — no notification is needed. A poll is skipped
// while the tab is hidden or while a ZIP verification or download
// is running (zipBusy). Since 2.7.0 there is no review panel to
// protect, and a poll whose fetched states match the rendered
// states skips the rebuild entirely (see jobsRenderFingerprint).
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
  if (zipBusy) return;
  try { await renderJobs(); } catch { /* the next tick retries */ }
}
setInterval(refreshJobs, 5000);

// Background preparation upkeep (2.8.0): read the Worker's clock
// and difficulty once at load (the bucket is reckoned on the
// Worker's time), and re-check the preparation every minute so
// a bucket that turns while the page sits open starts the next
// search without waiting for an edit. A failed read leaves the
// fallback difficulty and this machine's clock, and the send
// path still waits for a search at the click.
if (cfg.worker) {
  fetchWorkerInfo(cfg.worker).then((info) => {
    if (info && info.pow && Number.isInteger(info.pow.difficulty_bits)) {
      powBits = info.pow.difficulty_bits;
    }
    const t = info && Date.parse(info.server_time || '');
    if (!Number.isNaN(t)) serverOffsetMs = t - Date.now();
    void kickPow();
  }).catch(() => {});
}
setInterval(() => { void kickPow(); }, 60000);

renderConfig();
refreshDerived();
renderCacheList();
renderJobs();
if (cfg.setup) {
  $('loadBtn').hidden = false;
} else {
  startModelLoad();
}
