# Teacher audit app — HW Signing v2 (audit app v69)

**v69 (2026-11-27).** The wall's durability rebuild,
from the teacher's report that every video plays at
first and develops problems over a session — under
sustained many-tile load, in the teacher's default
browser (Firefox; every wall harness to date runs
Chromium). (1) The app now opens in Chrome when
Chrome is installed: the opener (the program's own,
since v37 — the launchers deliberately no longer open
the browser) resolves Chrome from the App Paths
registry or the standard install paths and starts it
with a dedicated profile stored in the app folder
(`browser-profile`), so the teacher's own profile and
its extensions cannot interfere; with no Chrome
installed the default browser opens, as before. The
wall also reports the browser's user-agent to the
Activity log once per load, so a future report names
the browser without the teacher having to say it.
(2) The wall's playback supervision is rebuilt around
one desired state and one reconciler. The v64–v68
stall watchdog had accreted a branch per failure
state, and tiles still stranded in states no branch
covered. Now `WALLSTATE` holds the wall's desired
state in one place (the master fraction, wall-level
playing, the tiles individually set playing or paused
by the teacher, the speed; the grouping/filter
selection stays in the persisted shared view),
persisted to localStorage, and a single periodic
reconciler compares each showing tile with the
desired state and applies the one matching correction
from a single decision table — an errored element
reloaded at its accounted fraction (the v67 recovery,
bounded retries with growing delays), an unlanded
seek target owed recovery with the v65 growing
patience, a stuck seek re-issued (v60), a tile that
should be playing but is paused played — escalating
to a reload after three ineffective plays (v67) — or
reloaded at its position when starved, a tile that
should be paused but is playing paused, a tile away
from the master fraction sought to it, a tile that
never got its frame nudged (v52). The seek and play
helpers express intent in the state and give it a
head start; correction is the reconciler's alone, and
a deferred play superseded by a pause no longer
fires. The desired state is restored after the zoom
round trip and across page loads: the wall returns at
the persisted fraction — before v69 Back sought every
tile to the zoom video's fraction, so a zoom whose
video never loaded (fraction 0) reset the whole wall
to 0%; the zoom's position now replaces the persisted
fraction only when the zoom video actually has one.
(3) Wall proxy files cut the sustained load: at
video-download time, and for videos already
downloaded in the background pass, the app's ffmpeg
makes a low-resolution proxy of each wall video (at
most 640 px wide, frame rate capped at 30, H.264/AAC
in MP4, audio at 48 kbit/s) beside the original; the
wall's tiles play the proxy when one exists and the
original otherwise, and the zoom view always plays
the original. Generation is background work — it
never blocks a download or a check, a failure leaves
the original in use, and the check fingerprint still
covers the original file only, so a proxy appearing
invalidates no stored check. Without ffmpeg
everything degrades to the pre-v69 behaviour.
Regression: `tests/wall_regression_v69.py` (headless
Chromium: a tile stranded with no legacy flags is
corrected by the reconciler, the zoom round trip
restores the persisted fraction, and the proxy wiring
and size effect are measured), the wall harnesses
v61 and v64–v68 and `tests/layout_regression_v68.py`
unchanged, plus checks in `tests/test_web.py`.

**v68 (2026-11-27).** Two teacher-reported defects.
(1) The Setup section's two columns were coupled and
wasteful: the Save settings row, the course details and
the status line sat below the two-column row as
full-width siblings, so expanding the “How this
works” details in the Activity column pushed all of
them down by the details' height (measured on v67:
82 px), and the flex row's default stretch sized the
settings column's box by the Activity column's
content, leaving a void under the settings fields.
The buttons, course details and status line now live
inside the settings column, the row aligns its
columns to the start (each column is as tall as its
own content), and the Activity log's height rises
from 190 px to 360 px. The Final grade number input
widens from 52 px to 76 px: two digits and the
spinner crowded at 52 px. (2) On the wall, the
audible tile now plays at exactly the wall speed.
Fraction-true playback (v66) rates every tile
differently, so the tile the teacher was listening
to — the hover-audio owner — sounded sped up or
slowed down. The differing rates are the app's own
scaling (a recording's frame rate does not drive
HTML5 playback timing), and the fix is in the sync
reference: while a tile owns the audio, the
reference duration is that tile's, so its rate is
the wall speed itself and the muted tiles are rated
relative to it; with no audible tile the reference
stays the longest showing tile. Ownership changes
(hover enter and leave, zoom open and close) re-rate
every tile through the one rate computation, and
preservesPitch is set explicitly (Chrome's default,
made deliberate): pitch is preserved, tempo follows
the rate. Regression: `tests/layout_regression_v68.py`
and `tests/wall_regression_v68.py` (both fail on the
v67 code, pass on v68), plus checks in
`tests/test_web.py`.

