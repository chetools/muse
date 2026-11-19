// Tier-2 media decode (2.5.0): MP4/MOV files the browser's own
// decodeAudioData cannot read. The container is demuxed with the
// vendored mp4box.js and the audio track is decoded with WebCodecs
// AudioDecoder, which reaches codecs and container structures (for
// example fragmented MP4) that the one-shot Web Audio decode rejects
// in some browsers. This module is loaded dynamically, only after the
// native decode has failed; nothing on the normal path imports it.
//
// The pure helpers live in js/media-mp4-pure.js (no imports, so the
// gate can run without loading mp4box) and are re-exported here;
// the demux and AudioDecoder run are browser-only.

import { createFile } from '../vendor/mp4box/mp4box.all.mjs';

import {
  webCodecsCodecString, decoderSpecificInfo, planesToChannels,
} from './media-mp4-pure.js';
export {
  isMp4FamilyFile, tier2BlockReason, webCodecsCodecString,
  decoderSpecificInfo, planesToChannels,
} from './media-mp4-pure.js';

// Demux an MP4/MOV file's audio track with mp4box.js. Resolves with
// { codec, sampleRate, channels, description, samples }, where
// samples is an array of { data, timestampUs, durationUs } in
// presentation order, or rejects when the file has no audio track or
// cannot be parsed. The extraction options must be set inside
// onReady: mp4box processes samples as it parses, so options set
// after parsing has finished extract nothing.
export function demuxMp4Audio(buf) {
  return new Promise((resolve, reject) => {
    const file = createFile();
    const samples = [];
    let settled = false;
    let readyFired = false;
    const fail = (err) => { if (!settled) { settled = true; reject(err); } };
    file.onError = (err) => fail(new Error('mp4box: ' + err));
    file.onReady = (info) => {
      readyFired = true;
      const track = (info.tracks || []).find((t) => t.type === 'audio');
      if (!track) { fail(new Error('no audio track in this file')); return; }
      const trak = file.moov.traks.find((tr) => tr.tkhd.track_id === track.id);
      const entry = trak && trak.mdia.minf.stbl.stsd.entries[0];
      let description = null;
      if (entry && entry.type === 'mp4a' && entry.esds && entry.esds.esd) {
        description = decoderSpecificInfo(entry.esds.esd.descs);
      }
      const timescale = track.timescale || 1;
      file.onSamples = (id, user, batch) => {
        for (const s of batch) {
          samples.push({
            data: s.data,
            timestampUs: Math.round((s.cts * 1e6) / timescale),
            durationUs: Math.round((s.duration * 1e6) / timescale),
          });
        }
      };
      const finish = () => {
        if (settled) return;
        settled = true;
        if (!samples.length) { reject(new Error('no audio samples in this file')); return; }
        resolve({
          codec: webCodecsCodecString(track.codec),
          sampleRate: (track.audio && track.audio.sample_rate) || 0,
          channels: (track.audio && track.audio.channel_count) || 0,
          description: description ? new Uint8Array(description) : null,
          samples,
        });
      };
      // mp4box parses synchronously: once the caller's appendBuffer
      // and flush have returned, every sample has been delivered, and
      // the caller settles the promise through `finish` (kept on the
      // file object for that call). onFlush, when the library fires
      // it, settles the same way.
      file._finishDemux = finish;
      file.onFlush = finish;
      file.setExtractionOptions(track.id, null, { nbSamples: 1000 });
      file.start();
    };
    const ab = buf.slice(0);
    ab.fileStart = 0;
    try {
      file.appendBuffer(ab);
      file.flush();
      if (readyFired && file._finishDemux) file._finishDemux();
    } catch (err) {
      fail(err);
    }
    // mp4box fires no callback at all for a buffer with no readable
    // movie box; never leave the promise unsettled.
    setTimeout(() => {
      fail(new Error(readyFired
        ? 'mp4box produced no audio samples'
        : 'not a readable MP4/MOV file'));
    }, 1000);
  });
}

// Decode a whole MP4/MOV file held in `buf` (an ArrayBuffer) with
// WebCodecs, streaming: each decoded chunk is passed to
// onChunk(channelArrays, sampleRate, timestampUs) in presentation
// order as it is
// decoded, and nothing decoded is retained here, so a long recording
// is never held in memory at its native rate. Resolves with the
// number of frames decoded. Rejects when this browser has no decoder
// for the track's codec, or when decoding yields nothing.
export async function decodeMp4WithWebCodecs(buf, onChunk) {
  const demuxed = await demuxMp4Audio(buf);
  const config = {
    codec: demuxed.codec,
    sampleRate: demuxed.sampleRate,
    numberOfChannels: demuxed.channels,
  };
  if (demuxed.description) config.description = demuxed.description;
  const support = await AudioDecoder.isConfigSupported(config);
  if (!support || !support.supported) {
    throw new Error('WebCodecs cannot decode codec ' + demuxed.codec);
  }
  let framesDecoded = 0;
  let sampleRate = demuxed.sampleRate;
  let decodeError = null;
  let onOutput = null;
  const decoder = new AudioDecoder({
    output: (data) => {
      try {
        const channels = data.numberOfChannels;
        const frames = data.numberOfFrames;
        const planes = [];
        if (data.format === 'f32-planar' || data.format === 's16-planar') {
          for (let ch = 0; ch < channels; ch++) {
            const size = data.allocationSize({ planeIndex: ch });
            const arr = data.format === 'f32-planar'
              ? new Float32Array(size / 4) : new Int16Array(size / 2);
            data.copyTo(arr, { planeIndex: ch });
            planes.push(arr);
          }
        } else {
          const size = data.allocationSize({ planeIndex: 0 });
          const arr = data.format === 's16'
            ? new Int16Array(size / 2) : new Float32Array(size / 4);
          data.copyTo(arr, { planeIndex: 0 });
          planes.push(arr);
        }
        if (data.sampleRate) sampleRate = data.sampleRate;
        framesDecoded += frames;
        onChunk(
          planesToChannels({ format: data.format, planes, frames, channels }),
          sampleRate, data.timestamp);
      } catch (err) {
        decodeError = decodeError || err;
      } finally {
        data.close();
        if (onOutput) { const notify = onOutput; onOutput = null; notify(); }
      }
    },
    error: (err) => {
      decodeError = decodeError || err;
      // No outputs follow an error, so a decode loop waiting for one
      // must be woken here or it never settles.
      if (onOutput) { const notify = onOutput; onOutput = null; notify(); }
    },
  });
  decoder.configure(support.config || config);
  const samples = demuxed.samples;
  for (let i = 0; i < samples.length; i++) {
    if (decodeError) break;
    while (decoder.decodeQueueSize > 100 && !decodeError) {
      await new Promise((resolve) => { onOutput = resolve; });
    }
    if (decodeError) break;
    const s = samples[i];
    const next = samples[i + 1];
    decoder.decode(new EncodedAudioChunk({
      type: 'key',
      timestamp: s.timestampUs,
      duration: next ? Math.max(0, next.timestampUs - s.timestampUs) : s.durationUs,
      data: s.data,
    }));
  }
  if (!decodeError) {
    try { await decoder.flush(); } catch (err) { decodeError = decodeError || err; }
  }
  try { decoder.close(); } catch { /* already closed on error */ }
  if (decodeError) throw decodeError;
  if (!framesDecoded) throw new Error('WebCodecs decoded no audio');
  return framesDecoded;
}
