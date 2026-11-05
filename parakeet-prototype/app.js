// Parakeet transcription page — page logic.
// Order matters: ONNX Runtime Web is imported and pointed at the WASM
// binaries vendored on this site BEFORE parakeet.js is imported, so the
// library never falls back to its default CDN address for those binaries.
import * as ort from 'onnxruntime-web';
import { correctWithLog } from './corrections.js';
import { assembleSegments, renderMarked, wordCount, formatTimestamp, escapeHtml } from './segments.js';
import { saveAutosave, loadAutosave, writeAutosaveFile, browserStorage } from './autosave.js';

ort.env.wasm.wasmPaths = new URL('./vendor/ort/', window.location.href).href;
ort.env.wasm.numThreads = 1;
ort.env.logLevel = 'warning';

const $ = (id) => document.getElementById(id);
const loadBtn = $('loadBtn'), runBtn = $('runBtn'), copyBtn = $('copyBtn');
const downloadBtn = $('downloadBtn'), tsCheck = $('tsCheck');
const loadProg = $('loadProg'), runProg = $('runProg');
const loadStatus = $('loadStatus'), runStatus = $('runStatus');
const audioStatus = $('audioStatus'), metrics = $('metrics');
const errBox = $('errBox'), transcriptBox = $('transcript'), netlog = $('netlog');
const correctionsBox = $('corrections'), saveStatus = $('saveStatus');
const liveProg = $('liveProg'), liveStatus = $('liveStatus'), liveBox = $('liveBox');
const liveRaw = $('liveRaw'), liveCorrected = $('liveCorrected'), liveMeta = $('liveMeta');

function showError(message, err) {
  errBox.textContent = message;
  errBox.style.display = 'block';
  if (err) console.error(err);
}
function clearError() { errBox.style.display = 'none'; errBox.textContent = ''; }

// --- Network log: list every resource this page fetches, from the
// browser's own resource timing records. ---
const seenResources = new Set();
function renderNetlog() {
  const entries = performance.getEntriesByType('resource')
    .map((e) => e.name).filter((n) => !n.startsWith('blob:'));
  for (const name of entries) seenResources.add(name);
  const list = [...seenResources];
  netlog.textContent = list.length
    ? list.map((n) => {
        let host = '(this site)';
        try { const u = new URL(n); if (u.origin !== window.location.origin) host = u.host; } catch { /* keep label */ }
        return host + '  ' + n;
      }).join('\n')
    : '(no resources recorded yet)';
}
new PerformanceObserver(renderNetlog).observe({ type: 'resource', buffered: true });
renderNetlog();

// --- Corrections applied: aggregated across segments so the reader can
// check every correction, including any over-correction by a predicted pair.
function renderApplied(agg) {
  if (!agg || agg.size === 0) {
    correctionsBox.textContent = 'No corrections were applied to this transcript.';
    return;
  }
  const lines = [...agg.values()].map((a) =>
    '“' + a.heard + '” → “' + a.term + '”' + (a.count > 1 ? ' ×' + a.count : '') +
    (a.mode === 'slash' ? ' — uncertain: the transcript shows the heard form and every candidate, slash-separated' : '') +
    (a.mode === 'context' ? ' — chosen by context (cue word “' + a.cue + '”)' : ''));
  correctionsBox.textContent = lines.join('\n');
}
function aggregateApplied(agg, applied) {
  for (const a of applied) {
    const key = a.heard + '|' + a.mode + '|' + a.term + '|' + (a.cue || '');
    const prev = agg.get(key);
    if (prev) prev.count += a.count; else agg.set(key, { ...a });
  }
}

// --- Autosave (SPEC B5): in-browser save after every transcribed segment
// and every 15 s while a transcript exists; optional file-on-disk save
// through the File System Access API. A failed save shows a note here and
// never interrupts transcription.
const storage = browserStorage();
let fileHandle = null;
let fileWriteChain = Promise.resolve();
let hasTranscript = false;
let lastSource = 'file';

