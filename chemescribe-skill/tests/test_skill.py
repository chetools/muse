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
# (2026-11-05) the pairs are two classes: certain pairs in
# corrections.json (replace outright) and 58 uncertain pairs in
# slash-pairs.json (context rules or slash form). The extension of
# 2026-11-05 added 2 certain Nabier pairs (one attested by the user's
# own test recording) and the term "Gibbs–Duhem equation": certain
# 152, total 212, 9 attested across both classes (7 in the certain
# class, plus the traps "gives" and "ideas" in the slash class).
glossary = json.loads((SKILL / "glossary" / "glossary.json").read_text())
corrections = json.loads((SKILL / "glossary" / "corrections.json").read_text())
slash_pairs = json.loads((SKILL / "glossary" / "slash-pairs.json").read_text())
vocab = (SKILL / "glossary" / "vocabulary.txt").read_text().strip().splitlines()
check("glossary has 756 entries", len(glossary) == 756, f"got {len(glossary)}")
check("corrections has 152 certain pairs", len(corrections) == 152,
      f"got {len(corrections)}")
check("slash-pairs has 60 uncertain pairs", len(slash_pairs) == 60,
      f"got {len(slash_pairs)}")
check("classes total 212 and are disjoint",
      len(corrections) + len(slash_pairs) == 212
      and not ({c["heard"].lower() for c in corrections}
               & {s["heard"].lower() for s in slash_pairs}))
attested = [c for c in corrections if c.get("status") == "attested"]
check("7 attested pairs in the certain class", len(attested) == 7,
      f"got {len(attested)}")
check("attested traps gives/ideas are slash class",
      {s["heard"] for s in slash_pairs} >= {"gives", "ideas"})
check("vocabulary has 745 terms", len(vocab) == 745, f"got {len(vocab)}")
# Extension data: the Nabier pairs, the Gibbs–Duhem term, the
# wordlist and the traps list.
cmap_all = {c["heard"]: c for c in corrections}
check("nabier stokes is a certain attested pair",
      cmap_all.get("nabier stokes", {}).get("term") == "Navier–Stokes equations"
      and cmap_all["nabier stokes"].get("status") == "attested")
check("nabier is a certain predicted pair",
      cmap_all.get("nabier", {}).get("term") == "Navier"
      and cmap_all["nabier"].get("status") == "predicted")
check("Gibbs–Duhem equation is a glossary term and in the vocabulary",
      any(e["term"] == "Gibbs–Duhem equation" for e in glossary)
      and "Gibbs–Duhem equation" in vocab)
check("no correction pair for Gibbs–Duhem (term only)",
      not any("duhem" in c["heard"] for c in corrections))
words = [l for l in (SKILL / "glossary" / "words.txt").read_text().splitlines()
         if l and not l.startswith("#")]
check("wordlist is large (SCOWL, >100k words)", len(words) > 100000,
      f"got {len(words)}")
check("wordlist has ordinary academic words, not mishearings",
      "committee" in words and "photosynthesis" in words
      and "nabier" not in words and "gasb" not in words)
traps = [l for l in (SKILL / "glossary" / "traps.txt").read_text().splitlines()
         if l and not l.startswith("#")]
check("traps list carries phaser but not nabier",
      "phaser" in traps and "nabier" not in traps, f"{len(traps)} traps")

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

# 3e. Dictionary pass: the general net for unpredicted mishearings.
DC = [str(SKILL / "scripts" / "dict_check.py"),
      str(SKILL / "glossary" / "words.txt"),
      str(SKILL / "glossary" / "vocabulary.txt"),
      str(SKILL / "glossary" / "glossary.json"),
      str(SKILL / "glossary" / "traps.txt")]
USER_SENTENCE = ("I am testing how well this thing works if the Gibbs-Duhem "
                 "equation, the Maxwell relations. And the various chemical "
                 "engineering terms are actually corrected properly. If the "
                 "Nabier Stokes Darcy friction factor Fanning friction "
                 "factor Optimally corrected.")
r = run([DC[0], "--text", USER_SENTENCE] + DC[1:])
check("dictionary pass alone catches Nabier Stokes",
      "Navier–Stokes equations" in r.stdout, r.stdout)
log = json.loads(r.stderr.strip().splitlines()[-1])
check("dictionary catch is logged as a replacement with scores",
      any(l["outcome"] == "replaced" and l["candidate"] == "Navier–Stokes equations"
          for l in log), f"got {log}")
r = run([DC[0], "--text", "The entahlpy balance closes."] + DC[1:])
check("dictionary pass replaces a near-spelling garble",
      r.stdout.strip() == "The enthalpy balance closes.", r.stdout)
