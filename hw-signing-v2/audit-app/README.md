# Teacher audit app — HW Signing v2 (audit app v27)

**v27 (2026-11-09).** One display fix: the video wall's zoom
view preserves the critique's line breaks, so its numbered
points appear on separate lines. Everything else is as in
v26, below.

**v26 (2026-11-09).** Errors appear where the user can see
them: beside the control that was used, in the part of the
window on screen (the teacher's rule, both apps). On the
dashboard, Cleanup and Packages pages the error element moves
next to the activated control for action errors and returns
to the top for page-load and background errors; on the video
wall, a failed 480p download reports beside its button as
well as in the header line. Everything else is as in v25,
below.

**v25 (2026-11-09).** One fix: Build-and-verify link on the
Packages page fetched the package's full text twice to check
its status and hash, which on a connection that drops calls
took tens of seconds or failed; it now fetches metadata only
and answers in about a second. The link produced is unchanged.
Everything else is as in v24, below.

**v24 (2026-11-09).** The web front end gains a Packages page
(`/packages`): it lists every HW Signing v2 prompt package version
held on the grading Worker — status, trial, job counts, content
hash — and manages the lifecycle there (show the full text,
record a trial, open, close, retire, upload a new version as a
draft, and build the verified student link for an open package),
through the Worker's admin API with an admin token stored only
in the local config file. The audit functions are unchanged from
v23. The Worker support for reading a package text in slices
(?text_offset / ?text_length on the show endpoint) is Worker
2.3.0, deployed the same day; the unparameterised endpoint is
unchanged. The v23 description follows.

**v23 (2026-11-09).** This is the single audit app; it audits HW
Signing v2 packages only. A submission is one ZIP, `submission.zip`,
holding exactly `submission.html` and `submission-audio.wav`. The
v1 two-file form was eliminated at the teacher's direction: v1 is
outdated and such submissions will never occur, so v1 attempts are
not considered at all — there is no second app and no transition.
The original ZIP is kept as `package.zip` beside the extracted
files. Verification is v2: the package's grade receipt is verified
through the grading Worker's `/verify-grade`, the signed grades
must equal the grades shown in the HTML, the critique hash is
recomputed, and the YouTube link's video ID is hashed and compared
with the value recorded at grading time. A failed grade signature
holds back the suggested final grade and is badged on the
dashboard and warned about in the gradebook. The app's Worker
setting is the grading Worker; a config still carrying the v1
signing Worker address is migrated to it on load. What follows
describes the app as it now stands; earlier-version history is in
the paragraphs below where it still applies.

Local Python app for the teacher's own machine, with a browser front
end (`web.py`, see `README-WEB.md`: `run-web.bat` on Windows or
`run-web.sh` here, then http://127.0.0.1:8766) covering every command
below plus final-grade entry and Canvas Gradebook CSV export. The
command-line interface remains available. Built to
Build order step 7 of
`~/workspace/your_files/anonymous-grading-build-plan-2026-11-08.md` and
steps 21–29 of `anonymous-grading-steps-2026-11-08.md`. Read-only against
Canvas: it downloads submissions and never writes to Canvas.

**Audit v2 (2026-11-08, revised the same day).** The audit is
integrity-first for every submission: signing-receipt verification,
audio and transcript fingerprints, the prompt-injection scan and
the acoustic YouTube cross-check — no numbers are re-derived.
When integrity is clean, the student's grade stands — grading is holistic
(no key points, no connections, no checklist, no weights; see
`../AUDIT-v2.md`), so there is no tally to re-derive.

There is no re-grade. A re-grade by the teacher's Muse would be a
second sample of the same grading process, not an independent
standard, so the design does not use one — no grade bands, no
re-grade sample. Any case the teacher wants to decide — an injection
flag, a YouTube flag, an appeal, or a case they simply choose to
look at — is decided by the teacher: watch the video and read the
transcript on the video wall (web app) and enter the grade there or
in the dashboard's Final grade column. An entered grade is the
grade of record.

## Setup

1. Copy `config.example.json` to `config.json` and fill it in:
   - `canvas_base_url`, `canvas_token` — the token lives only in this
     file, on this machine; the app never prints it.
   - `worker_base_url` — the HW Signing v2 grading Worker address
     (its `/verify-grade` verifies grade receipts).
   - `course_id`, `assignment_id` — the Canvas File Upload assignment.
   - `acoustic_threshold` — YouTube cross-check fingerprint
     similarity band (0–1, default 0.85). The same recording after
     YouTube transcoding measures about 0.99; a different recording
     about 0.5.
   - `appeal_period_passed` — retained in the config for
     compatibility; cleanup no longer consults it (it requires only
     `--confirm`).
   - `data_dir` — where downloads, exports, segments and the mapping
     are kept (default: `data/` beside `audit.py`). Keep it in encrypted
     storage, per the flow's retention rules.
2. Dependencies: Python 3 standard library; `requests` is used for
   Canvas if installed, otherwise `urllib`. No other packages. The
   YouTube cross-check also needs `ffmpeg` with its chromaprint
   muxer (the standard full ffmpeg builds include it; yt-dlp
   already needs ffmpeg for merging video).

## Commands

```
python3 audit.py --config config.json download [--force]
python3 audit.py --config config.json check-all
python3 audit.py --config config.json verify-package AUDIO.wav PACKAGE.html
python3 audit.py --config config.json export
python3 audit.py --config config.json youtube-check AUDIO.wav YOUTUBE.mp4 PACKAGE.html
python3 audit.py --config config.json cleanup --confirm
```

- `download` — lists submissions for the assignment and downloads
  the ZIP of each student's most recent attempt whose attempt holds
  a `.zip` attachment. The ZIP is stored as `package.zip` and
  extracted beside it (`submission.html`, `submission-audio.wav`);
  extraction rejects absolute paths, `..` components, any entry set
  other than exactly those two names, and oversize entries (200 MB
  per entry, 250 MB total). A structurally invalid ZIP produces an
  error record and nothing is extracted. A watermark
  (`download-state.json`: submission id, time, attempt, ZIP SHA-256)
  skips unchanged packages.
- `check-all` / `verify-package` — recomputes the audio fingerprint
  (SHA-256 of the audio file bytes), the transcript checksum
  (SHA-256 of the canonical transcript recovered from the grading
  section: scrubbed plain text, one chunk per line, LF, timestamps
  stripped) and the critique SHA-256 (the critique is the text of
  `<p class="critique">` in the grading section, whitespace-stripped,
  hashed as UTF-8), and verifies the grade receipt with the grading
  Worker's `/verify-grade`. The verification request carries the
  grades shown in the HTML, so it passes only when the shown grades
  are the signed grades; the verification section's own grade lines
  are compared against the shown grades as a separate check
  (`grades_match`). The YouTube link's video ID is hashed and
  compared with the package's recorded value (`youtube_id_ok`); it
  is reported separately and does not enter internal consistency.
  Reports each check separately; a package whose format version is
  not 2, or with any of the audio, transcript, critique, receipt or
  grade-match checks failing, is internally inconsistent.
- `export` — writes each package's grading section only (no summary, so
  no YouTube link; no verification section) to `exports/<CODE>.html`,
  with a random 6-character code per package from a CSPRNG, assigned in
  shuffled order — no relation to name, submission order, or time. The
  code-to-student mapping goes to `mapping.json` in the data folder
  only (permissions 0600 where the OS supports it) and never leaves
  this machine.
- `youtube-check` — the acoustic cross-check that the YouTube
  portfolio video is the same recording as the submitted WAV.
  Compares the two durations (flag beyond the larger of 2 s and
  2 % of the WAV duration) and their Chromaprint fingerprints,
  computed by ffmpeg over the whole recording: similarity is
  1 minus the fingerprint bit error rate at the best alignment
  within about 1 s, reported overall and per third of the
  recording. A byte hash cannot do this — YouTube transcodes
  every upload — but the fingerprint is built from the
  spectrogram and survives transcoding (measured: 0.99+
  similarity for the same take after AAC or Opus transcoding,
  about 0.5 for a different take). Below `acoustic_threshold`
  the package is flagged. No transcription is involved, so the
  check takes seconds and needs no re-transcription setup; if
  ffmpeg or chromaprint is missing it reports itself not
  configured rather than passing. In the web app it runs inside
  Run integrity checks once the video has been downloaded.
  Separately, `check_package` scans the submitted transcript for
  instruction-like text (demands to ignore instructions, demands for
  full marks, an embedded fake result block, and similar;
  `scan_injection`), and reports `injection_matches` /
  `injection_suspected`; a flagged case is likewise the teacher's
  to decide.
- `cleanup` — deletes downloads (the whole package folder,
  `package.zip` included), coded exports, segments, reference
  transcripts, the mapping, and the watermark. Requires
  `--confirm`.

## Package format the app reads

One ZIP per submission, `submission.zip`, containing exactly
`submission.html` and `submission-audio.wav` (the webapp writes
fixed 1980-01-01 entry timestamps, so a rebuilt ZIP is
byte-identical). The HTML sections are in plan order —
`<section id="summary">` (clickable YouTube link; signed grades as
`<span data-grade="completeness">` / `<span data-grade="accuracy">`),
`<section id="grading">` (transcript as `<pre class="transcript">`
with one `[mm:ss] text` line per chunk, the same signed grades, the
critique as `<p class="critique">`, empty nested audit section),
and `<section id="verification">` (a `<dl>` with the labels Format
version, Job, Prompt package, Prompt package content SHA-256,
Webapp version, Model version, Glossary version, YouTube link,
Audio file, Audio duration in s, Audio SHA-256, Transcript
SHA-256, Completeness, Accuracy, Critique SHA-256, YouTube video
SHA-256, Graded at, Grade receipt).

## Tests

```
python3 tests/test_audit.py
```

63 checks. Fixtures are synthetic: a 300 s, 16 kHz mono WAV
generated in code and a v2 HTML package whose fingerprints are
computed from the fixtures, packaged as a ZIP with fixed
1980-01-01 entry timestamps. Grade receipts are computed with a
Python replica of the v2 grading Worker's canonicalisation (the
SPEC's result bundle, HMAC-SHA-256, base64url) with a test secret,
and `/verify-grade` is a fake transport that recomputes the same
way; the Worker's own cryptography is covered by the Worker suite.
Covered: a good v2 package passes every check; the SPEC tamper
cases — a grade edited in the HTML spans fails the grade
signature, a grade line edited in the verification section fails
`grades_match`, an edited critique fails its hash, wrong audio
bytes fail the fingerprint, an edited transcript fails its
checksum, a receipt from a foreign secret fails, a YouTube link
to a different video fails `youtube_id_ok`, a v1-format HTML is
not internally consistent, a ZIP with an extra entry is rejected
at download, traversal and absolute entries are rejected with
nothing written outside the package folder, and oversize entries
are rejected; a v1 two-file attempt does not qualify; coded
exports contain no YouTube link and no verification data, with
unique codes not in submission order; download watermarking keyed
by the ZIP SHA-256; the absence of the removed listening check;
the YouTube acoustic cross-check (same fingerprint passes,
different fingerprint flags, a duration mismatch flags even with
the same fingerprint, a missing video is neither a pass nor a
flag, and — through the real ffmpeg — an AAC-transcoded copy of a
take passes while a different take flags); the absence of the
removed re-grade machinery; cleanup refusals and deletion,
`package.zip` included. (There is no listening check: it was
removed in v14 at the teacher's direction — it had never been
configured in production, and whether the transcript matches the
spoken audio is the teacher's judgement from the video wall.)
