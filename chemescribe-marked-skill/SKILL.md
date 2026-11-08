# ChemEScribe Marked — Transcribe with STOP RECORD / START RECORD Trim and Content Options

## Purpose

Transcribe a recording locally with NVIDIA Parakeet TDT 0.6B v2 (int8, CPU, through onnx-asr), correct it with the built-in chemical-engineering glossary, and apply the recording's own spoken edit markers: everything between a spoken "stop record" and the next spoken "start record" is removed. Two further options, each off unless the user asks for it, remove every speaker except the main one, and remove everything not directly related to the technical content. A personal dictionary is a third option.

The glossary is the ChemEScribe bundle, byte-identical to the one in the ChemEScribe skill: `glossary/glossary.json` (756 chemical-engineering and general-engineering terms), `glossary/vocabulary.txt` (745 terms), `glossary/corrections.json` (152 certain sound-alike pairs, replaced outright), `glossary/slash-pairs.json` (60 uncertain pairs, decided by `glossary/context-rules.json` or rendered in slash form), plus the dictionary-pass lists `glossary/words.txt` and `glossary/traps.txt`. The personal dictionary is not part of this bundle and is never shared with it: it lives at `~/workspace/user/personal-glossary.json` on the user's own installation and holds that user's attested names and terms.

## Trigger

Apply this skill when the user asks to transcribe a recording or points Muse at an audio file (WAV, MP3, M4A, WebM, OGG, MP4) and any of these holds: the recording uses "stop record" / "start record" markers, the user asks for the main speaker only, the user asks for the technical content only, or the user names this skill. For a plain transcription with no markers and no removal options, the ChemEScribe skill is the one to use.

## Options, settled before the run

- Marker trim is always on in this skill. It is the skill's defining step, not an option.

- Main speaker only: off by default. When on, timestamps are switched on for the transcription whatever the user chose, because every removal under this option is reported by time range.

- Technical content only: off by default. When on, timestamps are likewise switched on.

- Personal dictionary: when `~/workspace/user/personal-glossary.json` exists, its entries are applied in the contextual pass (step 7) unless the user says to leave it out for this run. When no such file exists, the option does nothing and the delivery says so.

- Timestamps: off by default, on when the user asks or when a removal option forces them on. With timestamps, each roughly 25 second chunk of the transcript carries its time range, preserved through every later stage.

- State the settled options in one line before transcribing, and again in the delivery.

## Setup (one time, for transcription)

Transcription runs through `scripts/transcribe.py` in this skill's folder. It needs the `onnx-asr` package and ffmpeg on the system path:

```
python3 -m pip install onnx-asr
```

The first run downloads the Parakeet model (about 670 MB) to a local cache; later runs reuse it. The audio never leaves the machine and no transcription service is called. ONNX Runtime telemetry is disabled in the runner before the model loads (`ORT_DISABLE_TELEMETRY=1` and `disable_telemetry_events()`); keep both in any edit of the script. If `transcribe.py` reports the setup is missing, walk the user through the install and stop there. Do not transcribe by any other means, and never reconstruct what was said from context, notes or guesswork.

## Procedure

Helpers: `scripts/transcribe.py`, `scripts/trim_markers.py`, `scripts/correct.py`, `scripts/context_choice.py`, `scripts/dict_check.py`, `scripts/tidy.py` and `scripts/learn_diff.py` (step 11 only), all in this skill's folder, plus the glossary in `glossary/`. File naming follows the ChemEScribe convention: `<audio-name>.raw.txt`, `<audio-name>.trimmed.txt`, then the correction stages, then the delivered final transcript. The raw transcript is the record and is never edited or deleted: every removal in this skill produces a new file, so any removal can be undone from the raw text.

1. **Transcribe, showing the words as they land.** Run `python3 scripts/transcribe.py [--timestamps] --partial <audio-name>.partial.txt <file>`. Add `--timestamps` when the settled options call for it. As each chunk lands, show the user the chunk number and time range, a progress count, the raw words, and the same chunk after the correction stages of steps 3 to 6, with that chunk's corrections listed, exactly as in the ChemEScribe skill's intermediate-progress rule. Save stdout as the raw transcript.

2. **Trim the marked-off sections.** Run `python3 scripts/trim_markers.py <rawFile> > <trimmedFile>`. The script matches the marker phrases "stop record", "stop recording", "stop the record", "stop the recording", "start record", "start recording", "start the record" and "start the recording", case-insensitive, on the whole word stream, so a marker split across two chunks is still found and a marker mid-sentence splits the sentence. Its rules for repeats: the recording starts as kept; a stop marker starts a removed section; further stop markers inside a removed section are duplicates and change nothing; a start marker ends the removed section; further start markers while recording are duplicates and change nothing; a stop marker never closed by a start marker removes everything to the end of the recording and is logged as unclosed. The marker words themselves are removed. The script logs every event and every removed section, with word counts, as JSON on stderr; keep that log for the delivery. One check before going on: if the log shows zero markers and the user said markers were used, stop and say so plainly. The marker may have been misheard beyond the listed phrases; do not trim by guessing at content.

3. **Apply the correction map (certain pairs).** Run `python3 scripts/correct.py <trimmedFile> glossary/corrections.json > <correctedFile>`. It replaces known sound-alike mishearings with the listed terms (case-insensitive, whole phrases, longest first) and reports on stderr which corrections it applied.

4. **Make the context-rules choices (uncertain pairs).** Run `python3 scripts/context_choice.py <correctedFile> glossary/slash-pairs.json glossary/context-rules.json [--topic "<topic>"] > <ruledFile>`. A candidate is chosen only at the calibrated bar (top score at least 8, at least 3 ahead of the runner-up); below the bar the pair's slash form is written instead, the heard word first, then the possibilities, slash-separated with no spaces.

