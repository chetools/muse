// Minimal deterministic ZIP writer (SPEC, Webapp section).
//
// The submission is one file, submission.zip, holding exactly
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
