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
  canonicalTranscript, findSuspects, formatDuration,
} from '../js/transcript.js';
import {
  VERSIONS, assemblePackage, parsePackageVerification,
  formatTranscriptTimestamp,
} from '../js/package.js';
import { encodeWavPcm16, wavDurationS } from '../js/media.js';
import { buildVocabulary } from '../js/vocab.js';
import { PAIRS } from '../chemescribe-base/corrections.js';
import { cacheKey, cacheHit, toCachedChunk, fromCachedChunk, recordingFirstWords } from '../js/cachekey.js';
import { crc32, buildZipBytes, ZIP_DOS_DATE, ZIP_DOS_TIME } from '../js/zip.js';
import {
  RETRIEVAL_CODE_RE, parseYouTubeVideoId, canonicalWatchUrl,
  classifyDuration, verifyBundleContents, reportDurationStat,
  validateJobPayload, buildJobPayload,
  loadJobEntries, addJobEntry, removeJobEntry, pruneExpiredEntries,
  submitJob, fetchJobStatus, finalizeJob,
} from '../js/jobs.js';
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
  assert.equal(scrubMetadata('jordan-lee-hw3.mp4', words), '-lee-hw3.mp4');
  assert.equal(scrubMetadata('Jordan Lee hw3.mp4', words), 'hw3.mp4');
});

await test('scrub: whole-word only; punctuation spacing repaired', () => {
  const { text } = scrubText('Annette and Ann went home , then left .', ['Ann']);
  assert.equal(text, 'Annette and went home, then left.');
});

await test('canonical: one chunk per line, LF, no trailing spaces or newline', () => {
  const sc = scrubChunks(rawChunks, parseScrubWords('Jordan Lee, jordan'));
  const canon = canonicalTranscript(sc);
  assert.equal(canon,
    'Hi I am and this is my homework\nexplains the reflux ratio, with watching');
  assert.ok(!canon.endsWith('\n'));
  assert.ok(!/ \n/.test(canon));
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
  assert.equal(v['Webapp version'], 'hw-signing-webapp 2.4.0');
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
  const recovered = parsed.transcriptLines
    .map((l) => l.replace(/^\[\d+:\d{2}\] /, '')).join('\n');
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
  assert.equal(parseYouTubeVideoId('https://www.youtube.com/watch?v=short'), null);
  assert.equal(parseYouTubeVideoId('https://example.com/watch?v=' + id), null);
  assert.equal(parseYouTubeVideoId('not a url'), null);
  assert.equal(parseYouTubeVideoId(''), null);
  assert.equal(canonicalWatchUrl(id), 'https://www.youtube.com/watch?v=' + id);
});

/* ---------------- retrieval code ---------------- */

await test('retrieval code: rule matches the Worker', () => {
  assert.ok(RETRIEVAL_CODE_RE.test('7'));
  assert.ok(RETRIEVAL_CODE_RE.test('abc123'));
  assert.ok(!RETRIEVAL_CODE_RE.test(''));
  assert.ok(!RETRIEVAL_CODE_RE.test('a b'));
  assert.ok(!RETRIEVAL_CODE_RE.test('code-1234'));
  assert.ok(!RETRIEVAL_CODE_RE.test('x'.repeat(129)));
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
  assert.equal(validateJobPayload({ ...base, retrieval_code: '7' }).ok, true);
  assert.equal(validateJobPayload({ ...base, retrieval_code: 'abc' }).ok, true);
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

await test('job calls: finalize posts the check to /jobs/finalize', async () => {
  const seen = [];
  const mockOk = async (url, opts) => {
    seen.push({ url, body: JSON.parse(opts.body) });
    return { ok: true, status: 200, json: async () => ({ ok: true, receipt: 'r1' }) };
  };
  const payload = { pkg: 'hw3 v2', retrieval_code: 'code1234' };
  payload['youtube' + '_token'] = 'tok';
  payload.youtube_video_id = 'abc123XYZ_-';
  payload.youtube_checked_at = '2026-11-09T10:00:00.000Z';
  const out = await finalizeJob('https://g.example.workers.dev', payload, mockOk);
  assert.equal(out.ok, true);
  assert.equal(seen[0].url, 'https://g.example.workers.dev/jobs/finalize');
  assert.equal(seen[0].body.youtube_video_id, 'abc123XYZ_-');
  const mock409 = async () => ({ ok: false, status: 409, json: async () => ({ error: 'a final job already exists for this recording' }) });
  await assert.rejects(() => finalizeJob('https://g.example.workers.dev', payload, mock409),
    /a final job already exists/);
});

await test('wiring: conversion panel present; no practice/final radios', () => {
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(index.includes('id="finPanel"'), 'conversion panel present');
  assert.ok(index.includes('id="finJobSel"'), 'graded-job picker present');
  assert.ok(!index.includes('kindPractice'), 'no practice radio');
  assert.ok(!index.includes('kindFinal'), 'no final radio');
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('finalizeJob('), 'page calls finalize');
  assert.ok(main.includes('refreshFinPanel'), 'panel refresh wired');
  assert.ok(!main.includes('convBtn'), 'no per-row conversion button (the picker is the route)');
  assert.ok(!main.includes("textContent = 'Turn into my submission'"),
    'row buttons do not carry the conversion label');
  assert.ok(main.includes('finPrevSelKey'), 'picker selection change tracking wired');
  assert.ok(main.includes('if (finPrevSelKey !== null && sel.value !== finPrevSelKey) finResetCheck();'),
    'stale link check reset when a rebuild changes the selected job');
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
  assert.ok(main.includes('transcriptionComplete && confirmed'),
    'submit gating includes the confirmation');
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
  assert.ok(main.includes("box.scrollIntoView({ block: 'nearest' })"),
    'the error box is scrolled into view where it lands');
  for (const a of ["$('loadBtn')", "$('mediaFile')", 'restoreBtn',
                   "$('runBtn')", "$('submitJobBtn')",
                   'downloadSubmissionZip(entry, bundle, zipBtn)']) {
    assert.ok(main.includes(a), 'anchored error call site: ' + a);
  }
});

await test('wiring: the section-7 critique keeps its line breaks', () => {
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes("crit.style.whiteSpace = 'pre-line'"),
    'numbered critique points appear on separate lines in the job list');
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(index.includes('<title>Practice and Get Feedback on Audio/Video Recordings for Canvas submission</title>'),
    'page title is the current one');
  assert.ok(index.includes('Submit your audio or video for transcription and anonymized graded'),
    'page description is the current one');
});