5. **Run the dictionary pass.** Run `python3 scripts/dict_check.py <ruledFile> glossary/words.txt glossary/vocabulary.txt glossary/glossary.json glossary/traps.txt > <dictFile>`. It catches mishearings no pair predicted, replacing silently only at its calibrated bar, rendering the slash form below it, and never touching numbers, units, negations or timestamp prefixes.

6. **Run the tidy-up (mechanical edits only).** Run `python3 scripts/tidy.py <dictFile> --final > <tidiedFile>`. Fillers, duplicate words, spacing, capitalisation and a terminal full stop only; never grammar or tense.

7. **Review every correction, then make the contextual pass.** Read each applied correction, context choice, dictionary decision, slash rendering and tidy edit against the raw transcript and revert any where the heard form was the speaker's genuine word (standing traps: "gives" or "ideas" for Gibbs free energy, "viral" for virial, "do point" for dew point). Then read the reviewed text against `glossary/vocabulary.txt`, any topic or terms the user supplied, and, when the personal dictionary option is on, the entries in `~/workspace/user/personal-glossary.json`, each applied under its own stated rule. Change only clear sound-alike errors of listed terms. Do not correct the speaker's own wrong terms, wrong statements or grammar. Numbers, units and negations are never changed silently: flag them and leave the text as transcribed. Flag passages that stay uncertain rather than guessing at them.

8. **Remove the other speakers (only when the option is on).** Parakeet produces no speaker labels, so this step is a judgement pass by Muse over the corrected, timestamped transcript, not a measurement. The main speaker is the user, or the person the user names; if neither identifies one, the main speaker is the voice carrying the sustained explanation. Remove only passages that are clearly another speaker: an audience question, an interjection, an announcement by someone else. Keep the main speaker's answers to removed questions; an answer is the main speaker's content even when its question is gone. When a passage's speaker cannot be told with confidence, keep it and flag it in the delivery as unattributed. Never remove a passage on a guess. Write the result as a new file, and log every removal with its time range and its first few words.

9. **Remove the non-technical content (only when the option is on).** A judgement pass by Muse over what step 8 produced (or over the step 7 text when step 8 is off). Keep everything directly related to the technical content: definitions, derivations, worked examples, data and numbers, technical questions and their answers, corrections of technical errors, and statements of what a result means. Remove logistics, scheduling, announcements, greetings and leave-taking, personal asides, and talk about the recording itself (the marker phrases are already gone under step 2). When a passage is borderline, for example motivation that sets up a derivation, keep it and flag it. Write the result as a new file, and log every removal with its time range and a one-line summary of what it was.

10. **Run the final marker scan.** Search the final text for every marker phrase listed in step 2. Any hit is a defect: a marker that survived means a section boundary was misread. Fix it by returning to step 2's log and the raw transcript, and do not deliver until the scan is clean.

11. **Run the learning loop (this user's installation, personal dictionary option on).** Compare the trimmed transcript with the delivered final transcript: `python3 scripts/learn_diff.py <trimmedFile> <finalFile> ~/workspace/user/personal-glossary.json --out <audio-name>.learn.json`. The sections removed under steps 8 and 9 appear as deletions, which the script lists and never proposes as pairs. Present the remaining substitution proposals to the user, classified as certain, context-gated, or paragraph-only (not proposed). Write an entry to the personal dictionary only after the user approves it, marked attested with the source recording and date, and append the run to `~/workspace/user/personal-glossary-ledger.json`. When the personal dictionary option is off, or no personal dictionary file exists, skip this step and say so in the delivery.

12. **Deliver.** Give the user the final transcript (in the reply for a short recording, as a file for a long one) and state: the options that were on; the marker log in plain form (how many sections were removed, their time ranges and word counts, any duplicate markers, and a warning if a stop marker was left unclosed); the speaker removals and the non-technical removals, each by time range, when those options were on; the corrections, context choices, dictionary decisions and tidy edits, with reversions noted; and the passages that stayed uncertain, with their time ranges when timestamps are on. Name the raw transcript's file: it holds everything that was removed, and it governs wherever the user cares about the exact wording.

## Limits

- English only. The bundled model is the English Parakeet v2 model.

- No speaker labels exist at any stage. Step 8 rests on content and turn-taking cues, and its keep-when-unsure rule is what keeps it honest; a recording with two speakers who alternate rapidly on the same topic will leave many passages flagged unattributed rather than removed.

- The marker phrases are the eight listed in step 2. A marker misheard into other words entirely is not found; step 2's zero-marker check is the guard, and the remedy is for the speaker to say the markers again in a re-recording, not for Muse to infer the boundaries from content.

- Timestamps are chunk-level, roughly 25 seconds, so a removal's reported time range names the chunks it spans, not the exact seconds of its first and last words. The trim itself is word-accurate in the text.

- Long files take a while on CPU. The chunk progress is the measure; report it, and do not promise a finishing time.

- A missing file, an unreadable format or a failed conversion is reported as-is. Do not fall back to another transcription service without the user's agreement, because that would send the audio off the machine.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- When the user needs speaker separation that can be relied on rather than judged, say so before the run: this skill has no diarisation tool, and the honest alternatives are the full transcript with passages flagged by likely speaker, or a separate diarisation pass outside this skill whose output is checked against the audio.

- When a passage stays uncertain after the correction stages, keep the slash form in the delivered transcript instead of choosing a term, so the user sees the doubt rather than a guess.
