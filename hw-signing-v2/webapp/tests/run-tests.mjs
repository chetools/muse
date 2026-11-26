// Node tests for the HW Signing v2 webapp's pure-logic modules.
// Run: node tests/run-tests.mjs   (from the webapp folder)
// Browser-only parts (Web Audio decode, the Parakeet model run,
// IndexedDB, the YouTube IFrame player, push) are not exercised here;
// see README.md.

import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

import { parseConfig, buildConfigLink, normaliseWorkerBase } from '../js/config.js';
import { sha256Hex } from '../js/hash.js';
import {
  parseScrubWords, scrubText, scrubChunks, scrubMetadata,
  canonicalTranscript, legacyCanonicalTranscript, findSuspects, formatDuration,
} from '../js/transcript.js';
import {
  VERSIONS, FINGERPRINT_FILE_NAME, assemblePackage, parsePackageVerification,
  chunksFromCanonical, formatTranscriptTimestamp,
} from '../js/package.js';
import { encodeWavPcm16, pcmFromWavBytes, wavDurationS, channelsToMono, createStreamResampler, decodeFileTo16kMono } from '../js/media.js';
import {
  isMp4FamilyFile, tier2BlockReason, webCodecsCodecString,
  decoderSpecificInfo, planesToChannels, demuxMp4Audio, decodeMp4WithWebCodecs,
} from '../js/media-mp4.js';
import { buildVocabulary } from '../js/vocab.js';
import { PAIRS } from '../chemescribe-base/corrections.js';
import { cacheKey, cacheHit, resetStaleRecord, toCachedChunk, fromCachedChunk, recordingFirstWords } from '../js/cachekey.js';
import { crc32, crc32Async, buildZipBytes, buildZipBytesAsync, ZIP_DOS_DATE, ZIP_DOS_TIME, submissionZipName } from '../js/zip.js';
import {
  RETRIEVAL_CODE_RE, parseYouTubeVideoId, canonicalWatchUrl,
  verifyBundleContents,
  validateJobPayload, buildJobPayload,
  loadJobEntries, addJobEntry, removeJobEntry, pruneExpiredEntries,
  submitJob, fetchJobStatus, finalizeJob,
  bundleChromaprintSha, verifyFingerprintContents,
  kindFromResultBundle, duplicateJobEntry, collapseSameJobEntries,
  generateRetrievalToken, RECOVERY_TOKEN_LENGTH, entryPollable,
} from '../js/jobs.js';
import { encodeRawFingerprint, decodeRawFingerprint } from '../js/fingerprint.js';
import { urlBase64ToUint8Array, uint8ArrayToUrlBase64 } from '../js/push.js';

let passed = 0, failed = 0, skipped = 0;
async function test(name, fn) {
  try {
    await fn();
    passed += 1;
    console.log('PASS', name);
  } catch (err) {
    failed += 1;
    console.log('FAIL', name, '—', err.message);
  }
}
function skip(name, why) {
  skipped += 1;
  console.log('SKIP', name, '—', why);
}

const nodeSha256 = (text) =>
  createHash('sha256').update(text, 'utf8').digest('hex');
const SHA_A = 'a'.repeat(64);
const SHA_B = 'b'.repeat(64);
const SHA_C = 'c'.repeat(64);

/* ---------------- config ---------------- */

await test('config: parses a full teacher link, including ph', () => {
  const cfg = parseConfig('?w=https%3A%2F%2Fhw.example.workers.dev%2F&pkg=hw3+v2&ph=' + SHA_A + '&course=CHE%203025&asg=HW3');
  assert.equal(cfg.worker, 'https://hw.example.workers.dev');
  assert.equal(cfg.pkg, 'hw3 v2');
  assert.equal(cfg.ph, SHA_A);
  assert.equal(cfg.course, 'CHE 3025');
  assert.equal(cfg.asg, 'HW3');
  assert.equal(cfg.setup, false);
});

await test('config: missing parameters are null; setup flag read', () => {
  const cfg = parseConfig('?setup=1');
  assert.equal(cfg.worker, null);
  assert.equal(cfg.pkg, null);
  assert.equal(cfg.ph, null);
  assert.equal(cfg.setup, true);
});

await test('config: built link round-trips through parse, with ph', () => {
  const link = buildConfigLink('https://pages.example/grade/index.html', {
    worker: 'https://hw.example.workers.dev/', pkg: 'hw3 v2', ph: SHA_B,
    course: 'CHE 3025', asg: 'HW 3',
  });
  const cfg = parseConfig(new URL(link).search);
  assert.equal(cfg.worker, 'https://hw.example.workers.dev');
  assert.equal(cfg.pkg, 'hw3 v2');
  assert.equal(cfg.ph, SHA_B);
  assert.equal(cfg.course, 'CHE 3025');
  assert.equal(cfg.asg, 'HW 3');
  assert.equal(normaliseWorkerBase('https://x.dev///'), 'https://x.dev');
  assert.ok(!link.includes('pkgurl'), 'v2 links carry no pkgurl');
});

await test('config: worker address must be a plain https address (2.6.12)', () => {
  assert.equal(parseConfig('?w=http%3A%2F%2Fhw.example.workers.dev').worker, null);
  assert.equal(parseConfig('?w=http%3A%2F%2F127.0.0.1%3A8787').worker, 'http://127.0.0.1:8787');
  assert.equal(parseConfig('?w=https%3A%2F%2Fuser%3Apass%40hw.example.workers.dev').worker, null);
  assert.equal(normaliseWorkerBase('https://x.dev/?next=1'), null);
  assert.equal(normaliseWorkerBase('https://x.dev/#frag'), null);
  assert.equal(normaliseWorkerBase('not a url'), null);
  assert.equal(normaliseWorkerBase('https://x.dev/base///'), 'https://x.dev/base');
});

await test('job entries: polled only against their creating Worker (2.6.12)', () => {
  const prod = 'https://hw-grading.carloscomail.workers.dev';
  const other = 'https://attacker.example';
  assert.equal(entryPollable({ worker: prod }, prod), true);
  assert.equal(entryPollable({ worker: prod }, other), false);
  assert.equal(entryPollable({ worker: other }, prod), false);
  assert.equal(entryPollable({}, prod), true);   // legacy entry, production Worker
  assert.equal(entryPollable({}, other), false); // legacy entry, foreign Worker
  assert.equal(entryPollable({ worker: prod }, null), false);
});

await test('scrub: separator variants of a removal entry match (2.6.12)', () => {
  assert.equal(scrubText('my partner Ann Marie Lee helped', ['Ann-Marie Lee']).text,
    'my partner helped');
  assert.equal(scrubText('presented by Ann, Marie Lee today', ['Ann-Marie Lee']).text,
    'presented by today');
});

await test('package: grades are escaped like every other bundle field (2.6.12)', () => {
  const html = assemblePackage({
    youtubeLink: '', audioFileName: 'submission-audio.wav', durationS: 5,
    chunks: [{ start: 0, text: 'x' }],
    bundle: { completeness: '</span><script>alert(1)</script>', accuracy: 5,
      critique: 'ok', job_id: 'j', pkg: 'p v1', pkg_content_sha256: SHA_A,
      audio_sha256: SHA_B, transcript_sha256: SHA_C, critique_sha256: SHA_A,
      youtube_video_sha256: 'none', t: '2026-01-01T00:00:00.000Z', receipt: 'r' },
  });
  assert.ok(!html.includes('<script>alert(1)</script>'), 'grade payload not present verbatim');
  assert.ok(html.includes('&lt;script&gt;'), 'grade payload is escaped');
});

/* ---------------- scrub + canonical + checksum ---------------- */

const rawChunks = [
  { start: 0, raw: 'Hi I am Jordan Lee and this is my homework',
    corrected: 'Hi I am Jordan Lee and this is my homework' },
  { start: 25, raw: 'jordan lee explains the reflux ratio, with JORDAN watching',
    corrected: 'Jordan Lee explains the reflux ratio, with JORDAN watching' },
];

await test('scrub: every occurrence removed, any case, chunks and metadata', () => {
  const words = parseScrubWords('Jordan Lee\njordan');
  const sc = scrubChunks(rawChunks, words);
  assert.equal(sc[0].text, 'Hi I am and this is my homework');
  assert.ok(!/jordan/i.test(sc[0].text) && !/jordan/i.test(sc[1].text));
  assert.equal(scrubMetadata('jordan-lee-hw3.mp4', words), '-hw3.mp4'); // 2.6.12: separator variants match, so the full name goes
  assert.equal(scrubMetadata('Jordan Lee hw3.mp4', words), 'hw3.mp4');
});

await test('scrub: whole-word only; punctuation spacing repaired', () => {
  const { text } = scrubText('Annette and Ann went home , then left .', ['Ann']);
  assert.equal(text, 'Annette and went home, then left.');
});

await test('canonical: one chunk per line with its [mm:ss] marker, LF, no trailing spaces or newline', () => {
  const sc = scrubChunks(rawChunks, parseScrubWords('Jordan Lee, jordan'));
  const canon = canonicalTranscript(sc);
  assert.equal(canon,
    '[00:00] Hi I am and this is my homework\n[00:25] explains the reflux ratio, with watching');
  assert.ok(!canon.endsWith('\n'));
  assert.ok(!/ \n/.test(canon));
  // The pre-2.4.2 markerless form remains available for verifying
  // bundles graded before the markers were incorporated.
  assert.equal(legacyCanonicalTranscript(sc),
    'Hi I am and this is my homework\nexplains the reflux ratio, with watching');
});

await test('checksum: matches an independent Node recomputation', async () => {
  const sc = scrubChunks(rawChunks, parseScrubWords('Jordan Lee, jordan'));
  const canon = canonicalTranscript(sc);
  assert.equal(await sha256Hex(canon), nodeSha256(canon));
  assert.equal(await sha256Hex(new Uint8Array([1, 2, 3])), nodeSha256(Buffer.from([1, 2, 3])));
});

await test('duration format: seconds, SI symbol, one decimal', () => {
  assert.equal(formatDuration(754.04), '754.0 s');
  assert.equal(formatDuration(58), '58.0 s');
});

/* ---------------- suspects ---------------- */

await test('suspects: mid-sentence unknown capitalised word and email flagged', () => {
  const { vocab, wordlist } = buildVocabulary();
  const sc = [{ start: 0, text: 'The gauge was checked by Zqxjk before the run started' },
              { start: 25, text: 'Send it to someone at a.b@example.com please' }];
  const found = findSuspects(sc, vocab, wordlist);
  const words = found.map((f) => f.word);
  assert.ok(words.includes('Zqxjk'), JSON.stringify(found));
  assert.ok(words.some((w) => w.includes('@')));
});

await test('suspects: sentence-initial capitals and known words not flagged', () => {
  const { vocab, wordlist } = buildVocabulary();
  let glossaryWord = null;
  for (const p of PAIRS) {
    const w = String(p.term).split(/\s+/).find((x) => /^[A-Z][a-z]{3,}$/.test(x));
    if (w && vocab.has(w.toLowerCase())) { glossaryWord = w; break; }
  }
  assert.ok(glossaryWord, 'fixture needs a capitalised glossary word');
  const sc = [{ start: 0, text: 'Reflux matters here. The value follows ' + glossaryWord + ' behaviour however it is measured' }];
  const found = findSuspects(sc, vocab, wordlist);
  assert.deepEqual(found, [], JSON.stringify(found));
});

/* ---------------- WAV ---------------- */

await test('wav: header, size and duration agree', () => {
  const samples = new Float32Array(16000); // 1 s of silence
  const wav = encodeWavPcm16(samples);
  assert.equal(wav.length, 44 + 32000);
  assert.equal(String.fromCharCode(...wav.slice(0, 4)), 'RIFF');
  assert.equal(String.fromCharCode(...wav.slice(8, 12)), 'WAVE');
  assert.equal(wavDurationS(wav), 1);
});

await test('wav: pcmFromWavBytes inverts encodeWavPcm16 within int16 quantisation (2.6.14)', () => {
  const samples = new Float32Array([0, 0.5, -0.5, 1, -1, 0.25, -0.125]);
  const back = pcmFromWavBytes(encodeWavPcm16(samples));
  assert.equal(back.length, samples.length);
  for (let i = 0; i < samples.length; i++) {
    assert.ok(Math.abs(back[i] - samples[i]) <= 1 / 32767,
      'sample ' + i + ' round-trips');
  }
  assert.equal(pcmFromWavBytes(new Uint8Array(10)).length, 0);
});

await test('cache reset: a stale-version record resets to a fresh transcript state (2.6.15)', () => {
  const stale = {
    audio_sha256: SHA_A, model: 'old-model', glossary: VERSIONS.glossary,
    wavBlob: 'old-blob', chunks: [{ start_s: 0, end_s: 25, raw: 'r', corrected: 'c' }],
    duration_s: 50, source_name: 'take.mp4', created_at: '2026-01-01T00:00:00Z',
    windows_done: 2, complete: true,
  };
  const reset = resetStaleRecord(stale, {
    model: VERSIONS.model, glossary: VERSIONS.glossary,
    wavBlob: null, duration_s: 0, source_name: '',
  });
  assert.equal(reset.model, VERSIONS.model);
  assert.equal(reset.glossary, VERSIONS.glossary);
  assert.deepEqual(reset.chunks, []);
  assert.equal(reset.windows_done, 0);
  assert.equal(reset.complete, false);
  assert.equal(reset.wavBlob, 'old-blob', 'WAV bytes are kept when none are supplied');
  assert.equal(reset.duration_s, 50);
  assert.equal(reset.source_name, 'take.mp4');
  assert.equal(reset.created_at, '2026-01-01T00:00:00Z');
  // A glossary-only change also resets, and fresh values win.
  const reset2 = resetStaleRecord(stale, {
    model: 'old-model', glossary: 'new-glossary',
    wavBlob: 'new-blob', duration_s: 60, source_name: 'take2.mp4',
  });
  assert.equal(reset2.glossary, 'new-glossary');
  assert.equal(reset2.wavBlob, 'new-blob');
  assert.equal(reset2.duration_s, 60);
  // A current record and an absent record need no reset.
  assert.equal(resetStaleRecord(
    { ...stale, model: VERSIONS.model }, {
      model: VERSIONS.model, glossary: VERSIONS.glossary,
      wavBlob: null, duration_s: 0, source_name: '',
    }), null);
  assert.equal(resetStaleRecord(null, {
    model: VERSIONS.model, glossary: VERSIONS.glossary,
    wavBlob: null, duration_s: 0, source_name: '',
  }), null);
});

