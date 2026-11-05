# Transcribe Audio with Parakeet and the Chemical-Engineering Glossary

## Purpose

Transcribe an audio file the user points to or uploads, on this machine, and correct the transcript for technical terms. The recogniser is NVIDIA Parakeet TDT 0.6B v2 in int8 form, run locally through `onnx-asr`. The correction knowledge is the bundled glossary in `glossary/`: `glossary.json` (755 chemical-engineering and general-engineering terms in 17 categories, each with its risk reasons), `vocabulary.txt` (the 744-term vocabulary drawn from it), and `corrections.json` (203 sound-alike correction pairs, each marked attested or predicted).

The user this skill serves speaks engineering: lectures, spoken explanations, interviews, meetings, dictation. General recognisers render that vocabulary badly (the attested examples in the glossary include fugacity heard as "GASB" and the Antoine equation heard as the "Anaconda equation"), so the transcript is corrected in two passes after recognition, and every correction is listed so the user can check it.

## Trigger

Apply this skill when the user asks to transcribe a recording or points you at an audio file and asks what was said. The file may be an upload in the chat, a path on this machine, or a file in the workspace. Common formats all work: WAV, MP3, M4A, WebM, OGG, MP4 and anything else ffmpeg reads. Several files may be transcribed in one run, in the order given, as one transcript per file.

If the user names a topic ("this is a distillation lecture") or supplies extra terms, use them in the contextual correction pass. If no file is identified, ask which file.

## Setup (one time)

Transcription runs through `scripts/transcribe.py` in this skill's folder. It needs two things on the machine:

```
python3 -m pip install onnx-asr
```

and ffmpeg on the system path (macOS `brew install ffmpeg`, Debian/Ubuntu `sudo apt install ffmpeg`, Windows `winget install ffmpeg`).

The first transcription run downloads the Parakeet model (about 670 MB) to a local cache; later runs reuse it. If `transcribe.py` reports the setup is missing, walk the user through the two installs and stop there. Do not transcribe by any other means, and never reconstruct what was said from context, notes or guesswork.

Privacy properties to state when the user asks: the audio never leaves this machine and no transcription service is called. ONNX Runtime sends telemetry to Microsoft by default, so the runner sets `ORT_DISABLE_TELEMETRY=1` and calls `disable_telemetry_events()` before the model loads. Keep both lines in any edit of the script.

## Procedure

Helpers: `scripts/transcribe.py` and `scripts/correct.py`, both in this skill's folder, plus the glossary in `glossary/`.

1. **Transcribe.**
   `python3 scripts/transcribe.py <file> [more files ...]`
   The script converts each file to 16 kHz mono WAV in a temporary folder when it is not already in that form, cuts long audio at quiet points near 25 s targets, and prints one transcript per file to stdout. Progress and chunk notes go to stderr: on a long file, tell the user transcription is running and report the chunk progress rather than leaving them with no word. Save stdout as the raw transcript, one file per recording, named `<audio-name>.raw.txt` beside the audio file or in the workspace location the user named.

2. **Apply the correction map.**
   `python3 scripts/correct.py <rawFile> glossary/corrections.json > <correctedFile>`
   It replaces known sound-alike mishearings with the listed terms (case-insensitive, whole phrases, longest first, single pass so inserted text is never rescanned) and reports on stderr a JSON list of every correction it applied, with counts. Name the result `<audio-name>.corrected.txt`.

3. **Review every applied correction.** The map output is never delivered unreviewed. Read each applied correction against the raw transcript and its context, and revert any where the heard form was the speaker's genuine word. The standing traps are pairs whose heard form is an ordinary English word, for example "gives" corrected to Gibbs, "ideas" corrected to Gibbs, "viral" corrected to virial, "do point" corrected to dew point: each is attested or predicted for a real mishearing and each is also a word a speaker may simply have said. A correction stands only where the surrounding words support the technical reading.

4. **Make a contextual pass.** Read the reviewed transcript against `glossary/vocabulary.txt`, plus any topic or terms the user supplied. Change only clear sound-alike errors of listed terms: a word that makes no sense in context where a listed term sounds like it. Do not correct the speaker's own wrong terms, wrong statements or grammar: a speaker who said the wrong term is transcribed as saying it. Flag passages that stay uncertain rather than guessing at them, and list them separately. Numbers, units and negations are never changed silently: if one looks wrong, flag it in the report and leave the text as transcribed.

5. **Deliver.** Give the user the corrected transcript (in the reply for a short recording, as the `.corrected.txt` file for a long one), the list of corrections with each reversion from step 3 noted, and the uncertain passages from step 4. State the raw transcript's file name as well: the raw transcript is the record, and the corrected transcript is a separate, marked layer over it. Where the two disagree and the user cares about the wording, the raw transcript and the audio govern.

## Limits

- English only. The v2 model bundled by `onnx-asr` under this name is the English model; for other languages, say so and stop rather than producing a poor transcript silently.
- No speaker labels and no timestamps. The runner returns text per chunk; chunk boundaries (printed to stderr, in seconds) give approximate locations when the user asks where something was said, and nothing finer.
- Long files take a while on CPU. The chunk progress on stderr is the measure; report it, and do not promise a finishing time.
- The correction map's pairs are 7 attested and 196 predicted (the status field in `corrections.json`). Predicted pairs are candidates for review, not established errors, which is why step 3 is mandatory.
- A missing file, an unreadable format or a failed conversion is reported as-is. Do not fall back to another transcription service without the user's agreement, because that would send the audio off the machine.
