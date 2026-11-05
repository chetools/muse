# Build a Keypoints Assignment (Teacher)

## Purpose

Build an explain-the-page assignment on the course server, in three phases:

- **The page.** The teacher's photographs of a handwritten equation page become the student page: a LaTeX source and an HTML fragment, containing only what the photographs contain.
- **The model take.** The teacher records the explanation in the recording app, as a student would. The audio is sealed on the course server, which holds it in custody only — the server never transcribes, here or anywhere in this flow.
- **The key.** You download the sealed model take, transcribe it locally with Parakeet, correct the transcript for chemical-engineering terms, and draft the answer key — key points and key connections — from the corrected transcript. The teacher corrects the draft and sets the weights; the approved key is uploaded to the server, and that upload is what opens the assignment to students.

## Trigger

Apply this skill when the teacher asks to create or set up a keypoints assignment, to turn photographs of handwriting into an assignment page, or to make the answer key from their model take. The teacher provides:

- the course server address (for example `https://seb-exams.example.com`),
- the exam ID of the assignment, which the teacher created in the teacher app (title, dates, roster) — the audit token is generated there too, and
- the audit token for that exam: read it from the environment variable `KP_AUDIT_TOKEN` when it is set; otherwise ask the teacher for it. The token is never printed in your replies and never written to a file; set it in the environment of the helper commands only.

If the server address or exam ID is missing, ask for it.

## Procedure

The helper script is `scripts/kp.mjs` in this skill's folder (Node, no dependencies). The transcription and correction helpers are `scripts/transcribe.py` and `scripts/correct.py`. The glossary lives in `glossary/`: `corrections.json` (heard form → term), `vocabulary.txt` (the term list for your contextual pass), and `glossary.json` (the full term record).

### Phase A — the page

1. The teacher supplies the photograph files and any arrangement instruction (which photograph comes first, and so on). If the order is unstated, propose the natural reading order and confirm it.
2. Read the handwriting in each photograph. Produce two files:
   - the **LaTeX source** of everything the photographs contain, and
   - the **page fragment**: one `<div class="tblock">` per photograph block, containing a `<div class="teq">` with the block's equation as HTML — `<sub>` and `<sup>` for indices, fractions as `<span class="frac"><span class="top">numerator</span><span class="bot">denominator</span></span>` — and a `<div class="tnote">` holding the block's handwritten words as plain text, beside the equation they belong to. A block with no handwritten words has no `.tnote`.
   
   The fragment contains only what the photographs contain: the equations, and the teacher's own handwritten words as text. Never add definitions, explanations, labels, or derived steps that do not appear in a photograph.
3. Show the teacher the blocks in order and confirm the arrangement. On confirmation, upload:
   `KP_AUDIT_TOKEN=<token> node scripts/kp.mjs page <server> <examId> <pageFile> <latexFile> <photoCount>`
   where `<photoCount>` is the number of photographs the page combines.

### Phase B — the model take

1. Enrol the teacher's own email as the model identity for this assignment:
   `KP_AUDIT_TOKEN=<token> node scripts/kp.mjs model-roster <server> <examId> <teacherEmail> <teacherName>`
2. Direct the teacher to the recording app: sign in with that email, open the assignment, and record the explanation in one take, going through the page as a student would, then seal the take.
3. Wait for the teacher to say the take is done. Do not proceed to Phase C on your own timing.

### Phase C — the key

1. Fetch the model take's session code:
   `KP_AUDIT_TOKEN=<token> node scripts/kp.mjs model <server> <examId>`
   If `model` is null, the take is not sealed yet — tell the teacher and wait.
2. Download the sealed audio:
   `node scripts/kp.mjs audio <server> <sessionCode> <outDir>`
   It writes one `slide-<n>.wav` per part and prints a manifest with each part's fingerprint.
3. Transcribe the parts locally, in slide order:
   `python3 scripts/transcribe.py <outDir>/slide-1.wav [<outDir>/slide-2.wav ...]`
   Parakeet runs on this machine; no audio or text leaves it. The first run may download the model (about 600 MB) — say so before running it the first time. Join the per-part transcripts into one transcript of the whole take.
4. Apply the glossary correction map:
   `python3 scripts/correct.py <transcriptFile> glossary/corrections.json`
   The corrected transcript goes to stdout; the corrections applied (`{heard, term, count}`) go to stderr as JSON.
5. Make a contextual pass over the corrected transcript against `glossary/vocabulary.txt` and the assignment page: change only clear sound-alike errors of listed terms, where the surrounding words settle which term was meant. Do not reword, complete unfinished statements, or repair content — a term correction is the only change allowed, and every change must be listable.
6. Show the teacher the corrected transcript with **every** correction listed — the mechanical ones from step 4 and your own from step 5, marked as yours.
7. Draft the answer key from the corrected transcript: the key points in the order the teacher made them, each point one or two sentences, each with its **connection** (the earlier points or quantities it rests on, or empty) and anchored to the page block it belongs to.
8. The teacher corrects the draft and sets the points weights, in conversation: points may be reworded, merged, dropped, or added; weights are positive numbers. Half credit (a point present but wrong — a broken connection is what makes a present point a half) is the standing scoring rule; the weights are the only numbers to settle.
9. Only on the teacher's explicit approval, write the key file `{"points": [{"text": "...", "connection": "...", "points": 20}, ...]}` and upload it:
   `KP_AUDIT_TOKEN=<token> node scripts/kp.mjs key <server> <examId> <keyFile>`
10. Report that the assignment is open: the uploaded key is what opens it, and the server response carries the total points and the number of points in the key.

## Limits

- The audit token is the credential for teacher-side writes on one exam. Use it only in the helper commands' environment, only against the course server the teacher named; never print it, never write it to a file, never send it anywhere else.
- The answer key is never shown to students. It exists in this conversation for the teacher to correct, and on the server for the grading comparison; do not put it in the page fragment, a student-facing file, or any other place a student could reach.
- Transcribe only the audio the helper downloaded from the course server under the model session code. A file the teacher hands you separately is not the sealed model take.
- Nothing in this flow asks the server to transcribe, and no transcript is uploaded: the server holds the sealed audio and, after approval, the key.
