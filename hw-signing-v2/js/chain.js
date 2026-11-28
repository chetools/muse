// Chain driver (webapp 2.9.0; see pow.js for the chain design
// this drives). A chain state is the page's record of one
// transcription's chain:
//
//   { audioSha256, runId, bits,
//     hashes:  [chunk text SHA-256 hex, by chunk index],
//     nonces:  [solved nonce (string), by chunk index],
//     digests: [link digest hex, by chunk index] }
//
// Links solve strictly in order: link i's seed carries link
// (i-1)'s digest, so nothing about link i can be computed
// before link (i-1) is solved. The state functions are pure —
// Node-tested. startChainSolver adds the live solving: a Web
// Worker on its own core when one can be started (the protocol
// of chain-worker.js), and otherwise the same search on this
// thread, in bounded slices with yields, so the page stays
// responsive. Either way every solved link is adopted into the
// state through the one checked path (chainTryAdoptNonce), and
// reported through onLink so the caller can persist it.

import {
  chainSearchChunk, chainLinkDigest, chainMeets, digestHex,
  CHAIN_GENESIS,
} from './pow.js';

export function createChainState(audioSha256, runId, bits) {
  return {
    audioSha256: audioSha256 || '',
    runId: runId || '',
    bits: bits || 0,
    hashes: [],
    nonces: [],
    digests: [],
  };
}

// Record chunk `index`'s text hash. Returns false when a
// different hash already stands for that index — the chain
// belongs to other chunks, and the caller should rebuild it.
export function chainAddChunk(state, index, chunkTextSha256) {
  if (state.hashes[index] !== undefined) {
    return state.hashes[index] === chunkTextSha256;
  }
  state.hashes[index] = chunkTextSha256;
  return true;
}

export function chainSolvedCount(state) {
  let n = 0;
  while (n < state.nonces.length && state.nonces[n] !== undefined) n++;
  return n;
}

// The first index that has a chunk hash but no solved link, or
// -1 when every recorded chunk is solved.
export function chainNextUnsolved(state) {
  const solved = chainSolvedCount(state);
  for (let i = solved; i < state.hashes.length; i++) {
    if (state.hashes[i] !== undefined) return i;
  }
  return -1;
}

// Complete relative to the chunks recorded so far: at least
// one chunk, and every recorded chunk's link solved.
export function chainComplete(state) {
  return state.hashes.length > 0 && chainNextUnsolved(state) === -1;
}

export function chainFinalDigest(state) {
  const n = chainSolvedCount(state);
  return n ? state.digests[n - 1] : null;
}

// The one checked adoption path: recompute link `index`'s
// digest from `nonce` (one hash), and record the link only
// when the nonce is the next link's and the digest meets the
// difficulty. Used for links the worker solved, for links the
// main-thread search solved, and for nonces restored from the
// recording's cache record — a stored nonce that no longer
// verifies (the difficulty was raised, or the record's chunks
// changed under it) is refused here, and adoption of any later
// stored link stops with it, because their seeds carry this
// link's digest.
export function chainTryAdoptNonce(state, index, nonce) {
  if (index !== chainSolvedCount(state)) return false;
  if (state.hashes[index] === undefined) return false;
  const prev = index === 0 ? CHAIN_GENESIS : state.digests[index - 1];
  const digest = chainLinkDigest(
    state.audioSha256, state.runId, index, state.hashes[index], prev, nonce);
  if (!chainMeets(digest, state.bits)) return false;
  state.nonces[index] = String(nonce);
  state.digests[index] = digestHex(digest);
  return true;
}

// The proof for the job-creation body, or null while the chain
// is incomplete: the chunk count, the per-chunk text hashes
// and the per-chunk nonces, in order. The run identifier rides
// in the body as before (run_id), not in the proof.
export function chainProof(state) {
  if (!chainComplete(state)) return null;
  return {
    count: state.hashes.length,
    chunk_hashes: [...state.hashes],
    nonces: [...state.nonces],
  };
}

// Resolve with the proof once the chain covers `expectedCount`
// chunks and every one is solved. Polls: the last chunk hashes
// and links can still be landing when the caller (the Send
// click) arrives, and there is deliberately no deadline — the
// remaining links are seconds of work, and the alternative the
// old design had (sending with no proof after a long wait) is
// not carried over.
export function chainWhenComplete(state, expectedCount, pollMs = 200) {
  return new Promise((resolve) => {
    const check = () => {
      if (state.hashes.length >= expectedCount &&
          chainSolvedCount(state) >= expectedCount) {
        resolve(chainProof(state));
        return;
      }
      setTimeout(check, pollMs);
    };
    check();
  });
}

