// Removal-list persistence (2.8.2). Pure functions over a
// Storage-like object; browser wiring lives in main.js.
//
// Until 2.8.1 the removal list was typed fresh on every visit and
// its contents never entered storage. The teacher reversed that
// for the list itself (2026-11-28): a student's names and words
// to remove are the same for every homework, so the list now
// persists in this browser's local storage, on this machine only,
// and is restored into the field on page load. The picker
// selections persist with it, keyed by recording (audio hash) and
// entry, as positions only — appearance ordinals, the same form
// the job entry stores at send time.
//
// Nothing here is ever sent anywhere: no network path reads these
// keys, and the job-creation payload is unchanged (it carries the
// send-time selections as positions, never the list's text).
//
// Every function tolerates a missing or throwing storage (private
// browsing, a full quota, a browser that refuses): the page then
// works in-memory only, exactly as before 2.8.2, with no error.

export const SCRUB_LIST_KEY = 'hw2-scrub-list';
export const PICKER_SELECTIONS_KEY = 'hw2-picker-selections';

function defaultStorage() {
  try { return globalThis.localStorage || null; } catch { return null; }
}

function resolve(storage) {
  return storage === undefined ? defaultStorage() : storage;
}

// The saved removal-list text, or '' when none is saved or the
// storage cannot be read.
export function loadScrubList(storage) {
  const s = resolve(storage);
  if (!s) return '';
  try {
    const v = s.getItem(SCRUB_LIST_KEY);
    return typeof v === 'string' ? v : '';
  } catch { return ''; }
}

// Save the removal-list text as it stands. Saving an empty text
// clears the key, so a student who empties the field is not
// greeted by the old list on the next visit.
export function saveScrubList(storage, text) {
  const s = resolve(storage);
  if (!s) return;
  try {
    if (text) s.setItem(SCRUB_LIST_KEY, String(text));
    else s.removeItem(SCRUB_LIST_KEY);
  } catch { /* in-memory only */ }
}

// The stored picker selections as one parsed object:
// { [audioSha]: { [entry]: [ordinal, ...] } }. Any shape problem
// reads as no selections.
function readPickerStore(s) {
  try {
    const raw = s.getItem(PICKER_SELECTIONS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    return parsed;
  } catch { return {}; }
}

function writePickerStore(s, store) {
  try {
    if (Object.keys(store).length) {
      s.setItem(PICKER_SELECTIONS_KEY, JSON.stringify(store));
    } else {
      s.removeItem(PICKER_SELECTIONS_KEY);
    }
  } catch { /* in-memory only */ }
}

function cleanOrdinals(list) {
  if (!Array.isArray(list)) return null;
  const ords = list.filter((n) => Number.isInteger(n) && n >= 0);
  return ords.length ? [...new Set(ords)].sort((a, b) => a - b) : null;
}

// The saved selections for one recording: a Map of entry text ->
// Set of appearance ordinals chosen for removal. Empty when the
// recording has none or the storage cannot be read.
export function loadPickerSelections(storage, audioSha) {
  const out = new Map();
  const s = resolve(storage);
  if (!s || !audioSha) return out;
  const perRecording = readPickerStore(s)[audioSha];
  if (!perRecording || typeof perRecording !== 'object') return out;
  for (const [entry, list] of Object.entries(perRecording)) {
    const ords = cleanOrdinals(list);
    if (ords) out.set(entry, new Set(ords));
  }
  return out;
}

// Save one recording's selections (a Map of entry text -> Set of
// ordinals), replacing what was saved for that recording and
// leaving other recordings' selections untouched.
export function savePickerSelections(storage, audioSha, selections) {
  const s = resolve(storage);
  if (!s || !audioSha) return;
  const store = readPickerStore(s);
  const perRecording = {};
  if (selections) {
    for (const [entry, ords] of selections.entries()) {
      const clean = cleanOrdinals([...ords]);
      if (clean) perRecording[entry] = clean;
    }
  }
  if (Object.keys(perRecording).length) store[audioSha] = perRecording;
  else delete store[audioSha];
  writePickerStore(s, store);
}

// Drop one recording's saved selections (its recording was
// deleted from this computer).
export function dropPickerSelections(storage, audioSha) {
  const s = resolve(storage);
  if (!s || !audioSha) return;
  const store = readPickerStore(s);
  if (!(audioSha in store)) return;
  delete store[audioSha];
  writePickerStore(s, store);
}
