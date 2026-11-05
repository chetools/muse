// Parakeet prototype — page logic.
// Order matters: ONNX Runtime Web is imported and pointed at the WASM
// binaries vendored on this site BEFORE parakeet.js is imported, so the
// library never falls back to its default CDN address for those binaries.
import * as ort from 'onnxruntime-web';
import { correctText } from './corrections.js';

ort.env.wasm.wasmPaths = new URL('./vendor/ort/', window.location.href).href;
ort.env.wasm.numThreads = 1;
ort.env.logLevel = 'warning';

const $ = (id) => document.getElementById(id);
const loadBtn = $('loadBtn'), runBtn = $('runBtn'), copyBtn = $('copyBtn');
const loadProg = $('loadProg'), runProg = $('runProg');
const loadStatus = $('loadStatus'), runStatus = $('runStatus');
const audioStatus = $('audioStatus'), metrics = $('metrics');
const errBox = $('errBox'), transcriptBox = $('transcript'), netlog = $('netlog');

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
  // The download callbacks stop when the files are in; session creation
  // follows with no callback of its own. If no download progress has
  // arrived for a few seconds, say so and switch the bar to indeterminate
  // so the load step never looks stalled on a "Downloading…" message.
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
    // Mix all channels down to one channel.
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

// --- Transcription, with an elapsed-time progress display ---
runBtn.addEventListener('click', async () => {
  if (!model || !pcm) return;
  clearError();
  runBtn.disabled = true;
  runProg.hidden = false;
  transcriptBox.textContent = 'Transcribing…';
  const t0 = performance.now();
  const timer = setInterval(() => {
    runStatus.textContent = 'Transcribing… ' + ((performance.now() - t0) / 1000).toFixed(0) + ' s elapsed.';
  }, 500);
  try {
    const result = await model.transcribeLongAudio(pcm, 16000, { returnTimestamps: true });
    const secs = (performance.now() - t0) / 1000;
    const rawText = (result.text || '').trim();
    const fixedText = correctText(rawText);
    transcriptBox.textContent = fixedText
      ? fixedText
      : '(The model returned no text for this recording.)';
    metrics.textContent = 'Audio ' + audioSeconds.toFixed(1) + ' s · transcribed in ' +
      secs.toFixed(1) + ' s · ' + (audioSeconds / secs).toFixed(1) + '× real time.' +
      (fixedText !== rawText ? ' Mishearing corrections applied.' : '');
    runStatus.textContent = 'Done.';
    copyBtn.disabled = !fixedText;
  } catch (err) {
    transcriptBox.textContent = 'The transcript will appear here.';
    runStatus.textContent = '';
    showError('Transcription failed. A long recording in one pass can run this page out of ' +
      'memory; try again, or try a shorter recording, and report what happens.', err);
  } finally {
    clearInterval(timer);
    runProg.hidden = true;
    runBtn.disabled = false;
  }
  renderNetlog();
});

copyBtn.addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(transcriptBox.textContent); } catch { /* clipboard may need focus; text stays selectable */ }
});

// --- Recording with live, segment-by-segment transcription ---
// The microphone stream is tapped with a ScriptProcessor node; captured
// samples accumulate in one growing buffer. Every ~12 s of new audio is
// resampled, transcribed, corrected and appended while recording goes on.
// All segment work uses a captured session object (R), never the global,
// so stopping cannot null the state out from under an in-flight piece.
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
      R.segments.push(correctText(raw));
      if (rec === R) {
        transcriptBox.textContent = R.segments.join(' ');
        copyBtn.disabled = false;
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
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
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
      t0: performance.now(), segments: [], timer: null, failStreak: 0,
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
    stream.getTracks().forEach((t) => t.stop());
    if (ctx) { try { await ctx.close(); } catch { /* ignore */ } }
    showError('The audio recorder could not be started in this browser. ' +
      'The microphone has been released; try again or use a file instead.', err);
    return;
  }
  transcriptBox.textContent = '';
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
  transcriptBox.textContent = R.segments.length
    ? R.segments.join(' ')
    : '(The model returned no text for this recording.)';
  copyBtn.disabled = !R.segments.length;
  const totalSecs = R.len / R.rate;
  const elapsed = (performance.now() - R.t0) / 1000;
  recStatus.textContent = 'Recording stopped. ' + totalSecs.toFixed(0) + ' s captured in ' +
    elapsed.toFixed(0) + ' s, transcribed in ' + R.segments.length + ' piece(s).';
  try { await R.ctx.close(); } catch { /* context already closed */ }
  if (rec === R) rec = null;
  recBtn.disabled = false;
  updateRunEnabled();
  renderNetlog();
});
