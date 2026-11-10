// Media stage (plan step 3). encodeWavPcm16 is pure and Node-tested;
// decodeFileTo16kMono is the browser adapter (Web Audio) and is not run
// by the tests — see README.md.

export const SAMPLE_RATE = 16000;

// Encode mono Float32 samples as a 16 kHz 16-bit PCM WAV file.
// Returns the exact bytes offered for download; the audio fingerprint is
// computed over these bytes.
export function encodeWavPcm16(samples, sampleRate = SAMPLE_RATE) {
  const n = samples.length;
  const bytes = new Uint8Array(44 + n * 2);
  const view = new DataView(bytes.buffer);
  const writeAscii = (offset, s) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };
  writeAscii(0, 'RIFF');
  view.setUint32(4, 36 + n * 2, true);
  writeAscii(8, 'WAVE');
  writeAscii(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);            // PCM
  view.setUint16(22, 1, true);            // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeAscii(36, 'data');
  view.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) {
    const v = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, Math.round(v * 32767), true);
  }
  return bytes;
}

export function wavDurationS(wavBytes) {
  const dataBytes = Math.max(0, wavBytes.length - 44);
  return dataBytes / 2 / SAMPLE_RATE;
}

// Browser adapter: decode a local audio or video file and resample to
// 16 kHz mono PCM, following the base page's decode path. Browser only.
export async function decodeFileTo16kMono(file) {
  const buf = await file.arrayBuffer();
  const ctx = new AudioContext();
  let decoded;
  try {
    decoded = await ctx.decodeAudioData(buf);
  } finally {
    await ctx.close();
  }
  const mono = new Float32Array(decoded.length);
  for (let ch = 0; ch < decoded.numberOfChannels; ch++) {
    const data = decoded.getChannelData(ch);
    for (let i = 0; i < data.length; i++) mono[i] += data[i] / decoded.numberOfChannels;
  }
  if (decoded.sampleRate === SAMPLE_RATE) return mono;
  const off = new OfflineAudioContext(
    1, Math.ceil((mono.length / decoded.sampleRate) * SAMPLE_RATE), SAMPLE_RATE);
  const srcBuf = off.createBuffer(1, mono.length, decoded.sampleRate);
  srcBuf.copyToChannel(mono, 0);
  const src = off.createBufferSource();
  src.buffer = srcBuf;
  src.connect(off.destination);
  src.start();
  const rendered = await off.startRendering();
  return rendered.getChannelData(0).slice();
}
