// Parakeet prototype — page logic.
// Order matters: ONNX Runtime Web is imported and pointed at the WASM
// binaries vendored on this site BEFORE parakeet.js is imported, so the
// library never falls back to its default CDN address for those binaries.
import * as ort from 'onnxruntime-web';

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
    // Resample to 16 kHz, the sample rate the model was trained for.
    const targetRate = 16000;
    if (decoded.sampleRate === targetRate) {
      pcm = mono;
    } else {
      const off = new OfflineAudioContext(1, Math.ceil(decoded.duration * targetRate), targetRate);
      const srcBuf = off.createBuffer(1, mono.length, decoded.sampleRate);
      srcBuf.copyToChannel(mono, 0);
      const src = off.createBufferSource();
      src.buffer = srcBuf;
      src.connect(off.destination);
      src.start();
      const rendered = await off.startRendering();
      pcm = rendered.getChannelData(0).slice();
    }
    audioSeconds = pcm.length / targetRate;
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
    transcriptBox.textContent = result.text && result.text.trim()
      ? result.text.trim()
      : '(The model returned no text for this recording.)';
    metrics.textContent = 'Audio ' + audioSeconds.toFixed(1) + ' s · transcribed in ' +
      secs.toFixed(1) + ' s · ' + (audioSeconds / secs).toFixed(1) + '× real time.';
    runStatus.textContent = 'Done.';
    copyBtn.disabled = !result.text || !result.text.trim();
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
