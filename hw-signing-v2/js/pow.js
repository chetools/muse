// Proof of work as a chain woven through the transcription
// (webapp 2.9.0; Worker 2.10.0). This replaces the 2.8.0/2.9.0
// single-shot token, whose seed bound the finished transcript:
// every removal-list or picker edit changed that seed and
// restarted the search, so a student who edited late met a wait
// at Send. The token is eliminated entirely, not dual-accepted:
// Worker 2.10.0 treats a submission carrying the old token
// fields exactly like one carrying no proof (the teacher's
// decision of 2026-11-28), so nothing of the token remains in
// this module.
//
// The chain instead binds the transcription itself. As the
// transcription produces each chunk (piece), the page hashes the
// chunk's corrected (pre-scrub) text, and a solver finds one
// small proof per chunk, chained: link i's seed is
//
//   "chain:<audio_sha256>:<run_id>:<i>:<chunk_text_sha256>:<prev>"
//
// where <prev> is link (i-1)'s resulting digest in hex, or the
// genesis value below for link 0, and a link is a nonce whose
// SHA-256 over "<seed>:<nonce>" has at least the per-chunk
// difficulty in leading zero bits (the Worker serves the
// difficulty in its root response, as it served the old one).
//
// Two properties follow from the seed basis. First, the seeds
// use the pre-scrub chunk texts, so later removal-list and
// picker edits do NOT invalidate the chain: nothing restarts
// when the student edits, and there is no wait at Send beyond
// finishing any last links (each link's expected work is well
// under the time to transcribe one chunk). Second, there is no
// time bucket in the seeds: the old design needed one because a
// bare token could be stockpiled and replayed at leisure; a
// chain is bound to one transcription run (the run identifier
// is in every seed) and the Worker records the chain's final
// digest in the same spent-token store, so a chain is
// single-use — the run binding plus the spent record do the
// bucket's work.
//
// The per-chunk difficulty is constant, so the total price
// scales with the recording's length, like the transcription
// itself. Calibration (2026-11-28): the synchronous SHA-256
// below runs at 8.9e4 hashes/s in a worker on this project's
// sandbox VM over the ~243-byte chain input; 16 bits is an
// expected 2^16 hashes per link (~0.7 s at that rate), and a
// typical 40-minute recording (~96 chunks) totals ~2^22.6
// hashes — roughly the replaced token's 2^23.
//
// Nothing about this mechanism is named or explained on the
// page. Pure functions — Node-tested; the worker driver and the
// main-thread fallback live in chain.js.

import { sha256Bytes, leadingZeroBits } from './sha256sync.js';

// Fallback per-chunk difficulty, used only when the Worker's
// root response could not be read: the Worker's calibrated
// constant (Worker 2.10.0). The Worker is the authority; its
// response wins.
export const POW_CHAIN_FALLBACK_BITS = 16;

// The chain head's <prev>: a fixed genesis value, so link 0's
// seed has the same shape as every other link's.
export const CHAIN_GENESIS = '0'.repeat(64);

export function chainLinkSeed(audioSha256, runId, index, chunkTextSha256, prevDigestHex) {
  return `chain:${audioSha256}:${runId || ''}:${index}:${chunkTextSha256}:${prevDigestHex}`;
}

export function chainLinkDigest(audioSha256, runId, index, chunkTextSha256, prevDigestHex, nonce) {
  return sha256Bytes(
    `${chainLinkSeed(audioSha256, runId, index, chunkTextSha256, prevDigestHex)}:${nonce}`);
}

export function digestHex(digest) {
  return [...digest].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export function chainMeets(digest, bits) {
  return leadingZeroBits(digest) >= bits;
}

// One bounded slice of one link's search: try up to `budget`
// nonces starting at `start`. Returns { nonce, digestHex } when
// one meets the difficulty, else { next } — the nonce to resume
// from. The caller (worker driver or fallback) drives the loop.
export function chainSearchChunk(audioSha256, runId, index, chunkTextSha256, prevDigestHex, bits, start, budget) {
  for (let i = 0; i < budget; i++) {
    const nonce = start + i;
    const digest = chainLinkDigest(
      audioSha256, runId, index, chunkTextSha256, prevDigestHex, nonce);
    if (chainMeets(digest, bits)) {
      return { nonce: String(nonce), digestHex: digestHex(digest) };
    }
  }
  return { next: start + budget };
}