**v67 (2026-11-27).** Two teacher-reported defects.
(1) Some healthy packages showed YouTube match “no
fingerprint” beside OK Package integrity and Grade
signature. Those packages are in the audio form and
their WAV's “fmt ” chunk identifier is zeroed — intact
PCM, a header ffmpeg cannot open (the corruption
documented at v48) — so the hash checks, which run over
the submitted bytes, pass while the fingerprint decode
fails. The WAV repair removed in the v62 simplification
is restored for the cross-check: such a package is
fingerprinted from a one-off repaired copy and measures
(`wav_repaired` in the result); hash checks still run
over the submitted bytes only. With it: a package
record no longer names the first audio file found in
its folder as the media — the fingerprint file is the
media whenever the folder holds one, as the package's
form decides — and the YouTube cell's token now carries
the stored fingerprint diagnostic as a tooltip, so the
reason behind a “no fingerprint” row is visible in
place. Check schema 7: stored results are re-done once.
(2) On the wall, tiles still stopped and stayed black
while others played. A tile whose video element errors
(a fatal fetch or decode failure) had no recovery: no
‘error’ handler existed, and every stall-watchdog
branch passes an errored tile by — the intent branch
and the generic branch both need a duration, which an
early error destroys. A tile now recovers from its
error event: reloaded at the fraction captured when
the error fired, its play intent preserved, a bounded
number of times with growing delays (the budget is
restored when a frame arrives), and the stall watchdog
routes an errored tile to the same recovery as a
backstop. The watchdog's intent branch also escalates:
a tile a scrub left paused with data ready and its
play intent set was observed standing across many
visits whose plain play() calls did not restart it, so
after three visits the branch reloads the tile at its
position instead of repeating the ineffective call
(demonstrated against the v66 code by
`tests/wall_regression_v67.py`, which fails there and
passes on v67).

**v66 (2026-11-27).** Four teacher-reported defects.
(1) A previous attempt fetched by the Redownload tool
was never checked: the check machinery itself was whole
— enumeration, the stored key and the table's lookup all
agree, and the automatic pass does check attempts — but
the Redownload run triggered no check pass at all, so a
fetched attempt sat “not checked” until the next
automatic pass, up to ten minutes later. A Redownload
run now ends with the incremental check pass, so what it
fetched, current and previous attempts alike, is checked
by the same run, and the Done line reports the counts.
(2) The Redownload tool's always-visible lines
enumerated every not-in-format attempt by student name;
they now carry counts only, and the enumeration lives in
a collapsed details block under the tool (no information
lost, only moved). (3) Privacy coverage completed: the
enumeration in that details block wraps names in priv
spans, the Activity log re-renders when the roster
arrives (a line written before it loaded is covered
too), dashboard error text is rendered through the same
name-wrapping, the wall hover panel's and the zoom
view's transcript blocks carry the priv class (free text
is barred whole), and the Cleanup page — which had no
privacy machinery at all — gains the toggle and
priv-wrapped student names in its item labels and
loose-video file names. (4) Wall playback is
fraction-true and stall-resuming: tiles playing together
advance at the same fraction rate (each tile's rate is
the wall speed scaled by its duration against the
longest showing tile, clamped to 0.25x–3x the wall
speed), a tile the wall wants playing records that
intent and the stall watchdog resumes it after a stall
instead of leaving it stopped, and an ended tile no
longer counts in the master position average while
others still play (demonstrated against the v65 code by
`tests/wall_regression_v66.py`, which fails there and
passes on v66).

