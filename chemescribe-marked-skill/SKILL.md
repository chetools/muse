# ChemEScribe Marked — Transcribe with STOP RECORD / START RECORD Trim

## Purpose

Transcribe a recording locally with NVIDIA Parakeet TDT 0.6B v2 (int8, CPU, through onnx-asr), correct it with the built-in chemical-engineering glossary, and apply the recording's own spoken edit markers: everything between a spoken "stop record" and the next spoken "start record" is removed.

The glossary is the ChemEScribe bundle, byte-identical to the one in the ChemEScribe skill: `glossary/glossary.json` (756 chemical-engineering and general-engineering terms), `glossary/vocabulary.txt` (745 terms), `glossary/corrections.json` (152 certain sound-alike pairs, replaced outright), `glossary/slash-pairs.json` (60 uncertain pairs, decided by `glossary/context-rules.json` or rendered in slash form), plus the dictionary-pass lists `glossary/words.txt` and `glossary/traps.txt`.

## Trigger

Apply this skill when the user asks to transcribe a recording or points Muse at an audio file (WAV, MP3, M4A, WebM, OGG, MP4) and the recording uses "stop record" / "start record" markers, or the user names this skill. For a plain transcription with no markers, the ChemEScribe skill is the one to use.

## Options, settled before the run

- Marker trim is always on in this skill. It is the skill's defining step, not an option.

- Timestamps: off by default, on when the user asks. With timestamps, each roughly 25 second chunk of the transcript carries its time range, preserved through every later stage, and removed sections are reported by time range.

- State the settled options in one line before transcribing, and again in the delivery.

## Setup (one time, for transcription)

Transcription runs through `scripts/transcribe.py` in this skill's folder. It needs the `onnx-asr` package and ffmpeg on the system path:

```
python3 -m pip install onnx-asr
```

The first run downloads the Parakeet model (about 670 MB) to a local cache; later runs reuse it. The audio never leaves the machine and no transcription service is called. ONNX Runtime telemetry is disabled in the runner before the model loads (`ORT_DISABLE_TELEMETRY=1` and `disable_telemetry_events()`); keep both in any edit of the script. If `transcribe.py` reports the setup is missing, walk the user through the install and stop there. Do not transcribe by any other means, and never reconstruct what was said from context, notes or guesswork.

## Procedure

Helpers: `scripts/transcribe.py`, `scripts/trim_markers.py`, `scripts/correct.py`, `scripts/context_choice.py`, `scripts/dict_check.py` and `scripts/tidy.py`, all in this skill's folder, plus the glossary in `glossary/`. File naming follows the ChemEScribe convention: `<audio-name>.raw.txt`, `<audio-name>.trimmed.txt`, then the correction stages, then the delivered final transcript. The raw transcript is the record and is never edited or deleted: the trim produces a new file, so any removal can be undone from the raw text.

1. **Transcribe, showing the words as they land.** Run `python3 scripts/transcribe.py [--timestamps] --partial <audio-name>.partial.txt <file>`. Add `--timestamps` when the settled options call for it. As each chunk lands, show the user the chunk number and time range, a progress count, the raw words, and the same chunk after the correction stages of steps 3 to 6, with that chunk's corrections listed, exactly as in the ChemEScribe skill's intermediate-progress rule. Save stdout as the raw transcript.

2. **Trim the marked-off sections.** Run `python3 scripts/trim_markers.py <rawFile> > <trimmedFile>`. The script matches the marker phrases "stop record", "stop recording", "stop the record", "stop the recording", "start record", "start recording", "start the record" and "start the recording", case-insensitive, on the whole word stream, so a marker split across two chunks is still found and a marker mid-sentence splits the sentence. Its rules for repeats: the recording starts as kept; a stop marker starts a removed section; further stop markers inside a removed section are duplicates and change nothing; a start marker ends the removed section; further start markers while recording are duplicates and change nothing; a stop marker never closed by a start marker removes everything to the end of the recording and is logged as unclosed. The marker words themselves are removed. The script logs every event and every removed section, with word counts, as JSON on stderr; keep that log for the delivery. One check before going on: if the log shows zero markers and the user said markers were used, stop and say so plainly. The marker may have been misheard beyond the listed phrases; do not trim by guessing at content.

