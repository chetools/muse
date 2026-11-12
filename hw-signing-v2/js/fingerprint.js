// Chromaprint of the normalised 16 kHz mono WAV (SPEC 2.6.0).
// Browser only for the computation itself; the base64 helpers are
// pure and Node-tested.
//
// The implementation is rusty-chromaprint-wasm 0.1.5, vendored under
// webapp/vendor/chromaprint/ (wasm + glue, no bundler). Loading is
// lazy and the module is cached; any failure returns null and the
// job is sent without a fingerprint (exact-SHA dedup only) — a
// fingerprint failure never blocks a submission. Computing is about
// 1.6 ms per audio-second on the machine measured in spike/SPIKE.md,
// on the main thread.
//
// The loader is the one verified in spike/test-loader.mjs: import
// the bg glue, instantiate the wasm with the import object
// {'./rusty_chromaprint_wasm_bg.js': bg}, __wbg_set_wasm,
// __wbindgen_start, then call fingerprintFromSamples(16000, 1,
// samples). instantiateStreaming is tried first, with a fallback to
// fetch -> arrayBuffer -> instantiate in case the host serves .wasm
// with the wrong MIME type.

const GLUE_URL = new URL(
  '../vendor/chromaprint/rusty_chromaprint_wasm_bg.js', import.meta.url);
const WASM_URL = new URL(
  '../vendor/chromaprint/rusty_chromaprint_wasm_bg.wasm', import.meta.url);
const WASM_IMPORT_MODULE = './rusty_chromaprint_wasm_bg.js';

let loadedBg = null;      // the bg glue module, once instantiated
let loadingPromise = null;

// Load and instantiate the vendored module once; returns the bg
// glue module, or null when it cannot be loaded. A failed load is
// not cached, so a later call retries.
async function loadChromaprint() {
  if (loadedBg) return loadedBg;
  if (loadingPromise) return loadingPromise;
  loadingPromise = (async () => {
    const bg = await import(GLUE_URL.href);
    const imports = { [WASM_IMPORT_MODULE]: bg };
    let instance;
    try {
      const streamed = await WebAssembly.instantiateStreaming(
        fetch(WASM_URL.href), imports);
      instance = streamed.instance;
    } catch {
      // Wrong MIME type (or no streaming support): fetch the bytes
      // and instantiate them directly.
      const bytes = await (await fetch(WASM_URL.href)).arrayBuffer();
      const result = await WebAssembly.instantiate(bytes, imports);
      instance = result.instance;
    }
    bg.__wbg_set_wasm(instance.exports);
    instance.exports.__wbindgen_start();
    return bg;
  })();
  try {
    loadedBg = await loadingPromise;
  } catch {
    loadingPromise = null;
    return null;
  }
  return loadedBg;
}

// Compute the Chromaprint of 16 kHz mono int16 PCM — the samples of
// the page's normalised WAV. Returns { rawBase64, items } where
// rawBase64 is the base64 of the raw fingerprint bytes (little-endian
// uint32 per item, one item per ~0.124 s) and items is the item
// count; or null on any failure (WASM unavailable, load error,
// exception) or on empty/invalid input.
export async function computeFingerprint(pcmInt16) {
  try {
    if (!pcmInt16 || !(pcmInt16 instanceof Int16Array) || !pcmInt16.length) {
      return null;
    }
    const bg = await loadChromaprint();
    if (!bg) return null;
    const result = bg.fingerprintFromSamples(16000, 1, pcmInt16);
    let raw = null;
    try {
      raw = result.raw; // Uint32Array, copied out by the glue
    } finally {
      try { result.free(); } catch { /* already read; ignore */ }
    }
    if (!raw || !raw.length) return null;
    return { rawBase64: encodeRawFingerprint(raw), items: raw.length };
  } catch {
    return null;
  }
}

/* ---------------- base64 of raw fingerprint items ----------------
 * Standard base64 (not url-safe) of the little-endian uint32 bytes,
 * matching the Worker's decoding of the `chromaprint` field. Pure;
 * implemented by hand so the helpers work identically in the
 * browser and in Node, with no dependency on btoa/atob.
 */

const B64_ALPHABET =
  'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const B64_DECODE = new Map(
  [...B64_ALPHABET].map((ch, i) => [ch, i]));

export function encodeRawFingerprint(items) {
  const raw = items instanceof Uint32Array
    ? items : new Uint32Array(items || []);
  const bytes = new Uint8Array(raw.buffer, raw.byteOffset, raw.byteLength);
  let out = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const b0 = bytes[i];
    const b1 = i + 1 < bytes.length ? bytes[i + 1] : 0;
    const b2 = i + 2 < bytes.length ? bytes[i + 2] : 0;
    out += B64_ALPHABET[b0 >> 2];
    out += B64_ALPHABET[((b0 & 3) << 4) | (b1 >> 4)];
    out += i + 1 < bytes.length
      ? B64_ALPHABET[((b1 & 15) << 2) | (b2 >> 6)] : '=';
    out += i + 2 < bytes.length ? B64_ALPHABET[b2 & 63] : '=';
  }
  return out;
}

// Decode the base64 of raw fingerprint bytes back to the Uint32Array
// of items. Returns null when the input is not valid base64 of whole
// uint32 items (bad characters, bad padding, or a byte length not
// divisible by 4); an empty input is not a fingerprint.
export function decodeRawFingerprint(base64) {
  if (typeof base64 !== 'string' || !base64.length || base64.length % 4 !== 0) {
    return null;
  }
  const bytes = [];
  for (let i = 0; i < base64.length; i += 4) {
    const c0 = B64_DECODE.get(base64[i]);
    const c1 = B64_DECODE.get(base64[i + 1]);
    if (c0 === undefined || c1 === undefined) return null;
    const pad2 = base64[i + 2] === '=';
    const pad3 = base64[i + 3] === '=';
    if (pad2 && !pad3) return null; // '=' may only pad the tail
    if (pad2 && i + 4 !== base64.length) return null;
    const c2 = pad2 ? 0 : B64_DECODE.get(base64[i + 2]);
    const c3 = pad3 ? 0 : B64_DECODE.get(base64[i + 3]);
    if (c2 === undefined || c3 === undefined) return null;
    bytes.push((c0 << 2) | (c1 >> 4));
    if (!pad2) bytes.push(((c1 & 15) << 4) | (c2 >> 2));
    if (!pad3) bytes.push(((c2 & 3) << 6) | c3);
  }
  if (bytes.length === 0 || bytes.length % 4 !== 0) return null;
  return new Uint32Array(new Uint8Array(bytes).buffer);
}