**v65 (2026-11-27).** Two teacher-reported defects. (1)
The Redownload tool honours “Include previous attempts”
again: the v62 form planned and ran that scope as current
attempts only while the panel still offered the scope and
the table still directed the teacher to it. The plan and
the run fetch previous attempts through the
submission-history machinery, the estimate counts them
(packages, to-fetch, bytes), and a previous attempt with
no ZIP or a rejected ZIP is reported again
(`not_in_format` / rejected) instead of silently skipped;
automatic passes stay current-attempt only. The YouTube
cross-check measures a package in the older audio form:
the submitted fingerprint is computed from its WAV and
the same per-block rule runs, so the “old format” cell
state disappears for those packages (the reason remains
only for a package holding neither the fingerprint file
nor a readable WAV, and its cell token is now “no usable
media”). The check schema rises to 6, so a stored “old
format” result is re-done once under v65. (2) On the
wall, a quick scrub no longer strands tiles black at 0%:
a tile's intended fraction is recorded when a seek is
issued and its badge shows that target while the seek is
unlanded (badges are paired to tiles by media file name,
not position), and the stall watchdog gives a tile with
an unlanded target a longer, growing patience window and
no retry cap — the v64 watchdog reloaded a tile whose
far-seek fetch was still in flight after 3 s, discarding
the fetch and the frame, and after three cycles left it
black at 0% for the session (demonstrated against the
v64 code by `tests/wall_regression_v65.py`, which fails
there and passes on v65).

**v64 (2026-11-27).** The four check columns are renamed
for what they hold — Package integrity, Grade signature,
YouTube match and Warnings (the package mismatch stands
in Warnings) — the submissions table gains fixed column
widths so the empty Warnings column no longer takes the
slack, and the Final grade header's sub-label becomes a
tooltip. The YouTube cross-check now stores a
machine-readable `reason` whenever no comparison could be
made (`not-downloaded`, `not-fingerprint-format`,
`submitted-fingerprint-missing`,
`video-fingerprint-failed`, with the fingerprint
diagnostic — ffmpeg missing, a non-zero exit, an
exception, or no output — in `video_fingerprint_error`
where the production fingerprint function produced one),
and the dashboard cell names the state — “old format”,
“no fingerprint” or “video fingerprint failed” — instead
of the blanket “unavailable”; the notice above the table
aggregates the states actually shown, and a degraded row
stored before v64 (no reason) shows “not measured”. The
check schema rises to 5: the check-input fingerprint
gains an app-check-era entry, so a degraded result stored
before v64 is owed exactly one acoustic re-check under
v64 and then stands until its inputs or tooling change.
On the wall, `render()` and `renderAttemptTiles()` tear
down the grid's videos (pause, mute, unload) before
rebuilding the grid, and a registry of every video
element created lets the audio claim and the stall
watchdog reach elements a rebuild detached — a tile
playing through a Group by change no longer keeps
sounding off-screen.

**v63 (2026-11-27).** A display pass; no check changes
and the check schema stays 4. The app version is the
single `APP_VERSION` constant in `web.py`: every page
header shows it small beside its title, and
`/api/status` reports it as `app_version`. The
dashboard, Cleanup and Packages pages widen to 96% of
the window, capped at 1760px, with prose capped at
80ch. The dashboard's long explanations move into
collapsed “How this works” details blocks (Sections
1–3; Section 4 keeps one line per tool), and the
submissions table's single Integrity column splits
into four — Package, Signature, YouTube and Flags —
one short token per cell. The repeated per-row
“acoustic check not available” sentence is gone: the
YouTube cell shows “unavailable” and one notice above
the table states the fact once. A package mismatch
now stands in the Flags column.

**v62 (2026-11-27).** A simplification pass; the check
schema rises to 4, so stored checks are re-done. (1)
`youtube_id_ok` is removed entirely: no check in
`check_package`, no gate in the suggested final grade, and
no flag displays. A legacy bundle claiming a real
`youtube_video_sha256` is treated as claiming none — the
hash is ignored (the field is still parsed and still sent
in the `/verify-grade` body, whose canonical forms are
unchanged). (2) The YouTube cross-check stores no duration
diagnostics: no `duration_diff_s`, `duration_tolerance_s`,
`duration_ok` or `duration_flag` is computed or stored.
(3) The cross-check's verdict, and the similarity it
displays, both follow the per-block comparison
(`compare_fingerprints_blockwise`): the displayed
similarity is the median block similarity, the quantity
the verdict rule compares against its 0.90 minimum (the
rule also requires 90% of blocks at or above 0.85). The
global `compare_fingerprints` comparison no longer takes
part in the cross-check (the function remains for other
callers). (4) There is no audio ZIP form:
`extract_package_zip` accepts the fingerprint entry set
only (`submission.html` + `submission-fingerprint.bin`); a
WAV-form package is rejected as not in the current format.
The cross-check's audio verdict rule (global similarity
against the configurable threshold) and the WAV-repair
retry are removed. The `acoustic_threshold` setting is
kept: it is still consumed by the Setup settings
validation and by the check-input fingerprint, so a change
to it still earns an acoustic re-check — it no longer
decides any verdict. (5) `grades_match` is removed from
`check_package` and from internal consistency (the Worker
receipt check covers grade agreement), and the duplicated
receipt fields collapse to the single `grade_receipt_ok`.
(6) The suggested final grade has no separate second
receipt test; internal consistency remains its gate.
(7) Check invalidation has one diff classification
(`_classify_check_diff`), called by both `_check_mode` and
the `/api/youtube-check` handler. (8) Downloads are
current-attempt only: `download_packages` loses the
`include_history` attempt-folder machinery and its
not_in_format and rejected-mark records, and the
download-rate calibration (stats load/record, effective
rate, time estimate) is removed — the redownload tool
reports counts and bytes only. The watermark skip is
unchanged. Everything else is as in v61, below.

