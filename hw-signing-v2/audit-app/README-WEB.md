# Teacher Audit — web front end (HW Signing)

A local web app for the teacher's own computer. It puts a browser page
in front of the audit functions that until now were command-line only
(`audit.py`): Canvas download, integrity checks, coded export, the
cross-check, and cleanup. Canvas access is read-only.
Grades return to Canvas as a Gradebook CSV file that you upload in
Canvas (Grades → Import); the app never writes to Canvas directly.

## Start

- Windows PC: unzip the package, double-click `run-web.bat`, then open
  http://127.0.0.1:8766 in your browser. Keep the black window open
  while you work; close it to stop the app.
- Here (Muse machine): `sh run-web.sh`, then open the same address.

The server binds to 127.0.0.1 only. No other machine can reach it.
Python 3 standard library only; on Windows, `run-web.bat` uses uv to
provide Python if none is installed.

## v68 (2026-11-27) — Setup columns decoupled, Activity log taller, Final grade input wider, the audible wall tile plays at the wall speed

The Setup section's two columns were coupled: the
Save settings row, the course details and the status
line sat below the two-column row as full-width
siblings, so expanding the “How this works” details
in the Activity column pushed all of them down by
the details' height (measured on v67: 82 px), and
the flex row's default stretch sized the settings
column's box by the Activity column's content,
leaving a void under the settings fields. The
buttons, course details and status line now live
inside the settings column, the row aligns its
columns to the start (each column is as tall as its
own content), and the Activity log's height rises
from 190 px to 360 px, so more of the log is
visible at once. The Final grade number input
widens from 52 px to 76 px: two digits and the
spinner crowded at 52 px. On the wall, the audible
tile now plays at exactly the wall speed:
fraction-true playback (v66) rates every tile
differently, so the hover-audio tile the teacher is
listening to sounded sped up or slowed down. The
differing rates are the app's own scaling — a
recording's frame rate does not drive HTML5
playback timing — and the fix is in the sync
reference: while a tile owns the audio (claimAudio
records the owner), the reference duration is that
tile's, so its playbackRate is the wall speed
itself and the muted tiles are rated relative to
it; with no audible tile the reference stays the
longest showing tile, as in v66. Hover leave
releases the ownership and re-rates the same way,
and preservesPitch is set explicitly on the tiles
(Chrome's default, made deliberate): pitch is
preserved, tempo follows the rate. The zoom view
still plays at the plain wall speed.
Regression: `tests/layout_regression_v68.py` and
`tests/wall_regression_v68.py` (headless Chromium;
both fail on the v67 code, pass on v68), plus
checks in `tests/test_web.py`.

## v67 (2026-11-27) — “No fingerprint” rows explained and measured, wall tiles recover from video errors

Some healthy packages showed YouTube match “no
fingerprint” beside OK Package integrity and Grade
signature. The cause: those packages are in the audio
form and their WAV's “fmt ” chunk identifier is zeroed
(intact PCM, a header ffmpeg cannot open — the
corruption documented at v48), so the hash checks pass
over the submitted bytes while the fingerprint decode
fails. The WAV repair removed in v62 is restored for
the cross-check: the submitted fingerprint is computed
from a one-off repaired copy and the package measures
(the result notes `wav_repaired`); hash checks still
run over the submitted bytes only, never the repair.
A package record now names the fingerprint file as the
folder's media whenever one is present — before v67
the first audio file found won, so a stray audio file
beside a fingerprint package stood in for its media —
and the YouTube cell's token carries the stored
fingerprint diagnostic as a tooltip. Check schema 7:
stored results are re-done once under the new
semantics. On the wall, a tile whose video element
errors (a fatal fetch or decode failure) now recovers:
before v67 no ‘error’ handler existed and every
stall-watchdog branch passed an errored tile by (the
intent and generic branches both need a duration,
which an early error destroys), so it stayed black
for the session. The tile is reloaded at the fraction
captured when the error fired, with its play intent
preserved, a bounded number of times with growing
delays; the watchdog routes an errored tile to the
same recovery as a backstop. The watchdog's intent
branch also escalates: a tile a scrub left paused,
with data ready and its play intent set, was observed
standing across many visits whose plain play() calls
did not restart it (intermittently, in the v67
browser probes), so after three such visits the
branch reloads the tile at its position and plays it
on landing, instead of repeating the ineffective
call.
Regression: `tests/wall_regression_v67.py` (headless
Chromium, twelve tiles; fails on the v66 code, passes
on v67), plus checks in `tests/test_web.py` and
`tests/test_audit.py`.

## v66 (2026-11-27) — Redownload checks what it fetches, counts-only Redownload lines, complete privacy coverage, fraction-true wall playback with stall resume

A Redownload run now ends with the incremental integrity
check pass, so a package it fetched — a previous attempt
above all, which no other path fetches — is checked by
the same run instead of sitting “not checked” until the
next automatic pass (the check machinery itself was
whole: enumeration, the stored key and the table's
lookup all agree). The Redownload tool's always-visible
lines carry counts only; the per-attempt enumeration of
not-in-format previous attempts lives in a collapsed
details block under the tool. Privacy coverage is
completed: names in that details block are priv-wrapped,
the Activity log re-renders when the roster arrives,
dashboard errors render through the name wrapper, the
wall hover panel's and zoom view's transcript blocks are
barred whole under the toggle, and the Cleanup page
gains the toggle with priv-wrapped item labels. On the
wall, tiles playing together now advance at the same
fraction rate — each tile's playback rate is the wall
speed scaled by its duration against the longest
showing tile, clamped to 0.25x–3x the wall speed — a
tile the wall wants playing records that intent
(`_wantPlay`, cleared by every user pause action) and
the stall watchdog resumes it after a stall, and an
ended tile no longer counts in the master position
average while others still play.
Regression: `tests/wall_regression_v66.py` (headless
Chromium; fails on the v65 code, passes on v66), plus
checks in `tests/test_web.py` and `tests/test_audit.py`.

## v65 (2026-11-27) — Redownload fetches previous attempts again, audio-form packages are measured, wall scrub no longer strands tiles

The Redownload tool's “Include previous attempts” scope
works again (it was planned and run as current attempts
only since v62, while the panel offered it and the table
directed you to it): previous attempts are fetched from
the submission history, the estimate counts them, and a
previous attempt with no ZIP or a rejected ZIP is
reported rather than silently skipped. Automatic passes
still fetch current attempts only. The YouTube
cross-check measures a package in the older audio form
from its WAV (the submitted fingerprint is computed and
the same per-block rule runs), so the “old format” cell
state is gone for those packages; the remaining
no-comparison token for a package with neither media
form reads “no usable media”. Check schema 6: a stored
“old format” result is re-done once. On the wall, a
quick scrub no longer leaves tiles black at 0%: a tile's
badge shows its scrub target while the seek is unlanded,
and the stall watchdog no longer abandons a tile whose
target is known — its patience window starts at 10 s and
grows, with no retry cap (the v64 watchdog reloaded a
tile at 3 s, discarding the in-flight seek fetch and the
frame, and stopped after three cycles).
Regression: `tests/wall_regression_v65.py` (headless
Chromium; fails on the v64 code, passes on v65), plus
checks in `tests/test_web.py` and `tests/test_audit.py`.

## v64 (2026-11-27) — Clearer column names, fixed column widths, YouTube failure reasons, wall stuck-audio fix

The four check columns are renamed for what they hold:
**Package integrity**, **Grade signature**, **YouTube
match** and **Warnings** (the package mismatch stands in
Warnings). The submissions table gains a colgroup with
fixed layout: the check and result columns stay compact
(Warnings is capped and wraps), and the Student column
takes the remaining slack. The Final grade header loses
its “auto-saves · amber = differs from signed grade”
sub-label to a title tooltip; the full explanation stays
in the collapsed “How this works” block. The YouTube
cross-check stores a machine-readable reason whenever no
comparison could be made (see `README.md`), and the
YouTube match cell names it — “old format”, “no
fingerprint” or “video fingerprint failed” — retaining
“error” for the error case and the similarity number for
a measured row; a degraded row stored before v64 shows
“not measured”. The notice above the table aggregates
the states actually shown (“YouTube match could not be
measured for N shown row(s): …”) instead of asserting
the tooling is unavailable. The check schema rises to
5: a degraded result stored before v64 is owed exactly
one acoustic re-check under v64 (the check-input
fingerprint gains an app-check-era entry) and then
stands until its inputs or tooling change. On the wall,
`render()` and `renderAttemptTiles()` pause, mute and
unload every grid video before replacing the grid, and a
registry of every video element created lets
`claimAudio()` and the stall watchdog mute and pause
elements a rebuild detached — a tile playing through a
Group by change (or a sort, filter or page turn) no
longer keeps sounding off-screen under the next hovered
tile. Regression: `tests/wall_regression_v64.py`
(headless Chromium), plus node-level assertions in
`tests/test_web.py`.

## v63 (2026-11-27) — Version label, wider pages, collapsed explanations, four check columns

Display only; no check changes and the check schema
stays 4. The app version is the single `APP_VERSION`
constant in `web.py`: each page header shows it small
beside its title (dashboard, video wall, Cleanup,
Packages), the templates carrying a placeholder the
constant replaces, and `/api/status` reports it as
`app_version`; the dashboard status line shows it too.
The dashboard, Cleanup and Packages pages widen to
96% of the window, capped at 1760px (the wall was
already full-width), with explanatory prose capped at
80ch. The dashboard's long explanations — Grade,
YouTube, Re-checks, Examined, the view description and
the Final grade note in Section 2, the Section 3
introduction, and the Section 1 Activity note — move
into collapsed “How this works” details blocks, closed
by default and kept in full; Section 4 keeps one line
per tool. The submissions table's single Integrity
column splits into four: **Package** (OK / FAILED /
not checked / check failed / —), **Signature** (OK /
FAILED / —), **YouTube** (the similarity number alone,
FLAGGED plus the number, “error”, “unavailable”, or —)
and **Flags** (the flag badges, and the package
mismatch note that stood in the Integrity cell before
v63). The Final grade header carries the sub-label
“auto-saves · amber = differs from signed grade”.
When any shown row's YouTube state is the
tooling-unavailable one, one notice above the table
states it once — “YouTube acoustic check unavailable
on this computer (ffmpeg/Chromaprint)” — instead of a
sentence per row. Group rows span the new 12 columns
and attempt-note rows 11 beside their empty cell;
previous-attempt rows use the same four columns. The
wall's one-line integrity text is unchanged.

## v62 (2026-11-27) — Simplification: fingerprint form only, one receipt field, one check-diff classification

The audit changes are in `audit.py` and summarised in
`README.md`: `youtube_id_ok` and `grades_match` are gone,
the receipt fields collapse to `grade_receipt_ok`, the
YouTube cross-check follows the per-block fingerprint rule
only (its displayed similarity is the median block
similarity; no duration diagnostics are stored), package
ZIPs are fingerprint-form only, downloads are
current-attempt only with no download-rate calibration,
and the check schema rises to 4. In this front end: the
suggested final grade keeps internal consistency as its
only receipt-related gate, check invalidation judges input
differences through the one `_classify_check_diff` used by
both `_check_mode` and the `/api/youtube-check` handler,
and the redownload tool downloads current attempts only
and estimates counts and bytes (no time estimate). The
`acoustic_threshold` setting remains in Setup — the
settings validation and the check-input fingerprint still
consume it — but it decides no verdict. Everything else
is as in v61, below.

## v61 (2026-11-26) — Activity starts blank; the zoom video recovers; browser Back closes the zoom

- **The Activity panel starts blank.** On page load the
  panel shows nothing; the first poll only sets the
  baseline, so lines logged before the page session are
  never replayed into it. Lines from work done while the
  page is open appear as they are logged.
- **The zoom video is watched like a tile.** The stall
  watchdog also runs on the zoom view's video while the
  zoom view is open: a seek that stalls is re-issued, a
  video that was playing resumes when the re-issued seek
  lands, and the zoom view's opening play waits out its
  seek instead of racing it. A whole-wall scrub that
  stalls the one playing tile's seek recovers it framed
  and playing.
- **Browser Back closes the zoom view.** Opening the zoom
  view pushes a history entry (switching students
  replaces it); the browser's Back button and the Back
  to wall button take the same path, closing the zoom
  view onto the wall with its tiles alive. Forward
  reopens the zoom view.

## v60 (2026-11-26) — the wall survives the zoom round trip

- **Back keeps the tiles alive.** Returning from the zoom
  view no longer rebuilds the wall: each tile keeps its
  element, its decoded frame and its buffered ranges, and
  the wall comes back as it was, at the zoom view's
  position. The wall is rebuilt on return only when its
  data was replaced while the zoom view was open. A final
  grade saved in the zoom view is refreshed on the tile in
  place, as the examined badge already was.
- **A stalled seek recovers.** A tile whose seek has run
  for over three seconds with no frame to show is treated
  as stalled: the wall re-issues its seek, a bounded number
  of times, instead of skipping it for being mid-seek.
- **Play is never dead.** A play asked for while a seek is
  in flight waits at most 1.5 seconds for the seek to land
  before going ahead anyway.

## v59 (2026-11-26) — no binding; the YouTube check is the similarity only

- **There is no binding.** Package checks make no binding call
  to the Worker, nothing in the wall, the dashboard, the
  gradebook or the exports reports a submission as displaced
  by a later one, and the dashboard's integrity cell has no
  release action. A ZIP whose bundle carries a legacy video
  hash verifies exactly as before on its other checks; the
  hash is compared only within the package — the link's video
  ID against the claimed hash, when the bundle claims a real
  one. A bundle claiming "none" is not compared at all.
- **The YouTube cross-check follows the Chromaprint
  similarity only.** A duration difference — however large —
  never flags and never passes; durations are recorded in the
  result as diagnostics and are not displayed. When no
  fingerprint comparison could be made, the result is neither
  a pass nor a flag. The integrity cell shows the similarity:
  **YouTube similarity 0.9851** (the value to four decimal
  places) on a pass, **YouTube FLAGGED · similarity …** on a
  flag, and the existing pending wording before a measurement
  exists.
- **Check schema 3.** Stored checks are re-done once under
  the new meanings.

## v54 (2026-11-26) — repair: the dashboard loaded no data under v53

- v53 shipped with a mismatched quote in one line of the
  dashboard's script (the Expected-package selector's
  empty-list line). The browser refused the page's whole
  script, so the dashboard opened but stayed empty: no
  settings, no submissions, no activity. Your config and
  data were never touched. This release fixes that one
  character; the test suite now also parses every page's
  script before a release, so this class of error is
  caught here rather than on your computer.