r = run([DC[0], "--text",
         "The guitarist ran the solo through a phaser pedal."] + DC[1:])
log = json.loads(r.stderr.strip().splitlines()[-1])
check("a trap word is never replaced silently",
      all(l["outcome"] != "replaced" for l in log)
      and "phasor pedal" not in r.stdout.replace("phaser/phasor", ""),
      f"{r.stdout} {log}")
r = run([DC[0], "--text",
         "The committee reviewed the results and the analysis was significant."] + DC[1:])
check("ordinary academic prose is untouched and unflagged",
      r.stdout.strip()
      == "The committee reviewed the results and the analysis was significant."
      and json.loads(r.stderr.strip().splitlines()[-1]) == [], r.stdout)
r = run([DC[0], "--text", "[00:00-00:25] The entahlpy balance closes."] + DC[1:])
check("dictionary pass leaves the timestamp prefix untouched",
      r.stdout.strip() == "[00:00-00:25] The enthalpy balance closes.", r.stdout)
r = run([DC[0], "--text"])
check("dict_check usage exit 2", r.returncode == 2, f"got {r.returncode}")
# Independent-review regressions (Brief A findings 1-3, 2026-11-05):
# units, digit-adjacent letter runs and malformed candidate fragments.
r = run([DC[0], "--text",
         "the pressure is 101 kpa and the amount is 3 mol"] + DC[1:])
check("dictionary pass never touches unit symbols",
      r.stdout.strip() == "the pressure is 101 kpa and the amount is 3 mol"
      and json.loads(r.stderr.strip().splitlines()[-1]) == [], r.stdout)
r = run([DC[0], "--text", "entahlpy300 and 300entahlpy and h2o"] + DC[1:])
check("dictionary pass never touches letter runs touching digits",
      r.stdout.strip() == "entahlpy300 and 300entahlpy and h2o"
      and json.loads(r.stderr.strip().splitlines()[-1]) == [], r.stdout)
r = run([DC[0], "--text", "The absorbtion column removes the solvent."] + DC[1:])
log = json.loads(r.stderr.strip().splitlines()[-1])
check("annotated-line term is reachable (absorption salvaged)",
      any(l["candidate"] == "absorption" for l in log), f"{r.stdout} {log}")
r = run([DC[0], "--text", "The seperation factor determines the purity."] + DC[1:])
check("a non-head component alone is not offered (seperation missed, as on the page)",
      r.stdout.strip() == "The seperation factor determines the purity.", r.stdout)
sys.path.insert(0, str(SKILL / "scripts"))
from dict_check import DictData as _DD
_dd = _DD(DC[1], DC[2], DC[3], DC[4])
check("no malformed candidate terms (unbalanced parens or notes)",
      all(t.count("(") == t.count(")") and " — " not in t for t, _ in _dd.terms),
      f"{len(_dd.terms)} terms")


# 3e2. 2026-11-05 user-test extension: Ponchon, Bode, Routh-Hurwitz,
# the dictionary guard, and the weekday/month supplement.
check("poinch savarit certain", cmap.get("poinch savarit") == "Ponchon–Savarit")
check("ponchon savarit certain", cmap.get("ponchon savarit") == "Ponchon–Savarit")
check("berwitz certain", cmap.get("berwitz") == "Hurwitz")
check("rude berwitz certain", cmap.get("rude berwitz") == "Routh–Hurwitz")
check("berlouse certain (attested, skill only)",
      cmap_all.get("berlouse", {}).get("term") == "Bernoulli"
      and cmap_all["berlouse"].get("status") == "attested")
check("poinch slash pair", smap.get("poinch") == "poinch/pinch/Ponchon")
check("boday slash pair", smap.get("boday") == "boday/Bode")
check("weekday and month names are in the wordlist",
      all(w in words for w in ["monday", "friday", "sunday", "january", "december"]))
r = run([DC[0], "--text", "the poinch and savarit method is graphical"] + DC[1:])
check("dictionary guard: poinch and savarit is never silently pinch",
      "pinch" not in r.stdout.replace("poinch/pinch/Ponchon–Savarit", "")
      and r.stdout.strip() == "the poinch/pinch/Ponchon–Savarit and savarit method is graphical",
      r.stdout)
