// Minimal deterministic ZIP writer (SPEC, Webapp section).
//
// The submission is one ZIP file (downloaded under a per-job name
// since 2.4.4 — see submissionZipName below), holding exactly
// submission.html and submission-audio.wav. Entries are STORED (no
// compression), written in the caller's order, and every header field
// that could vary between runs is fixed: DOS date/time is 1980-01-01
// 00:00 (the earliest DOS timestamp), no extra fields, no comments, no
// external attributes beyond a plain file. Building the same entries
// twice therefore produces byte-identical output, so a ZIP rebuilt at
// a later visit (after a lost download) is the same file the audit
// watermark expects.
//
// CRC-32 (IEEE, polynomial 0xEDB88320) is implemented locally; no
// compression library is involved anywhere in this module.
// Pure — Node-tested (buildZipBytes). buildZip wraps the bytes in a
// Blob for the browser download.

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[n] = c >>> 0;
  }
  return table;
})();

export function crc32(bytes) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) {
    crc = CRC_TABLE[(crc ^ bytes[i]) & 0xFF] ^ (crc >>> 8);
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

// Fixed DOS timestamp: 1980-01-01 00:00:00.
// DOS date bits: ((year-1980) << 9) | (month << 5) | day = 0<<9 | 1<<5 | 1.
export const ZIP_DOS_TIME = 0;
export const ZIP_DOS_DATE = (0 << 9) | (1 << 5) | 1; // 33

const VERSION_NEEDED = 20;
const METHOD_STORED = 0;

function u16le(v) { return [v & 0xFF, (v >>> 8) & 0xFF]; }
function u32le(v) { return [v & 0xFF, (v >>> 8) & 0xFF, (v >>> 16) & 0xFF, (v >>> 24) & 0xFF]; }

// entries: [{ name: string, data: Uint8Array }] in archive order.
// Returns the complete ZIP file as a Uint8Array.
export function buildZipBytes(entries) {
  const enc = new TextEncoder();
  const parts = [];
  const central = [];
  let offset = 0;
  for (const entry of entries || []) {
    const nameBytes = enc.encode(entry.name);
    const data = entry.data instanceof Uint8Array ? entry.data : new Uint8Array(entry.data);
    const crc = crc32(data);
    const local = new Uint8Array([
      ...u32le(0x04034b50),               // local file header signature
      ...u16le(VERSION_NEEDED),
      ...u16le(0),                        // flags
      ...u16le(METHOD_STORED),
      ...u16le(ZIP_DOS_TIME),
      ...u16le(ZIP_DOS_DATE),
      ...u32le(crc),
      ...u32le(data.length),              // compressed size (stored)
      ...u32le(data.length),              // uncompressed size
      ...u16le(nameBytes.length),
      ...u16le(0),                        // extra field length
    ]);
    parts.push(local, nameBytes, data);
    central.push(new Uint8Array([
      ...u32le(0x02014b50),               // central directory signature
      ...u16le(VERSION_NEEDED),           // version made by
      ...u16le(VERSION_NEEDED),           // version needed
      ...u16le(0),                        // flags
      ...u16le(METHOD_STORED),
      ...u16le(ZIP_DOS_TIME),
      ...u16le(ZIP_DOS_DATE),
      ...u32le(crc),
      ...u32le(data.length),
      ...u32le(data.length),
      ...u16le(nameBytes.length),
      ...u16le(0),                        // extra field length
      ...u16le(0),                        // comment length
      ...u16le(0),                        // disk number
      ...u16le(0),                        // internal attributes
      ...u32le(0),                        // external attributes
      ...u32le(offset),                   // local header offset
    ]), nameBytes);
    offset += local.length + nameBytes.length + data.length;
  }
  const centralStart = offset;
  let centralSize = 0;
  for (const c of central) centralSize += c.length;
  const end = new Uint8Array([
    ...u32le(0x06054b50),                 // end of central directory
    ...u16le(0),                          // disk number
    ...u16le(0),                          // central directory disk
    ...u16le((entries || []).length),    // entries on this disk
    ...u16le((entries || []).length),    // total entries
    ...u32le(centralSize),
    ...u32le(centralStart),
    ...u16le(0),                          // comment length
  ]);
  const total = centralStart + centralSize + end.length;
  const out = new Uint8Array(total);
  let pos = 0;
  for (const p of [...parts, ...central, end]) {
    out.set(p, pos);
    pos += p.length;
  }
  return out;
}

export function buildZip(entries) {
  return new Blob([buildZipBytes(entries)], { type: 'application/zip' });
}

export const SUBMISSION_ZIP_NAME = 'submission.zip';
export const ZIP_ENTRY_HTML = 'submission.html';
export const ZIP_ENTRY_AUDIO = 'submission-audio.wav';

// The name the submission ZIP is downloaded under (2.4.4): distinct
// per job, so two downloads in one folder cannot be confused when the
// student picks a file for Canvas. Form:
//   C<course number>H<homework number>-G<total grade>-Y<HHMM>-<YYMMDD>.zip
// e.g. C4061H5-G7-Y1905-261110.zip — course 4061, homework 5, grade
// 7 of 10 (completeness + accuracy), YouTube link checked at 19:05
// local time on 2026-11-10. Only the course/homework numbers are
// taken from the teacher's labels. The Y time is the job's YouTube
// check time when the entry kept one, otherwise the grading time;
// shown in the student's local time. The name is a property of the
// job, so re-downloading a job gives the same name. This is only the
// download file name: the ZIP's bytes and its two entry names are
// unchanged, and any segment whose data is missing is omitted, with
// SUBMISSION_ZIP_NAME as the fallback when nothing is known.
export function submissionZipName(fields) {
  const f = fields || {};
  const digits = (s) => {
    const m = String(s == null ? '' : s).match(/\d+/g);
    return m ? m.join('') : '';
  };
  const pad = (n, w) => String(n).padStart(w, '0');
  const parts = [];
  const course = digits(f.course);
  const hw = digits(f.asg);
  if (course || hw) parts.push('C' + course + 'H' + hw);
  const total = Number(f.completeness) + Number(f.accuracy);
  if (Number.isFinite(total) &&
      f.completeness != null && f.accuracy != null) {
    parts.push('G' + total);
  }
  let when = null;
  for (const v of [f.youtubeCheckedAt, f.gradedAt]) {
    if (v) {
      const d = v instanceof Date ? v : new Date(v);
      if (!Number.isNaN(d.getTime())) { when = d; break; }
    }
  }
  if (when) {
    parts.push('Y' + pad(when.getHours(), 2) + pad(when.getMinutes(), 2) +
      '-' + pad(when.getFullYear() % 100, 2) +
      pad(when.getMonth() + 1, 2) + pad(when.getDate(), 2));
  }
  return parts.length ? parts.join('-') + '.zip' : SUBMISSION_ZIP_NAME;
}