## v53 (2026-11-26) — the Expected package selector: no Auto, no Not set

- The selector now lists the grading Worker's packages only.
  There is no "Auto" entry and no "Not set" entry.
- The selection it opens on is the **latest version of the
  package most of the assignment's submissions used** (counted
  by package name), unless you have picked a package for that
  assignment yourself — your pick is kept.
- Matching is unchanged: grading accepts **any version** of
  the selected package; only a different package is a mismatch.

## v52 (2026-11-26) — the gate matches by name, defaults to the majority; wall and table fixes

- **Package matching is by name.** A submission graded under a
  different *version* of the same prompt package (v2 where v3 is
  expected) is the same homework and grades normally; only a
  different package counts as a mismatch.
- **The Expected package selector defaults to Auto.** With no
  choice stored, the package most of the assignment's downloaded
  submissions were graded under is the expected one, and the
  selector shows it ("Auto — majority: ⟨package⟩"). Choosing a
  package from the list still sets it explicitly; "Not set — no
  package check" now switches the gate off deliberately, as its
  own stored choice.
- **Table headers no longer split words across lines** ("Downloaded",
  "Grade", "Examined" broke mid-word at some window widths).
- **The video wall fills the screen** at 100% zoom instead of
  sitting in a centred column.
- **Wall playback after the single view is hardened:** a tile's
  play now waits until its seek has completed (a play issued
  while the seek was still running could be cancelled by the
  seek landing, leaving the tile stopped or black on a long
  take), and the wall revives a tile whose frame never arrived.