await test('wiring: 2.6.15 scenario-campaign fixes are in place', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  const cache = readFileSync(new URL('../js/cache.js', import.meta.url), 'utf8');
  assert.ok(!main.includes('row.after(box)'),
    'the error box is never relocated into a rebuilt container');
  assert.ok(main.includes("line.className = 'err errline'"),
    'an error copy is placed beside the control that was used');
  assert.ok(main.includes("ev.target.value = '';"),
    'the file input is cleared so the same file can be chosen again');
  assert.ok(main.includes('The link check is voided only once the restore is known'),
    'a refused restore keeps a standing link check');
  assert.ok(main.includes("'Recording and transcript restored from this computer"),
    'the restore status line names what was restored');
  assert.ok(main.includes('storedSha === bundle.transcript_sha256'),
    'the fingerprint ZIP falls back to the graded transcript the Worker kept');
  assert.ok(main.includes('return { foreign: true };'),
    'an entry from another grading service is marked foreign, not failed');
  assert.ok(main.includes("'sent to a different grading service — not checked from this page'"),
    'a foreign entry\u2019s row says it is not checked from this page');
  assert.ok(cache.includes('resetStaleRecord(existing,'),
    'cacheInit resets stale-version records');
});

await test('wiring: restore leaves the recording transcribable, delete unloads the loaded recording, empty records are labelled not transcribed (2.6.14)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('pcm = pcmFromWavBytes(wavBytes);'),
    'adopting a stored record derives the samples from its WAV');
  assert.ok(main.includes('entry.audio_sha256 === audioSha'),
    'the delete handler checks whether the deleted record is the loaded one');
  assert.ok(main.includes("'Recording deleted from this computer.'"),
    'deleting the loaded recording says so in the media status');
  assert.ok(main.includes(": 'not transcribed'"),
    'a record with no pieces is labelled not transcribed');
});

/* ---------------- cache key rules ---------------- */

await test('cache key: fingerprint + model + glossary; nothing else enters', () => {
  const k1 = cacheKey(SHA_A, VERSIONS.model, VERSIONS.glossary);
  const k2 = cacheKey(SHA_A, VERSIONS.model, VERSIONS.glossary);
  assert.equal(k1, k2, 'deterministic');
  // Course, assignment and package are not parameters of the key, so
  // the same recording under another course's link yields the same
  // key by construction; a different fingerprint or version does not.
  assert.notEqual(cacheKey(SHA_B, VERSIONS.model, VERSIONS.glossary), k1);
  assert.notEqual(cacheKey(SHA_A, 'other-model', VERSIONS.glossary), k1);
  assert.notEqual(cacheKey(SHA_A, VERSIONS.model, 'other-glossary'), k1);
  assert.ok(k1.startsWith(SHA_A + '|'));
});

await test('cache hit: requires model AND glossary match', () => {
  const record = { audio_sha256: SHA_A, model: VERSIONS.model, glossary: VERSIONS.glossary };
  assert.equal(cacheHit(record, VERSIONS.model, VERSIONS.glossary), true);
  assert.equal(cacheHit(record, 'newer-model', VERSIONS.glossary), false);
  assert.equal(cacheHit(record, VERSIONS.model, 'newer-glossary'), false);
  assert.equal(cacheHit(null, VERSIONS.model, VERSIONS.glossary), false);
  assert.equal(cacheHit(undefined, VERSIONS.model, VERSIONS.glossary), false);
});

await test('cache chunks: stored shape is pre-scrub pipeline shape, round-trips', () => {
  const item = { start: 25, end: 49.5, raw: 'raw words', corrected: 'corrected words', parts: [], applied: [] };
  const cached = toCachedChunk(item);
  assert.deepEqual(cached, { start_s: 25, end_s: 49.5, raw: 'raw words', corrected: 'corrected words' });
  assert.deepEqual(fromCachedChunk(cached),
    { start: 25, end: 49.5, raw: 'raw words', corrected: 'corrected words' });
});

/* ---------------- ZIP ---------------- */

function unzipStored(bytes) {
  // Minimal reader for stored entries: walk local headers in order.
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const dec = new TextDecoder();
  const entries = [];
  let pos = 0;
  while (pos + 4 <= bytes.length && view.getUint32(pos, true) === 0x04034b50) {
    const method = view.getUint16(pos + 8, true);
    const time = view.getUint16(pos + 10, true);
    const date = view.getUint16(pos + 12, true);
    const crc = view.getUint32(pos + 14, true);
    const size = view.getUint32(pos + 18, true);
    const nameLen = view.getUint16(pos + 26, true);
    const extraLen = view.getUint16(pos + 28, true);
    const name = dec.decode(bytes.slice(pos + 30, pos + 30 + nameLen));
    const dataStart = pos + 30 + nameLen + extraLen;
    const data = bytes.slice(dataStart, dataStart + size);
    entries.push({ name, data, method, time, date, crc });
    pos = dataStart + size;
  }
  return { entries, endPos: pos };
}

await test('zip: byte-deterministic across builds; fixed 1980 timestamp', () => {
  const entries = [
    { name: 'submission.html', data: new TextEncoder().encode('<html>hello</html>') },
    { name: 'submission-audio.wav', data: new Uint8Array([1, 2, 3, 4, 5]) },
  ];
  const a = buildZipBytes(entries);
  const b = buildZipBytes(entries.map((e) => ({ ...e, data: new Uint8Array(e.data) })));
  assert.deepEqual(a, b, 'same entries → identical bytes');
  assert.equal(ZIP_DOS_TIME, 0);
  assert.equal(ZIP_DOS_DATE, 33); // 1980-01-01
  const { entries: read } = unzipStored(a);
  for (const e of read) {
    assert.equal(e.time, 0);
    assert.equal(e.date, 33);
    assert.equal(e.method, 0, 'stored, no compression');
  }
});

await test('zip: round-trip — entries in order, contents and CRC intact', () => {
  const wav = encodeWavPcm16(new Float32Array(1600));
  const htmlBytes = new TextEncoder().encode('<!DOCTYPE html>\n<p>package</p>\n');
  const zip = buildZipBytes([
    { name: 'submission.html', data: htmlBytes },
    { name: 'submission-audio.wav', data: wav },
  ]);
  const { entries, endPos } = unzipStored(zip);
  assert.deepEqual(entries.map((e) => e.name), ['submission.html', 'submission-audio.wav']);
  assert.deepEqual(entries[0].data, htmlBytes);
  assert.deepEqual(entries[1].data, wav);
  assert.equal(entries[0].crc, crc32(htmlBytes));
  assert.equal(entries[1].crc, crc32(wav));
  // Central directory follows the local entries.
  const view = new DataView(zip.buffer, zip.byteOffset, zip.byteLength);
  assert.equal(view.getUint32(endPos, true), 0x02014b50);
  // CRC-32 of "123456789" is the standard check value.
  assert.equal(crc32(new TextEncoder().encode('123456789')), 0xCBF43926);
});

await test('zip async: byte-identical to the synchronous build; progress ends at total', async () => {
  // An entry larger than the 4 MiB slice size, so slicing engages.
  const big = new Uint8Array(9 * 1024 * 1024 + 123);
  for (let i = 0; i < big.length; i++) big[i] = (i * 31 + 7) & 0xFF;
  const entries = [
    { name: 'submission.html', data: new TextEncoder().encode('<html>hello</html>') },
    { name: 'submission-audio.wav', data: big },
  ];
  const total = entries.reduce((s, e) => s + e.data.length, 0);
  const calls = [];
  const asyncZip = await buildZipBytesAsync(entries, (done, tot) => calls.push([done, tot]));
  assert.deepEqual(asyncZip, buildZipBytes(entries),
    'async build → bytes identical to the synchronous build');
  assert.ok(calls.length >= 3, 'progress reported across slices');
  for (const [done, tot] of calls) {
    assert.equal(tot, total);
    assert.ok(done <= total, 'progress never exceeds the total');
  }
  assert.deepEqual(calls[calls.length - 1], [total, total],
    'final progress call is exactly (total, total)');
  assert.equal(await crc32Async(big), crc32(big),
    'chunked CRC-32 equals the one-shot CRC-32');
});

await test('zip name: course, homework, total grade and YouTube check time', () => {
  // Dates are constructed locally so the expectation holds in any
  // timezone: the name uses local time.
  const name = submissionZipName({
    course: 'CHE 4061', asg: 'HW5', completeness: 4, accuracy: 3,
    youtubeCheckedAt: new Date(2026, 10, 10, 19, 5),
  });
  assert.equal(name, 'C4061H5-G7-Y1905-261110.zip');
});

await test('zip name: falls back to the grading time when no check time was kept', () => {
  const graded = new Date(2026, 10, 9, 8, 30);
  assert.equal(
    submissionZipName({ course: 'CHE3025', asg: 'HW 3', completeness: 5, accuracy: 5, youtubeCheckedAt: '', gradedAt: graded }),
    'C3025H3-G10-Y0830-261109.zip');
  assert.equal(
    submissionZipName({ course: 'CHE3025', asg: 'HW 3', completeness: 5, accuracy: 5, youtubeCheckedAt: 'not a date', gradedAt: graded }),
    'C3025H3-G10-Y0830-261109.zip');
});

await test('zip name: zero-padded time and date fields', () => {
  const name = submissionZipName({
    course: 'CHE 4061', asg: 'HW5', completeness: 4, accuracy: 3,
    youtubeCheckedAt: new Date(2026, 0, 5, 9, 3),
  });
  assert.equal(name, 'C4061H5-G7-Y0903-260105.zip');
});

await test('zip name: no data at all gives the plain fallback name', () => {
  assert.equal(submissionZipName({}), 'submission.zip');
  assert.equal(submissionZipName(), 'submission.zip');
});

/* ---------------- HTML package v2 ---------------- */

const bundle = {
  v: 2,
  job_id: 'job-2026-0001',
  audio_sha256: SHA_A,
  transcript_sha256: SHA_B,
  pkg: 'hw3 v2',
  pkg_content_sha256: SHA_C,
  completeness: 4,
  accuracy: 3,
  critique: 'The efficiency argument is incomplete.\nThe feed description is exact.',
  critique_sha256: 'd'.repeat(64),
  youtube_video_sha256: 'e'.repeat(64),
  t: '2026-11-09T10:00:00.000Z',
  receipt: 'grade-receipt-value',
};
const pkgInput = {
  youtubeLink: 'https://www.youtube.com/watch?v=abc123XYZ_-',
  audioFileName: 'submission-audio.wav',
  durationS: 4520.04,
  chunks: [
    { start: 0, text: 'Hello world this is the feed' },
    { start: 4520, text: 'later chunk about reflux' },
  ],
  bundle,
};
const html = assemblePackage(pkgInput);

await test('package v2: sections in order, grade spans, audit section empty', () => {
  const iSummary = html.indexOf('<section id="summary">');
  const iGrading = html.indexOf('<section id="grading">');
  const iVerif = html.indexOf('<section id="verification">');
  assert.ok(iSummary >= 0 && iGrading > iSummary && iVerif > iGrading);
  assert.ok(html.includes('<span data-grade="completeness">4</span>'));
  assert.ok(html.includes('<span data-grade="accuracy">3</span>'));
  assert.ok(html.includes('<section id="audit">'));
  const audit = html.slice(html.indexOf('<section id="audit">'), html.indexOf('<section id="verification">'));
  assert.ok(!audit.includes('<p>'), 'audit section empty');
});

await test('package v2: build/parse round-trip recovers every signed field', () => {
  const parsed = parsePackageVerification(html);
  const v = parsed.verification;
  assert.equal(v['Format version'], '2');
  assert.equal(v['Job'], 'job-2026-0001');
  assert.equal(v['Prompt package'], 'hw3 v2');
  assert.equal(v['Prompt package content SHA-256'], SHA_C);
  assert.equal(v['Webapp version'], 'hw-signing-webapp 2.6.20');
  assert.equal(v['Model version'], VERSIONS.model);
  assert.equal(v['Glossary version'], VERSIONS.glossary);
  assert.equal(v['YouTube link'], 'https://www.youtube.com/watch?v=abc123XYZ_-');
  assert.equal(v['Audio file'], 'submission-audio.wav');
  assert.equal(v['Audio duration'], '4520.0');
  assert.equal(v['Audio SHA-256'], SHA_A);
  assert.equal(v['Transcript SHA-256'], SHA_B);
  assert.equal(v['Completeness'], '4');
  assert.equal(v['Accuracy'], '3');
  assert.equal(v['Critique SHA-256'], 'd'.repeat(64));
  assert.equal(v['YouTube video SHA-256'], 'e'.repeat(64));
  assert.equal(v['Graded at'], '2026-11-09T10:00:00.000Z');
  assert.equal(v['Grade receipt'], 'grade-receipt-value');
  assert.equal(parsed.completeness, 4);
  assert.equal(parsed.accuracy, 3);
});

