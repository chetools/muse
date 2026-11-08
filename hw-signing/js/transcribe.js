// Transcription adapter (plan step 4): the browser-only boundary around
// the copied ChemEScribe pipeline. The base page's pattern is reused
// unchanged: ONNX Runtime Web is imported and pointed at the vendored
// WASM binaries BEFORE parakeet.js is imported, the model loads from
// Hugging Face only on request, and file transcription runs in 25 s
// windows through transcribeLongAudio with timestamps, each returned
// chunk corrected with correctWithLog. Browser only — not run by the
// Node tests (see README.md).

import * as ort from 'onnxruntime-web';
import { correctWithLog } from '../chemescribe-base/corrections.js';

ort.env.wasm.wasmPaths = new URL('./chemescribe-base/vendor/ort/', window.location.href).href;
ort.env.wasm.numThreads = 1;
ort.env.logLevel = 'warning';

export const FILE_WINDOW_S = 25;

export async function loadModel(onProgress) {
  const { fromHub } = await import('parakeet.js');
  return fromHub('parakeet-tdt-0.6b-v2', {
    backend: 'wasm',
    encoderQuant: 'int8',
    decoderQuant: 'int8',
    preprocessorBackend: 'js',
    cpuThreads: 1,
    progress: onProgress,
  });
}

// Transcribe 16 kHz mono PCM in windows. onChunk receives
// { start, end, raw, corrected, parts, applied } per chunk, in order;
// onWindow(doneSeconds, totalSeconds) reports progress after each window.
export async function transcribePcm(model, pcm, durationS, { onChunk, onWindow } = {}) {
  const chunks = [];
  const nWindows = Math.max(1, Math.ceil(durationS / FILE_WINDOW_S));
  for (let w = 0; w < nWindows; w++) {
    const wStart = w * FILE_WINDOW_S;
    const slice = pcm.subarray(
      Math.floor(wStart * 16000),
      Math.min(pcm.length, Math.ceil((wStart + FILE_WINDOW_S) * 16000)));
    if (!slice.length) break;
    const result = await model.transcribeLongAudio(slice, 16000, {
      returnTimestamps: true, timeOffset: wStart,
    });
    const rawChunks = (Array.isArray(result.chunks) && result.chunks.length)
      ? result.chunks
      : (result.text ? [{ text: result.text, timestamp: [wStart, wStart] }] : []);
    for (const chunk of rawChunks) {
      const raw = (chunk.text || '').trim();
      if (!raw) continue;
      const corrected = correctWithLog(raw);
      const start = (Array.isArray(chunk.timestamp) && Number.isFinite(chunk.timestamp[0]))
        ? chunk.timestamp[0] : wStart;
      const end = (Array.isArray(chunk.timestamp) && Number.isFinite(chunk.timestamp[1]))
        ? chunk.timestamp[1] : start;
      const item = {
        start, end, raw,
        corrected: corrected.text,
        parts: corrected.parts,
        applied: corrected.applied,
      };
      chunks.push(item);
      if (onChunk) onChunk(item, { done: end, total: durationS });
    }
    if (onWindow) onWindow(Math.min(durationS, wStart + FILE_WINDOW_S), durationS);
  }
  return chunks;
}
