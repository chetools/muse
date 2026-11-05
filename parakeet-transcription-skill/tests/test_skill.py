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


# 1. Glossary bundle counts and status split. Since the Phase 1 cleanup
# (2026-11-05) the 203 pairs are two classes: 145 certain pairs in
# corrections.json (replace outright) and 58 uncertain pairs in
# slash-pairs.json (context rules or slash form). 7 pairs are attested:
# 5 in the certain class, plus the traps "gives" and "ideas" in the
# slash class.
glossary = json.loads((SKILL / "glossary" / "glossary.json").read_text())
corrections = json.loads((SKILL / "glossary" / "corrections.json").read_text())
slash_pairs = json.loads((SKILL / "glossary" / "slash-pairs.json").read_text())
vocab = (SKILL / "glossary" / "vocabulary.txt").read_text().strip().splitlines()
check("glossary has 755 entries", len(glossary) == 755, f"got {len(glossary)}")
check("corrections has 145 certain pairs", len(corrections) == 145,
      f"got {len(corrections)}")
check("slash-pairs has 58 uncertain pairs", len(slash_pairs) == 58,
      f"got {len(slash_pairs)}")
check("classes total 203 and are disjoint",
      len(corrections) + len(slash_pairs) == 203
      and not ({c["heard"].lower() for c in corrections}
               & {s["heard"].lower() for s in slash_pairs}))
attested = [c for c in corrections if c.get("status") == "attested"]
check("5 attested pairs in the certain class", len(attested) == 5,
      f"got {len(attested)}")
check("attested traps gives/ideas are slash class",
      {s["heard"] for s in slash_pairs} >= {"gives", "ideas"})
check("vocabulary has 744 terms", len(vocab) == 744, f"got {len(vocab)}")

# 1b. The Phase 1 fixes are in the shipped data.
cmap = {c["heard"]: c["term"] for c in corrections}
smap = {s["heard"]: s["replacement"] for s in slash_pairs}
check("buckingham certain as Buckingham Pi theorem",
      cmap.get("buckingham") == "Buckingham Pi theorem")
check("thermo-siphon certain as thermosiphon",
      cmap.get("thermo-siphon") == "thermosiphon")
check("stoy-kee-o-metric certain as stoichiometric",
      cmap.get("stoy-kee-o-metric") == "stoichiometric")
check("centering slash pair (length limit waived)",
      smap.get("centering")
      == "centering/poisoning/deactivation/fouling/sintering")
check("no pair offers trays, downcomer",
      not any("trays, downcomer" in r for r in smap.values()))
check("weir family offers weir itself",
      smap.get("weir") == "weir/weir" and smap.get("we're") == "we're/weir"
      and smap.get("weird") == "weird/weir")
check("aldehyde offers no methyl ethyl ketone",
      smap.get("aldehyde") == "aldehyde/aldehyde")
check("new offers nu, not mu", smap.get("new") == "new/nu")

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

# 3b. correct.py --text form: one chunk, same contract as the file form.
r = run([str(SKILL / "scripts" / "correct.py"), "--text",
         "The gasb governs it.", str(SKILL / "glossary" / "corrections.json")])
check("text form corrects gasb", "fugacity" in r.stdout, r.stdout)
applied_t = json.loads(r.stderr.strip().splitlines()[-1]) if r.stderr.strip() else []
check("text form reports 1 applied", len(applied_t) == 1, f"got {applied_t}")
r = run([str(SKILL / "scripts" / "correct.py"), "--text"])
check("text form usage exit 2", r.returncode == 2, f"got {r.returncode}")

# 3d. Context-rules stage: coverage, decide, abstain, kept, pipeline.
rules = json.loads((SKILL / "glossary" / "context-rules.json").read_text())
check("rules cover exactly the slash set",
      [i["heard"].lower() for i in rules["items"]]
      == [s["heard"].lower() for s in slash_pairs],
      f"{len(rules['items'])} items vs {len(slash_pairs)} slash pairs")
check("rules slash forms match slash-pairs",
      all(i["slash_form"] == smap[i["heard"]] for i in rules["items"]))

CC = [str(SKILL / "scripts" / "context_choice.py"),
      str(SKILL / "glossary" / "slash-pairs.json"),
      str(SKILL / "glossary" / "context-rules.json")]
r = run([CC[0], "--text",
         "The second viral coefficient is temperature dependent."] + CC[1:])
check("rules decide: virial coefficient chosen, not duplicated",
      r.stdout.strip()
      == "The second virial coefficient is temperature dependent.",
      r.stdout)
log = json.loads(r.stderr.strip().splitlines()[-1])
check("rules decide: choice logged with cues",
      log[0]["outcome"] == "chose"
      and log[0]["candidate"] == "virial coefficient"
      and log[0]["scores"]["virial coefficient"] >= 8
      and any("second virial coefficient" in c for c in log[0]["cues"]),
      f"got {log}")
r = run([CC[0], "--text", "The viral coefficient was noted."] + CC[1:])
check("rules abstain: slash form stands",
      "viral/virial equation/virial coefficient" in r.stdout, r.stdout)