await test('package v2: no v1 receipt or session; transcript recovers canonically', () => {
  assert.ok(!html.includes('<dt>Receipt</dt>'), 'v1 Receipt label gone');
  assert.ok(!html.includes('<dt>Session</dt>'), 'v1 Session label gone');
  assert.ok(!html.includes('<dt>Signed at</dt>'), 'v1 Signed at label gone');
  const parsed = parsePackageVerification(html);
  assert.deepEqual(parsed.transcriptLines, [
    '[00:00] Hello world this is the feed',
    '[75:20] later chunk about reflux',
  ]);
  const recovered = parsed.transcriptLines.join('\n');
  assert.equal(recovered, canonicalTranscript(pkgInput.chunks.map(
    (c) => ({ start: c.start, text: c.text }))));
  const grading = html.slice(html.indexOf('<section id="grading">'), html.indexOf('<section id="verification">'));
  assert.ok(!grading.includes('<a '), 'no links inside the grading section');
  assert.ok(!html.includes('base64') && !html.includes('data:audio'));
  assert.ok(grading.includes('efficiency argument is incomplete'));
});

await test('package v2: practice bundle prints YouTube video SHA-256 as none', () => {
  const practice = assemblePackage({
    ...pkgInput, youtubeLink: '',
    bundle: { ...bundle, youtube_video_sha256: 'none' },
  });
  const parsed = parsePackageVerification(practice);
  assert.equal(parsed.verification['YouTube video SHA-256'], 'none');
});

await test('package: transcript timestamp format', () => {
  assert.equal(formatTranscriptTimestamp(0), '00:00');
  assert.equal(formatTranscriptTimestamp(65), '01:05');
  assert.equal(formatTranscriptTimestamp(4520), '75:20');
});

/* ---------------- YouTube ID parsing ---------------- */

await test('youtube id: all accepted forms parse; others rejected', () => {
  const id = 'abc123XYZ_-';
  assert.equal(parseYouTubeVideoId('https://www.youtube.com/watch?v=' + id), id);
  assert.equal(parseYouTubeVideoId('https://youtu.be/' + id), id);
  assert.equal(parseYouTubeVideoId('https://www.youtube.com/shorts/' + id), id);
  assert.equal(parseYouTubeVideoId('https://www.youtube.com/live/' + id + '?x=1'), id);
  assert.equal(parseYouTubeVideoId('https://www.youtube.com/embed/' + id), id);
  assert.equal(parseYouTubeVideoId('https://m.youtube.com/watch?v=' + id + '&t=5'), id);
  // 2.6.16: a YouTube Studio edit address parses to the same ID, so
  // the row field can convert it to the canonical watch form.
  assert.equal(parseYouTubeVideoId('https://studio.youtube.com/video/' + id + '/edit'), id);
  assert.equal(parseYouTubeVideoId('https://studio.youtube.com/video/' + id), id);
  assert.equal(parseYouTubeVideoId('https://www.youtube.com/watch?v=short'), null);
  assert.equal(parseYouTubeVideoId('https://example.com/watch?v=' + id), null);
  assert.equal(parseYouTubeVideoId('not a url'), null);
  assert.equal(parseYouTubeVideoId(''), null);
  assert.equal(canonicalWatchUrl(id), 'https://www.youtube.com/watch?v=' + id);
});

await test('no binding: a legacy bundle carrying a video hash packages a different link (2.6.19)', () => {
  // A job finalised under Worker 2.7.3 carries the SHA-256 of
  // video A in its signed bundle. The page no longer consults
  // that hash: packaging with video B's link writes B's link and
  // no rejection arises. assemblePackage is the packaging step;
  // the wiring tests below prove no bundle-hash comparison
  // remains in the page flow.
  const videoA = 'boundVideo1';
  const videoB = 'def456UVWxy';
  const bundle = {
    v: 2, job_id: 'job-legacy1', audio_sha256: SHA_A,
    transcript_sha256: SHA_B, pkg: 'test v1', pkg_content_sha256: SHA_C,
    completeness: 5, accuracy: 4, critique: '1. A critique point.',
    critique_sha256: SHA_C,
    youtube_video_sha256: nodeSha256(videoA),
    t: '2026-11-26T15:00:00.000Z', receipt: 'receipt-legacy',
  };
  const html = assemblePackage({
    youtubeLink: canonicalWatchUrl(videoB),
    audioFileName: 'submission-audio.wav', durationS: 12.5,
    chunks: [{ start: 0, text: 'alpha bravo' }],
    bundle,
  });
  const parsed = parsePackageVerification(html);
  assert.equal(parsed.verification['YouTube link'], canonicalWatchUrl(videoB),
    'the ZIP carries the row link (video B), not the legacy bound video A');
  assert.ok(!html.includes('Not the video bound to this job'),
    'no bound-video rejection text is packaged');
  const jobs = readFileSync(new URL('../js/jobs.js', import.meta.url), 'utf8');
  assert.ok(!jobs.includes('bundleBoundVideoSha'),
    'jobs.js no longer exposes a bound-video helper');
});
await test('retrieval code: rule matches the Worker', () => {
  assert.ok(!RETRIEVAL_CODE_RE.test('7'));
  assert.ok(!RETRIEVAL_CODE_RE.test('abc123'));
  assert.ok(!RETRIEVAL_CODE_RE.test('abcd123'));
  assert.ok(RETRIEVAL_CODE_RE.test('abcd1234'));
  assert.ok(RETRIEVAL_CODE_RE.test('x'.repeat(128)));
  assert.ok(!RETRIEVAL_CODE_RE.test(''));
  assert.ok(!RETRIEVAL_CODE_RE.test('a b'));
  assert.ok(!RETRIEVAL_CODE_RE.test('code-1234'));
  assert.ok(!RETRIEVAL_CODE_RE.test('x'.repeat(129)));
});

await test('recovery token: generated tokens satisfy the code rule and differ', () => {
  assert.equal(RECOVERY_TOKEN_LENGTH, 24);
  const seen = new Set();
  for (let i = 0; i < 200; i++) {
    const t = generateRetrievalToken();
    assert.equal(t.length, RECOVERY_TOKEN_LENGTH);
    assert.ok(RETRIEVAL_CODE_RE.test(t), 'token passes the Worker code rule');
    seen.add(t);
  }
  assert.equal(seen.size, 200, 'no repeats in 200 tokens');
});

await test('recovery token: byte mapping is uniform, with rejection of bytes >= 248', () => {
  // Byte b maps to alphabet[b % 62]: 0 -> 'A', 25 -> 'Z',
  // 26 -> 'a', 51 -> 'z', 52 -> '0', 61 -> '9', 62 -> 'A'.
  const fixed = (seq) => (n) => {
    const out = new Uint8Array(n);
    for (let i = 0; i < n; i++) out[i] = i < seq.length ? seq[i] : 0;
    return out;
  };
  const t = generateRetrievalToken(fixed([0, 25, 26, 51, 52, 61, 62]));
  assert.equal(t.slice(0, 7), 'AZaz09A');
  assert.equal(t.length, RECOVERY_TOKEN_LENGTH);
  // A source that first offers only rejected bytes still completes.
  let calls = 0;
  const rejecting = (n) => {
    calls += 1;
    return new Uint8Array(n).fill(calls === 1 ? 255 : 0);
  };
  assert.equal(generateRetrievalToken(rejecting), 'A'.repeat(RECOVERY_TOKEN_LENGTH));
});

await test('wiring: the page generates the job token internally; the student never sees or enters a code (2.6.11)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(main.includes('retrievalCode: generateRetrievalToken()'),
    'the submit payload carries a freshly generated token');
  assert.ok(!main.includes('showRecoveryCode') && !index.includes('recoveryLine'),
    'no send-time code display remains');
  assert.ok(!index.includes('id="manualCode"') && !main.includes('manualBtn'),
    'no manual code entry remains');
  assert.ok(!index.includes('Retrieving on a different browser'),
    'the different-browser retrieval section is gone');
  assert.ok(!index.includes('recovery'),
    'the page never mentions a recovery code');
  assert.ok(!main.includes("$('retrievalCode')"),
    'no page code reads a code input');
  assert.ok(!index.includes('id="retrievalCode"'),
    'step 6 has no retrieval code input');
});

await test('wiring: no check on paste; the click check carries the cell reasons (2.6.18)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(!main.includes('runRowCheck'), 'no row check runs while the student types');
  assert.ok(!main.includes('That is not a YouTube link this page can read.'),
    'the old on-paste unreadable-link message is gone');
  assert.ok(main.includes('Set it to Unlisted or Public and check again.'),
    'a private or missing video has its own cell reason, from the click check');
  assert.ok(main.includes('Could not complete the check. Try again.'),
    'a failed click check has its own cell reason');
  assert.ok(main.includes('await requestYouTubeCheck(cfg.worker, canonical);'),
    'the reachability check runs at the Generate ZIP click');
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(!index.includes('id="ytLink"') && !index.includes('id="finLink"'),
    'no step-6 or panel link field remains');
});

/* ---------------- job payload ---------------- */

const jobState = {
  pkg: 'hw3 v2',
  pkgContentSha256: SHA_C,
  kind: 'practice',
  transcript: 'the scrubbed transcript',
  audioSha256: SHA_A,
  transcriptSha256: SHA_B,
  versions: VERSIONS,
  retrievalCode: 'code1234',
  youtubeToken: null,
  youtubeVideoId: null,
};

await test('job payload: practice builds and validates; no youtube fields sent', () => {
  const body = buildJobPayload(jobState);
  assert.equal(validateJobPayload(body).ok, true);
  assert.ok(!('youtube_token' in body) && !('youtube_video_id' in body) &&
    !('youtube_checked_at' in body));
  assert.ok(!('push_subscription' in body));
  assert.ok(!('retrieval_name' in body));
  assert.deepEqual(body.versions, VERSIONS);
});

await test('job payload: final requires the check token and video id', () => {
  const noToken = buildJobPayload({ ...jobState, kind: 'final' });
  const res = validateJobPayload(noToken);
  assert.equal(res.ok, false);
  assert.match(res.reason, /YouTube link checked/);
  const withToken = buildJobPayload({
    ...jobState, kind: 'final', youtubeToken: 'tok', youtubeVideoId: 'abc123XYZ_-',
    youtubeCheckedAt: '2026-11-09T10:00:00.000Z',
  });
  assert.equal(validateJobPayload(withToken).ok, true);
  assert.equal(withToken.youtube_token, 'tok');
  assert.equal(withToken.youtube_checked_at, '2026-11-09T10:00:00.000Z');
  const noCheckedAt = buildJobPayload({
    ...jobState, kind: 'final', youtubeToken: 'tok', youtubeVideoId: 'abc123XYZ_-',
  });
  assert.equal(validateJobPayload(noCheckedAt).ok, false);
});

await test('job payload: bad fields rejected', () => {
  const base = buildJobPayload(jobState);
  assert.equal(validateJobPayload({ ...base, pkg_content_sha256: 'zz' }).ok, false);
  assert.equal(validateJobPayload({ ...base, transcript: '   ' }).ok, false);
  assert.equal(validateJobPayload({ ...base, transcript: 'x'.repeat(200001) }).ok, false);
  assert.equal(validateJobPayload({ ...base, audio_sha256: 'a'.repeat(63) }).ok, false);
  assert.equal(validateJobPayload({ ...base, retrieval_code: '' }).ok, false);
  assert.equal(validateJobPayload({ ...base, retrieval_code: '7' }).ok, false);
  assert.equal(validateJobPayload({ ...base, retrieval_code: 'abc' }).ok, false);
  assert.equal(validateJobPayload({ ...base, retrieval_code: 'code1234' }).ok, true);
  assert.equal(validateJobPayload({ ...base, retrieval_code: 'a b' }).ok, false);
  assert.equal(validateJobPayload({ ...base, retrieval_code: 'code-1234' }).ok, false);
  assert.equal(validateJobPayload({ ...base, kind: 'graded' }).ok, false);
  assert.equal(validateJobPayload({ ...base, versions: { webapp: 'x' } }).ok, false);
});

await test('job calls: submit posts to /jobs; status maps 403 to forbidden', async () => {
  const seen = [];
  const mockSubmit = async (url, opts) => {
    seen.push({ url, body: JSON.parse(opts.body) });
    return { ok: true, status: 201, json: async () => ({ job_id: 'j1', created_at: 't0', expires_at: 't1' }) };
  };
  const out = await submitJob('https://g.example.workers.dev/', buildJobPayload(jobState), mockSubmit);
  assert.equal(out.job_id, 'j1');
  assert.equal(seen[0].url, 'https://g.example.workers.dev/jobs');
  const mock403 = async () => ({ ok: false, status: 403, json: async () => ({ error: 'forbidden' }) });
  const st = await fetchJobStatus('https://g.example.workers.dev',
    { pkg: 'hw3 v2', retrieval_code: 'wrong' }, mock403);
  assert.equal(st.status, 'forbidden');
  assert.equal(st.data, null);
});

