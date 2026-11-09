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
4. On startup the app also checks whether a newer **yt-dlp** is
   available and updates it in the background; the result shows in
   the line under the Setup form. If yt-dlp is not installed at
   all, that line gives the install command
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
  result (the YouTube
  cross-check result, and any flag badges — there is no separate
  Flags column), the
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
  the HTML (so the shown grades must be the signed grades); also
  compares the YouTube video ID in the submission against the ID
  hash the Worker recorded before grading, and runs the
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
  different take. It also compares the two durations. Below the
  acoustic threshold (0.85 by default; set it in Setup, stored
  as `acoustic_threshold` in `config.json`)
  or with a duration mismatch, the row shows **YouTube FLAGGED**
  and a "youtube" flag badge under Integrity, the wall shows
  "YouTube mismatch", and the final grade stays blank until you
  enter one.
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
