# lec-trim — specification as decided 2026-11-27

## Purpose

A Windows command-line tool for students. A student records a homework
explanation in OBS as several clips, acting as the lecturer. The student
says "start recording" near the start of each clip and "stop recording"
near the end. `lec-trim` finds those cues locally, trims each clip to the
speech between the cues, and stitches the trimmed clips into one video.

No cloud service is used. Speech recognition runs on the student's
machine.

## Decisions taken by the user, 2026-11-27

1. Audience: students recording homework; the student is the speaker.
2. Test data: mock clips are created for development. Real student clips
   are not available yet, so detection on real voices is unverified.
3. Audio tracks: a clip may carry several audio tracks. Only one track
   is used — the most robust one, selected as defined below — and only
   that track is kept in the output.
4. Cue phrases: "start recording" and "stop recording".
5. Speech model: Whisper base English model, `ggml-base.en.bin`
   (about 142 MB).
6. Missed cue: keep the whole clip from that end (inpoint 0 s, or
   outpoint at the end of the clip) and print a warning naming the file.
   The stitch proceeds.
7. Tight cuts: the parts of a kept segment that lie between keyframes
   are re-encoded; the part between keyframes is stream-copied. See
   "Smart trim" below.
8. Distribution: no GitHub workflows and no GitHub releases. A zip is
   built locally and handed to the user.
9. Platform: Windows only. No macOS build.
10. Speech engine: a bundled `whisper-cli` program (from whisper.cpp),
    run as a separate process in the same way as `ffmpeg`. Whisper is
    not embedded in the Rust binary.
11. Scope: the full pipeline in the first version, not a dry-run-only
    prototype.
12. Output name: `stitched_lecture_v01`, `stitched_lecture_v02`, and so
    on — the first version number not already present in the input
    folder is used; an existing output is never overwritten.
13. Input formats: the containers OBS commonly writes — `.mkv`, `.mp4`,
    `.mov`, `.flv`, `.ts`, `.webm`.

## Defaults set by the builder for items the user did not answer

These stand until the user changes them.

- Output container: MP4, because YouTube does not accept MKV (see the
  README). Video is H.264 and audio is AAC in the re-encoded parts, at
  the source frame rate, resolution and sample rate. `--format mkv`
  keeps the source codecs in the re-encoded parts where the container
  allows.
- Accuracy gate for the mock-clip tests: no missed cue, and the cut
  points within 0.5 s of the hand-labelled cue times in the mock clips.
  This gate says nothing about real student voices.
- Mismatched clips: a clip whose video codec, resolution, frame rate or
  audio sample rate differs from the first clip is re-encoded in full
  to the first clip's profile, then treated like the other clips. A
  warning names each such clip.
- Bundling: the zip contains `lec-trim.exe`, `ffmpeg.exe`,
  `ffprobe.exe`, `whisper-cli.exe` with its runtime libraries, and
  `ggml-base.en.bin`. Nothing is downloaded at run time.
- Unsigned binary: Windows SmartScreen will warn on first run. The
  README states the one-time "More info → Run anyway" step plainly.

## Recommendation on Q1 (who speaks, and how they should record)

The user asked for a recommendation. Students record at a desk, close to
a laptop or headset microphone, with many different voices and accents.
The design therefore assumes a close microphone, not a room microphone:
the OBS guide in the README tells students to keep the microphone within
about 0.5 m, to pause for 1 s, say "start recording" clearly, pause
again, teach, then pause, say "stop recording", and pause before
stopping OBS. The base model (decision 5) is the smallest Whisper model
that should be trusted across varied voices for two fixed phrases; the
tiny model is not used.

## Pipeline

1. Discover and sort. Scan the input folder (default: current folder)
   for the containers in decision 13, excluding previous
   `stitched_lecture_v*.mp4/.mkv` outputs and temporary files. Sort by
   the OBS timestamp in the file name where present, otherwise by file
   name, otherwise by creation time.
2. Probe. Run `ffprobe` on each clip: duration in seconds (s), video
   codec, width and height in pixels (px), frame rate in frames per
   second (s^-1), and for each audio track its codec, sample rate in
   hertz (Hz) and channel count.
3. Extract head and tail audio. For each clip and each audio track,
   extract the first 30 s and the last 30 s as 16 kHz mono WAV files in
   a temporary folder, using `ffmpeg -sseof` for the tail so the middle
   of the file is not read.
4. Select the audio track. Run cue detection (step 5) on every track.
   The most robust track is the one on which both cues are found; if
   several qualify, the one with the highest mean token probability; if
   none qualifies, the track with the highest root-mean-square (RMS)
   audio level in the head window, and the missed-cue rule (decision 6)
   applies. The chosen track index is reported per clip.
5. Detect cues. Run `whisper-cli` with the base model and word-level
   timestamps (JSON output) on the head and tail WAV files. Normalise
   tokens: lower-case, strip punctuation. In the head, find the first
   occurrence of the token sequence "start recording"; the inpoint, in
   seconds (s), is the end time of "recording" plus a pad of 0.15 s.
   In the tail, find the last occurrence of "stop recording"; the
   outpoint, in seconds (s), is the start time of "stop", converted to
   clip time, minus a pad of 0.15 s. Require the kept segment to be at
   least 2.0 s long, otherwise warn and keep the whole clip.
6. Smart trim. For each clip, read its keyframe times with `ffprobe`.
   Split the kept segment [inpoint, outpoint] into up to three parts:
   a head part from the inpoint to the next keyframe, a middle part
   between keyframes, and a tail part from the previous keyframe to the
   outpoint. Re-encode the head and tail parts (each under one keyframe
   interval, set to 1 s in the recommended OBS settings) with accurate
   seeking; stream-copy the middle part. If a part is empty it is
   omitted. Concatenate the parts of all clips in order with the
   `ffmpeg` concat demuxer and `-c copy`, which is valid because the
   re-encoded parts are encoded to the same codec, resolution, frame
   rate, pixel format and audio parameters as the copied parts.
7. Report. Print a table: per clip, the chosen audio track, inpoint,
   outpoint, kept duration, and any warning. `--dry-run` stops after
   step 5 and prints the table (and JSON with `--json`) without
   writing video.

## Verification checks (named before building, per standing rule)

- C1 Cue detection: mock clips made with `ffmpeg`'s `flite` speech
  synthesiser, saying the cue phrases at known times, must be detected
  with no miss and cut error at most 0.5 s.
- C2 Cut accuracy: the stitched output duration must equal the sum of
  the kept durations within 0.5 s per clip, measured with `ffprobe`.
- C3 Middle is copied, not re-encoded: a mock clip whose middle section
  carries a unique video pattern must keep that pattern bit-exact in
  the copied range — checked by comparing frame hashes (`framemd5`)
  for frames in the middle part.
- C4 Track selection: a mock clip with speech on track 2 and silence on
  track 1 must select track 2.
- C5 Versioned output: running twice in the same folder produces
  `stitched_lecture_v01.mp4` then `stitched_lecture_v02.mp4`, and the
  first file is unchanged (checksum compared).
- C6 Mismatched clip: a set with one clip at a different resolution is
  normalised, stitched, and the output probes at the first clip's
  resolution.
- C7 Missed cue: a clip with no cue phrase is kept whole, a warning
  names it, and the stitch completes.

Checks C1–C7 run on mock clips only. Detection on real student
recordings remains unverified until real clips are supplied.