await test('job calls: finalize sends NO youtube fields; an already-final 409 is success (2.6.19)', async () => {
  const seen = [];
  const mockOk = async (url, opts) => {
    seen.push({ url, body: JSON.parse(opts.body) });
    return { ok: true, status: 200, json: async () => ({ ok: true, receipt: 'r1' }) };
  };
  // Even a payload still carrying youtube fields must not send
  // them: finalize marks the job final and binds nothing.
  const payload = { pkg: 'hw3 v2', retrieval_code: 'code1234' };
  payload['youtube' + '_token'] = 'tok';
  payload.youtube_video_id = 'abc123XYZ_-';
  payload.youtube_checked_at = '2026-11-09T10:00:00.000Z';
  const out = await finalizeJob('https://g.example.workers.dev', payload, mockOk);
  assert.equal(out.ok, true);
  assert.equal(seen[0].url, 'https://g.example.workers.dev/jobs/finalize');
  assert.deepEqual(Object.keys(seen[0].body).sort(), ['pkg', 'retrieval_code'],
    'the finalize body is exactly pkg + retrieval_code');
  assert.ok(!('youtube_token' in seen[0].body) &&
    !('youtube_video_id' in seen[0].body) &&
    !('youtube_checked_at' in seen[0].body), 'no youtube fields are sent');
  // An already-final response for this same job is success: the
  // caller proceeds to fetch status and package.
  const mockAlready = async () => ({ ok: false, status: 409, json: async () => ({ error: 'job already final' }) });
  const again = await finalizeJob('https://g.example.workers.dev',
    { pkg: 'hw3 v2', retrieval_code: 'code1234' }, mockAlready);
  assert.equal(again.ok, true);
  assert.equal(again.already_final, true);
  // A different 409 — another job already final for the recording
  // — still throws with the Worker's message.
  const mock409 = async () => ({ ok: false, status: 409, json: async () => ({ error: 'a final job already exists for this recording' }) });
  await assert.rejects(() => finalizeJob('https://g.example.workers.dev', payload, mock409),
    /a final job already exists/);
});

/* ---------------- Chromaprint base64 + duplicate responses (2.6.0) ---------------- */

await test('fingerprint base64: raw items round-trip, little-endian', () => {
  const items = new Uint32Array([0, 1, 0x12345678, 0xffffffff, 0x00000080]);
  const encoded = encodeRawFingerprint(items);
  assert.deepEqual(decodeRawFingerprint(encoded), items);
  // Independent check: the bytes are little-endian uint32.
  const rawBytes = Buffer.from(encoded, 'base64');
  assert.equal(rawBytes.length, 20);
  assert.equal(rawBytes.readUInt32LE(8), 0x12345678);
  assert.equal(rawBytes.readUInt32LE(12), 0xffffffff);
  // A single item encodes with padding.
  assert.equal(encodeRawFingerprint(new Uint32Array([1])), 'AQAAAA==');
  assert.deepEqual(decodeRawFingerprint('AQAAAA=='), new Uint32Array([1]));
});

await test('fingerprint base64: invalid input decodes to null', () => {
  assert.equal(decodeRawFingerprint(''), null);
  assert.equal(decodeRawFingerprint(null), null);
  assert.equal(decodeRawFingerprint('AQ=='), null); // one byte: not whole uint32 items
  assert.equal(decodeRawFingerprint('####'), null);
  assert.equal(decodeRawFingerprint('AQAA'), null); // 3 bytes: not divisible by 4
  assert.equal(decodeRawFingerprint('AQAAAA==AQAA'), null); // padding mid-string
  assert.equal(encodeRawFingerprint(new Uint32Array([])), '');
});

await test('job payload: chromaprint included when present, omitted when null', () => {
  const fp = encodeRawFingerprint(new Uint32Array([1, 2, 3]));
  const withFp = buildJobPayload({ ...jobState, chromaprint: fp });
  assert.equal(withFp.chromaprint, fp);
  assert.equal(validateJobPayload(withFp).ok, true);
  const withoutFp = buildJobPayload({ ...jobState, chromaprint: null });
  assert.ok(!('chromaprint' in withoutFp));
  const unset = buildJobPayload(jobState);
  assert.ok(!('chromaprint' in unset));
  assert.equal(validateJobPayload(unset).ok, true);
});

const readyDupBundle = {
  v: 2, job_id: 'job-old', audio_sha256: SHA_A, transcript_sha256: SHA_B,
  pkg: 'hw3 v2', pkg_content_sha256: SHA_C, completeness: 4, accuracy: 3,
  critique: 'Good.', critique_sha256: SHA_C, youtube_video_sha256: 'e'.repeat(64),
  t: '2026-11-10T10:00:00.000Z', receipt: 'r-old',
};
const practiceDupBundle = { ...readyDupBundle, youtube_video_sha256: 'none' };

await test('job calls: submit returns a duplicate response instead of throwing', async () => {
  const queued = async () => ({
    ok: true, status: 200, json: async () => ({
      duplicate: true, job_id: 'job-old', created_at: 't0', expires_at: 't1',
      pkg: 'hw3 v2', status: 'queued', queue_ahead: 2, alias_created: true,
    }),
  });
  const out = await submitJob('https://g.example.workers.dev', buildJobPayload(jobState), queued);
  assert.equal(out.duplicate, true);
  assert.equal(out.job_id, 'job-old');
  assert.equal(out.queue_ahead, 2);
  const ready = async () => ({
    ok: true, status: 200, json: async () => ({
      duplicate: true, job_id: 'job-old', created_at: 't0', expires_at: 't1',
      pkg: 'hw3 v2', status: 'ready', result: readyDupBundle, alias_created: true,
    }),
  });
  const outReady = await submitJob('https://g.example.workers.dev', buildJobPayload(jobState), ready);
  assert.equal(outReady.status, 'ready');
  assert.deepEqual(outReady.result, readyDupBundle);
});

await test('duplicate entry: alias stored under the submitted code; kind follows the existing job', () => {
  const submitted = {
    pkg: 'hw3 v2', course: 'CHE3025', asg: 'HW3',
    retrieval_code: 'newcode99', kind: 'practice',
    youtube_link: '', youtube_title: '', youtube_checked_at: '',
  };
  const finalSubmitted = {
    ...submitted, kind: 'final',
    youtube_link: 'https://www.youtube.com/watch?v=abc123XYZ_-',
    youtube_title: 'T', youtube_checked_at: '2026-11-10T09:00:00.000Z',
  };
  // Ready final job: the entry is final, under the submitted code.
  const finalEntry = duplicateJobEntry({
    duplicate: true, job_id: 'job-old', created_at: 't0', expires_at: 't1',
    pkg: 'hw3 v2', status: 'ready', result: readyDupBundle, alias_created: true,
  }, finalSubmitted);
  assert.equal(finalEntry.retrieval_code, 'newcode99');
  assert.equal(finalEntry.kind, 'final');
  assert.equal(finalEntry.youtube_link, 'https://www.youtube.com/watch?v=abc123XYZ_-');
  assert.equal(finalEntry.youtube_title, 'T');
  assert.equal(finalEntry.created_at, 't0');
  // Ready practice job submitted as final: the existing job is
  // practice, so the entry is practice and keeps no link.
  const practiceEntry = duplicateJobEntry({
    duplicate: true, job_id: 'job-old', created_at: 't0', expires_at: 't1',
    pkg: 'hw3 v2', status: 'ready', result: practiceDupBundle, alias_created: true,
  }, finalSubmitted);
  assert.equal(practiceEntry.kind, 'practice');
  assert.equal(practiceEntry.youtube_link, '');
  // Queued job: no result yet, so the submitted kind stands.
  const queuedEntry = duplicateJobEntry({
    duplicate: true, job_id: 'job-old', created_at: 't0', expires_at: 't1',
    pkg: 'hw3 v2', status: 'queued', queue_ahead: 1, alias_created: true,
  }, submitted);
  assert.equal(queuedEntry.kind, 'practice');
  // Stored under the submitted code in localStorage.
  const store = fakeStorage();
  addJobEntry(finalEntry, store);
  const entries = loadJobEntries(store);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].retrieval_code, 'newcode99');
  assert.equal(entries[0].kind, 'final');
});

await test('duplicate entry: alias_created false stores nothing', () => {
  const submitted = {
    pkg: 'hw3 v2', course: 'CHE3025', asg: 'HW3',
    retrieval_code: 'takencode1', kind: 'practice',
    youtube_link: '', youtube_title: '', youtube_checked_at: '',
  };
  assert.equal(duplicateJobEntry({
    duplicate: true, job_id: 'job-old', created_at: 't0', expires_at: 't1',
    pkg: 'hw3 v2', status: 'ready', result: readyDupBundle, alias_created: false,
  }, submitted), null);
  assert.equal(duplicateJobEntry(null, submitted), null);
  assert.equal(duplicateJobEntry({ duplicate: false }, submitted), null);
  assert.equal(kindFromResultBundle(readyDupBundle), 'final');
  assert.equal(kindFromResultBundle(practiceDupBundle), 'practice');
  assert.equal(kindFromResultBundle(null), 'practice');
});

await test('duplicate entry: the alias entry carries the existing job_id (2.5.3)', () => {
  const submitted = {
    pkg: 'hw3 v2', course: 'CHE3025', asg: 'HW3',
    retrieval_code: 'newcode99', kind: 'final',
    youtube_link: 'https://www.youtube.com/watch?v=abc123XYZ_-',
    youtube_title: 'T', youtube_checked_at: '2026-11-10T09:00:00.000Z',
  };
  const entry = duplicateJobEntry({
    duplicate: true, job_id: 'job-old', created_at: 't0', expires_at: 't1',
    pkg: 'hw3 v2', status: 'ready', result: readyDupBundle, alias_created: true,
  }, submitted);
  assert.equal(entry.job_id, 'job-old');
});

/* ---------------- one row per underlying job (2.5.3) ---------------- */

const collapseEntry = (code, over = {}) => ({
  pkg: 'hw3 v2', course: 'CHE3025', asg: 'HW3', retrieval_code: code,
  kind: 'final', youtube_link: '', youtube_title: '', youtube_checked_at: '',
  created_at: '2026-11-10T00:00:00.000Z', expires_at: 't1', ...over,
});

await test('collapse: three codes for one job keep one entry — the one carrying the link', () => {
  const items = [
    { entry: collapseEntry('codeaaa1'), jobId: 'job-1' },
    { entry: collapseEntry('codebbb2', {
        youtube_link: 'https://www.youtube.com/watch?v=abc123XYZ_-',
        youtube_title: 'T', youtube_checked_at: '2026-11-10T09:00:00.000Z',
        created_at: '2026-11-10T01:00:00.000Z' }), jobId: 'job-1' },
    { entry: collapseEntry('codeccc3', { created_at: '2026-11-10T02:00:00.000Z' }), jobId: 'job-1' },
  ];
  const kept = collapseSameJobEntries(items);
  assert.equal(kept.length, 1);
  assert.equal(kept[0].entry.retrieval_code, 'codebbb2');
  assert.equal(kept[0].entry.job_id, 'job-1');
  assert.equal(kept[0].entry.youtube_link, 'https://www.youtube.com/watch?v=abc123XYZ_-');
});

await test('collapse: link fields merge onto the survivor from a dropped entry', () => {
  // The linked entry wins on score even though its stored kind is
  // a stale 'practice'; the dropped entry is the final one, so the
  // survivor must gain kind 'final' from it (and keeps its link).
  const items = [
    { entry: collapseEntry('codeaaa1'), jobId: 'job-1' },
    { entry: collapseEntry('codebbb2', { kind: 'practice',
        youtube_link: 'https://www.youtube.com/watch?v=abc123XYZ_-',
        youtube_title: 'T', youtube_checked_at: '2026-11-10T09:00:00.000Z',
        created_at: '2026-11-10T01:00:00.000Z' }), jobId: 'job-1' },
  ];
  const kept = collapseSameJobEntries(items);
  assert.equal(kept.length, 1);
  assert.equal(kept[0].entry.youtube_link, 'https://www.youtube.com/watch?v=abc123XYZ_-');
  assert.equal(kept[0].entry.youtube_title, 'T');
  assert.equal(kept[0].entry.kind, 'final');
});

await test('collapse: distinct jobs and unknown-job entries are all kept', () => {
  const items = [
    { entry: collapseEntry('codeaaa1'), jobId: 'job-1' },
    { entry: collapseEntry('codebbb2'), jobId: 'job-2' },
    { entry: collapseEntry('codeccc3'), jobId: null },
    { entry: collapseEntry('codeddd4'), jobId: null },
  ];
  const kept = collapseSameJobEntries(items);
  assert.equal(kept.length, 4);
  // A lone entry with a known job gains job_id for later visits.
  assert.equal(kept[0].entry.job_id, 'job-1');
  assert.equal(kept[1].entry.job_id, 'job-2');
});

await test('wiring: one ZIP button per job — collapse in render, review replaces the button', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('collapseSameJobEntries(live)'),
    'renderJobsOnce collapses same-job entries before rendering');
  assert.ok(main.includes('job_id: res.job_id'),
    'a newly sent job entry carries its job_id');
  assert.ok(main.includes('if (!reviewOpen && parseYouTubeVideoId(rowLinkDraft(entry)))'),
    'the Generate ZIP button is rendered while the field holds a readable link, with no review open (2.6.18)');
  assert.ok(main.includes("'Close review'"),
    'the open review panel can be closed, restoring the Review button');
  assert.ok(!main.includes('manualBtn') && !main.includes('clearManualRowIfListed'),
    'no manual-retrieval row exists to duplicate a listed job (2.6.11)');
});