## v51 (2026-11-26) — the package-match gate: grade entry only when the package matches

- In section 3 (Grades back to Canvas), each assignment now has
  an **Expected package** selector: the prompt-package versions
  held on the grading Worker, or "Not set". The choice is stored
  on this computer, per course and assignment.
- Where an expected package is set, a submission graded under a
  different package is treated as misplaced, not gradable: the
  submissions table shows "Package mismatch — submitted under
  ⟨package⟩ · this assignment expects ⟨package⟩" in its
  Integrity cell and offers no final-grade field; the zoom view
  shows no grade field either, and a grade save is refused with
  the mismatch named; the wall tile, attempt tiles and student
  cards carry a "package mismatch" badge; and the gradebook CSV
  leaves that student's score blank, with the mismatch named in
  the preview warnings. A final grade already entered stays
  stored but is not exported while the mismatch lasts.
- Where the packages match — or no expected package is set —
  nothing changes: the final grade stands pre-filled from the
  student's grade, and the only entry is a grade you choose to
  override. A submission whose package is not known yet (not
  downloaded, not checked) is never flagged.

## v50 (2026-11-26) — each submission's prompt package shown in the table and on the wall

- Every submission now shows the prompt package it was graded
  under — the name and version in its signed verification
  section (for example "ponchon-savarit v3"). In the submissions
  table it appears under the course and homework in the Student
  column, and on each previous-attempt row; on the video wall it
  appears on the tile, on the attempt tiles, and in the student
  card of the side panel and the zoom view. A submission whose
  package differs from the homework you are looking at is
  visible at a glance. The line stays visible under Privacy —
  a package name is not a student identifier. Display only:
  no check changes.

## v48 (2026-11-26) — fingerprint-form packages, per-block YouTube comparison, WAV repair

- **Two package forms.** A submission ZIP now arrives in one of two
  forms, decided by its entry set alone: the audio form
  (`submission.html` + `submission-audio.wav`), as always, or the
  fingerprint form (`submission.html` +
  `submission-fingerprint.bin`), which carries the recording's raw
  Chromaprint bytes instead of the WAV. Which form a student builds
  follows the job's signed grade bundle: a bundle carrying a signed
  Chromaprint SHA-256 (Worker 2.7.0 and later) produces the
  fingerprint form; an older bundle produces the audio form. A mixed
  or partial entry set is neither form and is rejected, as a wrong
  set always was. There is no flag day — old ZIPs keep checking
  exactly as before.
- **Fingerprint-form checks.** The submitted fingerprint's SHA-256
  must equal the value the Worker signed into the bundle (shown in
  the package's verification section as "Chromaprint SHA-256", and
  included in the receipt offered to the Worker's /verify-grade —
  the Worker accepts receipts in both the old and the new canonical
  form). The bundle's Audio SHA-256 names the original WAV, which
  this form does not carry; the signed receipt binds it, so no
  audio hash is recomputed. Transcript, critique, grades, receipt,
  YouTube-ID and injection checks are unchanged.
