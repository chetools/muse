#!/usr/bin/env python3
"""Transcribe WAV files locally with Parakeet TDT 0.6B v2 (int8, CPU).

Usage:
    python3 transcribe.py <file.wav> [more.wav ...]

Prints one transcript per input file to stdout, in argument order.
Progress and chunk notes go to stderr. The audio is the sealed audio the
helper downloaded from the course server; transcription runs entirely on
this machine and nothing is uploaded anywhere.

Long files are cut at low-energy points near 25 s targets before
transcription (Parakeet's encoder handles only ~20-30 s per call), and the
chunk transcripts are joined with spaces. Input must be 16 kHz mono
16-bit WAV, the format the recording app seals.

Setup (one time):  python3 -m pip install onnx-asr
The first run also downloads the model (about 670 MB) to a local cache.
"""
import os
import sys

# ONNX Runtime sends telemetry to Microsoft by default. Disable it before
# onnxruntime is imported anywhere, and again on the module itself.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

import wave

TARGET = 25.0  # seconds per chunk
SEARCH = 4.0   # seconds either side to look for a quiet cut point

INSTALL = ("The local Parakeet transcription setup is missing. Install it once with:\n"
           "    python3 -m pip install onnx-asr\n"
           "The first transcription run then downloads the Parakeet model "
           "(about 670 MB) to a local cache. Nothing is transcribed until "
           "the setup is in place.")


def read_wav(path):
    import numpy as np
    with wave.open(path, "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sr != 16000 or ch != 1 or sw != 2:
        raise ValueError(
            f"{path}: expected 16 kHz mono 16-bit WAV, got {sr} Hz, {ch} channel(s), "
            f"{sw * 8}-bit. The sealed audio is always 16 kHz mono; do not convert "
            "or re-record it — report the problem instead.")
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0, sr


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
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[3], file=sys.stderr)
        print("usage: python3 transcribe.py <file.wav> [more.wav ...]", file=sys.stderr)
        return 2
    try:
        import numpy as np  # noqa: F401  (pulled in by onnx-asr; checked here for the setup message)
        import onnxruntime as ort
        ort.disable_telemetry_events()
        import onnx_asr
    except ImportError:
        print(INSTALL, file=sys.stderr)
        return 1
    print("Loading the Parakeet model (the first run downloads it, about 670 MB; "
          "it stays on this machine).", file=sys.stderr)
    # One thread, measured on a 4-core machine (2026-11-06): ONNX Runtime's
    # default threading made recognition about 25% slower for this model,
    # whose decoding loop is sequential; a single thread was faster in
    # repeated interleaved runs.
    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = 1
    sess_options.inter_op_num_threads = 1
    model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2", quantization="int8",
                                providers=["CPUExecutionProvider"],
                                sess_options=sess_options)
    for path in argv[1:]:
        try:
            audio, sr = read_wav(path)
        except (ValueError, wave.Error, FileNotFoundError) as e:
            print(f"transcribe.py: {e}", file=sys.stderr)
            return 1
        cuts = chunk_bounds(audio, sr)
        parts = []
        for i in range(len(cuts) - 1):
            seg = audio[int(cuts[i] * sr):int(cuts[i + 1] * sr)]
            text = model.recognize(seg, sample_rate=sr)
            if not isinstance(text, str):
                text = text.text
            parts.append(text.strip())
            print(f"{path}: chunk {i + 1} [{cuts[i]:.1f}-{cuts[i + 1]:.1f} s] done",
                  file=sys.stderr)
        print(" ".join(p for p in parts if p))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