function currentTranscriptText() { return hasTranscript ? transcriptBox.textContent : ''; }

async function autosaveNow() {
  const text = currentTranscriptText();
  if (!text) return;
  const when = new Date();
  const okLocal = saveAutosave(storage, {
    text, savedAtISO: when.toISOString(), source: lastSource,
  });
  let note = okLocal
    ? 'Autosave: saved in this browser at ' + when.toLocaleTimeString() + '.'
    : 'Autosave: the in-browser save failed (storage unavailable). Download the transcript to keep it.';
  if (fileHandle) {
    // File writes are serialised through one chain: two saves must
    // never open a writable on the same handle at the same time.
    const run = fileWriteChain.then(() => writeAutosaveFile(fileHandle, text));
    fileWriteChain = run.then(() => undefined, () => undefined);
    const okFile = await run;
    note += okFile
      ? ' Saved to the chosen file as well.'
      : ' The save to the chosen file failed; the in-browser save above still holds.';
  }
  saveStatus.textContent = note;
}
setInterval(() => { if (hasTranscript) autosaveNow(); }, 15000);
window.addEventListener('beforeunload', () => {
  const text = currentTranscriptText();
  if (text) {
    saveAutosave(storage, { text, savedAtISO: new Date().toISOString(), source: lastSource });
    // A last file write is attempted on the serialised chain; a
    // browser closing the page may not let it finish, which is why
    // the in-browser save above is the guaranteed copy at close.
    if (fileHandle) autosaveNow();
  }
});

// Restore offer on load: never overwrites anything; the reader chooses.
const savedAutosave = loadAutosave(storage);
if (savedAutosave) {
  const when = new Date(savedAutosave.savedAtISO);
  $('restoreInfo').textContent = 'An autosaved transcript from ' +
    (Number.isNaN(when.getTime()) ? 'an earlier session' : when.toLocaleString()) +
    ' (' + (savedAutosave.source || 'file') + ') is saved in this browser. ';
  $('restoreBox').style.display = 'block';
  $('restoreBtn').addEventListener('click', () => {
    transcriptBox.textContent = savedAutosave.text;
    hasTranscript = true;
    lastSource = savedAutosave.source || 'file';
    copyBtn.disabled = false;
    downloadBtn.disabled = false;
    correctionsBox.textContent = 'Restored autosaved transcript. The list of corrections ' +
      'applied is not stored with an autosave.';
    $('restoreBox').style.display = 'none';
  });
}

const fsSupported = typeof window.showSaveFilePicker === 'function';
if (fsSupported) {
  $('autosaveFileBtn').disabled = false;
  $('fsNote').textContent = '';
} else {
  $('fsNote').textContent = 'This browser does not offer file picking to pages, so the ' +
    'file save needs the “Choose autosave file” button in desktop Chrome; the in-browser ' +
    'autosave is active either way.';
}
$('autosaveFileBtn').addEventListener('click', async () => {
  try {
    fileHandle = await window.showSaveFilePicker({
      suggestedName: 'parakeet-transcript.txt',
      types: [{ description: 'Text file', accept: { 'text/plain': ['.txt'] } }],
    });
    saveStatus.textContent = 'Autosave file chosen: ' + (fileHandle.name || 'parakeet-transcript.txt') +
      '. The transcript will be written to it after every piece and every 15 s.';
    if (hasTranscript) autosaveNow();
  } catch { /* the file picker was closed without a choice; nothing changes */ }
});

