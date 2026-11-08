// Page wiring (plan steps 2–5). Browser only. All logic that can be pure
// lives in the sibling modules; this file holds page state and events.
//
// Privacy invariants held here:
// - the scrub field's contents are read only to scrub, and never enter
//   any export, storage, or network call;
// - nothing is written to browser storage: the page keeps no autosave,
//   so no unscrubbed text can persist;
// - the only network call carrying submission data is the signing call
//   (fingerprints and versions only), to the configured Worker.

import { parseConfig, buildConfigLink } from './config.js';
import { sha256Hex } from './hash.js';
import {
  parseScrubWords, scrubChunks, scrubMetadata, canonicalTranscript,
  findSuspects,
} from './transcript.js';
import { validateResultBlock } from './resultblock.js';
import { buildHandoff, handoffFileName } from './handoff.js';
import {
  AUDIO_FILE_NAME, PACKAGE_FILE_NAME, buildSigningPayload,
  requestSignature, assemblePackage, generateSessionCode,
  formatTranscriptTimestamp,
} from './package.js';
import { encodeWavPcm16, decodeFileTo16kMono, SAMPLE_RATE } from './media.js';
import { loadModel, transcribePcm } from './transcribe.js';
import { buildVocabulary } from './vocab.js';

const $ = (id) => document.getElementById(id);
const cfg = parseConfig(window.location.search);

let model = null;
let pcm = null;
let wavBytes = null;
let audioSha = null;
let durationS = 0;
let sourceName = '';
let chunks = [];            // pipeline output: {start, end, raw, corrected, ...}
let transcriptionComplete = false;  // true only after a full run finishes
let pkgText = null;                 // fetched prompt package text, if pkgurl set
let pkgFetchFailed = false;
let confirmed = false;
let vocabulary = null;      // built lazily on first review render

function showError(message, err) {
  const box = $('errBox');
  box.textContent = message;
  box.style.display = 'block';
  if (err) console.error(err);
}
function clearError() { $('errBox').style.display = 'none'; }

function scrubWords() { return parseScrubWords($('scrubField').value); }
function scrubbed() { return scrubChunks(chunks, scrubWords()); }
function canonical() { return canonicalTranscript(scrubbed()); }

