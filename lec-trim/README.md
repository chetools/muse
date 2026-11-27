# lec-trim

`lec-trim` trims and stitches OBS homework recordings. You record your
explanation in OBS as several clips. In each clip you say
**“start recording”** near the beginning and **“stop recording”** near
the end. `lec-trim` finds those two phrases on your own computer — no
recording leaves your machine — keeps the part of each clip between the
phrases, and stitches the kept parts into one video,
`stitched_lecture_v01.mp4`. If that file already exists, the next run
writes `stitched_lecture_v02.mp4`, and so on. An existing file is never
overwritten.

## Quick start

1. Unzip the release folder anywhere, for example on your Desktop.
2. Put your OBS clips in one folder.
3. Open that folder, type `cmd` in the address bar, and run:

```text
path\to\lec-trim.exe .
```

Or drag the clips' folder onto `lec-trim.exe`. The window stays open at
the end when you use drag-and-drop if you add `--pause-at-end`; the
release folder's `run-lec-trim.bat` already does this — drag the clips'
folder onto that file instead.

4. Read the table it prints. For each clip it shows the part kept, in
   seconds (s). A warning names any clip where a phrase was not found;
   that clip is kept whole, from the end where the phrase is missing.
5. Upload `stitched_lecture_v01.mp4` as your homework video.

To check the cut points without writing a video, run with `--dry-run`.

## Does YouTube accept MKV?

No. YouTube's supported upload formats include MP4, MOV, AVI, WMV,
FLV, WebM and MPEG-4, but not MKV. That is why `lec-trim` writes MP4 by
default even though OBS records MKV. If you need MKV for another
purpose, run with `--format mkv`.

## OBS settings

These settings make the cuts clean and the stitching fast:

* Recording format: MKV (OBS's default remux-safe format). MP4, MOV,
  FLV, TS and WebM clips are also accepted as input.
* Video encoder: H.264 (NVENC, QuickSync, or x264).
* Max B-frames: 0. With B-frames, stream-copy trimming is not
  frame-accurate, so `lec-trim` re-encodes such a clip in full and
  warns you. Setting this to 0 keeps stitching fast.
* Keyframe interval: 1 s. The kept part of a clip is stream-copied
  between keyframes, and only the short parts at the two ends — each
  under one keyframe interval — are re-encoded, so a 1 s interval keeps
  the re-encoding to at most about 2 s per clip.
* Audio: AAC, 48 kHz. If a clip has several audio tracks, `lec-trim`
  uses the one track on which it finds the phrases (or, failing that,
  the loudest track) and keeps only that track.
* Use the same settings for every clip of one homework. A clip recorded
  with different settings is re-encoded in full, which is slower, and a
  warning names it.

## Recording habit

1. Press Start Recording in OBS.
2. Pause for 1 s.
3. Say **“start recording”** clearly, at your normal volume, with the
   microphone within about 0.5 m.
4. Pause for 1 s, then teach your explanation.
5. Pause, say **“stop recording”** clearly, pause for 1 s.
6. Press Stop Recording.

Say the phrases exactly as written. “Start” and “stop” sound alike, and
the recogniser tells them apart from the whole phrase, so do not shorten
them to one word.

## What is in the release folder

* `lec-trim.exe` — the tool.
* `ffmpeg.exe` and `ffprobe.exe` — used to read, trim and stitch video.
* `whisper-cli.exe` and its libraries — the speech recogniser.
* `ggml-base.en.bin` — the Whisper base English speech model
  (about 142 MB). Recognition runs entirely on your computer.
* `run-lec-trim.bat` — drag a folder of clips onto this file.

Nothing is downloaded when the tool runs.

## First run on Windows

The program is not code-signed, so Windows SmartScreen may show
“Windows protected your PC” the first time. Choose **More info**, then
**Run anyway**. This is needed once.

## Options

```text
lec-trim [INPUT_DIR] [--format mp4|mkv] [--dry-run] [--json]
         [--start-phrase "start recording"] [--stop-phrase "stop recording"]
         [--head-window 30] [--tail-window 30]
         [--pad-start 0.15] [--pad-end 0.15] [--pause-at-end]
```

The head window, in seconds (s), is how much audio at the start of each
clip is searched for the start phrase; the tail window is the same at
the end. The pad after the start phrase, in seconds (s), is skipped
before the kept part begins; the pad before the stop phrase is removed
from the end of the kept part.

## Limits

* A clip in which a phrase is not found is kept whole from that end and
  named in a warning. Check those clips yourself.
* The recogniser is a general speech model. It was tested here on
  synthetic (computer-spoken) clips only; quiet speech, a distant
  microphone, or heavy background noise can cause a missed phrase, which
  the warning then reports.
* All clips must contain an audio track.
