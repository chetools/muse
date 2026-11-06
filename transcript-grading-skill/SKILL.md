# Grade a Sealed Transcript or Sealed Audio Take

## Purpose

Grade a student's sealed spoken-explanation take with the teacher's own prompt and rubric, and upload the critique and grades to the course server. Takes come in two sealed forms:

- **Text-sealed:** the server holds the master transcript, sealed when it was recorded. Grade that text; a swapped or edited transcript is detected by the server and refused.
- **Audio-sealed:** the server holds the student's per-slide audio, sealed when it was recorded (the app shows an audio fingerprint). There is no master text: *you* transcribe the sealed audio, grade your transcript, and upload all three — transcript, critique, and grades. The server stores your transcript as the student's-Muse transcript; the server never transcribes. The sealed audio stays on the server, and a take the student marks final is guarded differently: the teacher's Muse transcribes the same sealed audio independently and the server compares the two transcripts — that comparison, not a server transcription, is what a final grade rests on.

## Trigger

Apply this skill when the student says "grade this", "grade my transcript", "transcribe and grade this", or similar, and provides (or has provided) two things:

- the course server address (for example `https://seb-exams.example.com`), and
- the sealed session code, which is printed in the summary of their recording app (labelled "Sealed session").

If either is missing, ask for it. Do not grade from a pasted transcript or a re-recorded audio file alone: without the session code there is no sealed record to grade against, and only the audio served by the course server under that code is the sealed audio.

## Procedure

The helper script is `scripts/grade.mjs` in this skill's folder (Node, no dependencies).

1. **Fetch the grading packet.**
   `node scripts/grade.mjs packet <server> <sessionCode>`
   The packet contains the exam title, the teacher's grading prompt, the rubric (element names, points, guidance), the student's variation item, and either the sealed transcript or the sealed audio list (slide numbers, titles, and a fingerprint per slide).
2. **Text-sealed take** (`transcript` in the packet is not null): grade the packet transcript, as in step 4. If the student also pasted a transcript, save it to a file and check it with `node scripts/grade.mjs verify <server> <sessionCode> <file>`; if it does not match, tell the student plainly that the pasted text is not the sealed transcript, and grade the sealed one either way.
3. **Audio-sealed take** (`transcript` is null and `audio` lists the slides):
   a. Download the sealed audio: `node scripts/grade.mjs audio <server> <sessionCode> <outDir>`. It writes one `slide-<n>.wav` per slide and prints each slide's fingerprint from the packet.
   b. **Transcribe each file yourself, in slide order.** Listen to the actual files. Transcribe exactly what is said: do not correct wrong terms, complete unfinished statements, or tidy grammar — the grading must judge what the student said. If you cannot play or hear audio files in your environment, say so plainly and stop; never write a transcript from the slide titles, the rubric, or guesswork.
   c. Assemble the transcript in the packet's format, one line per slide: `<n> (<slide title>): <what was said on that slide>`, using the titles from the packet.
4. **Grade.** Follow the teacher's prompt in the packet exactly, judging the transcript against every rubric element. For each element assign a fraction from 0 to 1 (1 = full credit for that element). Apply each element's guidance: for example, the introduction, relevance, summary and conclusion elements are judged by whether what the student said does the work that part is supposed to do. Write the critique as feedback to the student, naming what was correct, what was missing or wrong, element by element. For an audio take, quote the student's words from your transcript.
5. **Upload.** Write a JSON file `{"critique": "<the critique>", "grades": {"<element name>": <fraction>, ...}}` with one entry per rubric element, using the element names exactly as given in the packet. For an audio-sealed take, add `"transcript": "<your assembled transcript>"`. Then run
   `node scripts/grade.mjs submit <server> <sessionCode> <file>`.
   **Practice or final.** Attempts are practice by default, and practice is unlimited: the student records a take, gets the feedback, records again, as often as they want. Only when the student says this attempt is the one to submit for a grade ("submit this as final", "this is my final") do you add `"final": true` to the result file. Never mark an attempt final on your own judgement of its quality. A final submission locks the exam for that student until the teacher releases it, and the grade is set only after the teacher's Muse validates it.
6. **Report the outcome to the student.** The submit response carries `status`, `auditStatus`, and, for audio takes, `transcriptionCheck`:
   - `status: "graded"` — a practice attempt: show the feedback and grades, and tell the student they can record another take whenever they are ready.
   - `status: "awaiting_validation"` — a final submission: tell the student it is with the teacher for validation, and that the validated grade is the one that counts.
   - `status: "flagged"` — one or more elements differ from the server's audit grade by more than a quarter of the element's range, or (audio takes) your transcript's word similarity to the server's transcription is below 0.6. Tell the student the submission is flagged for the teacher to settle, and show what was flagged.
   Show the student the transcript you graded (for audio takes, the one you made), the critique, and the per-element grades in the reply.

## Limits

- The session code is the credential for grading one sealed take. Do not use it for any other purpose, and do not send it anywhere except the course server named by the student.
- For audio takes, transcribe only the files the helper downloaded from the course server in this session. A file the student hands you separately is not the sealed audio, even if it sounds the same.
- A failed upload (server error, mismatch) is reported to the student as-is; do not retry with altered grades or an altered transcript to make it pass.
- Grades are fractions of each element; points are computed by the server from the rubric.