// --- Configuration display and teacher setup ---
function renderConfig() {
  const parts = [];
  if (cfg.course) parts.push('Course: ' + cfg.course);
  if (cfg.asg) parts.push('Assignment: ' + cfg.asg);
  if (cfg.pkg) parts.push('Prompt package: ' + cfg.pkg);
  if (cfg.pkgurl && pkgText) {
    parts.push('package file loaded (' + pkgText.length + ' characters, included in the handoff file)');
  } else if (cfg.pkgurl && pkgFetchFailed) {
    parts.push('package file could not be fetched (the handoff file will name the package instead)');
  } else if (cfg.pkgurl) {
    parts.push('package file loading…');
  }
  if (cfg.worker) parts.push('Signing Worker: ' + cfg.worker);
  $('cfgLine').textContent = parts.length
    ? 'Configuration — ' + parts.join(' · ')
    : 'Configuration: none in this link. The teacher’s configured link sets the course, the prompt package, and the signing Worker.';
  if (!cfg.worker || !cfg.pkg) {
    $('packageStatus').textContent =
      'Packaging needs the teacher’s configured link (signing Worker and prompt package).';
  }
  if (cfg.setup) {
    $('setupSection').hidden = false;
    $('suWorker').value = cfg.worker || '';
    $('suPkg').value = cfg.pkg || '';
    $('suPkgUrl').value = cfg.pkgurl || '';
    $('suCourse').value = cfg.course || '';
    $('suAsg').value = cfg.asg || '';
  }
}
$('suBuild').addEventListener('click', () => {
  const link = buildConfigLink(window.location.origin + window.location.pathname, {
    worker: $('suWorker').value.trim(),
    pkg: $('suPkg').value.trim(),
    pkgurl: $('suPkgUrl').value.trim(),
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
    showError('The model could not be loaded. Check the connection and try again.', err);
    $('loadBtn').disabled = false;
  }
});

// --- Media stage ---
function updateRunEnabled() { $('runBtn').disabled = !(model && pcm); }

$('mediaFile').addEventListener('change', async (ev) => {
  clearError();
  const file = ev.target.files && ev.target.files[0];
  pcm = null; wavBytes = null; audioSha = null; durationS = 0;
  transcriptionComplete = false;
  $('audioDl').disabled = true;
  updateRunEnabled();
  if (!file) { $('mediaStatus').textContent = 'No file chosen.'; return; }
  sourceName = file.name;
  $('mediaStatus').textContent = 'Reading the file…';
  try {
    pcm = await decodeFileTo16kMono(file);
    durationS = pcm.length / SAMPLE_RATE;
    wavBytes = encodeWavPcm16(pcm);
    audioSha = await sha256Hex(wavBytes);
    $('mediaStatus').textContent = 'Audio extracted on this device.';
    $('audioMeta').textContent =
      'Source file: ' + scrubMetadata(sourceName, scrubWords()) +
      ' · duration ' + durationS.toFixed(1) + ' s' +
      ' · extracted audio: ' + AUDIO_FILE_NAME +
      ' · SHA-256 ' + audioSha;
    $('audioDl').disabled = false;
    updateRunEnabled();
    refreshDerived();
  } catch (err) {
    $('mediaStatus').textContent = 'That file could not be decoded.';
    showError('The chosen file could not be decoded as audio or video by this browser.', err);
  }
});

$('audioDl').addEventListener('click', () => {
  if (!wavBytes) return;
  const blob = new Blob([wavBytes], { type: 'audio/wav' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = AUDIO_FILE_NAME;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
});

// --- Scrub field: re-derive everything when it changes ---
$('scrubField').addEventListener('input', () => {
  confirmed = false;
  $('confirmChk').checked = false;
  if (sourceName) {
    $('audioMeta').textContent =
      'Source file: ' + scrubMetadata(sourceName, scrubWords()) +
      ' · duration ' + durationS.toFixed(1) + ' s' +
      ' · extracted audio: ' + AUDIO_FILE_NAME +
      ' · SHA-256 ' + (audioSha || '');
  }
  refreshDerived();
});

// --- Transcription ---
$('runBtn').addEventListener('click', async () => {
  if (!model || !pcm) return;
  clearError();
  chunks = [];
  transcriptionComplete = false;
  confirmed = false;
  $('confirmChk').checked = false;
  $('runBtn').disabled = true;
  $('runProg').hidden = false;
  $('runProg').value = 0;
  $('liveBox').hidden = false;
  $('runStatus').textContent = 'Transcribing…';
  const t0 = performance.now();
  let lastPct = 0;
  const timer = setInterval(() => {
    $('runStatus').textContent = 'Transcribing… ' + lastPct +
      ' % of the audio · ' + Math.round((performance.now() - t0) / 1000) +
      ' s elapsed. The page may appear to pause while a piece is processed.';
  }, 1000);
  try {
    await transcribePcm(model, pcm, durationS, {
      onWindow: (done, total) => {
        if (total > 0) {
          lastPct = Math.round(100 * Math.min(1, done / total));
          $('runProg').value = Math.min(1, done / total);
        }
      },
      onChunk: (item, progress) => {
        chunks.push(item);
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
    $('runStatus').textContent = chunks.length
      ? 'Done — ' + chunks.length + ' piece(s).'
      : 'The model returned no text for this recording.';
  } catch (err) {
    showError('Transcription failed or stopped partway. Pieces already shown are kept.', err);
    $('runStatus').textContent = '';
  } finally {
    clearInterval(timer);
    $('runBtn').disabled = false;
    refreshDerived();
  }
});

// --- Derived views: transcript, checksum note, review list ---
async function refreshDerived() {
  const sc = scrubbed();
  if (sc.length) {
    $('transcriptBox').textContent = sc
      .map((c) => '[' + formatTranscriptTimestamp(c.start) + '] ' + c.text)
      .join('\n');
    $('handoffBtn').disabled = !(transcriptionComplete && confirmed);
    const words = scrubWords();
    $('scrubStatus').textContent = words.length
      ? 'Removal list active: ' + words.length + ' entr' + (words.length === 1 ? 'y' : 'ies') + '.'
      : '';
  } else {
    $('transcriptBox').textContent = 'The transcript will appear here.';
    $('handoffBtn').disabled = true;
  }
  renderSuspects(sc);
  updatePackageEnabled();
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

$('handoffBtn').addEventListener('click', () => {
  const text = canonical();
  if (!text) return;
  const blob = new Blob([buildHandoff(cfg, text, pkgText)], { type: 'text/markdown' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = handoffFileName(cfg);
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  $('handoffStatus').textContent =
    'Handoff file downloaded as ' + handoffFileName(cfg) +
    (pkgText
      ? '. It includes the prompt package; give the file to Muse.'
      : '. Give it to Muse together with the prompt package.');
});

$('confirmChk').addEventListener('change', () => {
  confirmed = $('confirmChk').checked;
  updatePackageEnabled();
  refreshDerived();
});

// --- Result block validation ---
let validResult = null;
async function checkResult() {
  const res = await validateResultBlock($('resultPaste').value, sha256Hex);
  validResult = res.ok ? res.parsed : null;
  $('resultStatus').textContent = res.ok
    ? 'Result block accepted — completeness ' + res.parsed.completeness +
      '/5, accuracy ' + res.parsed.accuracy + '/5.'
    : res.reason;
  updatePackageEnabled();
  return res;
}
$('validateBtn').addEventListener('click', checkResult);
$('resultPaste').addEventListener('input', () => {
  validResult = null;
  $('resultStatus').textContent = '';
  updatePackageEnabled();
});

// --- Packaging ---
function updatePackageEnabled() {
  $('packageBtn').disabled = !(
    cfg.worker && cfg.pkg && wavBytes && audioSha && chunks.length &&
    confirmed && validResult && $('ytLink').value.trim());
}

$('packageBtn').addEventListener('click', async () => {
  clearError();
  $('packageBtn').disabled = true;
  $('packageStatus').textContent = 'Checking the result block…';
  try {
    const res = await checkResult();
    if (!res.ok) throw new Error(res.reason);
    const transcriptSha = await sha256Hex(canonical());
    const session = generateSessionCode();
    const payload = buildSigningPayload({
      session, audioSha256: audioSha, transcriptSha256: transcriptSha, pkg: cfg.pkg,
    });
    $('packageStatus').textContent = 'Signing…';
    const { t, receipt } = await requestSignature(cfg.worker, payload);
    const html = assemblePackage({
      youtubeLink: $('ytLink').value.trim(),
      audioFileName: AUDIO_FILE_NAME,
      durationS,
      audioSha256: audioSha,
      transcriptSha256: transcriptSha,
      pkg: cfg.pkg,
      session,
      t,
      receipt,
      chunks: scrubbed(),
      result: res.parsed,
    });
    const blob = new Blob([html], { type: 'text/html' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = PACKAGE_FILE_NAME;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    $('packageStatus').textContent =
      'Package downloaded as ' + PACKAGE_FILE_NAME + '. Submit it with ' +
      AUDIO_FILE_NAME + ' in one Canvas attempt.';
  } catch (err) {
    showError('Packaging failed: ' + err.message, err);
    $('packageStatus').textContent = '';
  } finally {
    updatePackageEnabled();
  }
});

renderConfig();
refreshDerived();

// Fetch the prompt package file, when the configured link carries its
// address, so the handoff file can include it whole. A failed fetch is
// not fatal: the handoff file then names the package and the student
// supplies it separately, as before.
if (cfg.pkgurl) {
  fetch(cfg.pkgurl)
    .then((r) => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    })
    .then((t) => { pkgText = t; renderConfig(); })
    .catch(() => { pkgFetchFailed = true; renderConfig(); });
}