log = json.loads(r.stderr.strip().splitlines()[-1])
check("rules abstain: logged as abstained",
      log[0]["outcome"] == "abstained", f"got {log}")
r = run([CC[0], "--text",
         "The liquid flows over the weird into the downcomer."] + CC[1:])
check("rules choose weir for a misheard contraction slot",
      "flows over the weir into the downcomer" in r.stdout, r.stdout)
# Ordinary candidates must be reachable on their own phrase evidence:
# the phrase search uses the qualifier-stripped label (the heard word
# itself for ordinary candidates), never "viral (ordinary)".
r = run([CC[0], "--text", "The patient has a viral infection."] + CC[1:])
log = json.loads(r.stderr.strip().splitlines()[-1])
check("rules keep ordinary viral on its phrase evidence",
      r.stdout.strip() == "The patient has a viral infection."
      and log[0]["outcome"] == "kept", f"{r.stdout} {log}")
r = run([CC[0], "--text",
         "This equation gives us the following result."] + CC[1:])
log = json.loads(r.stderr.strip().splitlines()[-1])
check("rules keep ordinary gives on its phrase evidence",
      r.stdout.strip() == "This equation gives us the following result."
      and log[0]["outcome"] == "kept", f"{r.stdout} {log}")
# An abstention with non-zero scores must still log the cues that fired.
r = run([CC[0], "--text",
         "The viral equation of state is used for a real gas."] + CC[1:])
log = json.loads(r.stderr.strip().splitlines()[-1])
check("abstention log carries the fired cues",
      log[0]["outcome"] == "abstained" and len(log[0]["cues"]) > 0
      and max(log[0]["scores"].values()) > 0, f"got {log}")
r = run([CC[0]])
check("context_choice usage exit 2", r.returncode == 2,
      f"got {r.returncode}")

# Pipeline: certain map first, then the rules stage; a timestamp
# prefix passes through both untouched.
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "raw.txt"
    src.write_text("[00:00-00:25] The gasb and the second viral "
                   "coefficient is temperature dependent.\n")
    r1 = run([str(SKILL / "scripts" / "correct.py"), str(src),
              str(SKILL / "glossary" / "corrections.json")])
    mid = Path(td) / "mid.txt"
    mid.write_text(r1.stdout)
    r2 = run([CC[0], str(mid)] + CC[1:])
    check("pipeline: map then rules, timestamp prefix intact",
          r2.stdout.strip() == "[00:00-00:25] The fugacity and the "
          "second virial coefficient is temperature dependent.",
          r2.stdout)

# 3c. transcribe.py partial-file writer and WORDS progress lines.
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("transcribe_partial", SKILL / "scripts" / "transcribe.py")
_tmod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_tmod)
with tempfile.TemporaryDirectory() as td:
    pp = str(Path(td) / "x.partial.txt")
    _tmod.write_partial(pp, ["[00:00-00:25] first words"])
    check("partial file written", Path(pp).read_text().strip() == "[00:00-00:25] first words",
          Path(pp).read_text())
    _tmod.write_partial(pp, ["[00:00-00:25] first words", "[00:25-00:50] more words"])
    check("partial file grows by chunk", "more words" in Path(pp).read_text(), Path(pp).read_text())
    check("no partial tmp left", not Path(pp + ".tmp").exists())
r = run([str(SKILL / "scripts" / "transcribe.py"), "--partial"])
check("partial without path exit 2", r.returncode == 2, f"got {r.returncode}")

# 4. transcribe.py usage error costs nothing and needs no setup.
r = run([str(SKILL / "scripts" / "transcribe.py")])
check("usage exit 2", r.returncode == 2 and "usage" in r.stderr, r.stderr[:120])
r = run([str(SKILL / "scripts" / "transcribe.py"), "--timestamps"])
check("usage exit 2 with flag only", r.returncode == 2, f"got {r.returncode}")

# 4b. Timestamp formatting.
import importlib.util
spec = importlib.util.spec_from_file_location(
    "transcribe", SKILL / "scripts" / "transcribe.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
check("format_ts zero", mod.format_ts(0) == "00:00", mod.format_ts(0))
check("format_ts minutes", mod.format_ts(65.2) == "01:05", mod.format_ts(65.2))
check("format_ts hours", mod.format_ts(3661) == "1:01:01", mod.format_ts(3661))

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
        r2 = run([str(SKILL / "scripts" / "transcribe.py"), "--timestamps", mp3])
        import re
        first = r2.stdout.strip().splitlines()[0] if r2.stdout.strip() else ""
        check("live timestamps prefix", bool(re.match(r"^\[\d\d:\d\d-\d\d:\d\d\] ", first)),
              f"first line: {first[:80]!r}")
        stripped = re.sub(r"\[\d+:\d\d(?::\d\d)?-\d+:\d\d(?::\d\d)?\] ", "", r2.stdout)
        check("live timestamps same words", stripped.split() == words,
              "timestamped output changed the words")
else:
    print("SKIP live transcription (onnx-asr not in this python, or no clip given)")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