- **YouTube cross-check, per block.** In the fingerprint form the
  submitted fingerprint is compared against the downloaded video's
  fingerprint in blocks of 242 items (30 s), each block at its own
  best offset over ±16 items, instead of at one global offset for
  the whole file. The check passes when the median block similarity
  is at least 0.90 and at least 90% of blocks score at least 0.85;
  the result reports the median, the fraction at or above 0.85, the
  block count and the worst block, and keeps the whole-file
  comparison alongside. The rule is set from the twelve past
  packages measured on 2026-11-26: every same-recording block
  scored at least 0.929, 99.9% of cross-recording blocks scored
  below 0.842, and one real pair that scored only 0.796 at a single
  global offset scored 0.926–0.991 in every block at per-block
  offsets. (Since v59 the check follows the similarity only:
  the fingerprint span and the durations are recorded as
  diagnostics and are not compared for any verdict.)
- **WAV repair.** Five of the twelve past packages carry a WAV
  whose "fmt " chunk identifier is zeroed while the sound data is
  intact; ffmpeg cannot open such a file, and those packages
  silently recorded no YouTube result. The audio form now retries
  a failed decode once against a repaired copy — a canonical
  header (PCM, 16-bit, 16 000 Hz, mono) over the submitted bytes
  from offset 44 — and the result notes `wav_repaired` when the
  repair was used. Hash checks always run over the original
  submitted bytes, never the repair.
- **Check schema 2.** The check schema rises from 1 to 2, so
  packages checked under the old checks are re-checked under v48
  on the next pass.
- **Front end.** The web front end discovers both forms on
  disk: a downloaded package is found by its HTML plus either
  media entry, and its record's media path names the
  fingerprint file for a fingerprint package (the checks
  decide the form from that name). The redownload presence
  test accepts the fingerprint file in the WAV's place, so a
  fingerprint package is not fetched again on every scan.
  Nothing in the front end serves or plays a package's own
  media — the wall and the single view play the downloaded
  YouTube take — so a fingerprint package appears there
  exactly as an audio package does.

## v35 (2026-11-13) — previous attempts checked and downloaded, final grades auto-save, grade differences highlighted