downloadBtn.addEventListener('click', () => {
  const text = currentTranscriptText();
  if (!text) return;
  const blob = new Blob([text], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'parakeet-transcript.txt';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
});

// --- Live progress: the words of each piece are shown as soon as the
// piece is transcribed, first as transcribed and then after the glossary
// correction, with corrected words marked. The full transcript below
// grows the same way, piece by piece, with the same marks. Copy,
// download and autosave read the transcript box's plain text, so the
// marks never enter a saved transcript.
let liveWords = 0;
function renderTranscript(segments, useTimestamps) {
  const clean = (segments || []).filter((sg) => sg && sg.text && sg.text.trim());
  if (!clean.length) { transcriptBox.textContent = ''; return; }
  transcriptBox.innerHTML = clean.map((sg) => {
    const body = sg.parts ? renderMarked(sg.parts) : escapeHtml(sg.text.trim());
    return useTimestamps ? '[' + formatTimestamp(sg.start || 0) + '] ' + body : body;
  }).join(useTimestamps ? '\n' : ' ');
}
function showLivePiece(label, raw, result, progress) {
  liveBox.hidden = false;
  liveRaw.textContent = raw;
  liveCorrected.innerHTML = result.parts ? renderMarked(result.parts) : escapeHtml(result.text);
  liveWords += wordCount(result.text);
  const nCorr = (result.applied || []).reduce((a, c) => a + c.count, 0);
  liveMeta.textContent = label + ' — ' + wordCount(result.text) + ' words in this piece, ' +
    liveWords + ' words so far' +
    (nCorr ? '; ' + nCorr + ' glossary correction' + (nCorr === 1 ? '' : 's') + ' in this piece (marked, listed below).'
           : '; no glossary corrections in this piece.');
  if (progress && progress.total > 0) {
    liveProg.hidden = false;
    liveProg.value = Math.min(1, progress.done / progress.total);
    liveStatus.textContent = label + ' — ' + Math.round(100 * Math.min(1, progress.done / progress.total)) +
      '% of the audio transcribed.';
  } else {
    liveStatus.textContent = label + '.';
  }
}
function liveBusy(label) {
  liveProg.hidden = false;
  liveStatus.textContent = label;
}

// --- Model loading (only on the explicit button press) ---
let model = null;
const fileProgress = new Map();
let lastProgressAt = 0;
function onDownloadProgress({ loaded, total, file }) {
  lastProgressAt = performance.now();
  fileProgress.set(file, { loaded, total });
  let sumLoaded = 0, sumTotal = 0;
  for (const v of fileProgress.values()) { sumLoaded += v.loaded; sumTotal += v.total || 0; }
  if (sumTotal > 0) {
    loadProg.value = sumLoaded / sumTotal;
    loadStatus.textContent = 'Downloading ' + file + ' — ' +
      (sumLoaded / 1048576).toFixed(0) + ' MB of ' + (sumTotal / 1048576).toFixed(0) + ' MB…';
  }
  renderNetlog();
}

loadBtn.addEventListener('click', async () => {
  clearError();
  loadBtn.disabled = true;
  loadProg.hidden = false;
  loadProg.value = 0;
  loadStatus.textContent = 'Downloading model files from Hugging Face…';
  const t0 = performance.now();
  lastProgressAt = t0;
  const tailTimer = setInterval(() => {
    if (performance.now() - lastProgressAt > 3000) {
      loadProg.removeAttribute('value');
      loadStatus.textContent = 'Still loading… ' +
        ((performance.now() - t0) / 1000).toFixed(0) + ' s elapsed. ' +
        'Once the files are in, the model is built in memory; that step has no progress signal of its own.';
    }
  }, 1000);
  try {
    const { fromHub } = await import('parakeet.js');
    model = await fromHub('parakeet-tdt-0.6b-v2', {
      backend: 'wasm',
      encoderQuant: 'int8',
      decoderQuant: 'int8',
      preprocessorBackend: 'js',
      cpuThreads: 1,
      progress: onDownloadProgress,
    });
    const s = ((performance.now() - t0) / 1000).toFixed(1);
    loadProg.value = 1;
    loadStatus.textContent = 'Model loaded in ' + s + ' s. Transcription runs on WebAssembly, one thread.';
    updateRunEnabled();
    $('recBtn').disabled = false;
    $('recStatus').textContent = 'Ready to record.';
  } catch (err) {
    loadStatus.textContent = 'Model did not load.';
    showError('The model could not be loaded. Check the connection and try again. ' +
      'If this repeats, note the message in the browser console and report it.', err);
    loadBtn.disabled = false;
  } finally {
    clearInterval(tailTimer);
  }
  renderNetlog();
});

// --- Audio file handling: decode to mono PCM at 16 kHz on this device ---
let pcm = null;          // Float32Array, mono, 16 kHz
let audioSeconds = 0;

function updateRunEnabled() { runBtn.disabled = !(model && pcm); }

// Resample mono PCM to 16 kHz, the sample rate the model was trained for.
async function resampleTo16k(mono, fromRate) {
  if (fromRate === 16000) return mono;
  const off = new OfflineAudioContext(1, Math.ceil((mono.length / fromRate) * 16000), 16000);
  const srcBuf = off.createBuffer(1, mono.length, fromRate);
  srcBuf.copyToChannel(mono, 0);
  const src = off.createBufferSource();
  src.buffer = srcBuf;
  src.connect(off.destination);
  src.start();
  const rendered = await off.startRendering();
  return rendered.getChannelData(0).slice();
}

$('audioFile').addEventListener('change', async (ev) => {
  clearError();
  pcm = null; updateRunEnabled();
  const file = ev.target.files && ev.target.files[0];
  if (!file) { audioStatus.textContent = 'No file chosen.'; return; }
  audioStatus.textContent = 'Reading ' + file.name + '…';
  try {
    const buf = await file.arrayBuffer();
    const ctx = new AudioContext();
    const decoded = await ctx.decodeAudioData(buf);
    await ctx.close();
    const mono = new Float32Array(decoded.length);
    for (let ch = 0; ch < decoded.numberOfChannels; ch++) {
      const data = decoded.getChannelData(ch);
      for (let i = 0; i < data.length; i++) mono[i] += data[i] / decoded.numberOfChannels;
    }
    pcm = await resampleTo16k(mono, decoded.sampleRate);
    audioSeconds = pcm.length / 16000;
    audioStatus.textContent = file.name + ' — ' + audioSeconds.toFixed(1) +
      ' s of audio, decoded and resampled to 16 kHz on this device.';
    updateRunEnabled();
  } catch (err) {
    audioStatus.textContent = 'That file could not be decoded.';
    showError('The chosen file could not be decoded as audio by this browser. ' +
      'A WAV, MP3, M4A or WebM recording is expected.', err);
  }
});

// --- File transcription, in windows of 25 s of audio. Each window is
// transcribed with transcribeLongAudio (returnTimestamps: true and the
// window's own timeOffset); the vendored long_audio.js returns chunks
// of {text, timestamp: [start, end]} built from the model's word times,
// so each segment's start below is a time the library itself returned,
// already offset into the file. After every window the transcript is
// updated and autosaved, so a crash mid-file loses at most the window
// in progress. The timestamps option only changes how segments are
// displayed.
const FILE_WINDOW_S = 25;
// One transcription mode at a time. Both handlers set this synchronously
// at entry, before their first await, and clear it only when they own
// it: disabling a button cannot stop a handler that has already entered
// and is suspended at an await, so the guard, not the buttons, is what
// keeps a file run and a recording from ever interleaving.
let activeMode = null;
runBtn.addEventListener('click', async () => {
  if (!model || !pcm) return;
  if (activeMode) return;
  activeMode = 'file';
  clearError();
  const useTimestamps = tsCheck.checked;
  lastSource = 'file';
  runBtn.disabled = true;
  $('recBtn').disabled = true;
  $('recStopBtn').disabled = true;
  copyBtn.disabled = true;
  downloadBtn.disabled = true;
  runProg.hidden = false;
  transcriptBox.textContent = 'Transcribing…';
  hasTranscript = false;
  liveWords = 0;
  liveBox.hidden = true;
  liveBusy('Transcribing — the words of each piece will appear below as they are transcribed and corrected.');
  const t0 = performance.now();
  const timer = setInterval(() => {
    runStatus.textContent = 'Transcribing… ' + ((performance.now() - t0) / 1000).toFixed(0) + ' s elapsed.';
  }, 500);
  const agg = new Map();
  const segments = [];
  try {
    const nWindows = Math.max(1, Math.ceil(audioSeconds / FILE_WINDOW_S));
    for (let w = 0; w < nWindows; w++) {
      const wStart = w * FILE_WINDOW_S;
      const slice = pcm.subarray(
        Math.floor(wStart * 16000),
        Math.min(pcm.length, Math.ceil((wStart + FILE_WINDOW_S) * 16000)));
      if (!slice.length) break;
      runStatus.textContent = 'Transcribing window ' + (w + 1) + ' of ' + nWindows + '…';
      liveBusy('Transcribing window ' + (w + 1) + ' of ' + nWindows + ' — no new words yet for this window.');
      const result = await model.transcribeLongAudio(slice, 16000, {
        returnTimestamps: true, timeOffset: wStart,
      });
      const chunks = (Array.isArray(result.chunks) && result.chunks.length)
        ? result.chunks
        : (result.text ? [{ text: result.text, timestamp: [wStart, wStart] }] : []);
      for (const chunk of chunks) {
        const raw = (chunk.text || '').trim();
        if (!raw) continue;
        const result = correctWithLog(raw);
        const { text, applied } = result;
        aggregateApplied(agg, applied);
        const start = (Array.isArray(chunk.timestamp) && Number.isFinite(chunk.timestamp[0]))
          ? chunk.timestamp[0] : wStart;
        const end = (Array.isArray(chunk.timestamp) && Number.isFinite(chunk.timestamp[1]))
          ? chunk.timestamp[1] : start;
        segments.push({ start, text, raw, parts: result.parts });
        renderTranscript(segments, useTimestamps);
        hasTranscript = true;
        renderApplied(agg);
        copyBtn.disabled = false;
        downloadBtn.disabled = false;
        showLivePiece('File piece ' + segments.length + ' (window ' + (w + 1) + ' of ' + nWindows + ')',
          raw, result, { done: end, total: audioSeconds });
        autosaveNow();
      }
    }
    const secs = (performance.now() - t0) / 1000;
    if (segments.length) renderTranscript(segments, useTimestamps);
    else transcriptBox.textContent = '(The model returned no text for this recording.)';
    if (segments.length) {
      liveProg.value = 1;
      liveStatus.textContent = 'Done — ' + segments.length + ' piece(s), ' + liveWords + ' words, shown above as they arrived.';
    }
    hasTranscript = segments.length > 0;
    renderApplied(agg);
    let nCorrections = 0;
    for (const a of agg.values()) nCorrections += a.count;
    metrics.textContent = 'Audio ' + audioSeconds.toFixed(1) + ' s · transcribed in ' +
      secs.toFixed(1) + ' s · ' + (audioSeconds / secs).toFixed(1) + '× real time.' +
      (nCorrections ? ' Corrections applied: ' + nCorrections + ' (listed below the result).' : '');
    runStatus.textContent = 'Done.';
    copyBtn.disabled = !hasTranscript;
    downloadBtn.disabled = !hasTranscript;
    if (hasTranscript) autosaveNow();
  } catch (err) {
    if (segments.length) {
      renderTranscript(segments, useTimestamps);
      hasTranscript = true;
      autosaveNow();
      showError('Transcription stopped partway through the file. The pieces already ' +
        'transcribed are shown above and autosaved.', err);
    } else {
      transcriptBox.textContent = 'The transcript will appear here.';
      showError('Transcription failed. A long recording can run this page out of ' +
        'memory; try again, or try a shorter recording, and report what happens.', err);
    }
    runStatus.textContent = '';
  } finally {
    clearInterval(timer);
    runProg.hidden = true;
    if (activeMode === 'file') activeMode = null;
    runBtn.disabled = false;
    $('recBtn').disabled = false;
    $('recStatus').textContent = 'Ready to record.';
  }
  renderNetlog();
});

copyBtn.addEventListener('click', async () => {
  const text = currentTranscriptText();
  if (!text) return;
  try { await navigator.clipboard.writeText(text); } catch { /* clipboard may need focus; text stays selectable */ }
});

// --- Recording with live, segment-by-segment transcription ---
// The microphone stream is tapped with a ScriptProcessor node; captured
// samples accumulate in one growing buffer. Every ~12 s of new audio is
// resampled, transcribed, corrected and appended while recording goes on.
// All segment work uses a captured session object (R), never the global,
// so stopping cannot null the state out from under an in-flight piece.
// A segment's start time is the count of samples already transcribed
// divided by the capture sample rate — a position in the recording,
// computed from the capture itself.
const recBtn = $('recBtn'), recStopBtn = $('recStopBtn'), recStatus = $('recStatus');
const SEGMENT_SECONDS = 12;
let rec = null;

async function transcribeRecSegment(R, finalPiece) {
  if (R.busy) return;
  const available = R.len - R.doneUpTo;
  const minSamples = finalPiece ? Math.floor(0.5 * R.rate) : SEGMENT_SECONDS * R.rate;
  if (available < minSamples) return;
  R.busy = true;
  const from = R.doneUpTo;
  const to = R.len;
  try {
    const seg16 = await resampleTo16k(R.buf.slice(from, to), R.rate);
    const out = await model.transcribe(seg16, 16000, {});
    const raw = (out.utterance_text || '').trim();
    R.doneUpTo = to;
    R.failStreak = 0;
    if (raw) {
      const result = correctWithLog(raw);
      const { text, applied } = result;
      aggregateApplied(R.applied, applied);
      R.segments.push({ start: from / R.rate, text, raw, parts: result.parts });
      if (rec === R) {
        renderTranscript(R.segments, R.timestamps);
        hasTranscript = true;
        lastSource = 'recording';
        copyBtn.disabled = false;
        downloadBtn.disabled = false;
        renderApplied(R.applied);
        showLivePiece('Recording piece ' + R.segments.length, raw, result,
          { done: to / R.rate, total: Math.max(R.len / R.rate, to / R.rate) });
        autosaveNow();
      }
    }
    if (rec === R) {
      metrics.textContent = 'Recorded ' + (R.len / R.rate).toFixed(0) + ' s · ' +
        R.segments.length + ' piece(s) transcribed.';
    }
  } catch (err) {
    // doneUpTo stays where it was, so the piece is tried again on the next
    // pass. After two failures in a row it is skipped, and that is said.
    R.failStreak = (R.failStreak || 0) + 1;
    if (R.failStreak >= 2) {
      R.doneUpTo = to;
      R.failStreak = 0;
      showError('One piece of the recording could not be transcribed after two tries ' +
        'and was skipped. The rest of the transcript is unaffected.', err);
    } else {
      showError('A piece of the recording could not be transcribed; it will be tried again.', err);
    }
  } finally {
    R.busy = false;
  }
}

recBtn.addEventListener('click', async () => {
  clearError();
  if (!model) return;
  if (activeMode) return;
  activeMode = 'recording';
  runBtn.disabled = true;
  recBtn.disabled = true;
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    if (activeMode === 'recording') activeMode = null;
    recBtn.disabled = false;
    updateRunEnabled();
    showError('The microphone could not be opened. Allow microphone access for this page ' +
      'in the browser settings, then try again.', err);
    return;
  }
  let ctx = null;
  let R = null;
  try {
    ctx = new AudioContext();
    await ctx.resume();
    const source = ctx.createMediaStreamSource(stream);
    const node = ctx.createScriptProcessor(4096, 1, 1);
    const mute = ctx.createGain();
    mute.gain.value = 0;
    R = {
      stream, ctx, node, rate: ctx.sampleRate, len: 0, doneUpTo: 0,
      buf: new Float32Array(1024 * 1024), busy: false, stopped: false,
      t0: performance.now(), segments: [], applied: new Map(), timer: null,
      failStreak: 0, timestamps: tsCheck.checked,
    };
    rec = R;
    node.onaudioprocess = (e) => {
      if (rec !== R || R.stopped) return;
      const data = e.inputBuffer.getChannelData(0);
      if (R.len + data.length > R.buf.length) {
        const bigger = new Float32Array(Math.max(R.buf.length * 2, R.len + data.length));
        bigger.set(R.buf.subarray(0, R.len));
        R.buf = bigger;
      }
      R.buf.set(data, R.len);
      R.len += data.length;
    };
    source.connect(node);
    node.connect(mute);
    mute.connect(ctx.destination);
  } catch (err) {
    if (rec === R) rec = null;
    if (activeMode === 'recording') activeMode = null;
    recBtn.disabled = false;
    updateRunEnabled();
    stream.getTracks().forEach((t) => t.stop());
    if (ctx) { try { await ctx.close(); } catch { /* ignore */ } }
    showError('The audio recorder could not be started in this browser. ' +
      'The microphone has been released; try again or use a file instead.', err);
    return;
  }
  transcriptBox.textContent = '';
  hasTranscript = false;
  liveWords = 0;
  liveBox.hidden = true;
  liveBusy('Recording — each piece of about 12 s will appear below as it is transcribed and corrected.');
  correctionsBox.textContent = 'Recording… corrections will be listed here as pieces land.';
  recBtn.disabled = true;
  recStopBtn.disabled = false;
  runBtn.disabled = true;
  recStatus.textContent = 'Recording… 0 s captured.';
  R.timer = setInterval(() => {
    if (rec !== R) return;
    recStatus.textContent = 'Recording… ' + (R.len / R.rate).toFixed(0) + ' s captured' +
      (R.busy ? ' · transcribing a piece…' : '') + '.';
    transcribeRecSegment(R, false);
  }, 1000);
});

