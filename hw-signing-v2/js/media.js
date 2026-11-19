// Media stage (plan step 3). encodeWavPcm16 is pure and Node-tested;
// decodeFileTo16kMono is the browser adapter (Web Audio, with the
// tier-2 WebCodecs fallback of js/media-mp4.js) and is not run by the
// tests — see README.md.

import { tier2BlockReason } from './media-mp4-pure.js';

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
  view.setUint32(12, 'fmt ');
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

// Mix one Float32Array per channel down to a single mono array, by
// the mean of the channels at each frame. Pure; Node-tested.
export function channelsToMono(channelArrays) {
  const channels = channelArrays.length;
  const frames = channels ? channelArrays[0].length : 0;
  const mono = new Float32Array(frames);
  for (let ch = 0; ch < channels; ch++) {
    const data = channelArrays[ch];
    for (let i = 0; i < frames; i++) mono[i] += data[i] / channels;
  }
  return mono;
}

// Resample mono samples to 16 kHz with an OfflineAudioContext.
// Browser only.
export async function resampleMonoTo16k(mono, fromRate) {
  if (fromRate === SAMPLE_RATE) return mono;
  const off = new OfflineAudioContext(
    1, Math.ceil((mono.length / fromRate) * SAMPLE_RATE), SAMPLE_RATE);
  const srcBuf = off.createBuffer(1, mono.length, fromRate);
  srcBuf.copyToChannel(mono, 0);
  const src = off.createBufferSource();
  src.buffer = srcBuf;
  src.connect(off.destination);
  src.start();
  const rendered = await off.startRendering();
  return rendered.getChannelData(0).slice();
}

// Streaming resampler to 16 kHz for the tier-2 path: decoded chunks
// are pushed as they arrive and the resampled output is returned
// chunk by chunk, so a long recording never exists in memory at its
// native rate. Each output sample is a Hann-windowed sinc sum over
// the input, with the kernel widened by the rate ratio when
// decimating, so content above the 8 kHz output band is filtered out
// rather than aliased into it, as the browser's own resampler does
// on the native path. Weights are normalised per output sample, so a
// constant signal resamples to exactly itself. Pure; Node-tested.
// push(monoChunk) returns the output that is ready; finish() flushes
// the tail. Feeding the same samples in any chunk sizes gives the
// same output. The output count for N input samples is
// ceil(N * 16000 / fromRate), the same count the OfflineAudioContext
// resample produces.
export function createStreamResampler(fromRate) {
  const step = fromRate / SAMPLE_RATE;
  const scale = Math.max(1, step);
  const support = 8 * scale;
  let pending = new Float32Array(0);
  let baseIndex = 0;
  let nextPos = 0;
  let totalReceived = 0;
  function kernel(d) {
    if (Math.abs(d) >= support) return 0;
    const x = d / scale;
    const sinc = x === 0 ? 1 : Math.sin(Math.PI * x) / (Math.PI * x);
    const hann = 0.5 + 0.5 * Math.cos((Math.PI * d) / support);
    return (sinc * hann) / scale;
  }
  function emit(final) {
    const out = [];
    while (true) {
      if (final ? nextPos >= totalReceived
                : Math.floor(nextPos + support) > totalReceived - 1) break;
      let num = 0;
      let den = 0;
      const jStart = Math.max(0, Math.ceil(nextPos - support));
      const jEnd = Math.min(totalReceived - 1, Math.floor(nextPos + support));
      for (let j = jStart; j <= jEnd; j++) {
        const h = kernel(nextPos - j);
        num += h * pending[j - baseIndex];
        den += h;
      }
      out.push(den !== 0 ? num / den : 0);
      nextPos += step;
    }
    const keepFrom = Math.min(Math.max(0, Math.floor(nextPos - support) - 1), totalReceived);
    if (keepFrom > baseIndex) {
      pending = pending.slice(keepFrom - baseIndex);
      baseIndex = keepFrom;
    }
    return Float32Array.from(out);
  }
  return {
    push(monoChunk) {
      if (monoChunk.length) {
        const merged = new Float32Array(pending.length + monoChunk.length);
        merged.set(pending);
        merged.set(monoChunk, pending.length);
        pending = merged;
        totalReceived += monoChunk.length;
      }
      return emit(false);
    },
    finish() {
      return emit(true);
    },
  };
}

// Native decode of a whole file buffer with Web Audio. Browser only.
async function decodeBufferNative(buf) {
  const ctx = new AudioContext();
  let decoded;
  try {
    decoded = await ctx.decodeAudioData(buf);
  } finally {
    await ctx.close();
  }
  const channelArrays = [];
  for (let ch = 0; ch < decoded.numberOfChannels; ch++) {
    channelArrays.push(decoded.getChannelData(ch));
  }
  return resampleMonoTo16k(channelsToMono(channelArrays), decoded.sampleRate);
}

// Browser adapter: decode a local audio or video file and resample to
// 16 kHz mono PCM. Tier 1 is the browser's own decodeAudioData. When
// that rejects an MP4/MOV-family file and this browser has WebCodecs,
// tier 2 (js/media-mp4.js, loaded only then) demuxes the file with
// mp4box.js and decodes the audio track with AudioDecoder. `onTier2`
// is called when tier 2 starts, so the page can say what it is doing.
// When neither tier can read the file, the tier-1 error is thrown, so
// the page's failure behaviour is unchanged.
export async function decodeFileTo16kMono(file, onTier2) {
  const buf = await file.arrayBuffer();
  try {
    return await decodeBufferNative(buf.slice(0));
  } catch (nativeErr) {
    if (tier2BlockReason(globalThis, file)) throw nativeErr;
    try {
      if (onTier2) onTier2();
      const mp4 = await import('./media-mp4.js');
      // Streaming: each decoded chunk is downmixed and resampled as
      // it arrives and then dropped, so the memory held is the 16 kHz
      // result (about 3.8 MB per minute) plus one chunk, however long
      // the recording is.
      let resampler = null;
      const parts = [];
      let total = 0;
      // Timeline placement: decoded chunks carry the container's
      // timestamps. A start offset or a gap larger than the slack
      // (2048 native samples, about 43 ms at 48 kHz) is honoured —
      // silence is inserted, or an overlap trimmed — rather than the
      // audio being silently closed up. Smaller discrepancies, such
      // as codec priming, are left as the decoder presents them.
      let emitted = 0;
      const ALIGN_SLACK = 2048;
      await mp4.decodeMp4WithWebCodecs(buf, (channelArrays, sampleRate, timestampUs) => {
        if (!resampler) resampler = createStreamResampler(sampleRate);
        let mono = channelsToMono(channelArrays);
        const pushMono = (m) => {
          const out = resampler.push(m);
          emitted += m.length;
          if (out.length) { parts.push(out); total += out.length; }
        };
        if (timestampUs != null && Number.isFinite(timestampUs)) {
          const startFrame = Math.round((timestampUs * sampleRate) / 1e6);
          if (startFrame > emitted + ALIGN_SLACK) {
            pushMono(new Float32Array(startFrame - emitted));
          } else if (startFrame < emitted - ALIGN_SLACK) {
            const trim = emitted - startFrame;
            mono = trim >= mono.length ? new Float32Array(0) : mono.subarray(trim);
          }
        }
        if (mono.length) pushMono(mono);
      });
      const tail = resampler.finish();
      if (tail.length) { parts.push(tail); total += tail.length; }
      const pcm = new Float32Array(total);
      let offset = 0;
      for (const part of parts) { pcm.set(part, offset); offset += part.length; }
      return pcm;
    } catch {
      throw nativeErr;
    }
  }
}
