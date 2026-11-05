#!/usr/bin/env python3
"""Transcribe audio files locally with Parakeet TDT 0.6B v2 (int8, CPU).

Usage:
    python3 transcribe.py [--timestamps] <audio-file> [more files ...]

With --timestamps, each chunk is printed on its own line prefixed with
its time range in the recording, [mm:ss-mm:ss] (h:mm:ss past one hour),
one chunk per line. Without it, one plain transcript line per file.

Accepts WAV, MP3, M4A, WebM, OGG, MP4 and any other format ffmpeg can
read. Anything that is not already 16 kHz mono 16-bit WAV is converted
with ffmpeg into a temporary WAV first; the original file is untouched.

Prints one transcript per input file to stdout, in argument order.
Progress and chunk notes go to stderr. Transcription runs entirely on
this machine; the audio is never uploaded.

Long files are cut at low-energy points near 25 s targets before
transcription (Parakeet's encoder handles only about 20 to 30 s per
call), and the chunk transcripts are joined with spaces.

Setup (one time):  python3 -m pip install onnx-asr
plus ffmpeg on the system path. The first run also downloads the
Parakeet model (about 670 MB) to a local cache; later runs reuse it.
"""
import os
import sys

# ONNX Runtime sends telemetry to Microsoft by default. Disable it before
# onnxruntime is imported anywhere, and again on the module itself.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

import shutil
import subprocess
import tempfile
import wave

TARGET = 25.0  # seconds per chunk
SEARCH = 4.0   # seconds either side to look for a quiet cut point

INSTALL = ("The local Parakeet transcription setup is missing. Install it once with:\n"
           "    python3 -m pip install onnx-asr\n"
           "and put ffmpeg on the system path (macOS: brew install ffmpeg; "
           "Debian/Ubuntu: sudo apt install ffmpeg; Windows: winget install ffmpeg). "
           "The first transcription run then downloads the Parakeet model "
           "(about 670 MB) to a local cache. Nothing is transcribed until "
           "the setup is in place.")


def wav_spec_ok(path):
    try:
        with wave.open(path, "rb") as w:
            return (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
    except (wave.Error, EOFError, OSError):
        return False


def to_wav(path, tmpdir):
    """Return a 16 kHz mono 16-bit WAV for path, converting when needed."""
    if path.lower().endswith(".wav") and wav_spec_ok(path):
        return path
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not on the system path")
    out = os.path.join(tmpdir, os.path.basename(path) + ".16k.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path,
                    "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", out],
                   check=True)
    return out


def format_ts(seconds):
    s = int(round(seconds))
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    return f"{s // 60:02d}:{s % 60:02d}"


def read_wav(path):
    import numpy as np
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        raw = w.readframes(n)
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def chunk_bounds(audio, sr):
    """Cut points (seconds) at the lowest-energy 0.1 s window near each target."""
    import numpy as np
    dur = len(audio) / sr
    if dur <= TARGET + 8.0:
        return [0.0, dur]
    win = int(0.1 * sr)
    rms = np.array([np.sqrt(np.mean(audio[i:i + win] ** 2))
                    for i in range(0, len(audio) - win, win)])
    cuts = [0.0]
    t = TARGET
    while t < dur - 8.0:
        lo, hi = int((t - SEARCH) * 10), int((t + SEARCH) * 10)
        cuts.append((lo + int(np.argmin(rms[lo:hi]))) / 10.0)
        t = cuts[-1] + TARGET
    cuts.append(dur)
    return cuts


def main(argv):
    timestamps = "--timestamps" in argv[1:]
    files = [a for a in argv[1:] if a != "--timestamps"]
    if not files:
        print("usage: python3 transcribe.py [--timestamps] <audio-file> [more files ...]",
              file=sys.stderr)
        return 2
    try:
        import numpy as np  # noqa: F401  (pulled in by onnx-asr; checked for the setup message)
        import onnxruntime as ort
        ort.disable_telemetry_events()
        import onnx_asr
    except ImportError:
        print(INSTALL, file=sys.stderr)
        return 1
    if shutil.which("ffmpeg") is None:
        print(INSTALL, file=sys.stderr)
        return 1
    print("Loading the Parakeet model (the first run downloads it, about 670 MB; "
          "it stays on this machine).", file=sys.stderr)
    model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2", quantization="int8",
                                providers=["CPUExecutionProvider"])
    sr = 16000
    with tempfile.TemporaryDirectory() as tmpdir:
        for path in files:
            if not os.path.isfile(path):
                print(f"transcribe.py: no such file: {path}", file=sys.stderr)
                return 1
            try:
                wav_path = to_wav(path, tmpdir)
            except (RuntimeError, subprocess.CalledProcessError) as e:
                print(f"transcribe.py: cannot convert {path}: {e}", file=sys.stderr)
                return 1
            audio = read_wav(wav_path)
            cuts = chunk_bounds(audio, sr)
            parts = []
            for i in range(len(cuts) - 1):
                seg = audio[int(cuts[i] * sr):int(cuts[i + 1] * sr)]
                text = model.recognize(seg, sample_rate=sr)
                if not isinstance(text, str):
                    text = text.text
                parts.append(text.strip())
                print(f"{path}: chunk {i + 1} of {len(cuts) - 1} "
                      f"[{cuts[i]:.1f}-{cuts[i + 1]:.1f} s] done", file=sys.stderr)
            if timestamps:
                if len(files) > 1:
                    print(f"# {path}")
                for i, part in enumerate(parts):
                    if part:
                        print(f"[{format_ts(cuts[i])}-{format_ts(cuts[i + 1])}] {part}")
            else:
                print(" ".join(p for p in parts if p))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