r = run([CC[0], "--text", "The poinch point analysis is standard."] + CC[1:])
check("rules choose pinch on pinch collocations", r.stdout.strip() == "The pinch point analysis is standard.", r.stdout)
r = run([CC[0], "--text", "The boday plot shows the margin."] + CC[1:])
check("rules choose Bode for the boday plot", r.stdout.strip() == "The Bode plot shows the margin.", r.stdout)
r = run([CC[0], "--text", "Mr Boday spoke first."] + CC[1:])
check("bare surname Boday stays slash", "Boday/Bode" in r.stdout, r.stdout)
r = run([str(SKILL / "scripts" / "correct.py"), "--text",
         "the Rude-Berwitz criterion", str(SKILL / "glossary" / "corrections.json")])
check("hyphen form matches rude berwitz pair", r.stdout.strip() == "the Routh–Hurwitz criterion", r.stdout)

# 3f. Tidy stage: mechanical edits only, all logged.
TD = [str(SKILL / "scripts" / "tidy.py")]
r = run(TD + ["--text", "um the the pressure , rises"])
check("tidy removes fillers, duplicates and space before punctuation",
      r.stdout.strip() == "the pressure, rises", r.stdout)
log = json.loads(r.stderr.strip().splitlines()[-1])
check("tidy logs its edit classes",
      {e["edit"] for e in log} >= {"filler", "duplicate", "spacing"}, f"got {log}")
r = run(TD + ["--text", "the value is stable", "--final"])
check("tidy final adds initial capital and terminal full stop",
      r.stdout.strip() == "The value is stable.", r.stdout)
r = run(TD + ["--text", "[00:00-00:25] um the gasb rises", "--final"])
check("tidy keeps the timestamp prefix intact",
      r.stdout.strip() == "[00:00-00:25] The gasb rises.", r.stdout)
r = run(TD + ["--text"])
check("tidy usage exit 2", r.returncode == 2, f"got {r.returncode}")


# 3g2. Full pipeline on the user's second test paragraph (2026-11-05):
# the skill version, with Bernoulli restored by the berlouse pair.
USER_PARA = ("The Navier-Stokes equation works on Monday, Tuesday, Wednesday, "
             "Thursday, Friday, Saturday, and Sunday, every day of the week. "
             "Conjunction with the Berlouse equation, POINCH and Savarit, and "
             "the RUDE-BERWITZ criterion in determining stability for transfer "
             "functions. The BODAY stability diagram, or also sometimes called "
             "Bode diagram, can be a bit confusing for some users.")
USER_PARA_SKILL = USER_PARA.replace("Berlouse equation", "Bernoulli equation") \
    .replace("POINCH and Savarit", "Ponchon and Savarit") \
    .replace("RUDE-BERWITZ criterion", "Routh–Hurwitz criterion") \
    .replace("BODAY stability diagram", "Bode stability diagram")
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "raw.txt"; src.write_text(USER_PARA)
    r1 = run([str(SKILL / "scripts" / "correct.py"), str(src), str(SKILL / "glossary" / "corrections.json")])
    f2 = Path(td) / "s2.txt"; f2.write_text(r1.stdout)
    r2 = run([CC[0], str(f2)] + CC[1:])
    f3 = Path(td) / "s3.txt"; f3.write_text(r2.stdout)
    r3 = run([DC[0], str(f3)] + DC[1:])
    f4 = Path(td) / "s4.txt"; f4.write_text(r3.stdout)
    r4 = run(TD + [str(f4), "--final"])
    check("full pipeline on the user's second test paragraph",
          r4.stdout.strip() == USER_PARA_SKILL, r4.stdout)

# 3g. Full pipeline regression fixture: the user's own test sentence
# (2026-11-05) through map -> rules -> dictionary -> tidy (final).
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "raw.txt"
    src.write_text(USER_SENTENCE)
    r1 = run([str(SKILL / "scripts" / "correct.py"), str(src),
              str(SKILL / "glossary" / "corrections.json")])
    f2 = Path(td) / "s2.txt"; f2.write_text(r1.stdout)
    r2 = run([CC[0], str(f2)] + CC[1:])
    f3 = Path(td) / "s3.txt"; f3.write_text(r2.stdout)
    r3 = run([DC[0], str(f3)] + DC[1:])
    f4 = Path(td) / "s4.txt"; f4.write_text(r3.stdout)
    r4 = run(TD + [str(f4), "--final"])
    expected = ("I am testing how well this thing works if the Gibbs-Duhem "
                "equation, the Maxwell relations. And the various chemical "
                "engineering terms are actually corrected properly. If the "
                "Navier–Stokes equations Darcy friction factor Fanning "
                "friction factor Optimally corrected.")
    check("full pipeline on the user's test sentence",
          r4.stdout.strip() == expected, r4.stdout)

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
