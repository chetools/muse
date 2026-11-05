#!/usr/bin/env python3
"""Tests for the Parakeet transcription skill.

Run with the system python for the correction and packaging checks:
    python3 tests/test_skill.py
Run with a python that has onnx-asr installed to also run the live
transcription check (it uses the cached model and a short clip):
    <venv>/bin/python tests/test_skill.py <clip.wav>
The live check converts the clip to MP3 first, so the ffmpeg conversion
path in transcribe.py is exercised, not only the WAV path.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"PASS {name}")
    else:
        failed += 1
        print(f"FAIL {name} {detail}")


def run(args, **kw):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, **kw)


# 1. Glossary bundle counts and status split.
glossary = json.loads((SKILL / "glossary" / "glossary.json").read_text())
corrections = json.loads((SKILL / "glossary" / "corrections.json").read_text())
vocab = (SKILL / "glossary" / "vocabulary.txt").read_text().strip().splitlines()
check("glossary has 755 entries", len(glossary) == 755, f"got {len(glossary)}")
check("corrections has 203 pairs", len(corrections) == 203, f"got {len(corrections)}")
attested = [c for c in corrections if c.get("status") == "attested"]
check("7 attested pairs", len(attested) == 7, f"got {len(attested)}")
check("vocabulary has 744 terms", len(vocab) == 744, f"got {len(vocab)}")

# 2. Correction map: attested and predicted pairs applied, genuine word kept.
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "raw.txt"
    src.write_text("The gasb and the anaconda equation and the murphy efficiency "
                   "govern it. The flow is compressible.")
    r = run([str(SKILL / "scripts" / "correct.py"), str(src),
             str(SKILL / "glossary" / "corrections.json")])
    out = r.stdout
    check("map corrects gasb", "fugacity" in out, out)
    check("map corrects anaconda equation", "Antoine equation" in out, out)
    check("map corrects murphy efficiency", "Murphree efficiency" in out, out)
    check("genuine word untouched", "compressible" in out, out)
    applied = json.loads(r.stderr.strip().splitlines()[-1]) if r.stderr.strip() else []
    check("map reports 3 applied", len(applied) == 3, f"got {applied}")

# 3. Longest-first single pass: the inserted term is never rescanned.
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "raw.txt"
    src.write_text("Use the ratchford rice procedure here.")
    r = run([str(SKILL / "scripts" / "correct.py"), str(src),
             str(SKILL / "glossary" / "corrections.json")])
    check("ratchford rice corrected once",
          r.stdout.count("Rachford") == 1 and "Rachford–Rice" in r.stdout, r.stdout)

# 4. transcribe.py usage error costs nothing and needs no setup.
r = run([str(SKILL / "scripts" / "transcribe.py")])
check("usage exit 2", r.returncode == 2 and "usage" in r.stderr, r.stderr[:120])

# 5. Live transcription, only when onnx-asr is importable in this python.
try:
    import onnx_asr  # noqa: F401
    have_asr = True
except ImportError:
    have_asr = False
if have_asr and len(sys.argv) > 1:
    clip = sys.argv[1]
    with tempfile.TemporaryDirectory() as td:
        mp3 = str(Path(td) / "clip.mp3")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", clip, mp3], check=True)
        r = run([str(SKILL / "scripts" / "transcribe.py"), mp3])
        words = r.stdout.split()
        check("live transcription non-empty", len(words) > 20,
              f"got {len(words)} words: {r.stdout[:120]!r} stderr: {r.stderr[-200:]}")
else:
    print("SKIP live transcription (onnx-asr not in this python, or no clip given)")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