recStopBtn.addEventListener('click', async () => {
  const R = rec;
  if (!R) return;
  R.stopped = true;
  clearInterval(R.timer);
  recStopBtn.disabled = true;
  recStatus.textContent = 'Stopping — finishing the piece in progress…';
  try { R.node.disconnect(); } catch { /* already disconnected */ }
  R.stream.getTracks().forEach((t) => t.stop());
  // Let an in-flight piece finish against its own session object before
  // the final piece is attempted, so nothing recorded is dropped.
  while (R.busy) await new Promise((r) => setTimeout(r, 150));
  recStatus.textContent = 'Stopping — transcribing the last piece…';
  for (let i = 0; i < 3 && R.len - R.doneUpTo >= Math.floor(0.5 * R.rate); i++) {
    await transcribeRecSegment(R, true);
  }
  if (R.segments.length) renderTranscript(R.segments, R.timestamps);
  else transcriptBox.textContent = '(The model returned no text for this recording.)';
  if (R.segments.length) {
    liveProg.value = 1;
    liveStatus.textContent = 'Done — ' + R.segments.length + ' piece(s), ' + liveWords + ' words, shown above as they arrived.';
  }
  hasTranscript = R.segments.length > 0;
  copyBtn.disabled = !hasTranscript;
  downloadBtn.disabled = !hasTranscript;
  if (hasTranscript) { lastSource = 'recording'; autosaveNow(); }
  const totalSecs = R.len / R.rate;
  const elapsed = (performance.now() - R.t0) / 1000;
  recStatus.textContent = 'Recording stopped. ' + totalSecs.toFixed(0) + ' s captured in ' +
    elapsed.toFixed(0) + ' s, transcribed in ' + R.segments.length + ' piece(s).';
  try { await R.ctx.close(); } catch { /* context already closed */ }
  if (rec === R) rec = null;
  if (activeMode === 'recording') activeMode = null;
  recBtn.disabled = false;
  updateRunEnabled();
  renderNetlog();
});
