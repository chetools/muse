// Pure helpers for the tier-2 MP4 decode (see js/media-mp4.js). This
// module imports nothing, so js/media.js can gate the fallback with
// it on every native failure without loading the mp4box bundle: the
// bundle is fetched only when the gate passes. Node-tested through
// js/media-mp4.js, which re-exports these functions.

const MP4_FAMILY_EXTENSIONS = ['.mp4', '.m4a', '.m4v', '.mov', '.3gp', '.3g2'];
const MP4_FAMILY_MIME = [
  'video/mp4', 'audio/mp4', 'video/quicktime', 'audio/x-m4a',
  'video/3gpp', 'video/3gpp2',
];

// Whether a chosen file could be an ISO MP4/MOV-family file, by the
// name or type the browser reports. mp4box.js cannot parse other
// containers, so tier 2 is offered only for these.
export function isMp4FamilyFile(file) {
  if (!file) return false;
  const name = String(file.name || '').toLowerCase();
  if (MP4_FAMILY_EXTENSIONS.some((ext) => name.endsWith(ext))) return true;
  return MP4_FAMILY_MIME.includes(String(file.type || '').toLowerCase());
}

// Why tier 2 cannot run for this file in this browser, or null when
// it can. `env` is the global object to inspect (window in the page;
// a stand-in object in tests). Safari before version 26 has no
// AudioDecoder at all, and Firefox on Android has none either; both
// must skip tier 2 cleanly rather than fail a second time.
export function tier2BlockReason(env, file) {
  if (!isMp4FamilyFile(file)) return 'not an MP4/MOV-family file';
  if (!env || typeof env.AudioDecoder === 'undefined') return 'no WebCodecs AudioDecoder in this browser';
  if (typeof env.EncodedAudioChunk === 'undefined') return 'no WebCodecs EncodedAudioChunk in this browser';
  return null;
}

// The WebCodecs codec string for an mp4box track codec. mp4box
// reports most strings in WebCodecs form already ('mp4a.40.2',
// 'ac-3', 'ec-3'); its Opus label is capitalised, which WebCodecs
// does not accept.
export function webCodecsCodecString(mp4boxCodec) {
  const codec = String(mp4boxCodec || '');
  if (codec.toLowerCase() === 'opus') return 'opus';
  return codec;
}

// The DecoderSpecificInfo bytes (descriptor tag 5) inside an
// Elementary Stream Descriptor's descriptor tree, or null when the
// tree carries none. AudioDecoder needs these bytes as the AAC
// configuration description.
export function decoderSpecificInfo(descs) {
  for (const desc of descs || []) {
    if (!desc) continue;
    if (desc.tag === 5 && desc.data) return desc.data;
    const found = decoderSpecificInfo(desc.descs);
    if (found) return found;
  }
  return null;
}

// Convert one decoded chunk of audio, given as per-plane typed arrays
// in the WebCodecs plane layout, to one Float32Array per channel.
// Supported layouts: 'f32-planar', 'f32' (interleaved), 's16-planar'
// and 's16' (interleaved) — the formats AudioDecoder produces for the
// codecs this tier handles. Anything else throws, which the caller
// treats as a tier-2 failure and reports as the file being
// undecodable, as before.
export function planesToChannels({ format, planes, frames, channels }) {
  const out = [];
  for (let ch = 0; ch < channels; ch++) out.push(new Float32Array(frames));
  if (format === 'f32-planar') {
    for (let ch = 0; ch < channels; ch++) out[ch].set(planes[ch].subarray(0, frames));
  } else if (format === 'f32') {
    const flat = planes[0];
    for (let i = 0; i < frames; i++) {
      for (let ch = 0; ch < channels; ch++) out[ch][i] = flat[i * channels + ch];
    }
  } else if (format === 's16-planar') {
    for (let ch = 0; ch < channels; ch++) {
      const plane = planes[ch];
      for (let i = 0; i < frames; i++) out[ch][i] = plane[i] / 32768;
    }
  } else if (format === 's16') {
    const flat = planes[0];
    for (let i = 0; i < frames; i++) {
      for (let ch = 0; ch < channels; ch++) out[ch][i] = flat[i * channels + ch] / 32768;
    }
  } else {
    throw new Error('unsupported decoded audio format: ' + format);
  }
  return out;
}
