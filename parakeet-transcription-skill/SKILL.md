# Transcribe Audio with Parakeet and the Chemical-Engineering Glossary

## Purpose

Transcribe an audio file the user points to or uploads, on this machine, and correct the transcript for technical terms. The recogniser is NVIDIA Parakeet TDT 0.6B v2 in int8 form, run locally through `onnx-asr`. The correction knowledge is the bundled glossary in `glossary/`: `glossary.json` (755 chemical-engineering and general-engineering terms in 17 categories, each with its risk reasons), `vocabulary.txt` (the 744-term vocabulary drawn from it), and the 203 sound-alike correction pairs in two classes — `corrections.json` (145 certain pairs, each marked attested or predicted, replaced outright) and `slash-pairs.json` (58 uncertain pairs, decided by the context rules in `context-rules.json` or rendered in slash form).

The user this skill serves speaks engineering: lectures, spoken explanations, interviews, meetings, dictation. General recognisers render that vocabulary badly (the attested examples in the glossary include fugacity heard as "GASB" and the Antoine equation heard as the "Anaconda equation"), so the transcript is corrected in stages after recognition — a certain-pair map, then context-rules choices among the uncertain pairs — and every correction and choice is listed so the user can check it.

## Trigger

Apply this skill when the user asks to transcribe a recording or points you at an audio file and asks what was said. The file may be an upload in the chat, a path on this machine, or a file in the workspace. Common formats all work: WAV, MP3, M4A, WebM, OGG, MP4 and anything else ffmpeg reads. Several files may be transcribed in one run, in the order given, as one transcript per file.

If the user names a topic ("this is a distillation lecture") or supplies extra terms, use them in the contextual correction pass. If no file is identified, ask which file.

Timestamps are an option the user chooses: off by default, on when the user asks for them ("with timestamps", "timestamped transcript"). With the option on, every chunk of the transcript carries its time range in the recording. When the user has not chosen and the recording is long, offer the choice in one line before transcribing; a short recording does not need the question.

## Setup (one time)

Transcription runs through `scripts/transcribe.py` in this skill's folder. It needs two things on the machine:

```
python3 -m pip install onnx-asr
```

and ffmpeg on the system path (macOS `brew install ffmpeg`, Debian/Ubuntu `sudo apt install ffmpeg`, Windows `winget install ffmpeg`).

The first transcription run downloads the Parakeet model (about 670 MB) to a local cache; later runs reuse it. If `transcribe.py` reports the setup is missing, walk the user through the two installs and stop there. Do not transcribe by any other means, and never reconstruct what was said from context, notes or guesswork.

Privacy properties to state when the user asks: the audio never leaves this machine and no transcription service is called. ONNX Runtime sends telemetry to Microsoft by default, so the runner sets `ORT_DISABLE_TELEMETRY=1` and calls `disable_telemetry_events()` before the model loads. Keep both lines in any edit of the script.

## Procedure

Helpers: `scripts/transcribe.py`, `scripts/correct.py` and `scripts/context_choice.py`, all in this skill's folder, plus the glossary in `glossary/`. The correction stages run in a fixed order: the certain correction map, then the context-rules choices among the uncertain pairs, then review, then the contextual pass. A stage never reaches back into an earlier stage's output.

1. **Transcribe, showing the words as they land.**
   `python3 scripts/transcribe.py [--timestamps] --partial <audio-name>.partial.txt <file> [more files ...]`
   Add `--timestamps` when the user chose timestamps: each chunk is then printed on its own line prefixed with its time range, `[mm:ss-mm:ss]` (`h:mm:ss` past one hour). Without the flag the script prints one plain transcript line per file. The script converts each file to 16 kHz mono WAV in a temporary folder when it is not already in that form, and cuts long audio at quiet points near 25 s targets, so a timestamp names the roughly 25 s span its chunk was spoken in, not an exact word time. Save stdout as the raw transcript, one file per recording, named `<audio-name>.raw.txt` beside the audio file or in the workspace location the user named.
   
   Intermediate progress is part of the delivery, not an extra: the user sees the words while the work runs, in every case where the run lasts more than one chunk.
   - Run the transcription so its progress can be followed (a background run whose output can be polled, or an equivalent live arrangement). After every chunk the script writes the transcript so far to the `--partial` file and prints a `WORDS ... chunk i of n [start-end s]: <text>` line to stderr.
   - Each time a new chunk appears, show it to the user before transcribing the next chunk is reported as done: the chunk number and its time range, a progress count (chunk i of n, words so far, and a progress indicator for the run), the raw words exactly as transcribed, and then the same chunk after step 2's correction map, step 3's context-rules choices and step 4's review, with that chunk's corrections listed. Append each reviewed chunk to `<audio-name>.partial.corrected.txt`, so the corrected progress also survives an interruption.
   - The per-chunk correction is a progress display. A phrase split across a chunk boundary can be corrected differently there than in the full text, so the final full-text passes in steps 2–5 still govern the delivered transcript, and any difference between the per-chunk display and the final text is stated in the delivery.

