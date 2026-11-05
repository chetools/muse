#!/usr/bin/env python3
"""Transcribe WAV files locally with Parakeet TDT 0.6B v2 (int8, CPU).

Usage:
    python3 transcribe.py <file.wav> [more.wav ...]

Prints the transcript of each file to stdout, one per line, in argument
order. Progress goes to stderr. Nothing leaves this machine: the model
runs locally (onnx-asr), and the first run may download it (about 600 MB)
— that download is the only network use. Input must be 16 kHz, mono,
16-bit WAV, which is the format the recording app seals.

Long files are cut at low-energy points near 25 s targets before
recognition; Parakeet's encoder handles only about 20-30 s per call.
"""
import os
import sys

# ONNX Runtime sends 1DS telemetry to mobile.events.data.microsoft.com by
# default. Disable it before onnxruntime is imported anywhere.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

TARGET = 25.0  # seconds per recognition chunk
SEARCH = 4.0   # seconds either side to look for a quiet cut point

USAGE = "usage: python3 transcribe.py <file.wav> [more.wav ...]"


def load_wav(path):
    import wave

    import numpy as np

    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        width = w.getsampwidth()
        channels = w.getnchannels()
        raw = w.readframes(w.getnframes())
    if sr != 16000 or width != 2 or channels != 1:
        raise ValueError(
            f"{path}: expected 16 kHz mono 16-bit WAV, got {sr} Hz, "
            f"{channels} channel(s), {width * 8}-bit")
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0, sr


def cut_points(audio, sr):
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
        lo = int((t - SEARCH) * 10)
        hi = int((t + SEARCH) * 10)
        cuts.append((lo + int(np.argmin(rms[lo:hi]))) / 10.0)
        t = cuts[-1] + TARGET
    cuts.append(dur)
    return cuts


def transcribe_file(model, path):
    audio, sr = load_wav(path)
    cuts = cut_points(audio, sr)
    parts = []
    for i in range(len(cuts) - 1):
        seg = audio[int(cuts[i] * sr):int(cuts[i + 1] * sr)]
        text = model.recognize(seg, sample_rate=sr)
        if not isinstance(text, str):
            text = text.text
        parts.append(text.strip())
        print(f"{path}: chunk {i + 1}/{len(cuts) - 1} done", file=sys.stderr)
    return " ".join(p for p in parts if p)


def main(argv):
    if len(argv) < 2:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        import onnxruntime as ort
    except ImportError:
        print("onnxruntime is not installed in this Python environment; "
              "transcription cannot run here.", file=sys.stderr)
        return 1
    ort.disable_telemetry_events()
    try:
        import onnx_asr
    except ImportError:
        print("onnx-asr is not installed in this Python environment; "
              "transcription cannot run here.", file=sys.stderr)
        return 1
    print("loading Parakeet TDT 0.6B v2 (int8, CPU); the first run "
          "downloads the model (about 600 MB) — nothing else leaves "
          "this machine", file=sys.stderr)
    model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2",
                                quantization="int8",
                                providers=["CPUExecutionProvider"])
    transcripts = []
    for path in argv[1:]:
        try:
            transcripts.append(transcribe_file(model, path))
        except Exception as e:  # unreadable or wrong-format file
            print(f"{path}: {e}", file=sys.stderr)
            return 1
    for t in transcripts:
        print(t)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