await test('wiring: fingerprint computed after normalisation; duplicate handled in the submit path', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes("import { computeFingerprint } from './fingerprint.js'"),
    'main imports the fingerprint module');
  assert.ok(main.includes('refreshFingerprint()'), 'fingerprint computed after normalisation');
  assert.ok(main.includes('chromaprint,'), 'payload carries the fingerprint');
  assert.ok(main.includes('if (res.duplicate)'), 'submit branches on a duplicate response');
  assert.ok(main.includes('duplicateJobEntry(res,'), 'alias entry built from the duplicate response');
  assert.ok(main.includes('duplicateStatusText(res)'), 'grade/queue shown when no alias was created');
  assert.ok(main.includes('kindFromResultBundle(res.data.result)'),
    'ready bundle corrects an alias entry kind');
  // No 'dedup' text anywhere in the page wiring (the one former
  // occurrence was the duration-stats comment, removed in 2.6.18
  // with the duration reporting itself).
  const dedupLines = main.split('\n').filter((l) => /dedup/i.test(l));
  assert.deepEqual(dedupLines.map((l) => l.trim()), []);
  const jobs = readFileSync(new URL('../js/jobs.js', import.meta.url), 'utf8');
  assert.ok(jobs.includes('if (data && data.duplicate) return data;'),
    'submitJob returns a duplicate response instead of throwing');
});

await test('wiring: ZIP verification uses the link kept with the entry, from its row (2.6.16)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes("const link = entry.youtube_link || '';"),
    'both ZIP verifications read the entry link only — no page-level field remains');
  assert.ok(!main.includes("$('ytLink')"), 'no step-6 link field is read anywhere');
  assert.ok(main.includes('Keep a re-entered YouTube link with the job'),
    're-entered link is kept with the stored entry');
  assert.ok(main.includes('pending ? pending.videoId : parseYouTubeVideoId(link)'),
    'with a checked video pending the packaged video is the one the click checked');
  assert.ok(!main.includes('bundleBoundVideoSha'),
    'no bundle bound-video comparison remains anywhere in the page (2.6.19)');
  assert.ok(!main.includes('youtube_video_sha256'),
    'the page flow never consults the bundle video hash (2.6.19)');
});
await test('wiring: conversion panel and step-6 link field removed; finalise runs from the row (2.6.16)', () => {
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(!index.includes('id="finPanel"'), 'conversion panel removed');
  assert.ok(!index.includes('id="finJobSel"'), 'graded-job picker removed');
  assert.ok(!index.includes('id="ytLink"'), 'step 6 link field removed');
  assert.ok(!index.includes('kindPractice'), 'no practice radio');
  assert.ok(!index.includes('kindFinal'), 'no final radio');
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('finalizeJob('), 'page calls finalize');
  assert.ok(main.includes('await finalizeJob(cfg.worker, {'),
    'the review confirm finalises the job (2.6.19)');
  assert.ok(!main.includes('review.pending.mode') && !main.includes('pending.mode'),
    'no bind/supersede mode remains in the review flow (2.6.19)');
  assert.ok(!main.includes('youtube_token') && !main.includes('youtube_video_id'),
    'the page sends no youtube fields at finalize (2.6.19)');
  assert.ok(main.includes('await downloadSubmissionZip(entry, bundle, btn,'),
    'Generate ZIP runs the check and prepares the review, binding nothing');
  assert.ok(!main.includes('refreshFinPanel'), 'no conversion panel refresh remains');
  assert.ok(!main.includes('finCheck'), 'no conversion-panel check state remains');
  assert.ok(main.includes("kind: 'practice',"), 'sending always sends without a link');
});
/* ---------------- localStorage job entries ---------------- */

function fakeStorage() {
  const map = new Map();
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, String(v)),
    removeItem: (k) => map.delete(k),
  };
}

await test('job entries: add replaces same code, remove works, expiry prunes', () => {
  const store = fakeStorage();
  const e1 = {
    pkg: 'hw3 v2', course: 'CHE3025', asg: 'HW3',
    retrieval_code: 'code1234', kind: 'practice', youtube_link: '',
    created_at: '2026-11-09T10:00:00.000Z', expires_at: '2026-11-11T10:00:00.000Z',
  };
  addJobEntry(e1, store);
  addJobEntry({ ...e1, kind: 'final' }, store); // same (pkg, code) → replaced
  let entries = loadJobEntries(store);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].kind, 'final');
  addJobEntry({ ...e1, retrieval_code: 'other42' }, store);
  assert.equal(loadJobEntries(store).length, 2);
  removeJobEntry('hw3 v2', 'other42', store);
  entries = loadJobEntries(store);
  assert.equal(entries.length, 1);
  const now = Date.parse('2026-11-10T10:00:00.000Z');
  assert.equal(pruneExpiredEntries(entries, now).length, 1);
  assert.equal(pruneExpiredEntries(entries, Date.parse('2026-11-12T10:00:00.000Z')).length, 0);
  // Corrupt storage reads as an empty list.
  store.setItem('hw-signing.jobs.v2', '{oops');
  assert.deepEqual(loadJobEntries(store), []);
});

/* ---------------- push key conversion ---------------- */

await test('push: VAPID base64url round-trips', () => {
  const bytes = new Uint8Array([0, 1, 2, 250, 251, 252, 65, 66, 67]);
  const encoded = uint8ArrayToUrlBase64(bytes);
  assert.ok(!/[+/=]/.test(encoded));
  assert.deepEqual(urlBase64ToUint8Array(encoded), bytes);
  // A 65-byte uncompressed P-256 point encodes to 87 chars.
  const key = new Uint8Array(65).map((_, i) => i % 256);
  assert.equal(uint8ArrayToUrlBase64(key).length, 87);
  assert.deepEqual(urlBase64ToUint8Array(uint8ArrayToUrlBase64(key)), key);
});

/* ---------------- wiring guards ---------------- */

await test('wiring: identifier confirmation gates the job submit button', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('cfg.ph && transcriptionComplete'),
    'submit gating needs the package and a finished transcription');
  assert.ok(main.includes("cacheGet(audioSha, VERSIONS.model, VERSIONS.glossary)"),
    'cache is checked after fingerprinting');
  assert.ok(main.includes('transcript restored from this computer') ||
            main.includes('Transcript restored from this computer'),
    'cache hit is announced');
});

await test('wiring: errors are shown beside the control that was used', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('function showError(message, err, anchor)'),
    'showError takes the control whose action failed');
  assert.ok(main.includes("shown.scrollIntoView({ block: 'nearest' })"),
    'the error is scrolled into view where it lands');
  for (const a of ["$('loadBtn')", "$('mediaFile')", 'restoreBtn',
                   "$('runBtn')", "$('submitJobBtn')",
                   'generateZipForRow(entry, bundle, zipBtn)']) {
    assert.ok(main.includes(a), 'anchored error call site: ' + a);
  }
});

await test('wiring: the section-7 critique keeps its line breaks', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes("crit.style.whiteSpace = 'pre-line'"),
    'numbered critique points appear on separate lines in the job list');
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(index.includes('<title>Graded feedback on practice recordings for Canvas submission</title>'),
    'page title is the current one');
  assert.ok(index.includes('The recording never leaves this page'),
    'page description is the current one');
});

await test('wiring: the model loads automatically on page open (2.6.4)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('startModelLoad();'),
    'page init starts the model load without a click');
});

await test('wiring: no model section; the load is a progress bar, then nothing (2.6.20)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(!index.includes('The transcription model'),
    'the model section heading is gone');
  assert.ok(!index.includes('loads by itself') && !index.includes('670 MB'),
    'no text about the model, its size or its storage remains');
  assert.ok(index.includes('id="loadProg"'),
    'the loading progress bar remains');
  assert.ok(!main.includes('Model loaded.'),
    'a finished load leaves no line behind');
  assert.ok(main.includes("$('loadBtn').textContent = 'Retry';"),
    'a failed load offers a retry beside the failure line');
  assert.ok(main.includes("'Model did not load. Check the connection and try again.'"),
    'a failed load states one line beside the retry');
  assert.ok(index.includes('<h2>1. The recording file</h2>')
    && index.includes('<h2>6. Your grading jobs</h2>'),
    'the remaining sections are renumbered 1 to 6');
  assert.ok(index.includes('after your removals in step 2')
    && index.includes('to the list in step 2'),
    'cross-references point at the renumbered removal step');
});

await test('wiring: the page carries no unnecessary explanations (2.6.20)', () => {
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(!index.includes('keep the\n  recording file') && !index.includes('you need it for the Canvas submission ZIP'),
    'the intro no longer claims the recording file is needed for the ZIP');
  assert.ok(!index.includes('Sending takes no YouTube link'),
    'the sending section has no explanatory paragraph');
  assert.ok(!index.includes('An ungraded job is kept for 7 days'),
    'the jobs section has no retention preamble');
  assert.ok(!index.includes('how much of the question your explanation'),
    'the jobs section has no completeness/accuracy preamble');
  assert.ok(!index.includes('Runs 25 s at a time'),
    'the transcription chunking note is gone');
  assert.ok(!index.includes('never\n  transcribed twice') && !index.includes('never transcribed twice'),
    'the recordings cache note is gone');
  assert.ok(!main.includes('kept for 180 days'),
    'the send confirmation no longer restates retention');
});

await test('wiring: no separate download button for the extracted audio', () => {
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(!index.includes('audioDl') && !main.includes('audioDl'),
    'the extracted audio is kept automatically and goes into the ZIP; no manual download');
});

await test('wiring: page and worker carry the v2 version strings', () => {
  assert.equal(VERSIONS.webapp, 'hw-signing-webapp 2.6.20');
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(index.includes('id="suPh"'), 'setup form has the ph field');
  assert.ok(index.includes('id="jobsBox"'), 'jobs list section present');
  const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');
  assert.ok(sw.includes("addEventListener('push'"), 'service worker handles push');
  assert.ok(sw.includes("addEventListener('notificationclick'"), 'service worker handles clicks');
});

await test('wiring: status expiry is stored back into the job entry (2.4.1)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('entry.expires_at = res.data.expires_at'),
    'renderJobs keeps the stored expiry in step with the Worker');
  assert.ok(!main.includes('pruneExpiredEntries(loadJobEntries()'),
    'renderJobs must not prune on the stored expiry before asking the Worker: ' +
    'a pre-2.4.1 entry carries creation + 48 h while its job may still be live');
  assert.ok(main.includes("res.status === 'expired'"),
    'renderJobs drops an entry when the Worker reports the job expired');
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(!index.includes('id="recoveryLine"'),
    'no recovery-code line remains in step 6 (2.6.11)');
});

await test('wiring: jobs refresh never rebuilds the list under the student (2.4.5)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('Promise.all(entries.map'),
    'statuses are fetched in parallel, before the list is touched');
  assert.ok(main.includes('renderJobsPromise'),
    'renders are serialised: callers share one in-flight render');
  assert.ok(main.includes('zipReviews.size'),
    'the 5-second poll pauses while a ZIP review panel is open');
  assert.ok(main.includes('zipBusy'),
    'the 5-second poll pauses while a ZIP verification or download runs');
  assert.ok(!main.includes('holder.textContent'),
    'no row is rendered twice (stale state, then fresh state) any more');
  assert.ok((main.match(/zipReviews\.delete/g) || []).length >= 4,
    'a ZIP review entry is deleted on download, on removing its job, ' +
    'on the job expiring, and in the same-job collapse — ' +
    'an orphaned entry would pause the poll for good');
  assert.ok(!main.includes('renderJobRow(box, entry'),
    'no second (manual) row is rendered outside the jobs list (2.6.11)');
});

await test('wiring: ZIP steps show live status and a completion line (2.4.6)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(main.includes('buildZipAsync'),
    'the ZIP is built by the sliced async builder, not the blocking one');
  assert.ok(!main.includes('buildZip('),
    'no call site still uses the synchronous ZIP builder');
  assert.ok(main.includes("document.createElement('progress')"),
    'a native progress element is created for the ZIP steps');
  assert.ok(main.includes('Verifying the recording and the transcript'),
    'the verification step announces itself beside the ZIP button');
  assert.ok(main.includes('Building the submission ZIP… '),
    'the build step reports its percentage beside the download button');
  assert.ok(main.includes('status.box.remove()'),
    'the progress element is removed when a step completes');
  assert.ok(main.includes("$('zipDone')") && html.includes('id="zipDone"'),
    'a completion line element sits above the jobs list and is filled in');
  assert.ok(main.includes('has been downloaded. Upload that file to Canvas.'),
    'the completion line names the downloaded file and the next action');
});

/* ---------------- duration bands + bundle verification (2.4.0) ---------------- */

await test('duration: the length comparison is removed (2.6.18)', () => {
  const jobs = readFileSync(new URL('../js/jobs.js', import.meta.url), 'utf8');
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(!jobs.includes('classifyDuration'), 'jobs.js no longer classifies durations');
  assert.ok(!jobs.includes('reportDurationStat'), 'jobs.js no longer reports duration statistics');
  assert.ok(!main.includes('classifyDuration') && !main.includes('reportDurationOnce'),
    'the page never compares or reports lengths');
});

await test('bundle verification: exact contents pass; each tamper fails by name', () => {
  const bundle = {
    audio_sha256: SHA_A, transcript_sha256: SHA_B, critique_sha256: SHA_C,
  };
  const good = { wavSha256: SHA_A, transcriptSha256: SHA_B, critiqueSha256: SHA_C };
  assert.deepEqual(verifyBundleContents(bundle, good), []);
  assert.deepEqual(verifyBundleContents(bundle, { ...good, wavSha256: SHA_B }), ['audio']);
  assert.deepEqual(verifyBundleContents(bundle, { ...good, transcriptSha256: SHA_A }), ['transcript']);
  assert.deepEqual(verifyBundleContents(bundle, { ...good, critiqueSha256: SHA_A }), ['critique']);
  assert.equal(verifyBundleContents(null, good).length, 3);
});