**v61 (2026-11-26).** Three fixes. (1) The Activity panel
starts blank when the page loads: lines logged before the
page session are no longer replayed into it, and lines from
work done while the page is open appear as they are logged.
(2) The zoom view's video is watched by the same stall
recovery as the wall's tiles: a seek of the zoom video that
stalls is re-issued, a video that was playing resumes, and
its opening play waits out the seek the way a tile's does —
a scrub of the whole wall can no longer leave the one
playing video black and stopped, on the wall or in the zoom
view. (3) Opening the zoom view pushes a browser history
entry, so the browser's Back button closes the zoom view
and returns to the wall — the same close as the Back to
wall button — instead of leaving the wall page for the
submissions table; Forward reopens the zoom view. There is
no release action for video bindings: there has been none
since v59, and no such button or route exists in this
version. Everything else is as in v60, below.

**v60 (2026-11-26).** One fix, to the video wall: tiles no
longer come back black and refusing to play after a round
trip to the zoom view. Returning with Back now keeps the
wall's tile elements alive — their decoded frames and
buffered ranges survive — instead of rebuilding the wall
from scratch; the wall is rebuilt on return only when its
data was replaced while the zoom view was open, and the
followed student's grade badge (the one thing a zoom visit
can change) is refreshed in place. Two recovery paths are
completed: a tile whose seek has run for over three seconds
with no frame is treated as stalled and its seek is
re-issued (a bounded number of times), where the stall
watchdog previously skipped a tile for being in that state;
and a play asked for during a seek is waited on for at most
1.5 seconds before it goes ahead anyway, where it
previously waited for the seek to complete, for ever if the
seek never did. Everything else is as in v59, below.

**v59 (2026-11-26).** Two removals. (1) There is no binding:
package checks make no binding call to the Worker, no status
anywhere reports a submission as displaced by a later one, and
there is no release action. A ZIP whose bundle carries a legacy video hash
verifies exactly as before on its other checks; the hash is
compared only within the package itself — the YouTube link's
video ID is hashed and compared with the claimed hash when the
bundle claims a real one, and a bundle claiming “none” reports
`youtube_id_ok` as None (no video claim was made), whether or
not the package carries a link. (2) The YouTube cross-check
follows the Chromaprint fingerprint similarity only: in the
audio form, similarity below `acoustic_threshold` (0.85)
flags; in the fingerprint form, the per-block rule flags.
Duration differences are not used at all — durations are
measured and recorded in the result as diagnostics, but they
never pass, flag, or appear in a displayed reason; when no
fingerprint comparison could be made, the result is neither a
pass nor a flag. The dashboard's integrity cell shows the
similarity: “YouTube similarity 0.9851” on a pass, “YouTube
FLAGGED · similarity …” on a flag. The check schema rises to
3, so stored checks are re-done under the new meanings.
Everything else is as in v58, below.

**v58 (2026-11-26).** The audit app is developed only as a
standalone portable install on the teacher's computer; no
other deployment form is developed. One fix, in that form:
the startup yt-dlp update check no longer asks yt-dlp to
update itself — a pip-installed yt-dlp refuses `yt-dlp -U`,
and its refusal was logged at every start. The check now
upgrades yt-dlp with uv, into the Python environment the
found yt-dlp belongs to (in the portable install, the
bundled runtime Python): `uv pip install --python <that
python> --upgrade yt-dlp`, and logs the resulting version.
uv is always used, never pip; if uv is not found, the check
reports that yt-dlp was not updated. Everything else is as
in v57, below.

