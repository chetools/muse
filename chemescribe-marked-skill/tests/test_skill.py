#!/usr/bin/env python3
"""Tests for the ChemEScribe Marked skill.

Run with the system python:
    python3 tests/test_skill.py
Covers the STOP RECORD / START RECORD trim state machine (including
repeated markers, an unclosed stop, a stray start, markers split across
lines and mid-sentence, and timestamp prefixes), the bundled glossary
counts, and the package shape. No model is loaded.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
TRIM = SKILL / "scripts" / "trim_markers.py"

passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"PASS {name}")
    else:
        failed += 1
        print(f"FAIL {name} {detail}")


def trim(text):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(text)
        path = f.name
    r = subprocess.run([sys.executable, str(TRIM), path],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout, json.loads(r.stderr.strip().splitlines()[-1])


# 1. One marked section is removed; the rest is kept in order.
out, log = trim("alpha beta stop record gamma delta start record epsilon zeta\n")
check("basic trim", out.split() == ["alpha", "beta", "epsilon", "zeta"], out)
check("basic section count", log["section_count"] == 1 and
      log["sections_removed"][0]["words"] == 2, json.dumps(log))
check("basic word counts", log["words_kept"] == 4 and log["words_removed"] == 2)

# 2. Repeated stops inside a removed section and repeated starts while
# recording are duplicates: they change nothing and are counted.
out, log = trim("a stop record stop record stop recording b c start record "
                "start record start the recording d\n")
check("repeat trim", out.split() == ["a", "d"], out)
check("repeat duplicates", log["duplicate_stop"] == 2 and
      log["duplicate_start"] == 2, json.dumps(log))
check("repeat one section", log["section_count"] == 1 and
      log["sections_removed"][0]["words"] == 2, json.dumps(log))

# 3. Two separate sections are both removed.
out, log = trim("a stop record b start record c stop record d start record e\n")
check("two sections", out.split() == ["a", "c", "e"] and
      log["section_count"] == 2, out + json.dumps(log))

# 4. An unclosed stop removes to the end and is flagged.
out, log = trim("keep this stop record gone forever and ever\n")
check("unclosed stop", out.split() == ["keep", "this"] and
      log["unclosed_stop"] is True, out + json.dumps(log))

# 5. A start marker with no preceding stop is a stray duplicate; the
# text around it is kept and the marker words are consumed.
out, log = trim("start record alpha beta\n")
check("stray start", out.split() == ["alpha", "beta"] and
      log["duplicate_start"] == 1 and log["section_count"] == 0,
      out + json.dumps(log))

# 6. A marker in the middle of a sentence splits the sentence.
out, log = trim("the valve is stop record wait a moment start record open now\n")
check("mid-sentence marker", out.split() == ["the", "valve", "is", "open", "now"],
      out)

# 7. A marker split across two lines is still found.
out, log = trim("alpha stop\nrecord gamma start\nrecord beta\n")
check("split marker", out.split() == ["alpha", "beta"], out)

# 8. Case and punctuation variants match.
out, log = trim("Alpha. STOP THE RECORDING! aside here. Start the record. Beta.\n")
check("variants", "aside" not in out and "Alpha." in out and "Beta." in out, out)

# 9. Timestamp prefixes: a line fully removed is dropped with its
# prefix; a partly kept line keeps its prefix; section ranges are the
# markers' chunk labels.
text = ("[00:00-00:25] alpha beta stop record\n"
        "[00:25-00:50] gamma delta\n"
        "[00:50-01:15] start record epsilon\n")
out, log = trim(text)
lines = out.strip().splitlines()
check("ts kept lines", lines == ["[00:00-00:25] alpha beta",
                                 "[00:50-01:15] epsilon"], out)
check("ts section range", log["sections_removed"][0]["from"] == "00:00-00:25" and
      log["sections_removed"][0]["to"] == "00:50-01:15", json.dumps(log))

# 10. No markers: the text passes through word for word.
out, log = trim("nothing to trim in this recording\n")
check("no markers", out.split() == ["nothing", "to", "trim", "in", "this",
                                    "recording"] and log["section_count"] == 0,
      out + json.dumps(log))

# 11. Talking about recording is not a marker. "record" alone, "stop"
# alone, and "start the valve" must not trigger anything.
out, log = trim("record the value then stop the flow and start the valve\n")
check("non-marker phrases kept", log["section_count"] == 0 and
      len(out.split()) == 11, out + json.dumps(log))

# 12. Bundled glossary counts (the ChemEScribe bundle of record).
g = SKILL / "glossary"
check("glossary entries", len(json.loads((g / "glossary.json").read_text())) == 756)
check("corrections 152", len(json.loads((g / "corrections.json").read_text())) == 152)
check("slash pairs 60", len(json.loads((g / "slash-pairs.json").read_text())) == 60)
check("vocabulary 745", len((g / "vocabulary.txt").read_text().splitlines()) == 745)

# 13. The pipeline scripts copied from ChemEScribe are byte-identical
# when the source skill is present (skipped on a shared installation
# that does not carry it).
src = SKILL.parent / "local-chemescribe"
names = ["transcribe.py", "correct.py", "context_choice.py",
         "dict_check.py", "tidy.py"]
if src.exists():
    same = all((SKILL / "scripts" / n).read_bytes() ==
               (src / "scripts" / n).read_bytes() for n in names)
    check("pipeline scripts byte-identical to ChemEScribe", same)
    gsame = all((SKILL / "glossary" / p.name).read_bytes() == p.read_bytes()
                for p in (src / "glossary").iterdir() if p.is_file())
    check("glossary bundle byte-identical to ChemEScribe", gsame)
else:
    check("pipeline scripts byte-identical to ChemEScribe (source absent, skipped)", True)

# 14. Package shape: the sections the template requires, and the
# defining feature named in the instructions.
body = (SKILL / "SKILL.md").read_text()
for needle in ["## Available connectors", "## Alternatives for better results",
               "STOP RECORD", "trim_markers.py"]:
    check(f"SKILL.md carries {needle!r}", needle in body)
yaml_text = (SKILL / "skill.yaml").read_text()
check("skill.yaml name", "name: local_chemescribe_marked" in yaml_text)

# 15. The removed options stay removed: no main-speaker filter, no
# technical-content filter, no personal dictionary, in the
# instructions, the descriptor, or the scripts folder.
joined = body + yaml_text
for absent in ["personal-glossary", "learn_diff", "Main speaker only",
               "Technical content only"]:
    check(f"removed option absent: {absent!r}", absent not in joined)
check("learn_diff.py absent", not (SKILL / "scripts" / "learn_diff.py").exists())

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