await test('first words: opening words of the corrected chunks, whitespace collapsed', () => {
  const cached = [
    { start_s: 0, end_s: 25, raw: 'x', corrected: '  The reflux ratio   is defined as' },
    { start_s: 25, end_s: 50, raw: 'y', corrected: 'the ratio of liquid returned to product' },
  ];
  assert.equal(recordingFirstWords(cached),
    'The reflux ratio is defined as the ratio of liquid returned to');
  assert.equal(recordingFirstWords(cached, 4), 'The reflux ratio is');
  assert.equal(recordingFirstWords([]), '');
  assert.equal(recordingFirstWords(null), '');
});

await test('wiring: preview elements present; the check sits at the click, inside the review (2.6.18)', () => {
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(index.includes('id="ytPreviewArea"'), 'index has the fixed preview area');
  assert.ok(index.includes('Hover a YouTube link to play it here'),
    'the preview area carries its idle placeholder text');
  for (const id of ['ytConfirmRow', 'ytConfirmChk',
    'finConfirmRow', 'finConfirmChk', 'ytCheckBtn', 'finCheckBtn']) {
    assert.ok(!index.includes('id="' + id + '"'),
      'index no longer has ' + id);
  }
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(!main.includes('Link checks out'), 'no passed-check cell message remains');
  assert.ok(main.includes('previewPlayer.destroy()'),
    'clearing the player destroys it — the window actually clears');
  assert.ok(main.includes('previewOnLinkCommit(key, nowParsed);'),
    'editing the playing row’s link to a new video updates the player to it (2.6.20)');
  assert.ok(main.includes('previewMaybeClear(key, null)'),
    'editing the playing row’s link to nothing readable clears the player with it');
  assert.ok(main.includes('previewMaybeClear(key, null)'),
    'clearing the playing row’s link clears the player with it');
  assert.ok(main.includes("dlBtn.textContent = 'Download submission ZIP';"),
    'the review confirm label is always "Download submission ZIP" (2.6.19)');
  assert.ok(!main.includes('Bind this video'),
    'no bind label remains (2.6.19)');
  assert.ok(main.includes('This link is also on your '),
    'the review warns when the link is also on another row');
  assert.ok(!main.includes('currently a different '),
    'the review carries no supersede notice (2.6.19)');
  assert.ok(!/supersede/i.test(main.replace('superseded by a newer recording', '')),
    'no supersede path or text remains in the page flow (2.6.19)');
  assert.ok(main.includes('Transcript starts: '),
    'the review shows the opening words of the graded transcript');
  assert.ok(!main.includes(': chunks;'), 'no fallback to the on-page transcript at ZIP time');
  assert.ok(main.includes('verifyBundleContents'), 'ZIP contents verified against the bundle');
});
await test('media tier 2: MP4-family detection by name and by MIME type', () => {
  assert.equal(isMp4FamilyFile({ name: 'WIN_20261119_Pro.mp4', type: '' }), true);
  assert.equal(isMp4FamilyFile({ name: 'clip.MOV', type: '' }), true);
  assert.equal(isMp4FamilyFile({ name: 'voice.m4a', type: '' }), true);
  assert.equal(isMp4FamilyFile({ name: 'noext', type: 'video/mp4' }), true);
  assert.equal(isMp4FamilyFile({ name: 'movie.webm', type: 'video/webm' }), false);
  assert.equal(isMp4FamilyFile({ name: 'song.mp3', type: 'audio/mpeg' }), false);
  assert.equal(isMp4FamilyFile({ name: 'notes.txt', type: '' }), false);
  assert.equal(isMp4FamilyFile(null), false);
});

await test('media tier 2: gating skips cleanly when WebCodecs is absent or the file is not MP4-family', () => {
  const full = { AudioDecoder: function () {}, EncodedAudioChunk: function () {} };
  const mp4 = { name: 'a.mp4', type: '' };
  assert.equal(tier2BlockReason(full, mp4), null);
  // Safari before 26 / Firefox Android shape: no AudioDecoder at all.
  assert.match(tier2BlockReason({}, mp4), /AudioDecoder/);
  assert.match(tier2BlockReason({ AudioDecoder: function () {} }, mp4), /EncodedAudioChunk/);
  assert.match(tier2BlockReason(full, { name: 'a.webm', type: 'video/webm' }), /not an MP4/);
  assert.match(tier2BlockReason(null, mp4), /AudioDecoder/);
});

await test('media tier 2: WebCodecs codec strings from mp4box track codecs', () => {
  assert.equal(webCodecsCodecString('mp4a.40.2'), 'mp4a.40.2');
  assert.equal(webCodecsCodecString('mp4a.40.29'), 'mp4a.40.29');
  assert.equal(webCodecsCodecString('Opus'), 'opus');
  assert.equal(webCodecsCodecString('opus'), 'opus');
  assert.equal(webCodecsCodecString('ac-3'), 'ac-3');
  assert.equal(webCodecsCodecString('ec-3'), 'ec-3');
});

await test('media tier 2: decoder-specific info found anywhere in the ESD tree', () => {
  const dsi = new Uint8Array([0x11, 0x90]);
  const tree = [
    { tag: 3, descs: [{ tag: 4, descs: [{ tag: 5, data: dsi }, { tag: 6 }] }] },
  ];
  assert.equal(decoderSpecificInfo(tree), dsi);
  assert.equal(decoderSpecificInfo([{ tag: 3, descs: [{ tag: 4 }] }]), null);
  assert.equal(decoderSpecificInfo([]), null);
  assert.equal(decoderSpecificInfo(null), null);
});

await test('media tier 2: decoded planes convert to per-channel float arrays', () => {
  const planar = planesToChannels({
    format: 'f32-planar', frames: 3, channels: 2,
    planes: [new Float32Array([1, 2, 3]), new Float32Array([4, 5, 6])],
  });
  assert.deepEqual([...planar[0]], [1, 2, 3]);
  assert.deepEqual([...planar[1]], [4, 5, 6]);
  const interleaved = planesToChannels({
    format: 'f32', frames: 2, channels: 2,
    planes: [new Float32Array([1, 4, 2, 5])],
  });
  assert.deepEqual([...interleaved[0]], [1, 2]);
  assert.deepEqual([...interleaved[1]], [4, 5]);
  const s16 = planesToChannels({
    format: 's16', frames: 2, channels: 1,
    planes: [new Int16Array([16384, -32768])],
  });
  assert.deepEqual([...s16[0]], [0.5, -1]);
  const s16p = planesToChannels({
    format: 's16-planar', frames: 2, channels: 2,
    planes: [new Int16Array([0, 32767]), new Int16Array([-32768, 16384])],
  });
  assert.equal(s16p[1][0], -1);
  assert.throws(() => planesToChannels({
    format: 'u8', frames: 1, channels: 1, planes: [new Uint8Array([0])],
  }), /unsupported decoded audio format/);
});

await test('media: channelsToMono takes the per-frame mean', () => {
  const mono = channelsToMono([
    new Float32Array([1, -1, 0.5]), new Float32Array([0, 1, -0.5]),
  ]);
  assert.deepEqual([...mono], [0.5, 0, 0]);
  assert.deepEqual([...channelsToMono([new Float32Array([2, 4])])], [2, 4]);
  assert.equal(channelsToMono([]).length, 0);
});

await test('media tier 2: streaming resampler is exact at the native rate and decimates by the rate ratio', () => {
  const identity = createStreamResampler(16000);
  const src = new Float32Array([0.25, -0.5, 0.75, 1]);
  const joined = [...identity.push(src), ...identity.finish()];
  assert.deepEqual(joined, [...src]);
  const third = createStreamResampler(48000);
  const ramp = new Float32Array(9000);
  for (let i = 0; i < ramp.length; i++) ramp[i] = i / 9000;
  const out = [...third.push(ramp), ...third.finish()];
  assert.equal(out.length, 3000);
  // Interior points of a ramp are reproduced (the first and last few
  // output samples carry the kernel's edge transient, as any
  // resampler's do).
  assert.ok(Math.abs(out[1000] - 3000 / 9000) < 1e-3);
  assert.ok(Math.abs(out[2000] - 6000 / 9000) < 1e-3);
  // A constant signal resamples to exactly itself, edges included.
  const dcResampler = createStreamResampler(48000);
  const dc = [...dcResampler.push(new Float32Array(4800).fill(0.7)), ...dcResampler.finish()];
  assert.equal(dc.length, 1600);
  for (const v of dc) assert.ok(Math.abs(v - 0.7) < 1e-6);
});

await test('media tier 2: streaming resampler filters above the output band instead of aliasing it', () => {
  const sine = (freq) => {
    const n = 24000;
    const x = new Float32Array(n);
    for (let i = 0; i < n; i++) x[i] = Math.sin((2 * Math.PI * freq * i) / 48000);
    const rs = createStreamResampler(48000);
    const o = [...rs.push(x), ...rs.finish()];
    const mid = o.slice(200, o.length - 200);
    return Math.sqrt(mid.reduce((s, v) => s + v * v, 0) / mid.length);
  };
  // In-band 4 kHz passes at full amplitude (RMS of a unit sine).
  assert.ok(Math.abs(sine(4000) - Math.SQRT1_2) < 0.01);
  // 12 kHz and 10 kHz are above the 8 kHz output band: filtered out,
  // not folded back into the band.
  assert.ok(sine(12000) < 0.01);
  assert.ok(sine(10000) < 0.02);
});

await test('media tier 2: streaming resampler output does not depend on chunk sizes', () => {
  const n = 10007; // prime length, non-integer ratio at 44.1 kHz
  const src = new Float32Array(n);
  let seed = 42;
  for (let i = 0; i < n; i++) { seed = (seed * 1103515245 + 12345) % 2147483648; src[i] = seed / 2147483648 - 0.5; }
  const oneShotResampler = createStreamResampler(44100);
  const oneShot = [...oneShotResampler.push(src), ...oneShotResampler.finish()];
  const chunkedResampler = createStreamResampler(44100);
  const chunked = [];
  for (let at = 0; at < n;) {
    const take = [1, 7, 1024, 333][chunked.length % 4] || 1;
    chunked.push(...chunkedResampler.push(src.subarray(at, at + take)));
    at += take;
  }
  chunked.push(...chunkedResampler.finish());
  assert.equal(chunked.length, oneShot.length);
  assert.equal(oneShot.length, Math.ceil(n * 16000 / 44100));
  for (let i = 0; i < oneShot.length; i++) {
    assert.ok(Math.abs(chunked[i] - oneShot[i]) < 1e-6, 'sample ' + i + ' differs across chunkings');
  }
  // Interior spot check: an output landing exactly on input sample
  // 2205 of a ramp reproduces that sample's value.
  const at441 = createStreamResampler(44100);
  const ramp = new Float32Array(4410);
  for (let i = 0; i < ramp.length; i++) ramp[i] = i;
  const rampOut = [...at441.push(ramp), ...at441.finish()];
  assert.ok(Math.abs(rampOut[800] - 2205) < 0.5);
});

await test('media tier 2: demux rejects a non-MP4 buffer and accepts the module in Node', async () => {
  await assert.rejects(
    () => demuxMp4Audio(new TextEncoder().encode('not an mp4 file at all').buffer),
    /.+/);
  assert.equal(typeof demuxMp4Audio, 'function');
});

