# Teacher Audit — portable folder (Windows x64)

This folder is the whole installation. It contains the app, a
bundled Python (`runtime\python\`), `ffmpeg` and `ffprobe` with
the chromaprint muxer and `yt-dlp` (`runtime\bin\`), the settings
(`config.json`) and all working data (`data\`). Nothing is
installed on the computer, nothing is written outside this
folder, and no setup download is needed.

## Run it

1. Put the folder anywhere writable: a folder on the computer,
   or a USB drive (NTFS; see Notes).
2. Double-click `run-web.bat`. A console window opens, and
   the browser opens by itself at http://127.0.0.1:8766 once
   the app is ready (a few seconds; if it has not opened
   after half a minute, open that address by hand).
3. Keep the console window open while you work. Close it to
   stop the app. On a USB drive, stop the app and use Windows
   "Eject" before unplugging.

The first start on a new computer may take a little longer, and
Windows may ask about running the bundled programs the first
time. If the files arrived in a ZIP, right-click the ZIP,
Properties, tick "Unblock", then unzip.

## Move it to a new computer or a USB drive

Stop the app, copy the whole `teacher-audit` folder, and run
`run-web.bat` in the copy. Settings, tokens, downloads, videos,
grades, marks and check results are all inside the folder, so
the copy continues where the original left off. The drive
letter and the folder's path do not matter.

## Transfer an existing (non-portable) installation into this folder

An existing installation — for example
`C:\Users\carlo\Downloads\teacher-audit\` — keeps everything in
two places. Copy both, with the existing app stopped (close its
console window first, so the last grades and marks are fully
written):

1. **`config.json`** — the single file in the top level of the
   old folder, beside its `web.py`. Copy it into the top level
   of this folder (if this folder already has a `config.json`
   because the portable app was run before the transfer,
   replace that file). It holds the Canvas token, the grading
   admin token, the Worker addresses, the ticked course list
   and the acoustic threshold. Nothing else holds a token.
2. **The whole `data\` folder** — copy the old folder's entire
   `data` folder into this folder, replacing the empty `data`
   folder shipped here. Do not pick items inside it; the parts
   refer to each other. It holds:
   - `downloads\` — the submission packages, by course,
     assignment and student, including previous attempts;
   - `videos\` — the YouTube takes downloaded for the wall;
   - `audit-results.json` — integrity and acoustic results, so
     checks are not re-run;
   - `final-grades.json` — the final grades of record;
   - `examined.json`, `marks.json` — examined ticks, time marks;
   - `download-state.json` — the download watermark, so nothing
     already fetched is fetched again;
   - `package-index.json`, `attempt-formats.json`,
     `download-stats.json` — labels and records the pages use;
   - `mapping.json` and `exports\` — coded exports and the
     code-to-student mapping;
   - `gradebook\` — saved Gradebook CSV copies.
   The one part that may be left behind is `data\demo-videos\`
   (the generated test examples; they can be regenerated from
   the app's Tools section).

Do not copy the old folder's `.venv` or `__pycache__` — the
portable folder uses its bundled Python instead.

One setting is handled for you: the old `config.json` records
`data_dir` as the old folder's absolute path. On the first run
in this portable folder, the app detects the bundled runtime
and the transferred state in this folder's `data`, points
`data_dir` at that folder (stored as the relative value
`data`, so the folder stays movable), and saves the corrected
config. No edit by hand is needed.

### Check the transfer worked

Start the app and look at the dashboard:

- Setup reports that a Canvas token is saved.
- The status line shows the Data path inside this folder.
- The submissions table fills at once from the local copy,
  with grades, integrity results and examined ticks as they
  were, and wall tiles play without downloading again.

If the table is empty and the Data path names the old
computer's folder, the `data` copy did not land beside this
folder's `web.py` — copy it again into this folder.

## Notes

- Windows x64 only. The app code and `data\` are platform-free,
  but the bundled `runtime\` programs are Windows x64 builds.
- The folder must be writable: state files, downloads, videos
  and the `yt-dlp` update at startup all write inside it.
- The folder holds live tokens and student material. On a USB
  drive, use an encrypted drive (for example BitLocker To Go);
  a lost unencrypted drive is a lost Canvas token and student
  data.
- A computer whose policy blocks programs running from
  removable media or from the Downloads folder will block this
  folder too; copy it to an ordinary local folder there.
- Updating the app later: replace `web.py`, `audit.py` and
  `make_demo_videos.py` with the newer files, and keep
  `config.json`, `data\` and `runtime\` as they are.

## Bundled components and versions

- App: Teacher Audit v68 (`web.py`, `audit.py`), with the two
  portable changes described above (relative `data_dir`
  resolution; first-run `data_dir` correction in portable
  installs). v68: the Setup section's two columns are
  decoupled (the settings column carries its own Save
  settings row, course details and status line and no
  longer stretches to the Activity column's height, so
  expanding “How this works” moves nothing on the
  settings side; the Activity log stands 360 px tall,
  and the Final grade input is 76 px wide); and the
  wall rates its tiles against the audible tile's
  duration while one owns the audio, so the tile the
  teacher hears plays at exactly the wall speed, with
  pitch preserved (the differing tile rates are the
  app's own fraction-true scaling, not a frame-rate
  effect). v67: an audio-form package whose WAV's
  “fmt ” chunk identifier is zeroed (intact PCM, a header
  ffmpeg cannot open) is measured by the YouTube
  cross-check through a one-off repaired copy — those
  packages showed “no fingerprint” beside OK integrity,
  because the hash checks run over the submitted bytes
  and pass while the decode fails (check schema 7); a
  package record names the fingerprint file as the
  media whenever the folder holds one (a stray audio
  file no longer stands in for a fingerprint package's
  media); the YouTube cell's token carries the stored
  fingerprint diagnostic as a tooltip; and a wall tile
  whose video element errors now recovers (reloaded at
  its position, play intent preserved, bounded retries)
  instead of staying black for the session — and a tile
  a scrub left paused, which repeated play() calls were
  observed not to restart, is reloaded by the stall
  watchdog after three visits. v66: a Redownload run checks what it fetches
  in the same run (previous attempts included — before
  v66 they sat “not checked” until the next automatic
  pass); the Redownload tool's visible lines carry counts
  only, with the not-in-format enumeration in a collapsed
  details block; privacy coverage is completed (details
  block, Activity log, dashboard errors, wall and zoom
  transcripts, and the Cleanup page, which gains the
  toggle); and wall playback is fraction-true (tiles
  playing together advance at the same fraction rate)
  with stall resume for tiles the wall wants playing.
  v65: the Redownload tool honours “Include
  previous attempts” again (estimate, run and reporting;
  automatic passes stay current-attempt only), the
  YouTube cross-check measures audio-form packages from
  their WAV (check schema 6; a stored “old format” result
  is re-done once), and a quick wall scrub no longer
  strands tiles black at 0% (the badge shows the scrub
  target while a seek is unlanded, and the stall watchdog
  no longer abandons a tile with a known target). v64: the check columns are renamed Package
  integrity, Grade signature, YouTube match and Warnings,
  with fixed column widths and the Final grade sub-label
  moved to a tooltip; the YouTube cross-check records why
  no comparison could be made and the cell names it (“old
  format”, “no fingerprint”, “video fingerprint failed”)
  instead of “unavailable”, with one acoustic re-check
  owed to degraded results stored before v64 (check
  schema 5); and the wall tears down its grid videos
  before a rebuild, so a playing tile no longer keeps
  sounding after a Group by change. v63: a display pass — the version shows
  small in every page header (from the one `APP_VERSION`
  constant in `web.py`), the dashboard, Cleanup and
  Packages pages widen to 96% of the window capped at
  1760px, the dashboard's long explanations move into
  collapsed “How this works” blocks, and the submissions
  table's Integrity column splits into Package,
  Signature, YouTube and Flags columns, with the
  YouTube-unavailable fact stated once above the table.
  v62: the simplification pass described in
  `README.md` (fingerprint-form packages only, one receipt
  field, per-block YouTube verdict, current-attempt
  downloads, check schema 4). v61: the Activity panel starts blank on page
  load, the zoom view's video is covered by the stall
  recovery, and browser Back closes the zoom view onto the
  wall. v60: the video wall keeps its tiles alive across
  a trip to the zoom view and back (no black, unplayable
  tiles on return), a seek stalled for over three seconds
  with no frame is re-issued, and a play asked for during a
  seek goes ahead after at most 1.5 seconds. v59: there is no binding — package checks make no
  binding call to the Worker, no page reports a submission as
  displaced by a later one, and there is no release action;
  a legacy bundle's video hash is compared only within its
  own package, and a bundle claiming "none" is not compared.
  The YouTube check is the Chromaprint fingerprint similarity
  only, shown in the dashboard's integrity cell ("YouTube
  similarity …" on a pass, "YouTube FLAGGED · similarity …"
  on a flag); duration is not used in the check. v37: the browser opens only once the app
  answers, the download log states when an unchanged
  submission was decided from the local record with no bytes
  downloaded, and an acoustic result that could not measure
  a video is retried only when the acoustic tooling changes,
  not on every pass. v38 (efficiency only — what a check
  measures is unchanged): the YouTube video shared by an
  assignment's packages is fingerprinted once per run of the
  app instead of once per package; stored checks are keyed
  to a check-schema number rather than the app version, so
  later updates no longer re-check every package; and the
  media files are guarded by a content sample rather than
  their modification times, so copying the installation —
  this transfer included — triggers no re-check wave. The
  first pass after updating to v38 re-runs at most the
  acoustic part of each unchanged package; later passes
  skip unchanged packages as before.
- Python: CPython 3.13.18, python-build-standalone
  (`cpython-3.13.18+20261110-x86_64-pc-windows-msvc-install_only`),
  trimmed of debug symbols, the test suite and Tk.
- ffmpeg / ffprobe: FFmpeg 8.1, FFmpeg-Builds (BtbN)
  `ffmpeg-n8.1-latest-win64-gpl-shared-8.1`, built with
  `--enable-chromaprint` (the acoustic check's muxer);
  `ffplay` is not included — the app never uses it.
- yt-dlp: 2026.10.26, the standalone `yt-dlp.exe`. Since
  v58 the app upgrades yt-dlp with uv when the app starts —
  into the Python environment the found yt-dlp belongs to,
  in the portable the bundled runtime Python — and never
  asks yt-dlp to update itself.

## Repository note

The portable runtime binaries are not in this repository. In
the repository, the portable launcher is stored as
`run-web-portable.bat` beside the standard `run-web.bat` (which
is unchanged and remains the launcher for a fixed install).
Building the portable folder from this source: copy the app
files, copy `run-web-portable.bat` to `run-web.bat` in the
portable folder, add an empty `data\` folder, and add
`runtime\` assembled from the releases named above —
`runtime\python\` (the trimmed standalone Python),
`runtime\bin\ffmpeg.exe`, `runtime\bin\ffprobe.exe` with their
shared libraries, and `runtime\bin\yt-dlp.exe`. The first
delivered build (2026-11-21, ZIP SHA-256
`bf5a9886fad9f19ebece3144a28882582f0dc2da67de81b319a97f80220791dc`)
was verified from its extracted copy: audit tests 82/82, web
tests 264/264.
