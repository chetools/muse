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
  and the `yt-dlp` self-update at startup all write inside it.
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

- App: Teacher Audit v37 (`web.py`, `audit.py`), with the two
  portable changes described above (relative `data_dir`
  resolution; first-run `data_dir` correction in portable
  installs). v37: the browser opens only once the app
  answers, the download log states when an unchanged
  submission was decided from the local record with no bytes
  downloaded, and an acoustic result that could not measure
  a video is retried only when the acoustic tooling changes,
  not on every pass. The first pass after updating does one
  full check of each package (the checker version is part of
  each stored check's fingerprint); later passes skip
  unchanged packages as before.
- Python: CPython 3.13.18, python-build-standalone
  (`cpython-3.13.18+20261110-x86_64-pc-windows-msvc-install_only`),
  trimmed of debug symbols, the test suite and Tk.
- ffmpeg / ffprobe: FFmpeg 8.1, FFmpeg-Builds (BtbN)
  `ffmpeg-n8.1-latest-win64-gpl-shared-8.1`, built with
  `--enable-chromaprint` (the acoustic check's muxer);
  `ffplay` is not included — the app never uses it.
- yt-dlp: 2026.10.26, the standalone `yt-dlp.exe`. As in the
  standard app, it checks for its own update when the app
  starts and updates in place.

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