function fixtureBuffer(name) {
  const bytes = readFileSync(new URL('./fixtures/' + name, import.meta.url));
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

await test('media tier 2: demux of real MP4 fixtures (flat and fragmented)', async () => {
  for (const name of ['tone-flat.mp4', 'tone-fragmented.mp4']) {
    const d = await demuxMp4Audio(fixtureBuffer(name));
    assert.equal(d.codec, 'mp4a.40.2', name);
    assert.equal(d.sampleRate, 22050, name);
    assert.equal(d.channels, 1, name);
    assert.ok(d.description && d.description.length >= 2, name + ': AAC description present');
    assert.ok(d.samples.length >= 10, name + ': samples extracted');
    for (let i = 1; i < d.samples.length; i++) {
      assert.ok(d.samples[i].timestampUs > d.samples[i - 1].timestampUs, name + ': timestamps increase');
    }
    const last = d.samples[d.samples.length - 1];
    const endS = (last.timestampUs + last.durationUs) / 1e6;
    assert.ok(endS > 0.45 && endS < 0.6, name + ': ends near 0.5 s (got ' + endS + ')');
  }
});

// A WebCodecs stand-in: records its configuration and chunks, and
// answers each decode with one planar AudioData of a constant value.
function installFakeWebCodecs({ supported = true, framesPerChunk = 1024, value = 0.25, stall = false } = {}) {
  const saved = {
    AudioDecoder: globalThis.AudioDecoder,
    EncodedAudioChunk: globalThis.EncodedAudioChunk,
  };
  const seen = { configs: [], chunks: [], constructed: 0 };
  class FakeAudioData {
    constructor(timestamp) {
      this.format = 'f32-planar';
      this.numberOfChannels = 1;
      this.numberOfFrames = framesPerChunk;
      this.sampleRate = 22050;
      this.timestamp = timestamp;
    }
    allocationSize() { return framesPerChunk * 4; }
    copyTo(arr) { arr.fill(value); }
    close() {}
  }
  class FakeEncodedAudioChunk {
    constructor(init) { Object.assign(this, init); seen.chunks.push(init); }
  }
  class FakeAudioDecoder {
    static async isConfigSupported(config) {
      seen.configs.push(config);
      return supported ? { supported: true, config } : { supported: false };
    }
    constructor(callbacks) { this.callbacks = callbacks; seen.constructed += 1; seen.decoder = this; }
    get decodeQueueSize() { return stall ? 200 : 0; }
    configure() {}
    decode(chunk) { if (!stall) this.callbacks.output(new FakeAudioData(chunk.timestamp)); }
    async flush() {}
    close() {}
  }
  globalThis.AudioDecoder = FakeAudioDecoder;
  globalThis.EncodedAudioChunk = FakeEncodedAudioChunk;
  return {
    seen,
    restore() {
      if (saved.AudioDecoder === undefined) delete globalThis.AudioDecoder;
      else globalThis.AudioDecoder = saved.AudioDecoder;
      if (saved.EncodedAudioChunk === undefined) delete globalThis.EncodedAudioChunk;
      else globalThis.EncodedAudioChunk = saved.EncodedAudioChunk;
    },
  };
}

await test('media tier 2: decode streams demuxed samples through WebCodecs in order', async () => {
  const fake = installFakeWebCodecs();
  try {
    const chunks = [];
    const frames = await decodeMp4WithWebCodecs(fixtureBuffer('tone-fragmented.mp4'),
      (channelArrays, sampleRate, timestampUs) => chunks.push({ channelArrays, sampleRate, timestampUs }));
    const demuxed = await demuxMp4Audio(fixtureBuffer('tone-fragmented.mp4'));
    assert.equal(fake.seen.configs.length, 1);
    assert.equal(fake.seen.configs[0].codec, 'mp4a.40.2');
    assert.equal(fake.seen.configs[0].sampleRate, 22050);
    assert.ok(fake.seen.configs[0].description instanceof Uint8Array);
    assert.equal(fake.seen.chunks.length, demuxed.samples.length);
    assert.equal(fake.seen.chunks[0].timestamp, demuxed.samples[0].timestampUs);
    assert.equal(chunks.length, demuxed.samples.length);
    assert.equal(frames, demuxed.samples.length * 1024);
    for (let i = 1; i < chunks.length; i++) {
      assert.ok(chunks[i].timestampUs > chunks[i - 1].timestampUs, 'output in presentation order');
    }
    assert.equal(chunks[0].channelArrays[0][0], 0.25);
  } finally { fake.restore(); }
});

await test('media tier 2: unsupported codec config rejects before any decode', async () => {
  const fake = installFakeWebCodecs({ supported: false });
  try {
    await assert.rejects(
      () => decodeMp4WithWebCodecs(fixtureBuffer('tone-flat.mp4'), () => {}),
      /cannot decode codec mp4a\.40\.2/);
    assert.equal(fake.seen.chunks.length, 0);
  } finally { fake.restore(); }
});

await test('media tier 2: a decoder error during the backpressure wait settles the decode', async () => {
  const fake = installFakeWebCodecs({ stall: true });
  try {
    const promise = decodeMp4WithWebCodecs(fixtureBuffer('tone-flat.mp4'), () => {});
    // The stalled decoder never outputs, so the feed loop parks in
    // the backpressure wait; an error there must wake it and reject,
    // never leave the promise unsettled.
    await new Promise((r) => setTimeout(r, 20));
    fake.seen.decoder.callbacks.error(new Error('async boom'));
    await assert.rejects(promise, /async boom/);
  } finally { fake.restore(); }
});

await test('media tier 2 routing: native failure falls back, and only for MP4 files in WebCodecs browsers', async () => {
  const nativeErr = new Error('native boom');
  const savedCtx = globalThis.AudioContext;
  globalThis.AudioContext = class {
    async decodeAudioData() { throw nativeErr; }
    async close() {}
  };
  const fileOf = (name, buf) => ({ name, type: '', arrayBuffer: async () => buf.slice(0) });
  const fake = installFakeWebCodecs();
  try {
    // MP4 + WebCodecs present: tier 2 runs, callback fires, PCM returns.
    let tier2Calls = 0;
    const pcm = await decodeFileTo16kMono(
      fileOf('take.mp4', fixtureBuffer('tone-flat.mp4')), () => { tier2Calls += 1; });
    assert.equal(tier2Calls, 1);
    assert.ok(pcm instanceof Float32Array && pcm.length > 3000);
    for (const v of pcm) assert.ok(Math.abs(v - 0.25) < 0.05, 'constant input resamples to itself');
    // WebM: gate blocks tier 2; the identical native error propagates.
    await assert.rejects(
      () => decodeFileTo16kMono(fileOf('take.webm', fixtureBuffer('tone-flat.mp4'))),
      (err) => err === nativeErr);
    // No AudioDecoder (Safari < 26 shape): same unchanged failure.
    delete globalThis.AudioDecoder;
    await assert.rejects(
      () => decodeFileTo16kMono(fileOf('take.mp4', fixtureBuffer('tone-flat.mp4'))),
      (err) => err === nativeErr);
  } finally {
    fake.restore();
    if (savedCtx === undefined) delete globalThis.AudioContext;
    else globalThis.AudioContext = savedCtx;
  }
});

await test('wiring: version indicator under the title is fed by VERSIONS.webapp (2.5.1)', () => {
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(index.includes('id="appVersion"'), 'index has the version indicator element');
  const titleAt = index.indexOf('</h1>');
  const indicatorAt = index.indexOf('id="appVersion"');
  assert.ok(indicatorAt > titleAt && indicatorAt < index.indexOf('id="cfgLine"'),
    'indicator sits under the title, above the configuration line');
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes("$('appVersion').textContent = VERSIONS.webapp"),
    'indicator text is the package version string, set at page load');
});

await test('wiring: tier-2 gate loads no mp4box, and the page names the fallback beside the control (2.5.0)', () => {
  const pure = readFileSync(new URL('../js/media-mp4-pure.js', import.meta.url), 'utf8');
  assert.ok(!/^\s*import\s/m.test(pure), 'the gate module has no import statements, so gating never loads mp4box');
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('extracted another way'), 'status names the fallback while it runs');
  assert.ok(main.includes('That file could not be decoded.'), 'final failure text unchanged');
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(!index.includes('media-mp4'), 'tier 2 is not loaded on the normal path');
});

/* ---------------- fingerprint-form submissions (2.6.0) ---------------- */

// A fingerprint fixture: items, their base64 (as the status
// response carries them), the raw bytes, and the signed SHA-256.
const fpItemsFixture = new Uint32Array([0, 1, 0x12345678, 0xffffffff, 42, 7]);
const fpB64 = encodeRawFingerprint(fpItemsFixture);
const fpDecoded = decodeRawFingerprint(fpB64);
const fpBytes = new Uint8Array(
  fpDecoded.buffer, fpDecoded.byteOffset, fpDecoded.byteLength);
const FP_SHA = await sha256Hex(fpBytes);

await test('package v2: fingerprint form adds the Chromaprint SHA-256 line and names the fingerprint file', () => {
  const fpHtml = assemblePackage({ ...pkgInput, fingerprintSha256: FP_SHA });
  const v = parsePackageVerification(fpHtml).verification;
  assert.equal(v['Chromaprint SHA-256'], FP_SHA);
  assert.equal(v['Audio file'], 'submission-fingerprint.bin');
  assert.equal(v['Audio file'], FINGERPRINT_FILE_NAME);
  const iAudio = fpHtml.indexOf('<dt>Audio SHA-256</dt>');
  const iFp = fpHtml.indexOf('<dt>Chromaprint SHA-256</dt>');
  const iTr = fpHtml.indexOf('<dt>Transcript SHA-256</dt>');
  assert.ok(iAudio >= 0 && iFp > iAudio && iTr > iFp,
    'the line sits immediately after Audio SHA-256');
  // Everything else is identical to the WAV-form assembly: removing
  // the one added line and restoring the file name recovers it.
  const stripped = fpHtml
    .replace('<dt>Chromaprint SHA-256</dt><dd>' + FP_SHA + '</dd>\n', '')
    .replace('<dt>Audio file</dt><dd>' + FINGERPRINT_FILE_NAME + '</dd>',
      '<dt>Audio file</dt><dd>submission-audio.wav</dd>');
  assert.equal(stripped, html);
});

await test('package v2: no fingerprint hash, "none", or a malformed value leaves the assembly unchanged', () => {
  assert.equal(assemblePackage(pkgInput), html);
  assert.equal(assemblePackage({ ...pkgInput, fingerprintSha256: 'none' }), html);
  assert.equal(assemblePackage({ ...pkgInput, fingerprintSha256: 'zz' }), html);
  assert.ok(!('Chromaprint SHA-256' in parsePackageVerification(html).verification));
});

await test('chunksFromCanonical: round-trips canonicalTranscript output', () => {
  const chunks = [
    { start: 0, text: 'Hello world this is the feed' },
    { start: 25.7, text: 'a later chunk' },
    { start: 4520, text: 'much later chunk about reflux' },
  ];
  const canon = canonicalTranscript(chunks);
  const parsed = chunksFromCanonical(canon);
  assert.deepEqual(parsed, [
    { start: 0, text: 'Hello world this is the feed' },
    { start: 25, text: 'a later chunk' },
    { start: 4520, text: 'much later chunk about reflux' },
  ]);
  assert.equal(canonicalTranscript(parsed), canon);
  // A line with no marker is kept, at start 0 — never dropped.
  assert.deepEqual(chunksFromCanonical('no marker on this line'),
    [{ start: 0, text: 'no marker on this line' }]);
  assert.deepEqual(chunksFromCanonical(''), []);
});

await test('fingerprint form decision: a real signed sha takes the fingerprint form; "none" and pre-2.7.0 bundles do not', () => {
  assert.equal(bundleChromaprintSha({ chromaprint_sha256: FP_SHA }), FP_SHA);
  assert.equal(bundleChromaprintSha({ chromaprint_sha256: 'none' }), null);
  assert.equal(bundleChromaprintSha({ ...bundle }), null,
    'a pre-2.7.0 bundle has no chromaprint_sha256 field');
  assert.equal(bundleChromaprintSha({ chromaprint_sha256: 'A'.repeat(64) }), null,
    'uppercase is not the hex form the Worker signs');
  assert.equal(bundleChromaprintSha(null), null);
});

await test('fingerprint verification: exact contents pass; a tampered fingerprint fails by name', async () => {
  const fpBundle = {
    chromaprint_sha256: FP_SHA, transcript_sha256: SHA_B,
    critique_sha256: SHA_C,
  };
  const good = {
    fingerprintSha256: FP_SHA, transcriptSha256: SHA_B,
    critiqueSha256: SHA_C,
  };
  assert.deepEqual(verifyFingerprintContents(fpBundle, good), []);
  // The tamper the page refuses on: bytes that do not hash to the
  // signed chromaprint_sha256.
  const tampered = new Uint8Array(fpBytes);
  tampered[0] ^= 0xff;
  const tamperedSha = await sha256Hex(tampered);
  assert.notEqual(tamperedSha, FP_SHA);
  assert.deepEqual(
    verifyFingerprintContents(fpBundle, { ...good, fingerprintSha256: tamperedSha }),
    ['fingerprint']);
  assert.deepEqual(
    verifyFingerprintContents(fpBundle, { ...good, transcriptSha256: SHA_A }),
    ['transcript']);
  assert.deepEqual(
    verifyFingerprintContents(fpBundle, { ...good, critiqueSha256: SHA_A }),
    ['critique']);
  assert.equal(verifyFingerprintContents(null, good).length, 3);
});

await test('fingerprint ZIP: entries are exactly the HTML and the fingerprint bin; the bin hashes to the signed sha', async () => {
  const fpHtml = assemblePackage({
    ...pkgInput, audioFileName: FINGERPRINT_FILE_NAME,
    fingerprintSha256: FP_SHA,
  });
  const zip = buildZipBytes([
    { name: 'submission.html', data: new TextEncoder().encode(fpHtml) },
    { name: FINGERPRINT_FILE_NAME, data: fpBytes },
  ]);
  const { entries } = unzipStored(zip);
  assert.deepEqual(entries.map((e) => e.name),
    ['submission.html', 'submission-fingerprint.bin']);
  assert.deepEqual(entries[1].data, fpBytes);
  assert.equal(await sha256Hex(entries[1].data), FP_SHA);
  assert.ok(!entries.some((e) => e.name.endsWith('.wav')), 'no WAV entry');
});