3. **Apply the correction map (certain pairs).** Run `python3 scripts/correct.py <trimmedFile> glossary/corrections.json > <correctedFile>`. It replaces known sound-alike mishearings with the listed terms (case-insensitive, whole phrases, longest first) and reports on stderr which corrections it applied.

4. **Make the context-rules choices (uncertain pairs).** Run `python3 scripts/context_choice.py <correctedFile> glossary/slash-pairs.json glossary/context-rules.json [--topic "<topic>"] > <ruledFile>`. A candidate is chosen only at the calibrated bar (top score at least 8, at least 3 ahead of the runner-up); below the bar the pair's slash form is written instead, the heard word first, then the possibilities, slash-separated with no spaces.

5. **Run the dictionary pass.** Run `python3 scripts/dict_check.py <ruledFile> glossary/words.txt glossary/vocabulary.txt glossary/glossary.json glossary/traps.txt > <dictFile>`. It catches mishearings no pair predicted, replacing silently only at its calibrated bar, rendering the slash form below it, and never touching numbers, units, negations or timestamp prefixes.

6. **Run the tidy-up (mechanical edits only).** Run `python3 scripts/tidy.py <dictFile> --final > <tidiedFile>`. Fillers, duplicate words, spacing, capitalisation and a terminal full stop only; never grammar or tense.

7. **Review every correction, then make the contextual pass.** Read each applied correction, context choice, dictionary decision, slash rendering and tidy edit against the raw transcript and revert any where the heard form was the speaker's genuine word (standing traps: "gives" or "ideas" for Gibbs free energy, "viral" for virial, "do point" for dew point). Then read the reviewed text against `glossary/vocabulary.txt` and any topic or terms the user supplied. Change only clear sound-alike errors of listed terms. Do not correct the speaker's own wrong terms, wrong statements or grammar. Numbers, units and negations are never changed silently: flag them and leave the text as transcribed. Flag passages that stay uncertain rather than guessing at them.

8. **Run the final marker scan.** Search the final text for every marker phrase listed in step 2. Any hit is a defect: a marker that survived means a section boundary was misread. Fix it by returning to step 2's log and the raw transcript, and do not deliver until the scan is clean.

9. **Deliver.** Give the user the final transcript (in the reply for a short recording, as a file for a long one) and state: whether timestamps were on; the marker log in plain form (how many sections were removed, their time ranges and word counts, any duplicate markers, and a warning if a stop marker was left unclosed); the corrections, context choices, dictionary decisions and tidy edits, with reversions noted; and the passages that stayed uncertain, with their time ranges when timestamps are on. Name the raw transcript's file: it holds everything that was removed, and it governs wherever the user cares about the exact wording.

## Limits

- English only. The bundled model is the English Parakeet v2 model.

- No speaker labels are produced at any stage. Every speaker's words are transcribed as spoken; this skill separates content only by the spoken markers, never by speaker.

- The marker phrases are the eight listed in step 2. A marker misheard into other words entirely is not found; step 2's zero-marker check is the guard, and the remedy is for the speaker to say the markers again in a re-recording, not for Muse to infer the boundaries from content.

- Timestamps are chunk-level, roughly 25 seconds, so a removed section's reported time range names the chunks it spans, not the exact seconds of its first and last words. The trim itself is word-accurate in the text.

- Long files take a while on CPU. The chunk progress is the measure; report it, and do not promise a finishing time.

- A missing file, an unreadable format or a failed conversion is reported as-is. Do not fall back to another transcription service without the user's agreement, because that would send the audio off the machine.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- When a passage stays uncertain after the correction stages, keep the slash form in the delivered transcript instead of choosing a term, so the user sees the doubt rather than a guess.
