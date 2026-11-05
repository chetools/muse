# Grade a Keypoints Explanation (Sealed Audio Take)

## Purpose

Grade a student's sealed spoken explanation of a teacher's handwritten page against the teacher's answer key, and upload the corrected transcript, the feedback, and the per-point grades to the course server.

The assignment works like this. The student read a page typeset from the teacher's handwriting and explained it aloud in one recording in the app. The audio was sealed when it was recorded and is held by the course server. The answer key — the key points, their connections, and a points value per point — was drawn from the teacher's own model explanation and approved by the teacher. The key reaches you only after the student's take is sealed, and it is **never shown to the student**: not quoted, not paraphrased point by point as a list, not hinted at as "the key says". The student sees feedback about their own explanation, a score for this attempt, and their standing grade.

Grading is formative. Every upload is one attempt, and attempts are unlimited: the standing grade is the best attempt's grade, and a weaker attempt never lowers it. There is no final submission in this flow — never mark an attempt final, and never send a "final" flag.

## Trigger

Apply this skill when the student pastes the grading block for a keypoints assignment, or asks to grade their explanation take and provides:

- the course server address (for example `https://seb-exams.example.com`),
- the assignment (exam) ID, and
- the sealed session code, printed in the summary of their recording app (labelled "Sealed session").

If any of the three is missing, ask for it. Do not grade from a re-recording, a file the student hands you, or a pasted transcript: without the session code there is no sealed record to grade against, and only the audio served by the course server under that code is the sealed audio.

## Setup (one time, for transcription)

Transcription runs locally with Parakeet, through `scripts/transcribe.py` in this skill's folder; nothing is uploaded for transcription. It needs the `onnx-asr` package:

```
python3 -m pip install onnx-asr
```

The first transcription run also downloads the Parakeet model (about 670 MB) to a local cache; later runs reuse it. If `transcribe.py` reports the setup is missing, walk the student through the install command above and stop there — do not transcribe by any other means, and never write a transcript from the answer key, the assignment page, or guesswork.

## Procedure

Helpers: `scripts/kpgrade.mjs` (Node, no dependencies), `scripts/transcribe.py`, and `scripts/correct.py`, all in this skill's folder. The bundled glossary lives in `glossary/`: `corrections.json` (the sound-alike correction map), `vocabulary.txt` (the chemical-engineering terms list), and `glossary.json` (the full glossary the vocabulary is drawn from).

1. **Fetch the grading packet.**
   `node scripts/kpgrade.mjs packet <server> <sessionCode>`
   The packet contains the exam (confirm its ID matches the assignment in the pasted block), the rubric — one element per key point, named `Point 1`, `Point 2`, …, with the key point's text and connection carried in each element's guidance — and the sealed audio list (segment numbers, titles, and a fingerprint per segment).
2. **Download the sealed audio.**
   `node scripts/kpgrade.mjs audio <server> <sessionCode> <outDir>`
   It writes one `slide-<n>.wav` per segment and prints each segment's fingerprint from the packet. Transcribe only these files, in segment order.
3. **Transcribe locally.**
   `python3 scripts/transcribe.py <outDir>/slide-1.wav [<outDir>/slide-2.wav ...]`
   It prints one transcript per file, in argument order; save the output as the raw transcript, one line per segment, and assemble it in the packet's format: `<n> (<segment title>): <what was said in that segment>`, using the titles from the packet. If the setup is missing, follow the Setup section and stop.
4. **Correct the transcript for technical terms.** Two passes, in this order:
   a. The correction map: `python3 scripts/correct.py <rawTranscriptFile> glossary/corrections.json > <correctedFile>`. It replaces known sound-alike mishearings with the listed terms (case-insensitive, whole phrases, longest first) and reports on stderr which corrections it applied.
   b. A contextual pass by you, against `glossary/vocabulary.txt`: read the mapped transcript and change **only** clear sound-alike errors of terms in the vocabulary — a word the transcription produced that makes no sense in context where a listed term sounds like it. Do not correct the student's own wrong terms, wrong statements, or grammar: a student who said the wrong term is graded on having said it. When in doubt, leave the word as transcribed.
   The corrected transcript replaces the raw one: delete the raw transcript file, and keep and upload only the corrected transcript. (The sealed audio itself stays on the server; that is the record.)
5. **Fetch the answer key.**
   `node scripts/kpgrade.mjs key <server> <sessionCode>`
   It returns `{points: [{text, connection, points}], totalPoints}` — point *n* in this list is rubric element `Point n` and packet guidance entry *n*. Hold the key in this grading session only; it does not go into the feedback, the upload, or anything the student sees.
6. **Compare the corrected transcript against the key.** For each point assign a fraction: **1** (full) — the point is made, correctly; **0.5** (half) — the point is present but wrong in a way you can state, **or** a connection the key states is broken: the student uses a result before establishing what it rests on, or skips a stated dependency; **0** — the point is absent, or so wrong that nothing of it stands. The order of the student's explanation is their own: an order difference that breaks no stated connection is noted in the feedback and never faulted.
7. **Write the feedback.** One short paragraph per point, in the student's own terms of reference: name what their explanation did, and what it lacked or got wrong, against that point — "your equilibrium ratio appears without its source", not the key's sentence. Never quote the key's wording, never number or list the key's points as the key, and never reveal a point the student missed by stating it as the standard; state the lack ("the explanation never returns to the compositions the problem asks for") so the student knows what to repair without being handed the key. Note order differences that broke nothing as neutral observations.
8. **Upload.** Write a JSON file `{"transcript": "<the corrected transcript>", "critique": "<the feedback>", "grades": {"Point 1": 1, "Point 2": 0.5, ...}}` with one grades entry per point, named exactly `Point 1`, `Point 2`, … in key order, then run
   `node scripts/kpgrade.mjs submit <server> <sessionCode> <file>`.
   Send no "final" flag — this flow has none.
9. **Report the standing grade and the outcome.**
   `node scripts/kpgrade.mjs standing <server> <sessionCode>`
   Show the student the feedback, this attempt's score (`score` of the latest attempt, out of `max`), and the standing grade (`standing`, the best attempt's score). Tell them they may re-record in the app and be graded again whenever they are ready, and that a weaker attempt never lowers the standing grade. Do not show the student the answer key at any point in the report — the feedback is the whole of what the key produces for them.

## Limits

- The session code is the credential for grading one sealed take. Do not use it for any other purpose, and do not send it anywhere except the course server named by the student.
- Transcribe only the files the helper downloaded from the course server in this session. A file the student hands you separately is not the sealed audio, even if it sounds the same.
- The answer key is grading material, not course material: it stays out of the feedback, the report, and any file you leave where the student can read it.
- Keep only the corrected transcript. The raw transcript is an intermediate; delete it once the corrected transcript exists.
- A failed upload (server error, unknown code) is reported to the student as-is; do not retry with altered grades or an altered transcript to make it pass.
- Grades are fractions of each point; the server computes scores from the key's points values.
