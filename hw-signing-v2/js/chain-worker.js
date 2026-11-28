// The chain solver as a Web Worker (webapp 2.9.0; see pow.js
// for the chain design). It runs on its own core, apart from
// the transcription: the page posts each chunk's seed material
// as the chunk lands, and the worker works through the links in
// order — the chain is sequential, so link i+1 cannot start
// before link i is solved, which costs nothing because a link's
// expected solve time is well under a chunk's transcription
// time. Each solved link is posted back at once, and the page
// stores it in the recording's cache record, so an interrupted
// transcription resumes its chain where it stopped.
//
// Protocol (all messages are plain objects):
//   page -> worker  { type: 'init', audioSha256, runId, bits }
//   page -> worker  { type: 'chunk', index, chunkTextSha256 }
//                   (also the form a resumed chain's stored
//                   chunks are re-fed in, oldest first)
//   page -> worker  { type: 'solved', index, nonce, digestHex }
//                   (a link already solved in an earlier
//                   session: adopted as chain state, not
//                   re-searched, so a resume continues from the
//                   stored partial chain)
//   worker -> page  { type: 'link', index, nonce, digestHex }

import { chainSearchChunk, CHAIN_GENESIS } from './pow.js';

let audioSha256 = '';
let runId = '';
let bits = 0;
let prevDigestHex = CHAIN_GENESIS;
let nextIndex = 0;      // the next link the chain expects
let searchFrom = 0;     // nonce to resume the current link from
const queue = [];       // chunk text hashes waiting for their link

function pump() {
  while (queue.length && queue[0].index === nextIndex) {
    const { index, chunkTextSha256 } = queue.shift();
    let from = searchFrom;
    for (;;) {
      const r = chainSearchChunk(
        audioSha256, runId, index, chunkTextSha256, prevDigestHex, bits, from, 20000);
      if (r.nonce !== undefined) {
        prevDigestHex = r.digestHex;
        nextIndex = index + 1;
        searchFrom = 0;
        self.postMessage({
          type: 'link', index, nonce: r.nonce, digestHex: r.digestHex,
        });
        break;
      }
      from = r.next;
    }
  }
}

self.onmessage = (ev) => {
  const m = ev.data || {};
  if (m.type === 'init') {
    audioSha256 = m.audioSha256 || '';
    runId = m.runId || '';
    bits = m.bits || 0;
    prevDigestHex = CHAIN_GENESIS;
    nextIndex = 0;
    searchFrom = 0;
    queue.length = 0;
    return;
  }
  if (m.type === 'solved') {
    if (m.index === nextIndex) {
      prevDigestHex = m.digestHex;
      nextIndex = m.index + 1;
      searchFrom = 0;
      pump();
    }
    return;
  }
  if (m.type === 'chunk') {
    queue.push({ index: m.index, chunkTextSha256: m.chunkTextSha256 });
    queue.sort((a, b) => a.index - b.index);
    pump();
  }
};
