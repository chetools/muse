// Page wiring, HW Signing v2. Browser only. All logic that can be
// pure lives in the sibling modules; this file holds page state and
// events.
//
// Privacy invariants held here:
// - the scrub field's contents are read only to scrub, and never enter
//   any export, storage, or network call — except that the retrieval
//   name is checked against them (locally, in jobs.js) so a student
//   cannot put a scrubbed word back into a stored record;
// - nothing leaves the machine before the step-5 confirmation: the
//   job is the first network call carrying submission data, and it
//   carries the scrubbed transcript, fingerprints and versions — no
//   audio, no name, and no YouTube link;
// - browser storage holds only what the design settles: IndexedDB
//   caches the student's own recordings and corrected transcripts
//   (pre-scrub) on this machine, and localStorage holds the job
//   entries (retrieval name and code, labels, expiry, and the
//   YouTube link kept locally for ZIP creation). The transcript and
//   the grades are never written to localStorage.

import { parseConfig, buildConfigLink } from './config.js';
import { sha256Hex } from './hash.js';
import {
  parseScrubWords, scrubChunks, scrubMetadata, canonicalTranscript,
  findSuspects, formatDuration,
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
import { fromCachedChunk } from './cachekey.js';
import {
  parseYouTubeVideoId, canonicalWatchUrl, validateRetrievalName,
  validateJobPayload, buildJobPayload, loadJobEntries, addJobEntry,
  removeJobEntry, pruneExpiredEntries, saveJobEntries, fetchWorkerInfo,
  requestYouTubeCheck, submitJob, fetchJobStatus, markJobRetrieved,
} from './jobs.js';
import { subscribeToPush } from './push.js';
import { buildZip, SUBMISSION_ZIP_NAME, ZIP_ENTRY_HTML, ZIP_ENTRY_AUDIO } from './zip.js';

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
let ytCheck = null;         // { videoId, token, checkedAt } after an ok check
let ytPlayer = null;
let ytApiPromise = null;
const readyBundles = new Map(); // "pkg|name" -> result bundle from /jobs/status

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
function kind() { return $('kindFinal').checked ? 'final' : 'practice'; }

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
    showError('The model could not be loaded. Check the connection and try again.', err);
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
  $('audioDl').disabled = !wavBytes;
  setAudioMeta();
  refreshDerived();
}