2. **Apply the correction map (certain pairs).**
   `python3 scripts/correct.py <rawFile> glossary/corrections.json > <correctedFile>`
   `corrections.json` holds only the 145 certain pairs. It replaces known sound-alike mishearings with the listed terms (case-insensitive, whole phrases, longest first, single pass so inserted text is never rescanned) and reports on stderr a JSON list of every correction it applied, with counts. Name the result `<audio-name>.corrected.txt`.
   For one chunk of intermediate progress, the same map runs without a file: `python3 scripts/correct.py --text "<raw chunk>" glossary/corrections.json`, with the same stdout and stderr contract.

3. **Make the context-rules choices (uncertain pairs).**
   `python3 scripts/context_choice.py <correctedFile> glossary/slash-pairs.json glossary/context-rules.json [--topic "<topic>"] > <ruledFile>`
   The 58 uncertain pairs are not in the correction map. For each occurrence, this stage scores the pair's candidates against the words around the slot using `context-rules.json` (phrase patterns, the words that typically stand before and after, topic words, and cues that rule a candidate out; single-word stopword cues are dropped before scoring). A candidate is chosen only at the calibrated bar — top score at least 8 and at least 3 ahead of the runner-up — and every choice is logged on stderr with the cues that fired and all candidates' scores. Choosing an ordinary candidate, or one that is the heard word itself, keeps the word as heard. Below the bar the stage abstains and writes the pair's slash form instead — the heard word first, then the possibilities, slash-separated with no spaces, as in `viral/virial equation/virial coefficient` — and the passage stays for steps 4 and 5. Pass the user's topic with `--topic` when one was given; it counts as topic evidence. The `--text "<chunk>"` form does the same for one chunk of intermediate progress. Name the result `<audio-name>.ruled.txt`.

4. **Review every applied correction and choice.** Neither the map output nor the rules output is delivered unreviewed. Read each applied correction, each logged context choice and each slash rendering against the raw transcript and its context, and revert any where the heard form was the speaker's genuine word. The standing traps are pairs whose heard form is an ordinary English word, for example "gives" for Gibbs free energy, "ideas" for Gibbs free energy, "viral" for virial, "do point" for dew point: each is attested or predicted for a real mishearing and each is also a word a speaker may simply have said. A correction stands only where the surrounding words support the technical reading.

5. **Make a contextual pass.** Read the reviewed transcript against `glossary/vocabulary.txt`, plus any topic or terms the user supplied. Change only clear sound-alike errors of listed terms: a word that makes no sense in context where a listed term sounds like it. Do not correct the speaker's own wrong terms, wrong statements or grammar: a speaker who said the wrong term is transcribed as saying it. Flag passages that stay uncertain rather than guessing at them, and list them separately — a slash form left standing by step 3 is already such a flag; leave it in the text. Numbers, units and negations are never changed silently: if one looks wrong, flag it in the report and leave the text as transcribed.

   Timestamp prefixes pass through every correction step untouched: the stages replace words inside the chunk text only, the contextual pass never edits a time value, and the corrected transcript keeps the same prefixes on the same chunks, so a corrected line is found at the same place in the recording as its raw line.

6. **Deliver.** Give the user the corrected transcript (in the reply for a short recording, as the final stage's file for a long one), the list of corrections with each reversion from step 4 noted, the context choices step 3 logged, and the uncertain passages from step 5 (with their time ranges, when timestamps are on). State the raw transcript's file name as well: the raw transcript is the record, and the corrected transcript is a separate, marked layer over it. Where the two disagree and the user cares about the wording, the raw transcript and the audio govern.

## Limits

- English only. The v2 model bundled by `onnx-asr` under this name is the English model; for other languages, say so and stop rather than producing a poor transcript silently.
- No speaker labels. Timestamps, when the user chooses them, are chunk-level: each names the roughly 25 s span a chunk covers, not the moment a word was spoken, and nothing finer is available from this runner.
- Long files take a while on CPU. The chunk progress on stderr is the measure; report it, and do not promise a finishing time.
- The correction pairs are 7 attested and 196 predicted, split by the cleanup into 145 certain pairs (`corrections.json`, with the status field) and 58 uncertain pairs (`slash-pairs.json`). Predicted pairs are candidates for review, not established errors, which is why step 4 is mandatory.
- The context rules choose only at the calibrated bar (top score at least 8, margin at least 3). On the research benchmark that bar gave 0.968 accuracy on the cases it decided and correct abstention on 59 of 62 no-cue controls; the benchmark is synthetic and source-derived, not field accuracy on real recordings, so the review step stays mandatory for rule-made choices too.
- A missing file, an unreadable format or a failed conversion is reported as-is. Do not fall back to another transcription service without the user's agreement, because that would send the audio off the machine.
