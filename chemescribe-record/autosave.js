// Autosave for the raw transcript. Pure helpers plus thin wrappers
// around a storage object (localStorage in the page, a stub in tests)
// and a File System Access handle. No function here throws into the
// caller: save failures return false so transcription continues and
// the page can show a status note. The storage key is this page's own,
// distinct from the ChemEScribe page's key, so the two pages' restore
// offers never mix on their shared origin.

export const AUTOSAVE_KEY = 'chemescribe-record.autosave.v1';

export function saveAutosave(storage, { text, savedAtISO, source }) {
  if (!storage || !text) return false;
  try {
    storage.setItem(AUTOSAVE_KEY, JSON.stringify({ text, savedAtISO, source }));
    return true;
  } catch {
    return false;
  }
}

export function loadAutosave(storage) {
  if (!storage) return null;
  try {
    const raw = storage.getItem(AUTOSAVE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed.text !== 'string' || !parsed.text) return null;
    return parsed;
  } catch {
    return null;
  }
}

export async function writeAutosaveFile(handle, text) {
  if (!handle || !text) return false;
  try {
    const writable = await handle.createWritable();
    await writable.write(text);
    await writable.close();
    return true;
  } catch {
    return false;
  }
}

export function browserStorage() {
  try { return window.localStorage; } catch { return null; }
}