await test('fresh computer: a retrieved job builds the fingerprint ZIP once the correct YouTube link is supplied; a wrong link refuses', async () => {
  const videoId = 'abc123XYZ_-';
  const chunks = [
    { start: 0, text: 'Hello world this is the feed' },
    { start: 25, text: 'explains the reflux ratio' },
  ];
  const canon = canonicalTranscript(chunks);
  const retrievedBundle = {
    ...bundle,
    transcript_sha256: await sha256Hex(canon),
    critique_sha256: await sha256Hex(bundle.critique),
    youtube_video_sha256: await sha256Hex(videoId),
    chromaprint_sha256: FP_SHA,
  };
  assert.equal(bundleChromaprintSha(retrievedBundle), FP_SHA,
    'the retrieved bundle takes the fingerprint form');
  // No local entry and no local audio: the transcript comes from
  // the status response's text, parsed back into chunks, and its
  // canonical hash must equal the signed one.
  const parsedChunks = chunksFromCanonical(canon);
  assert.equal(await sha256Hex(canonicalTranscript(parsedChunks)),
    retrievedBundle.transcript_sha256);
  // The fingerprint bytes decode from the status response's base64
  // and hash to the signed chromaprint_sha256.
  const items = decodeRawFingerprint(fpB64);
  const bytes = new Uint8Array(items.buffer, items.byteOffset, items.byteLength);
  assert.equal(await sha256Hex(bytes), retrievedBundle.chromaprint_sha256);
  assert.deepEqual(verifyFingerprintContents(retrievedBundle, {
    fingerprintSha256: await sha256Hex(bytes),
    transcriptSha256: await sha256Hex(canonicalTranscript(parsedChunks)),
    critiqueSha256: await sha256Hex(retrievedBundle.critique),
  }), []);
  // The supplied link is accepted only when its video ID hashes to
  // the signed youtube_video_sha256 — the check the page performs
  // before anything is packaged.
  const suppliedId = parseYouTubeVideoId('https://youtu.be/' + videoId);
  assert.equal(suppliedId, videoId);
  assert.equal(await sha256Hex(suppliedId), retrievedBundle.youtube_video_sha256);
  const wrongId = parseYouTubeVideoId('https://youtu.be/ZZZ123XYZ_-');
  assert.ok(wrongId && (await sha256Hex(wrongId)) !== retrievedBundle.youtube_video_sha256,
    'a different video fails the signed check, so no ZIP is built');
  // Duration with no local record: fingerprint items × 0.124 s.
  assert.ok(Math.abs(items.length * 0.124 - 0.744) < 1e-9);
  // The package built from the parsed chunks carries the signed
  // lines and the retrieved transcript, line for line.
  const fpHtml = assemblePackage({
    youtubeLink: canonicalWatchUrl(videoId),
    audioFileName: FINGERPRINT_FILE_NAME,
    durationS: items.length * 0.124,
    chunks: parsedChunks,
    bundle: retrievedBundle,
    fingerprintSha256: retrievedBundle.chromaprint_sha256,
  });
  const parsed = parsePackageVerification(fpHtml);
  assert.equal(parsed.verification['Chromaprint SHA-256'], FP_SHA);
  assert.equal(parsed.verification['Audio file'], 'submission-fingerprint.bin');
  assert.equal(parsed.verification['Audio duration'], '0.7');
  assert.deepEqual(parsed.transcriptLines, canon.split('\n'));
  const zip = buildZipBytes([
    { name: 'submission.html', data: new TextEncoder().encode(fpHtml) },
    { name: FINGERPRINT_FILE_NAME, data: bytes },
  ]);
  assert.deepEqual(unzipStored(zip).entries.map((e) => e.name),
    ['submission.html', 'submission-fingerprint.bin']);
});

await test('wiring: cross-assignment guard on the row Generate ZIP button (2.6.2, 2.6.16)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes("if (bundle && entry.pkg !== cfg.pkg)"),
    'a job of another assignment gets no Generate ZIP button on this page');
  assert.ok(main.includes('open its assignment\u2019s link in Canvas'),
    'the guarded row says where its ZIP is built');
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(!html.includes('Turn a graded job into your Canvas submission'),
    'the conversion panel heading is gone with the panel');
  assert.ok(main.includes('To build this job\u2019s submission ZIP'),
    'the guarded row itself states the guard (the section preamble went in the 2.6.20 diet)');
});
await test('wiring: writing corrections from the 2026-11-26 audit (2.6.2)', () => {
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  const jobs = readFileSync(new URL('../js/jobs.js', import.meta.url), 'utf8');
  const pkg = readFileSync(new URL('../js/package.js', import.meta.url), 'utf8');
  assert.ok(!html.includes('carries its recording fingerprint')
    && !main.includes('carries the recording\u2019s fingerprint'),
    'no "carries" for "has" in the retrieval texts');
  assert.ok(!html.includes('Retrieving on a different browser'),
    'the different-browser retrieval section is gone (2.6.11)');
  assert.ok(!html.includes('the same three bands'), 'no unresolvable "bands" reference');
  assert.ok(main.includes('Open this page from the link your teacher put in Canvas'),
    'the link-check message names the Canvas link');
  assert.ok(!jobs.includes('grading Worker answered') && !jobs.includes('no grading Worker'),
    'student errors name the grading service, not the Worker');
  assert.ok(!pkg.includes('Audio duration is a plain number'),
    'the stray duration sentence is gone from the submission file');
  assert.ok(pkg.includes('<dt>Audio duration unit</dt><dd>seconds (s)</dd>'),
    'the duration unit is a labelled entry');
  assert.ok(!html.includes('its fingerprint goes into the submission ZIP'),
    'the step-2 fingerprint sentence went with the 2.6.20 text diet');
  assert.ok(!html.includes('for a job sent with a checked link, with the recording'),
    'the opening paragraph does not tie the fingerprint form to a checked link (2.6.3)');
  assert.ok(main.includes('Verifying the fingerprint and the transcript'),
    'the ZIP progress line names the fingerprint form\u2019s verification (2.6.3)');
});

await test('wiring: jobs render as a table; no recovery-code control on the row (2.6.16)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(main.includes("table.className = 'jobstable'"),
    'the jobs list builds a table');
  assert.ok(main.includes("for (const h of ['Job', 'Grades', 'YouTube link', 'Actions'])"),
    'the table carries the four approved columns');
  assert.ok(index.includes('.jobstable'), 'the table styles are in the page');
  assert.ok(index.includes('@media (max-width: 620px)'),
    'the table stacks on phone widths');
  assert.ok(!main.includes('Copy recovery code') && !main.includes('codeBtn'),
    'the row carries no recovery-code control (2.6.11)');
  assert.ok(main.includes("forgetBtn.textContent = 'Remove from this browser'"),
    'Remove sits in the row’s Actions cell');
});
await test('wiring: the 5-second poll is not blocked by focus in the jobs list (2.6.6)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  const poll = main.slice(main.indexOf('async function refreshJobs'),
    main.indexOf('setInterval(refreshJobs'));
  assert.ok(!poll.includes('activeElement'),
    'refreshJobs does not skip a poll because focus sits inside the jobs list');
  assert.ok(main.includes('row.dataset.jobKey = key;'),
    'each job row carries its job key for focus restoration');
  assert.ok(main.includes("ae.dataset.act && box.contains(ae)"),
    'the render notes the focused control before the swap');
  assert.ok(main.includes('target.focus({ preventScroll: true })'),
    'the render restores focus to the matching control in the rebuilt row');
  assert.ok(main.includes('expandedJobs.has(key)'),
    'an open details panel stays open across a refresh rebuild');
  const download = main.slice(main.indexOf('async function doDownloadZip'),
    main.indexOf('function renderJobRow'));
  assert.ok(!download.includes('removeJobEntry'),
    'downloading a submission ZIP keeps the job row, so the ZIP can be downloaded again');
  assert.ok(download.includes('you can download '),
    'the Done line tells the student the ZIP can be downloaded again');
});

await test('wiring: no step-5 confirmation box; stuck rows say the service cannot be reached (2.6.9)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(!html.includes('id="confirmChk"') && !main.includes('confirmChk'),
    'the step-5 confirmation checkbox is gone from page and code');
  assert.ok(!main.includes('transcriptionComplete && confirmed'),
    'Send no longer waits on a confirmation flag');
  assert.ok(main.includes('statusFailures.set(key, (statusFailures.get(key) || 0) + 1)'),
    'failed status fetches are counted per job');
  assert.ok(main.includes('(statusFailures.get(key) || 0) >= 3'),
    'the cannot-reach state needs three failed rounds');
  assert.ok(main.includes('can\u2019t reach the grading service \u2014 retrying'),
    'the row states the failure instead of sitting at checking\u2026');
});

await test('wiring: the Generate ZIP button follows readability; nothing is checked on paste (2.6.18)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('if (!reviewOpen && parseYouTubeVideoId(rowLinkDraft(entry)))'),
    'the button renders while the field holds a readable link');
  assert.ok(main.includes('function makeZipButton(entry, bundle)'),
    'one maker builds the button for renders and in-place toggles alike');
  assert.ok(!main.includes('runRowCheck') && !main.includes('rowChecks'),
    'no standing row check state remains');
  assert.ok(!main.includes('ytConfirmChk') && !main.includes('finConfirmChk'),
    'no confirmation checkbox is read anywhere');
});

await test('wiring: section 7 redesign — table rows, details row, compact review (2.6.7, 2.6.16)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const rowFn = main.slice(main.indexOf('function renderJobRow'),
    main.indexOf('// Rendering is serialised'));
  assert.ok(rowFn.includes("labelSpan.textContent = label + ' · ' + statusText"),
    'the row label is the course/assignment label plus the status — no kind, no link wording');
  assert.ok(!main.includes("? 'Final' : 'Practice'"),
    'no Practice/Final label anywhere in the page (2.6.16)');
  assert.ok(main.includes("'Show details'") && main.includes("'Hide details'"),
    'one toggle opens and closes the job’s details row');
  assert.ok(rowFn.includes('actions.append(forgetBtn)'),
    'Remove lives in the Actions cell (2.6.16)');
  assert.ok(main.includes("'Checks: recording \u2713 \u00b7 transcript \u2713 \u00b7 YouTube \u2713'"),
    'the ZIP review opens with the three checks on one line');
  assert.ok(!main.includes('Grades: Completeness'),
    'the ZIP review no longer repeats the grades the row already shows');
  assert.ok(main.includes('expandedJobs.add(jobKey(entry.pkg, entry.retrieval_code))'),
    'a completed verification opens the panel so the review is visible');
  assert.ok(html.includes('.jobstable .jobgrades'),
    'the grades sit in the table’s Grades column');
  assert.ok(rowFn.includes("'Necessary for ZIP generation'") ||
    main.includes("'Necessary for ZIP generation'"),
    'a row with no readable link carries the one succinct line');
  assert.ok(!main.includes('Add a YouTube link to download the ZIP.'),
    'the older caption wording is gone');
  assert.ok(main.includes("zipBtn.textContent = 'Generate ZIP'"),
    'a readable link produces the Generate ZIP button');
  assert.ok(rowFn.includes("clearBtn.textContent = '×'"),
    'a populated field carries the × clear control');
});
await test('wiring: no recovery-code control anywhere on the page (2.6.11)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(!main.includes('Copy recovery code') && !main.includes('Show recovery code'),
    'no job row carries a recovery-code button');
  assert.ok(main.includes('entry.retrieval_code'),
    'the entry\u2019s stored token is still used internally, for polling and the ZIP');
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(!html.includes('picked at the time'),
    'the retrieval note no longer mentions student-picked codes');
  assert.ok(!html.includes('shows it once'),
    'no page text still claims the code is shown only once');
  assert.ok(!main.includes('it is not shown again'),
    'the send-time line no longer claims the code is never shown again');
});

await test('wiring: no add-link button; the row field is the link route (2.6.16)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(!main.includes('addlink'), 'no per-row add-link button remains');
  assert.ok(!main.includes('make this your submission'),
    'the conversion wording is gone');
  assert.ok(main.includes("input.dataset.act = 'ytlink'"),
    'each ready row carries its own link field');
  assert.ok(main.includes('previewLoad(id, true, key);') && main.includes('}, 400);'),
    'dwelling on a populated link cell plays its video in the preview area');
  assert.ok(main.includes('if (!document.contains(input)) return;'),
    'the hover timer re-validates, so a cleared or rebuilt row cannot resurrect its video (2.6.20)');
  assert.ok(main.includes('previewPlayer.mute()') || main.includes('ev.target.mute()'),
    'the preview is muted before it plays — no audible autoplay');
});
await test('wiring: a link added or replaced in a row plays at once (2.6.20)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('function previewOnLinkCommit(key, videoId)'),
    'one helper takes the viewing area over for a committed link');
  assert.ok(main.includes('previewOnLinkCommit(key, nowParsed);'),
    'the field commit path plays the new video without a hover');
  assert.ok(main.includes('previewOnLinkCommit(key, videoId);'),
    'the Generate ZIP check path also takes the player over');
  assert.ok(main.includes('nowParsed !== prevParsed'),
    'the takeover fires on a change of video, not on every keystroke');
});

await test('wiring: fingerprint-form ZIP path is wired into the review and download steps (2.6.0)', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('bundleChromaprintSha(bundle)'),
    'the signed bundle decides the ZIP form at verification time');
  assert.ok(main.includes('verifyFingerprintParts(entry, bundle, anchor, onError, pending)'),
    'the fingerprint verification step is the branch taken for that form');
  assert.ok(main.includes('verifyFingerprintContents(bundle, {'),
    'fingerprint contents are checked against the signed hashes');
  assert.ok(main.includes('decodeRawFingerprint(extras.chromaprint)'),
    'fingerprint bytes are decoded from the status response');
  assert.ok(main.includes('chunksFromCanonical(extras.transcript)'),
    'the retrieved transcript is parsed back into chunks');
  assert.ok(main.includes('res.data.transcript') && main.includes('res.data.chromaprint'),
    'the status response transcript and chromaprint are surfaced per job');
  assert.ok(main.includes('items.length * 0.124'),
    'the packaged duration falls back to the fingerprint length');
  assert.ok(main.includes('name: FINGERPRINT_FILE_NAME'),
    'the ZIP fingerprint entry carries the fingerprint file name');
  assert.ok(main.includes('fingerprintSha256: liveBundle.chromaprint_sha256'),
    'the HTML assembly is told the signed fingerprint hash');
});

console.log('\n' + passed + ' passed, ' + failed + ' failed, ' + skipped + ' skipped');
process.exit(failed ? 1 : 0);
