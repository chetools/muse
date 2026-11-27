#!/usr/bin/env python3
"""Create mock OBS clips with ffmpeg's flite speech synthesiser.

Each clip's audio is a timeline of silence and spoken segments. The cue
phrases are placed at known times; the ground truth (cue start/end, in
seconds (s)) is written to ground_truth.json in the output folder.

Usage: make_mock_clips.py OUTPUT_DIR
"""
import json
import subprocess
import sys
from pathlib import Path

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def duration(path):
    out = subprocess.run(
        [FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True)
    return float(out.stdout.strip())


def speech_wav(text, path):
    run([FFMPEG, "-y", "-v", "error", "-f", "lavfi",
         "-i", f"flite=text='{text}':voice=slt",
         "-ar", "48000", "-ac", "1", str(path)])


def silence_wav(seconds, path):
    run([FFMPEG, "-y", "-v", "error", "-f", "lavfi",
         "-i", "anullsrc=r=48000:cl=mono", "-t", str(seconds), str(path)])


def build_audio(segments, work, name):
    """segments: list of ('sil', seconds) or ('say', text).
    Returns (wav_path, truth) where truth records cue times."""
    parts = []
    t = 0.0
    truth = {}
    for i, (kind, val) in enumerate(segments):
        p = work / f"{name}_seg{i}.wav"
        if kind == "sil":
            silence_wav(val, p)
            d = float(val)
        else:
            speech_wav(val, p)
            d = duration(p)
            low = val.lower()
            if low.startswith("start recording"):
                truth["start_say_begin"] = t
                truth["start_say_end"] = t + d
            if low.startswith("stop recording"):
                truth["stop_say_begin"] = t
                truth["stop_say_end"] = t + d
        parts.append(p)
        t += d
    listfile = work / f"{name}_audio.txt"
    listfile.write_text("".join(f"file '{p}'\n" for p in parts))
    out = work / f"{name}_audio.wav"
    run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(listfile), "-c", "copy", str(out)])
    truth["duration"] = duration(out)
    return out, truth


def build_clip(audio, total, path, width=640, height=360, second_audio=None):
    cmd = [FFMPEG, "-y", "-v", "error",
           "-f", "lavfi", "-i", f"testsrc2=size={width}x{height}:rate=30:duration={total:.3f}",
           "-i", str(audio)]
    if second_audio is not None:
        cmd += ["-i", str(second_audio)]
        cmd += ["-map", "0:v", "-map", "1:a", "-map", "2:a"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-bf", "0",
            "-g", "30", "-keyint_min", "30", "-sc_threshold", "0",
            "-c:a", "aac", "-ar", "48000", "-shortest", str(path)]
    run(cmd)


TEACH1 = "the mass balance over the reactor gives accumulation equal to flow in minus flow out plus generation"
TEACH2 = "for a first order reaction the concentration falls exponentially with the residence time in the vessel"


def main():
    outdir = Path(sys.argv[1])
    work = outdir / "_work"
    work.mkdir(parents=True, exist_ok=True)
    truth = {}

    a1, t1 = build_audio([
        ("sil", 2.0), ("say", "start recording"), ("sil", 1.0),
        ("say", TEACH1), ("sil", 1.0), ("say", "stop recording"), ("sil", 3.0),
    ], work, "clip1")
    c1 = outdir / "2026-11-27 09-00-00.mkv"
    build_clip(a1, t1["duration"], c1)
    truth[c1.name] = t1

    a2, t2 = build_audio([
        ("sil", 3.0), ("say", "start recording"), ("sil", 1.0),
        ("say", TEACH2), ("sil", 1.0), ("say", "stop recording"), ("sil", 2.0),
    ], work, "clip2")
    c2 = outdir / "2026-11-27 09-04-12.mkv"
    build_clip(a2, t2["duration"], c2)
    truth[c2.name] = t2

    # Clip 3: silence on the first audio track, speech on the second.
    a3, t3 = build_audio([
        ("sil", 2.0), ("say", "start recording"), ("sil", 1.0),
        ("say", TEACH1), ("sil", 1.0), ("say", "stop recording"), ("sil", 2.0),
    ], work, "clip3")
    sil3 = work / "clip3_silence.wav"
    silence_wav(t3["duration"], sil3)
    c3 = outdir / "2026-11-27 09-09-30.mkv"
    build_clip(sil3, t3["duration"], c3, second_audio=a3)
    truth[c3.name] = t3

    (outdir / "ground_truth.json").write_text(json.dumps(truth, indent=2))
    print(json.dumps(truth, indent=2))


if __name__ == "__main__":
    main()