- **Previous attempts are checked like current ones.** Every
  previous attempt on disk (downloaded with the Redownload
  tool's "Include previous attempts" scope) now gets its own
  integrity check — fingerprints, critique and grade signature,
  and the YouTube acoustic cross-check against that attempt's
  own downloaded video — in the manual "Run integrity checks"
  and in the automatic passes. The result line reports the
  attempt checks separately ("plus N previous-attempt
  check(s)"). An attempt's result is stored apart from the
  current attempt's, and the attempts rows in the submissions
  table and on the wall show it instead of "not checked". The
  grade of record is unchanged: finals, suggested grades and
  the Gradebook still come from the current attempt only, and
  a flagged previous attempt changes none of them.
- **Previous attempts' YouTube videos download automatically.**
  The automatic passes fetch them (each under its attempt file
  name) alongside the current attempts' videos, so an
  attempt's tile plays on the wall and its acoustic cross-check
  completes without a per-tile download. The resume scan
  counts owed attempt checks and videos.
- **Final grades save themselves — there is no Save button.**
  In the submissions table and in the wall zoom, changing a
  final grade and leaving the field saves it as the teacher's
  grade, with a "saved ✓" note beside the field; an error
  (for example a cleared field, where a grade is required)
  also appears beside the field. A field you never touched
  writes nothing, so a pre-filled clean grade is not
  re-labelled as a teacher entry; a flagged submission's blank
  field stores the grade as soon as you enter one and leave.
- **A final grade that differs from the signed grade is
  highlighted.** The Final grade cell in the table is shaded
  amber, with the signed grade shown beside it — as you type,
  not only after saving — and the wall zoom's teacher-grade
  field is shaded the same way. In the Gradebook preview, a
  differing row's score is shaded and its source reads
  "teacher entry (signed grade N)". The downloaded Gradebook
  CSV is unchanged. Equal grades (the student's 9 standing as
  a final 9) are never highlighted.

## v34 (2026-11-11) — redownload freeze fix, format reporting, collapsible hover sections, select all that appear

- **Redownload no longer freezes with "Include previous
  attempts".** The Start request returns at once; the selection
  is planned inside the run, and the progress line shows a
  planning phase while the assignments are read. One history
  walk per assignment now serves the estimate, the run and the
  wall's attempts fetch (a cache with the scan's 600 s
  lifetime) — before, each of the three fetched the history
  separately, inside what looked like one button press. A
  homework whose history cannot be read no longer stops the
  run: it is logged, counted in the closing summary ("N
  assignment(s) could not be read"), and the run continues
  with the next homework.
- **Previous attempts that are not in the package format are
  reported, not dropped.** The estimate and the run's closing
  summary count and list them (student, attempt, what the
  attempt holds instead — "audio + html files, no ZIP", "no
  files", or the file names). They are still never downloaded:
  the two-file form is not a package. The submissions table's
  attempt note uses the same knowledge where it is already on
  this computer (recorded by earlier redownload walks in
  `attempt-formats.json`): it now distinguishes "not
  downloaded" from "not in package format (no ZIP) — cannot be
  downloaded" and "rejected package ZIP".
- **A previous attempt whose ZIP is rejected is not re-fetched
  forever.** The rejection is recorded in
  `download-state.json` (the attempt's listing fields, the
  ZIP's SHA-256 and a rejected flag); later runs report it
  from the record and fetch nothing for it. Force still
  retries it. A current attempt's rejected ZIP is unchanged:
  no mark is left, and the next pass retries it.
- **The wall's hover panel sections collapse.** Time marks,
  Critique and Transcript each collapse like the zoom view's
  panels: click a section's head or its ▾ button and the
  section shrinks to its title bar while the others share the
  freed height; click again to restore. The choice is kept in
  this browser (localStorage `ta-wall-hover-v1`). The student
  card does not collapse.
- **The submissions table has a header tick** — "select all
  that appear". It ticks exactly the submissions currently
  shown under the active view (filters and grouping), and
  unticks the shown ones when all of them are already ticked;
  part-shown reads as the in-between (indeterminate) state.
  Ticks on submissions outside the current view are kept, and
  the tick writes through the same selection store as the
  per-row ticks, so "View selected on wall" opens exactly the
  ticked set.

## v33 (2026-11-11) — hover panel fix, table → wall selection and focus, table attempt rows

- **Hover panel fix.** In v32 the wall's side panel showed
  the student card but its Time marks, Critique and
  Transcript panels collapsed to hairlines: the panel had a
  maximum height but no definite height, so its three
  flexible sections had nothing to share out. The panel now
  has a definite height (the viewport height less the page
  furniture), the three sections share it, and each section
  body fills its section and scrolls. At phone width the
  panel stacks below the grid with each body capped, as the
  zoom panels are. The same fix covers the attempts wall,
  which shares the panel.
- **Table → wall selection.** Each submissions-table row
  carries a tick. "View selected on wall" (above the table,
  with the tick count) opens the video wall showing exactly
  the ticked students; a banner there states the count and
  offers Clear selection, which restores the ordinary
  shared-view wall. While a selection is shown, the wall's
  view filters and grouping are overridden (its sort still
  orders the selection). Ticks are kept in this browser.
- **Focused student view.** Clicking a student's name in
  the table opens the wall with that student's zoom view
  open — video, critique and transcript as usual. If the
  take's video has not been downloaded, the zoom opens with
  the no-video presentation and its download button where
  the player would be. A previous attempt's View link (next
  item) opens the attempts collage with that attempt's zoom
  open.
- **Table attempt rows.** The table's view controls gain
  an Attempts choice: "Latest only" (as before) or
  "Include previous". In Include-previous mode each
  submission gains a subordinate row for every earlier
  attempt already on disk — current attempt first, then
  previous attempts newest first — showing that attempt's
  own signed grade. Finals, examined ticks and stored
  checks stay with the current attempt's row, which is
  unchanged. When Canvas holds more earlier attempts than
  are on disk, a note row states how many are not
  downloaded and points at the Redownload tool. Nothing is
  downloaded from the table itself; the attempt data is
  disk-local, so the local prefill shows the rows too.

## v32 (2026-11-11) — wall hover panel, redownload tool, previous attempts

- **Hover panel on the video wall.** A fixed side column sits
  beside the collage (the grid shrinks; nothing is overlaid).
  It shows the selected tile's student card, time marks,
  critique and transcript — the same panels as the zoom view.
  Hovering a tile selects it; a tap selects it too; the panel
  keeps the last hovered tile when the mouse leaves, and
  defaults to the first tile in the current view order. The
  panel is text only: it never changes which tile plays or
  is audible. On a phone-width screen it stacks below the
  grid.
- **Redownload tool** (dashboard, under the Download /
  integrity-check controls). Filters work like the shared
  view: course, homework, student text, submitted-date
  range, Examined, Graded. A scope choice decides whether
  previous attempts are included, and Force re-fetches even
  packages that are present and unchanged. Before a run, an
  estimate line shows how many packages would be fetched,
  how many are already present, the total MB and an
  estimated time range. The rate comes from recent downloads
  on this computer, recorded in `download-stats.json` in the
  data folder; until the first run there is no record, the
  estimate uses an assumed 2,000,000 bytes/s and is marked
  uncalibrated. During a run the panel shows packages and MB
  done, elapsed time and a remaining estimate that follows
  the achieved rate; the closing line reports the actual
  time beside the estimate and updates the calibration
  record. The estimate covers package download and
  extraction only.
- **A check before fetching.** Whether a package needs
  fetching is now decided from the Canvas listing — attempt
  number and submitted time compared against the stored
  watermark — before any package bytes are downloaded, so
  unchanged, present packages cost no download. The
  automatic passes keep their behaviour; only the wasted
  bytes are gone.
- **Previous attempts.** Narrow the wall view to one student
  and one homework and an **All attempts** button appears.
  It switches the collage to that student's attempts for the
  homework, ordered by attempt number, each tile labelled
  "Attempt n · date" and marked current or previous; if the
  earlier packages are not on this computer yet, the button
  fetches them first (progress and errors appear beside the
  button). The redownload tool's "Include previous
  attempts" scope fetches them the same way. Storage: the
  current attempt keeps its existing folder; a previous
  attempt n lives in an `attempt-<n>/` subfolder with its
  own package and extracted files, and its watermark key
  gains `:attempt-<n>`. An attempt tile's video downloads on
  demand like any wall video, keyed per attempt, and zooming
  an attempt tile shows that attempt's own grades, critique
  and transcript. Boundaries: the grade of record, teacher
  final grades, examined ticks, stored checks and the
  gradebook export stay keyed to the current attempt only;
  previous attempts never overwrite them. Deleting a unit in
  Cleanup removes its attempt folders, attempt watermarks
  and attempt videos with it.

## v31 (2026-11-11) — local-first views, parallel scan

- The submissions table and the video wall no longer wait
  for Canvas before showing anything. Both pages first ask
  for the **local view** (`?local=1`): the downloaded
  submissions and takes, with their stored checks, final
  grades, examined ticks, and the names, course / homework
  labels and submitted dates kept in `package-index.json` —
  all read from this computer, in milliseconds. The full
  Canvas view then loads behind it and replaces it, adding
  submissions not yet downloaded. While the local view is
  up, the table says "Showing the submissions already on
  this computer — refreshing from Canvas…".
- The Canvas scan itself is faster: assignment lists and
  per-assignment submission lists are fetched six calls at
  a time instead of one after another, the scan cache now
  lasts 10 minutes (the automatic pass interval) instead of
  2, the wall's roster lookups are cached with the scan,
  the wall parses each submission's HTML once instead of
  twice, and the table reads a package's grades only when
  no stored check already holds them.
- Nothing about the data changes: the same rows and tiles
  appear, with the same grades and marks. What changes is
  only how long the first paint takes, and how much Canvas
  traffic a page load causes.

## v29 (2026-11-10) — select, sort, filter and group the submissions

- The submissions table (dashboard section 2) and the video
  wall share one set of view controls: **select** a course or
  a homework; **filter** by student name or ID, a submitted-
  date range, examined or not, and graded or not; **sort** by
  course, student, date submitted, homework, examined or
  grade (with an ascending / descending button); and **group**
  by course, homework, date, examined or graded, with a
  heading and a count for each group.
- "Graded" means a grade is present — the signed grade from
  the package, or a final grade entered by the teacher.
  Sorting by Examined lists the not-yet-examined first
  (ascending), as before.
- The table gains a **Submitted** column; the wall data now
  carries course, homework and submitted date as separate
  fields, and each tile shows its submitted date.
- The chosen view is kept in the browser and applies on both
  pages: a selection made in the table is the selection on
  the wall. **Reset view** restores the default (no filters,
  no grouping, not-yet-examined first). On the wall, Prev /
  Next student in the zoom view follows the current view.

## v27 (2026-11-09) — critique line breaks kept on the wall

- The video wall's zoom view now preserves the critique's
  line breaks, so its numbered points appear on separate
  lines — the same treatment the student's submission HTML
  and the student page (webapp 2.3.2) already give it. The
  one-point-per-line form itself is set in the prompt-package
  builder skill's standing grading rules.

## v26 (2026-11-09) — errors appear beside the control used

- **Errors show where the user is looking** (the teacher's
  rule, applying to both apps): on the dashboard, the Cleanup
  page and the Packages page, an action's error is written
  directly beside the button or field that was used — the
  page's error element moves next to it — instead of only on
  one line at the top of a long page, where it could sit
  off-screen. Errors with no control behind them (page load,
  background refresh) stay at the top and never scroll the
  page. On the video wall, a tile's failed 480p download now
  reports beside its button as well as in the header line.
- The student page carries the same rule in its own release
  (webapp 2.3.0, published separately).

## v25 (2026-11-09) — student-link verification fixed

- **Build and verify link** on the Packages page no longer
  downloads the package's full text twice to check its status
  and hash (in v24 that took tens of seconds on a connection
  that drops calls, and could fail outright when a retry budget
  ran out). It now fetches the metadata only — two small
  requests — and answers in about a second. The link produced
  is unchanged, byte for byte. Show still reads the full text,
  in slices, as in v24.

## v24 (2026-11-09) — HW prompt packages, listed and managed

- **Packages page** (`/packages`, linked from section 4 of the
  dashboard). The grading prompt packages live on the grading
  Worker, not on this computer; this page lists **every version
  held there** — package, status, trial grades, job counts,
  content SHA-256 and creation time — and manages them:
  **Show** reads one version's full text (fetched in 2,500-char
  slices and verified against its content SHA-256, because a
  whole-text response is the one most often cut short when a
  connection to the Worker drops mid-body); **Record trial**,
  **Open**, **Close** and **Retire** move a version along its
  lifecycle (draft → trialled → open → closed → retired; a trial
  below 5/5 + 5/5 is recorded only with an override reason);
  **Student link** builds the link for an open package and
  verifies it before showing it, exactly as the package-builder
  skill does; and a **New package version** form uploads approved
  text as a new draft (the Worker assigns the version and the
  hash; a stored version's text never changes).
- The page proxies the Worker's admin API. The **admin token**
  is entered on the Packages page, stored only in `config.json`
  on this computer, sent only to the grading Worker, and never
  shown again — the page reports only whether one is saved, and
  it can be removed there. The Worker itself enforces the
  lifecycle and the trial gate; a refusal (a wrong token's 401,
  an illegal move, a duplicate text) is shown with the Worker's
  own reason.
- The grading Worker gained matching support in 2.3.0: `GET
  /admin/packages/<pkg>?text_offset=N&text_length=M` returns one
  slice of the text with `text_total`; without parameters the
  endpoint is unchanged.

## v23 (2026-11-09) — one system only: HW Signing v2

- **ZIP submissions only.** A submission counts when its attempt
  holds a ZIP file (`submission.zip`, holding exactly
  `submission.html` and `submission-audio.wav`); the app downloads
  the ZIP, checks it, and extracts those two files. The v1 form —
  a separate audio file plus an HTML file — was eliminated: v1 is
  outdated and such submissions will never occur. They are ignored
  silently, as ordinary submissions are.
- **The Worker in Setup is the grading Worker**
  (hw-grading…workers.dev), which verifies the grade receipt that
  signs each submission's grades and critique hash. A config saved
  by an earlier version still carrying the v1 signing Worker
  address is switched to the grading Worker automatically the
  first time v23 loads it.
- **Checks** are the v2 set: format version 2, audio fingerprint,
  transcript checksum and critique hash recomputed, the grade
  receipt verified with the Worker over the grades shown in the
  HTML (the dashboard row carries a "grade signature OK / FAILED"
  badge), and the YouTube video-ID comparison. A failed grade
  signature or a video-ID mismatch holds the student's grade back
  (blank in the gradebook) until you enter one yourself, and the
  gradebook preview warns about both.
- **Course list label fixed:** a course in the automatic set that
  you have unticked by hand now reads "automatic · unticked by
  you — not scanned" instead of plain "automatic", so the label
  no longer claims a course is scanned when it is not.

## First use (Setup, section 1 of the page)

1. Paste your Canvas token into the token field and Save settings.
   The token is stored only in `config.json` beside `web.py` on this
   computer. The page never displays it again — it reports only that
   a token is saved.
2. Setup ends there. Under the form, the app lists **all your
   active courses with checkboxes**. The list is collapsed by
   default — the line above it states how many of the courses
   are being scanned; click the line to expand the list. The courses in which you
   are a teacher or a teaching assistant / grader are ticked
   automatically — sandbox courses included, even when
   unpublished — and the scan covers exactly the ticked courses
   and their published assignments. Every other active course
   is listed unticked, with its role and state shown (for
   example "student", or "unpublished"), so a course that is
   not being scanned is visible rather than silently absent;
   that is why a real course with no tick — CHE3025 and the
   like, when they hold no packages yet or are not
   auto-ticked — still appears in the list. Tick or untick any
   course to change the set; the change saves at once and a
   pass runs. "Reset course ticks to automatic" restores the
   automatic set. Within the scanned courses, only submissions
   whose attempt holds a ZIP file — an HW Signing v2 submission
   — are considered at all: ordinary submissions (PDFs, quizzes,
   v1 two-file uploads) are ignored silently, with no table row
   and no log line. A course whose name carries a badge "N new
   submissions to download" has work waiting for the next pass.
   **Test Canvas connection** shows your name and Canvas id.
3. The Grading Worker address is pre-filled with the HW Signing
   v2 grading Worker (see the v23 note above).
4. On startup the app also upgrades **yt-dlp** in the
   background, with uv, into the Python environment the found
   yt-dlp belongs to; the result, with the resulting version,
   shows in the line under the Setup form. If uv is not found,
   that line states that yt-dlp was not updated. If yt-dlp is
   not installed at all, that line gives the install command
   (`uv tool install yt-dlp`); the video wall needs it to download
   YouTube takes.

## Working an assignment (section 2)

- **Automatic passes** — you do not need the buttons below for
  routine work. A pass starts at startup and **as soon as a Canvas
  token is saved**, and then every 10 minutes while the app is
  open. Each pass scans all your published teaching courses (see
  Setup step 2), downloads new/changed submissions for every
  assignment it finds, then runs the integrity checks and
  downloads the YouTube videos for the wall **in parallel**. The
  submissions table covers every scanned assignment at once —
  each row names its course and assignment — and packages are
  stored per course and assignment, so the same student in
  several assignments never collides. A package downloaded by
  an early version into the old flat layout and again by a
  later scan into the per-course layout is still one package:
  the per-course copy wins and the student is listed, checked
  and counted once. The last pass and its
  result are shown above the table.
- **Moving between pages** — the dashboard keeps a snapshot of
  its tables (submissions, courses, gradebook targets) in the
  browser tab. Returning to the page — with Back, Forward, or a
  fresh visit in the same tab — paints the tables from the
  snapshot at once, marked "refreshing…", and the live data
  replaces them as it arrives; the pages are also served so
  the browser's own back/forward cache can restore the page
  exactly as it was, with the data then refreshed in place.
- **The black console window** — closing the page, or scrubbing
  and closing videos, makes the browser drop connections
  mid-stream; that is normal and the app now stays silent about
  it (earlier versions printed a `ConnectionResetError`
  traceback for each dropped video stream).
- **Activity panel** — the scrolling log in Setup's right column
  shows the background work as it happens: packages
  being downloaded, integrity checks starting and finishing per
  student, and YouTube videos being downloaded. The work runs in
  the app, not in the page, so closing the page does not stop it.
  If the app itself is closed mid-work, nothing incomplete is
  marked as done — the download watermark and each finished check
  are saved as they complete, and partial video files are kept —
  so the next pass after a restart picks up exactly what was left
  unfinished (the panel's pass line counts it as work to do).
- **Refresh list from Canvas** — one row per student: Canvas state,
  whether the submission ZIP is downloaded, the integrity
  result in the four check columns (Package integrity,
  Grade signature, YouTube match and Warnings — the flag
  badges stand in Warnings), the
  student's grade, the final-grade field, and the Examined box.
  The table refreshes itself whenever an automatic pass finishes
  (the Activity poll notices the pass-finished entry and reloads
  the list and the Setup counts), so background work shows up
  without a manual refresh; the button remains for an on-demand
  reload.
  The grade is one composite score out of 10
  (completeness 0–5 + accuracy 0–5); the split is not shown in the
  app — it lives in the student's submission HTML and critique. Grades
  show as soon as the submission is downloaded, before any check runs.
- **Download new / changed submissions** — downloads the ZIP of
  each student's most recent attempt and extracts
  `submission.html` + `submission-audio.wav` from it; unchanged
  submissions are skipped by watermark, as in the command-line app.
- **Run integrity checks** — for every downloaded submission:
  recomputes the audio fingerprint, the transcript checksum and
  the critique hash, requires format version 2, and verifies the
  grade receipt with the grading Worker over the grades shown in
  the HTML (so the shown grades must be the signed grades); also,
  when the bundle claims a real video hash, compares the YouTube
  video ID in the submission against that claimed hash (a bundle
  claiming "none" is not compared), and runs the
  prompt-injection scan, and runs the YouTube acoustic
  cross-check (below) for every package whose YouTube video has
  been downloaded. An injection flag carries the time of the
  flagged text (the start of the transcript chunk that contains
  it): the row badge reads "injection @ mm:ss", the wall shows
  the same time, and the gradebook warnings repeat it — the
  grading prompt asks the student's Muse for the same time in
  its flag note. It does not re-grade anything. A package
  whose check fails shows the reason on its row instead of
  stopping the run.
- **YouTube acoustic cross-check** — also part of Run integrity
  checks; no separate button. It confirms that the YouTube
  portfolio video is the same recording as the WAV submitted to
  Canvas. A byte hash cannot do this (YouTube transcodes every
  upload), so the check compares **acoustic fingerprints**:
  ffmpeg computes a Chromaprint fingerprint of the whole WAV and
  of the downloaded video's audio, and the row shows the
  similarity (1 minus the fingerprint bit error rate) — about
  0.99 for the same take after transcoding, about 0.5 for a
  different take. The similarity is the whole check: duration
  is not used. Below the acoustic threshold (0.85 by default;
  set it in Setup, stored as `acoustic_threshold` in
  `config.json`) the row shows **YouTube FLAGGED · similarity
  …** and a "youtube" flag badge under Integrity, the wall
  shows "YouTube mismatch", and the final grade stays blank
  until you enter one. A pass reads **YouTube similarity …**
  with the value to four decimal places.
  Until the video has been downloaded the row reads "YouTube:
  video not downloaded yet" — the automatic pass that downloads
  the video runs the cross-check again in the same pass, so no
  extra step is needed. The check takes seconds per package and
  needs no transcription; it does need ffmpeg with its
  chromaprint muxer (the Setup line reports whether ffmpeg was
  found). `/api/youtube-check` re-runs it for one student.
- **Examined** — the last column replaces the old View button
  (everything in the package is visible on the video wall). The
  box is ticked automatically when you hover the student's video
  on the wall or open it there; you can also tick or untick it
  here. Students not yet examined are listed
  first, here and on the wall — they are the queue; the tick is
  the only mark (there is no "unviewed" badge).
- **Final grade** — one composite score (0–10), pre-filled from the
  student's grade when integrity is clean (the audit v2 rule: a
  clean student's grade stands). A flagged submission stays blank
  until you type a final grade. Edited values are the grade of
  record.
- **Export coded grading sections** — the anonymised exports and the
  code-to-student mapping, exactly as the command-line app makes
  them; the mapping stays in the data folder.

## Video wall (watching the takes)

Section 2 links to the **video wall** (`/wall`). It shows a screenful
of students at a time, one tile per take. How many fit is set by the
**Zoom** slider (tile size) and your screen: the wall computes how
many tiles fit the window and pages through the class in screens of
that size (Prev/Next), recomputing when you drag the slider or resize
the window. Keyboard: **Space** plays/pauses everything showing,
**←/→** step all showing videos one frame (pausing first); in the
zoom
view Space plays/pauses that video, **←/→** step one frame (the
frame rate is measured from the video as it plays and
shown next to the student's name), **Esc** returns to the wall, and
**Tab / Shift-Tab** moves to the next / previous student.

- Tiles carry an **examined ✓** badge once examined. Hovering a
  tile (which plays its audio) or opening it marks it examined;
  unexamined students are placed first on the wall. The badge flips
  in place when you hover — the order re-applies on the next load,
  so tiles never jump around under the mouse.
- Each tile is the student's YouTube video downloaded at **medium
  resolution** (at most 480 px high, merged to MP4) into
  `data/videos/`. A tile whose take is not downloaded yet shows a
  **Download at medium resolution (480p)** button instead; downloading
  needs `yt-dlp` on the computer (the same install the
  ChemEScribe/yt-downloader setup provides). Tiles also show the
  integrity state, the student's grade (one score out of 10), and a
  live percent readout.
- **Scrubbing with the mouse**: hold the **right** mouse button on a
  hovered video and drag left/right — every showing video moves to
  the same fraction of its own length (one tile width of travel =
  the whole take), and the hovered video keeps the focus and the
  audio throughout, even if the pointer leaves its tile mid-drag.
  The right button was chosen because the left button already
  means "click to zoom" and hover already means "play with audio";
  its one cost is that the right-click menu is suppressed on the
  wall (only there), which the app does. On a trackpad that makes
  right-drag awkward, the master scrub bar below does the same job.
- The **master scrub** bar at the bottom moves every showing video to
  the same fraction (0–100%) of its own length, so takes of different
  lengths stay in step. **Play all / Pause all** and a speed control
  (0.5×–2×) act on every showing video. Tiles are muted, except that
  **hovering a tile plays that one take with its audio**; moving the
  mouse away re-mutes it (and pauses it again if the hover started
  it). **Only one video is ever audible at a time** — giving sound
  to one video mutes all the others — and picture-in-picture is
  disabled on every player.
- **Click a tile to zoom** into that one take: the player opens at
  the same fraction, next to the student's grade, the critique
  (from the submission's grading section), and the timed
  transcript — the transcript the student submitted in the package,
  not a new transcription. The transcript chunk for the current
  position is highlighted as it plays; clicking a chunk jumps the
  video to it. **Back to wall** returns at the same fraction.
- **The zoom position bar never disappears**: play/pause, the
  position slider with the `m:ss / m:ss` readout, mute and
  fullscreen sit in a fixed bar under the video, in the page
  layout — not an overlay that fades. (Fullscreen enlarges the
  video and the bar together.)
- **Panels**: Time marks, Critique and Transcript are separate
  panels beside the video. Each panel's title stays in place and
  only its body scrolls. A panel takes the space its content
  needs, up to an equal third of the column (less when its
  content is short); **⤢** expands a panel to a double share and
  **▾** collapses it to its title bar.
- **Sound follows the student you are following.** If a take was
  playing when you zoom in, it keeps playing, with its audio.
  **Tab / Shift-Tab** (or the Prev/Next student buttons) moves to
  the next/previous student at the same fraction, still playing
  and unmuted; **Back to wall** resumes that student's tile with
  its audio while every other tile stays muted.
- **Grading in the zoom view**: the student card shows the
  student's grade and a **Teacher final grade** field with a Save
  button — the same final grade as the dashboard field. If you
  change it and move on with Tab, the changed grade is saved on
  the way.
- **Time marks**: in the zoom view, **Mark this time** (or the **M**
  key) records the current position for that student, with an
  optional note. Marks are saved on this computer
  (`data/marks.json`), listed in the Time marks panel (click a time to jump
  to it, click the note or ✎ to edit it, ✕ deletes it), and
  **Export marks (.txt)** on the wall downloads one combined text
  file: grouped by student (name and email or login), marks in time
  order as `mm:ss` with their notes.

The wall can show **test examples** so the layout can be tried
before any real takes exist: eight fictional students (marked
DEMO), with generated videos of 0:58–3:30, grades, critiques and
timed transcripts. They are not shipped with the app — section 4
(Tools) has **Generate test examples**, which makes them on this
computer with ffmpeg (under a minute; progress in the Activity
log) into `data/demo-videos/`, and **Remove test examples**,
which deletes the generated set again — only the generated set:
examples bundled with an earlier install are never removed by
it. Installs from earlier versions that already hold a bundled
set in the app folder keep using it until a generated set
replaces it. Real submissions appear
first in the list once packages are downloaded; a real tile plays
from its downloaded MP4, or offers the download button plus a
link to the video on YouTube.

## Grades back to Canvas (section 3)

Section 3 lists every assignment holding HW Signing submissions, grouped
by course, each with its own
**Preview gradebook rows** and **Download Gradebook CSV** buttons
— one CSV per assignment, since a Canvas import file names a
single course's assignment. The preview table is grouped by
section when the course has more than one. The button beside
each course heading downloads all of that course's CSVs at
once as separate files inside one ZIP (a browser cannot save
several files from one click); unzip it and import each file
in turn. The file follows Instructure's grade-import format: columns
`Student, ID, SIS User ID, SIS Login ID, Section`, then one column
headed `<Assignment name> (<assignment id>)`, with a Points Possible
row under the header. Scores are completeness + accuracy; if the
Canvas assignment is not out of 10, the total is scaled to its points
possible. A student with no final grade gets a blank cell, which
leaves their Canvas grade unchanged on import. A copy of the CSV is
also saved under `data/gradebook/` on this computer.

In Canvas: open the course → **Grades** → **Import** → choose the
file → **Upload Data** → review the changes (lowered grades are
highlighted) → **Save Changes**. Per the Instructure article, a CSV
upload can set scores and create assignments; it cannot post
comments, change grade posting policies, or set assignment status.

## Tools (section 4)

- **Test examples** — generate or remove the wall's fictional
  demo students, as described under the video wall above. The
  set is made locally on demand; it is not part of the app
  download.
- **Cleanup** — a separate page (linked from section 4) that
  lists the working material grouped by course and assignment,
  with course/assignment/student filters and sizes for every
  package and video. The page reads this computer only — it
  never contacts Canvas; student and course names come from a
  small local index the app updates whenever it sees Canvas
  data. Tick whole groups or single students and
  delete exactly that: submission folder, wall video, check
  result, final grade, examined tick and watermark entry go
  together. The coded exports + mapping and the download
  watermark are separate tick boxes, and video files no submission
  claims are listed on their own. There is no appeal-period
  gate — when material may go is the teacher's decision; the
  confirmation states the exact selection before deleting.

## Files

- `web.py` — the server and the pages (standard library only),
  including the video wall and the Packages page.
- `make_demo_videos.py` — the test-example generator; the app
  runs it from section 4, and it can also be run directly.
- `data/demo-videos/` — the generated test examples, once made.
- `data/videos/` — YouTube takes downloaded at medium resolution
  by the video wall.
- `audit.py` — the audit functions the page calls; unchanged, and its
  command-line interface still works.
- `config.json` — created by the page on first Save; holds the
  tokens (Canvas, and the grading admin token saved on the
  Packages page). Keep it on this computer only.
- `data/` — downloads, check results (`audit-results.json`), final
  grades (`final-grades.json`), video-wall time marks
  (`marks.json`), coded exports, the mapping, and gradebook CSV
  copies.

## Tests

```
python3 tests/test_web.py     # 170 checks for the web app
python3 tests/test_audit.py   # 63 checks for the audit functions
```
