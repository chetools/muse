// Proof-of-work submission token (webapp 2.8.0; Worker 2.9.0).
//
// Before a job is sent, the page searches for a nonce such that
// the SHA-256 of "<seed>:<nonce>" has at least `bits` leading
// zero bits, where the seed is
// "<audio_sha256>:<transcript_sha256>:<run_id>:<bucket>" and the
// bucket is the current 30-minute window number. The Worker
// recomputes one hash to verify, accepts the current or previous
// bucket, and records the token as spent. Nothing about this
// mechanism is named or explained on the page (the student sees
// only a short wait, if anything): the search runs in the
// background while the student reviews the transcript.
//
// The bucket clock is the Worker's: the caller passes the server
// time offset it got from the Worker's root response, and this
// module never reads the page's clock for a bucket without it.
// Pure — Node-tested. The search itself is chunked: it runs a
// bounded number of hashes per call and yields between chunks,
// so the page stays responsive; the caller drives it.

import { sha256Bytes, leadingZeroBits } from './sha256sync.js';

export const POW_BUCKET_MS = 30 * 60 * 1000;
// Fallback difficulty, used only when the Worker's root response
// could not be read: the Worker's calibrated constant (Worker
// 2.9.0). The Worker is the authority; its response wins.
export const POW_FALLBACK_BITS = 23;

export function powBucket(serverNowMs) {
  return Math.floor(serverNowMs / POW_BUCKET_MS);
}

export function powSeed(audioSha256, transcriptSha256, runId, bucket) {
  return `${audioSha256}:${transcriptSha256}:${runId || ''}:${bucket}`;
}

export function powDigest(audioSha256, transcriptSha256, runId, bucket, nonce) {
  return sha256Bytes(`${powSeed(audioSha256, transcriptSha256, runId, bucket)}:${nonce}`);
}

export function powMeets(digest, bits) {
  return leadingZeroBits(digest) >= bits;
}

// One chunk of the search: try up to `budget` nonces starting at
// `start`. Returns { nonce } when one meets the difficulty, else
// { next } — the nonce to resume from.
export function powSearchChunk(audioSha256, transcriptSha256, runId, bucket, bits, start, budget) {
  for (let i = 0; i < budget; i++) {
    const nonce = start + i;
    if (powMeets(powDigest(audioSha256, transcriptSha256, runId, bucket, nonce), bits)) {
      return { nonce: String(nonce) };
    }
  }
  return { next: start + budget };
}

// Solve in the background: chunked search with yields, reporting
// progress as the fraction of the expected work done. `signal`
// is an object the caller mutates ({ aborted: true }) to stop a
// search whose seed has gone stale (the transcript changed, or
// the bucket rolled over mid-search). Resolves to
// { bucket, nonce } or null when aborted.
export async function solvePow({ audioSha256, transcriptSha256, runId, bucket, bits, signal, onProgress }) {
  const expected = Math.pow(2, bits);
  let next = 0;
  const budget = 4000;
  while (!signal || !signal.aborted) {
    const r = powSearchChunk(audioSha256, transcriptSha256, runId, bucket, bits, next, budget);
    if (r.nonce !== undefined) return { bucket, nonce: r.nonce };
    next = r.next;
    if (onProgress) onProgress(Math.min(1, next / expected));
    await new Promise((res) => setTimeout(res, 0));
  }
  return null;
}