$('mediaFile').addEventListener('change', async (ev) => {
  clearError();
  const file = ev.target.files && ev.target.files[0];
  pcm = null; wavBytes = null; audioSha = null; durationS = 0;
  chunks = []; windowsDoneBase = 0;
  transcriptionComplete = false;
  confirmed = false; $('confirmChk').checked = false;
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
    setAudioMeta();
    $('audioDl').disabled = false;
    // Cache check: a hit restores the transcript with no transcription.
    const record = await cacheGet(audioSha, VERSIONS.model, VERSIONS.glossary)
      .catch(() => null);
    await cacheInit(audioSha, {
      model: VERSIONS.model, glossary: VERSIONS.glossary,
      wavBlob: new Blob([wavBytes], { type: 'audio/wav' }), duration_s: durationS,
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
    showError('The chosen file could not be decoded as audio or video by this browser.', err);
  }
});

$('audioDl').addEventListener('click', () => {
  if (!wavBytes) return;
  downloadBlob(new Blob([wavBytes], { type: 'audio/wav' }), AUDIO_FILE_NAME);
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
    row.append(document.createTextNode(
      when + ' · ' + formatDuration(entry.duration_s) + ' · ' +
      (entry.size_bytes / 1048576).toFixed(1) + ' MB · ' +
      (entry.complete ? 'transcribed' : 'partly transcribed (' + entry.chunks + ' pieces)') +
      ' · fingerprint ' + entry.audio_sha256.slice(0, 12) + '… '));
    const restoreBtn = document.createElement('button');
    restoreBtn.textContent = 'Restore';
    restoreBtn.addEventListener('click', async () => {
      clearError();
      try {
        const record = await cacheGet(entry.audio_sha256, VERSIONS.model, VERSIONS.glossary);
        if (!record) { showError('That saved recording was made by an older model or glossary version and cannot be restored.'); return; }
        audioSha = entry.audio_sha256;
        sourceName = '';
        pcm = null;
        updateRunEnabled();
        await adoptCacheRecord(record, 'Recording restored from this computer.');
      } catch (err) { showError('The saved recording could not be restored.', err); }
    });
    const delBtn = document.createElement('button');
    delBtn.textContent = 'Delete';
    delBtn.addEventListener('click', async () => {
      await cacheDelete(entry.audio_sha256).catch(() => {});
      renderCacheList();
    });
    row.append(restoreBtn, document.createTextNode(' '), delBtn);
    box.append(row);
  }
}

// --- Scrub field: re-derive everything when it changes ---
$('scrubField').addEventListener('input', () => {
  confirmed = false;
  $('confirmChk').checked = false;
  setAudioMeta();
  refreshDerived();
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
    showError('Transcription failed or stopped partway. Pieces already shown are kept and saved; choosing the same file again resumes.', err);
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
  const ytReady = kind() !== 'final' || !!ytCheck;
  $('submitJobBtn').disabled = !(base && ytReady);
}
$('kindPractice').addEventListener('change', () => {
  $('finalFields').hidden = true;
  updateJobEnabled();
});
$('kindFinal').addEventListener('change', () => {
  $('finalFields').hidden = false;
  updateJobEnabled();
});
$('retrievalName').addEventListener('input', updateJobEnabled);
$('retrievalCode').addEventListener('input', updateJobEnabled);

// YouTube: the link invalidates any earlier check when it changes.
$('ytLink').addEventListener('input', () => {
  ytCheck = null;
  $('ytStatus').textContent = '';
  $('ytPlayerWrap').hidden = true;
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
// with the extracted audio's. A preview failure (embedding disabled,
// sign-in required) is a warning, not a block: the Worker check is
// the gate.
async function previewYouTube(videoId) {
  try {
    const YT = await loadYouTubeApi();
    $('ytPlayerWrap').hidden = false;
    if (ytPlayer) { ytPlayer.loadVideoById(videoId); return; }
    ytPlayer = new YT.Player('ytPlayer', {
      width: '480', height: '270', videoId,
      events: {
        onReady: (ev) => {
          const ytDuration = ev.target.getDuration();
          if (ytDuration > 0 && durationS > 0) {
            const diff = Math.abs(ytDuration - durationS);
            if (diff > Math.max(2, 0.02 * durationS)) {
              $('ytStatus').textContent +=
                ' Warning: the video runs ' + ytDuration.toFixed(1) +
                ' s but the audio runs ' + durationS.toFixed(1) +
                ' s — this may not be the same recording.';
            }
          }
        },
        onError: () => {
          $('ytStatus').textContent +=
            ' The preview could not play this video here (it may have embedding turned off); the link check above is what counts.';
        },
      },
    });
  } catch { /* preview is best-effort */ }
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
  try {
    const res = await requestYouTubeCheck(cfg.worker, canonicalWatchUrl(videoId));
    if (res.status === 'ok' && res.video_id === videoId && res.token) {
      ytCheck = { videoId, token: res.token, checkedAt: res.checked_at };
      $('ytStatus').textContent = 'Link checks out: the video is reachable (Unlisted or Public).';
    } else {
      ytCheck = null;
      $('ytStatus').textContent =
        'YouTube reports this video as private or missing. Set it to Unlisted or Public and check again.';
    }
  } catch (err) {
    ytCheck = null;
    $('ytStatus').textContent = 'The check could not be completed. Try again.';
    console.error(err);
  }
  previewYouTube(videoId);
  updateJobEnabled();
});

$('submitJobBtn').addEventListener('click', async () => {
  clearError();
  const nameCheck = validateRetrievalName($('retrievalName').value.trim(), scrubWords());
  if (!nameCheck.ok) {
    $('jobStatus').textContent = nameCheck.reason;
    return;
  }
  $('submitJobBtn').disabled = true;
  $('jobStatus').textContent = 'Preparing…';
  try {
    const transcript = canonical();
    const transcriptSha = await sha256Hex(transcript);
    let pushSubscription = null;
    if ($('notifyChk').checked) {
      $('jobStatus').textContent = 'Setting up the notification…';
      try {
        const info = await fetchWorkerInfo(cfg.worker);
        pushSubscription = await subscribeToPush(info && info.vapid_public_key);
      } catch (err) { console.error(err); }
      if (!pushSubscription) {
        $('jobStatus').textContent =
          'Notification could not be set up (permission or browser support); sending without it.';
      }
    }
    const payload = buildJobPayload({
      pkg: cfg.pkg,
      pkgContentSha256: cfg.ph,
      kind: kind(),
      transcript,
      audioSha256: audioSha,
      transcriptSha256: transcriptSha,
      versions: VERSIONS,
      retrievalName: $('retrievalName').value.trim(),
      retrievalCode: $('retrievalCode').value,
      youtubeToken: ytCheck ? ytCheck.token : null,
      youtubeVideoId: ytCheck ? ytCheck.videoId : null,
      youtubeCheckedAt: ytCheck ? ytCheck.checkedAt : null,
      pushSubscription,
    });
    const check = validateJobPayload(payload);
    if (!check.ok) throw new Error(check.reason);
    $('jobStatus').textContent = 'Sending for grading…';
    const res = await submitJob(cfg.worker, payload);
    addJobEntry({
      pkg: cfg.pkg,
      course: cfg.course,
      asg: cfg.asg,
      retrieval_name: payload.retrieval_name,
      retrieval_code: payload.retrieval_code,
      kind: payload.kind,
      youtube_link: payload.kind === 'final' ? $('ytLink').value.trim() : '',
      created_at: res.created_at,
      expires_at: res.expires_at,
    });
    $('jobStatus').textContent =
      'Sent. Grading usually takes minutes; this page shows the result when it is ready, ' +
      'and the job is kept until ' + new Date(res.expires_at).toLocaleString() + '.';
    renderJobs();
  } catch (err) {
    showError('Sending for grading failed: ' + err.message, err);
    $('jobStatus').textContent = '';
  } finally {
    updateJobEnabled();
  }
});

// --- Retrieval: jobs list, grades reveal, ZIP download ---
function jobKey(pkg, name) { return pkg + '|' + name; }

async function wavBytesForBundle(bundle) {
  if (wavBytes && audioSha === bundle.audio_sha256) return wavBytes;
  const record = await cacheGet(bundle.audio_sha256, VERSIONS.model, VERSIONS.glossary)
    .catch(() => null);
  if (record && record.wavBlob) {
    return new Uint8Array(await record.wavBlob.arrayBuffer());
  }
  return null;
}

async function downloadSubmissionZip(entry, bundle) {
  const wav = await wavBytesForBundle(bundle);
  if (!wav) {
    showError('The audio for this job is not on this computer. Choose the recording file in step 2 (or restore it from the saved recordings), then download the ZIP.');
    return;
  }
  // The HTML's YouTube link comes from local keeping only; cross-check
  // it against the signed bundle: the SHA-256 of its video ID must
  // equal the bundle's youtube_video_sha256.
  const link = entry.youtube_link || '';
  const videoId = parseYouTubeVideoId(link);
  if (!videoId) {
    showError('The YouTube link kept on this browser is missing. Re-enter it in step 6 and download again from the job list after re-checking.');
    return;
  }
  const videoIdSha = await sha256Hex(videoId);
  if (bundle.youtube_video_sha256 && bundle.youtube_video_sha256 !== videoIdSha) {
    showError('The YouTube link kept on this browser is not the video that was checked for this job.');
    return;
  }
  const record = await cacheGet(bundle.audio_sha256, VERSIONS.model, VERSIONS.glossary)
    .catch(() => null);
  const cachedChunks = record && record.chunks && record.chunks.length
    ? record.chunks.map(fromCachedChunk)
    : chunks;
  const html = assemblePackage({
    youtubeLink: canonicalWatchUrl(videoId),
    audioFileName: AUDIO_FILE_NAME,
    durationS: record ? record.duration_s : durationS,
    chunks: scrubChunks(cachedChunks, scrubWords()),
    bundle,
  });
  const zip = buildZip([
    { name: ZIP_ENTRY_HTML, data: new TextEncoder().encode(html) },
    { name: ZIP_ENTRY_AUDIO, data: wav },
  ]);
  downloadBlob(zip, SUBMISSION_ZIP_NAME);
  try {
    await markJobRetrieved(cfg.worker, {
      pkg: entry.pkg, retrieval_name: entry.retrieval_name, retrieval_code: entry.retrieval_code,
    });
  } catch { /* the ZIP is already in the student's hands */ }
  removeJobEntry(entry.pkg, entry.retrieval_name);
  renderJobs();
}

function renderJobRow(container, entry, statusInfo) {
  const row = document.createElement('div');
  row.className = 'jobrow';
  const label = [entry.course, entry.asg].filter(Boolean).join(' · ') || entry.pkg;
  const statusText = statusInfo === null ? 'checking…'
    : statusInfo === 'forbidden' ? 'not found under this name and code'
    : statusInfo === 'ready' ? 'ready'
    : 'grading';
  row.append(document.createTextNode(
    label + ' — ' + entry.retrieval_name + ' (' + entry.kind + '): ' + statusText + ' '));
  if (statusInfo === 'ready') {
    const bundle = readyBundles.get(jobKey(entry.pkg, entry.retrieval_name));
    const showBtn = document.createElement('button');
    showBtn.textContent = 'Show grades and critique';
    const detail = document.createElement('div');
    detail.hidden = true;
    if (bundle) {
      detail.innerHTML = '';
      const p = document.createElement('p');
      p.textContent = 'Completeness: ' + bundle.completeness + '/5 · Accuracy: ' +
        bundle.accuracy + '/5';
      const crit = document.createElement('div');
      crit.className = 'box';
      crit.textContent = bundle.critique || '';
      detail.append(p, crit);
    }
    showBtn.addEventListener('click', () => {
      detail.hidden = !detail.hidden;
      showBtn.textContent = detail.hidden ? 'Show grades and critique' : 'Hide grades and critique';
    });
    row.append(showBtn, detail);
    if (entry.kind === 'final' && bundle) {
      const zipBtn = document.createElement('button');
      zipBtn.className = 'primary';
      zipBtn.textContent = 'Download submission ZIP';
      zipBtn.addEventListener('click', () => downloadSubmissionZip(entry, bundle));
      row.append(document.createTextNode(' '), zipBtn);
    }
  }
  const forgetBtn = document.createElement('button');
  forgetBtn.textContent = 'Remove from this browser';
  forgetBtn.addEventListener('click', () => {
    removeJobEntry(entry.pkg, entry.retrieval_name);
    renderJobs();
  });
  row.append(document.createTextNode(' '), forgetBtn);
  container.append(row);
}

async function renderJobs() {
  const box = $('jobsBox');
  // localStorage hygiene: expired entries are dropped on load — the
  // Worker has deleted those jobs in any case.
  const entries = pruneExpiredEntries(loadJobEntries(), Date.now());
  saveJobEntries(entries);
  if (!entries.length) { box.textContent = 'No jobs sent from this browser yet.'; return; }
  box.textContent = '';
  for (const entry of entries) {
    const holder = document.createElement('div');
    box.append(holder);
    renderJobRow(holder, entry, null);
    try {
      const res = await fetchJobStatus(cfg.worker, {
        pkg: entry.pkg, retrieval_name: entry.retrieval_name, retrieval_code: entry.retrieval_code,
      });
      if (res.status === 'ready' && res.data && res.data.result) {
        readyBundles.set(jobKey(entry.pkg, entry.retrieval_name), res.data.result);
      }
      holder.textContent = '';
      renderJobRow(holder, entry, res.status);
    } catch {
      holder.textContent = '';
      renderJobRow(holder, entry, 'grading');
    }
  }
}

// Manual retrieval (different browser): status by typed name + code
// against the configured package. On ready, the same rendering is
// used, with a synthetic entry; the ZIP path then needs the audio on
// this computer, as the section text states.
$('manualBtn').addEventListener('click', async () => {
  clearError();
  const name = $('manualName').value.trim();
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
      pkg: cfg.pkg, retrieval_name: name, retrieval_code: code,
    });
    if (res.status === 'forbidden') {
      $('manualStatus').textContent = 'No job under that name and code.';
      return;
    }
    $('manualStatus').textContent = 'Status: ' + res.status + '.';
    if (res.status === 'ready' && res.data && res.data.result) {
      const entry = {
        pkg: cfg.pkg, course: cfg.course, asg: cfg.asg,
        retrieval_name: name, retrieval_code: code,
        kind: res.data.result.youtube_video_sha256 && res.data.result.youtube_video_sha256 !== 'none'
          ? 'final' : 'practice',
        youtube_link: '',
        created_at: '', expires_at: '',
      };
      // A final job retrieved manually needs its YouTube link for the
      // HTML; it is not stored anywhere off the original browser, so
      // the student enters it in step 6 and the row reads the live
      // entry at click time (the signed video hash check in
      // downloadSubmissionZip verifies it is the checked video).
      readyBundles.set(jobKey(entry.pkg, entry.retrieval_name), res.data.result);
      entry.youtube_link = $('ytLink').value.trim();
      $('ytLink').addEventListener('input', () => {
        entry.youtube_link = $('ytLink').value.trim();
      });
      box.hidden = false;
      box.textContent = '';
      const note = document.createElement('p');
      note.className = 'note';
      note.textContent = entry.kind === 'final'
        ? 'Final job. Enter the YouTube link in step 6 (it is checked against the signed record when the ZIP is built), then use Download submission ZIP here.'
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