// ------------------------------------------------------------
// The main-thread search: solve the chain's unsolved links in
// order, in bounded slices with yields between them. Runs as
// the fallback when no worker can be started, and is what the
// driver falls back to if the worker fails mid-chain. Each
// solved link is reported through onLink (when given) after its
// adoption, exactly as worker-solved links are.
export async function solveChainOnMainThread(state, shouldStop, onLink) {
  const stopped = () => !!(shouldStop && shouldStop());
  while (!stopped()) {
    const idx = chainNextUnsolved(state);
    if (idx === -1) return;
    const prev = idx === 0 ? CHAIN_GENESIS : state.digests[idx - 1];
    let from = 0;
    for (;;) {
      if (stopped()) return;
      const r = chainSearchChunk(
        state.audioSha256, state.runId, idx, state.hashes[idx],
        prev, state.bits, from, 4000);
      if (r.nonce !== undefined) {
        if (chainTryAdoptNonce(state, idx, r.nonce) &&
            typeof onLink === 'function') {
          onLink(idx, state.nonces[idx]);
        }
        break;
      }
      from = r.next;
      await new Promise((res) => setTimeout(res, 0));
    }
  }
}

function defaultCreateWorker() {
  return new Worker(
    new URL('./chain-worker.js', import.meta.url), { type: 'module' });
}

// ------------------------------------------------------------
// The live solver. startChainSolver(state, { onLink,
// createWorker }) returns a driver:
//
//   feed(index, chunkTextSha256)
//     Record a chunk and offer it to the solver. Chunks whose
//     links already stand (restored nonces) are not offered —
//     the worker's queue expects the next unsolved index.
//   adoptStored(index, nonce)
//     Adopt a nonce restored from the cache record through the
//     checked path, and tell the worker the link stands (its
//     digest, recomputed here) so its chain state advances.
//     Returns whether the link was adopted.
//   stop()
//     End solving: terminate the worker, halt the fallback.
//
// onLink(index, nonce) fires for every newly solved link,
// however it was solved, after its adoption into the state.
// createWorker is injectable for tests: pass null to force the
// main-thread fallback, or a factory returning a worker-like
// object with postMessage and a settable onmessage.
export function startChainSolver(state, { onLink, createWorker } = {}) {
  const report = typeof onLink === 'function' ? onLink : () => {};
  let stopped = false;
  let worker = null;
  let fallbackRunning = false;

  const startFallback = () => {
    if (stopped || fallbackRunning) return;
    fallbackRunning = true;
    solveChainOnMainThread(state, () => stopped || !!worker, report)
      .catch(() => {})
      .finally(() => {
        fallbackRunning = false;
        // A loop that found nothing to do can exit before the
        // chunks it should solve are fed — the feed calls land
        // synchronously after the solver starts, while this
        // flag clears a microtask later, and a feed in that
        // window sees the flag set and starts nothing. So the
        // exit itself re-checks: unsolved work with no worker
        // standing restarts the loop here, and no feed timing
        // can strand the chain.
        if (!stopped && !worker && chainNextUnsolved(state) !== -1) {
          startFallback();
        }
      });
  };

  const onWorkerLink = (m) => {
    if (stopped) return;
    if (chainTryAdoptNonce(state, m.index, m.nonce)) {
      report(m.index, state.nonces[m.index]);
    } else {
      // The worker's answer does not recompute — its state and
      // this page's have diverged, which should not happen.
      // Trust nothing further from it: drop to the fallback,
      // which re-derives every remaining link here.
      dropWorker();
      startFallback();
    }
  };

  const dropWorker = () => {
    if (!worker) return;
    const w = worker;
    worker = null;
    try { w.terminate(); } catch { /* already gone */ }
  };

  const factory = createWorker === undefined ? defaultCreateWorker : createWorker;
  if (factory) {
    try {
      worker = factory();
      worker.onmessage = (ev) => {
        const m = (ev && ev.data) || {};
        if (m.type === 'link') onWorkerLink(m);
      };
      worker.onerror = () => { dropWorker(); startFallback(); };
      worker.postMessage({
        type: 'init',
        audioSha256: state.audioSha256,
        runId: state.runId,
        bits: state.bits,
      });
    } catch {
      worker = null;
    }
  }
  if (!worker) startFallback();

  return {
    feed(index, chunkTextSha256) {
      if (stopped) return;
      if (!chainAddChunk(state, index, chunkTextSha256)) return;
      if (index < chainSolvedCount(state)) return; // link stands
      if (worker) {
        try {
          worker.postMessage({ type: 'chunk', index, chunkTextSha256 });
          return;
        } catch { dropWorker(); }
      }
      startFallback();
    },
    adoptStored(index, nonce) {
      if (stopped) return false;
      // A link that already stands in the state with this
      // nonce (adopted directly into the state before the
      // solver started) needs no re-check — only the worker
      // sync below. Any other nonce goes through the checked
      // adoption path.
      const stands = state.nonces[index] !== undefined &&
        state.nonces[index] === String(nonce);
      if (!stands && !chainTryAdoptNonce(state, index, nonce)) return false;
      if (worker) {
        try {
          worker.postMessage({
            type: 'solved', index,
            nonce: state.nonces[index], digestHex: state.digests[index],
          });
        } catch { dropWorker(); startFallback(); }
      }
      return true;
    },
    stop() {
      stopped = true;
      dropWorker();
    },
  };
}