await test('wiring: no separate download button for the extracted audio', () => {
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(!index.includes('audioDl') && !main.includes('audioDl'),
    'the extracted audio is kept automatically and goes into the ZIP; no manual download');
});

await test('wiring: page and worker carry the v2 version strings', () => {
  assert.equal(VERSIONS.webapp, 'hw-signing-webapp 2.4.0');
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(index.includes('id="suPh"'), 'setup form has the ph field');
  assert.ok(index.includes('id="jobsBox"'), 'jobs list section present');
  const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');
  assert.ok(sw.includes("addEventListener('push'"), 'service worker handles push');
  assert.ok(sw.includes("addEventListener('notificationclick'"), 'service worker handles clicks');
});

/* ---------------- duration bands + bundle verification (2.4.0) ---------------- */

await test('duration: bands pass / confirm / block, tolerance scales with length', () => {
  assert.equal(classifyDuration(600, 600.4).band, 'pass');
  assert.equal(classifyDuration(600, 601.0).band, 'pass');
  assert.equal(classifyDuration(600, 601.5).band, 'confirm');
  // 12 s tolerance at 600 s (2% beats the 2 s floor)
  assert.equal(classifyDuration(600, 611).band, 'confirm');
  assert.equal(classifyDuration(600, 613).band, 'block');
  // short recording: the 2 s floor is the tolerance
  assert.equal(classifyDuration(60, 61.5).band, 'confirm');
  assert.equal(classifyDuration(60, 62.5).band, 'block');
  const c = classifyDuration(600, 613);
  assert.ok(Math.abs(c.diffS - 13) < 1e-9 && Math.abs(c.tolS - 12) < 1e-9);
});

await test('duration: unknown when either length is missing', () => {
  assert.equal(classifyDuration(600, 0).band, 'unknown');
  assert.equal(classifyDuration(600, null).band, 'unknown');
  assert.equal(classifyDuration(0, 600).band, 'unknown');
  assert.equal(classifyDuration(600, 0).diffS, null);
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

await test('duration stat: posts the two durations and the package label only', async () => {
  let seen = null;
  const fetchFn = async (url, opts) => {
    seen = { url, body: JSON.parse(opts.body) };
    return { ok: true, status: 200, json: async () => ({ ok: true }) };
  };
  const ok = await reportDurationStat('https://w.example', {
    pkg: 'hw3 v2', context: 'send', audioS: 600, videoS: 600.4,
  }, fetchFn);
  assert.equal(ok, true);
  assert.ok(seen.url.endsWith('/stats/duration'));
  assert.deepEqual(seen.body, {
    pkg: 'hw3 v2', context: 'send', audio_s: 600, video_s: 600.4,
  });
  const down = async () => { throw new Error('offline'); };
  assert.equal(await reportDurationStat('https://w.example', {
    pkg: 'hw3 v2', context: 'send', audioS: 1, videoS: 1,
  }, down), false);
});

await test('wiring: duration gate and review elements present in the page', () => {
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  for (const id of ['ytDurStatus', 'ytConfirmRow', 'ytConfirmChk',
    'finDurStatus', 'finConfirmRow', 'finConfirmChk']) {
    assert.ok(index.includes('id="' + id + '"'), 'index has ' + id);
  }
  const main = readFileSync(new URL('../js/main.js', import.meta.url), 'utf8');
  assert.ok(main.includes('clearYtCheck()'), 'recording change voids the link check');
  assert.ok(!main.includes(': chunks;'), 'no fallback to the on-page transcript at ZIP time');
  assert.ok(main.includes('verifyBundleContents'), 'ZIP contents verified against the bundle');
});

console.log('\n' + passed + ' passed, ' + failed + ' failed, ' + skipped + ' skipped');
process.exit(failed ? 1 : 0);