Versions between v27 and v58 are recorded in the SPEC's audit
notes.

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
recomputed, and — when the bundle claims a real video hash —
the YouTube link's video ID is hashed and compared with the
claimed value, within the package only. A failed grade signature
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
   - `acoustic_threshold` — retained in the config (0–1,
     default 0.85) and still read by the Setup settings
     validation and the check-input fingerprint, so changing
     it earns an acoustic re-check; since v62 it decides no
     verdict (the cross-check follows the per-block rule).
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
  extracted beside it (`submission.html`,
  `submission-fingerprint.bin`); a ZIP in the older audio form
  is rejected as not in the current format;
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
  are the signed grades (v62: there is no separate grades-match
  check, and no YouTube video-ID check — a bundle's claimed
  video hash is ignored, treated as claiming none).
  Reports each check separately; a package whose format version is
  not 2, or with any of the audio, transcript, critique or receipt
  checks failing, is internally inconsistent.
- `export` — writes each package's grading section only (no summary, so
  no YouTube link; no verification section) to `exports/<CODE>.html`,
  with a random 6-character code per package from a CSPRNG, assigned in
  shuffled order — no relation to name, submission order, or time. The
  code-to-student mapping goes to `mapping.json` in the data folder
  only (permissions 0600 where the OS supports it) and never leaves
  this machine.
- `youtube-check` — the acoustic cross-check that the YouTube
  portfolio video is the same recording as the submitted one.
  It compares the package's submitted Chromaprint fingerprint
  against the video's per 30-second block, each block at its
  own best offset; it passes when the median block similarity
  is at least 0.90 and at least 90% of blocks reach 0.85, and
  the similarity it reports is that median block similarity.
  No duration diagnostics are recorded. A byte hash cannot do
  this — YouTube transcodes every upload — but the fingerprint
  is built from the spectrogram and survives transcoding. No
  transcription is involved, so the check takes seconds and
  needs no re-transcription setup; if ffmpeg or chromaprint is
  missing it reports itself not configured rather than passing
  or flagging. In the web app it runs inside Run integrity
  checks once the video has been downloaded, and the integrity
  cell shows the similarity.
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
`submission.html` and `submission-fingerprint.bin` (the webapp writes
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

106 checks. Fixtures are synthetic: a 300 s, 16 kHz mono WAV
generated in code and a v2 HTML package whose fingerprints are
computed from the fixtures, packaged as a ZIP with fixed
1980-01-01 entry timestamps. Grade receipts are computed with a
Python replica of the v2 grading Worker's canonicalisation (the
SPEC's result bundle, HMAC-SHA-256, base64url) with a test secret,
and `/verify-grade` is a fake transport that recomputes the same
way; the Worker's own cryptography is covered by the Worker suite.
Covered: a good v2 package passes every check; the SPEC tamper
cases — a grade edited in the HTML spans fails the grade
signature, an edited critique fails its hash, wrong audio
bytes fail the fingerprint, an edited transcript fails its
checksum, a receipt from a foreign secret fails, a v1-format HTML is
not internally consistent, a ZIP with an extra entry is rejected
at download, traversal and absolute entries are rejected with
nothing written outside the package folder, and oversize entries
are rejected; a v1 two-file attempt does not qualify; coded
exports contain no YouTube link and no verification data, with
unique codes not in submission order; download watermarking keyed
by the ZIP SHA-256; the absence of the removed listening check;
the YouTube acoustic cross-check (same fingerprint passes
under the per-block rule with the reported similarity equal
to the median block similarity, a different fingerprint
flags, no fingerprint comparison is neither a pass nor a
flag, a missing video is neither a pass nor a flag, an
audio-form package is reported as not in the current
format, no duration diagnostics are stored, and — through
the real ffmpeg — an AAC-transcoded copy of a take passes
while a different take flags); the absence of any binding
check (a legacy bound bundle verifies with its video hash
ignored and no binding request is made), of `youtube_id_ok`
and `grades_match`, of the WAV-repair retry and of the
download-rate calibration helpers; the absence of the
removed re-grade machinery; cleanup refusals and deletion,
`package.zip` included. (There is no listening check: it was
removed in v14 at the teacher's direction — it had never been
configured in production, and whether the transcript matches the
spoken audio is the teacher's judgement from the video wall.)
