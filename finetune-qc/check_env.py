#!/usr/bin/env python3
"""Preflight environment check for the QC fine-tuning GPU pipeline.

Run it before (or instead of debugging) the training scripts:
    python check_env.py

`train_sft.py`, `train_grpo.py`, and `eval.py` all call `require()` on
import, so a broken environment fails here with an actionable message
instead of a cryptic ImportError from inside `transformers`.

Checks:
  * torch imports and a CUDA GPU is visible;
  * every GPU-stack package imports AND satisfies its pinned version range
    (kept in sync with requirements-gpu.txt);
  * the version pins `transformers` itself enforces AT IMPORT TIME are
    satisfied by what is actually installed.

On the last point, precision matters (fixed 2026-10-09 after a false
alarm): `transformers` does NOT check its whole dependency table on
import. It checks only `pkgs_to_check_at_runtime` from its
`dependency_versions_check.py` (python, tqdm, regex, packaging, filelock,
numpy, tokenizers, huggingface-hub, safetensors, accelerate, pyyaml).
The full table also carries dev/test-only entries such as
`pytest>=7.2.0,<9.0.0` whose values embed the package name
(`"pytest>=7.2.0,<9.0.0"`, not just the spec), so a naive
`dep_pkg + spec` concatenation both doubles the name and evaluates the
wrong constraint -- reporting "PROBLEMS FOUND" for a pytest 9.1.1 that
`import transformers` never looks at. This module mirrors the real
import-time check exactly: same package list, proper requirement parsing.

Exit status 0 = good to go; 1 = prints exactly what to install/fix.
Stdlib only, so this module imports even when the ML stack is broken.
"""
import importlib
import importlib.metadata as _md
import platform
import re
import sys

# Pinned, mutually compatible versions (kept in sync with
# requirements-gpu.txt): (low_inclusive, high_exclusive, excludes,
# import_name, why). "excludes" are version specs that are banned even
# inside [low, high) (from upstream metadata, e.g. unsloth's != pins).
#
# Every bound below is attributed to a real, checked source (wheels
# downloaded 2026-10-09; Requires-Dist is the compatibility oracle):
#   torch:        high <2.15.0 from unsloth 2026.10.3 Requires-Dist
#                 (torch<2.15.0,>=2.4.0); low >=2.7 because torch 2.7 is the
#                 first release line shipping official CUDA 12.8 (cu128)
#                 wheels, which Blackwell sm_120 needs.
#   unsloth:      our exact pin (requirements-gpu.txt).
#   trl:          unsloth caps trl<=1.13.0 (Requires-Dist:
#                 trl!=0.19.0,<=1.13.0,>=0.18.2); our exact pin 1.13.0.
#                 SFTConfig(dataset_text_field, max_length, packing) and
#                 SFTTrainer(processing_class=...) verified in the
#                 trl 1.13.0 trainer sources.
#   transformers: unsloth caps transformers<=5.17.0 (Requires-Dist lists
#                 transformers!=4.53.0,...,<=5.17.0,>=4.52.4); our exact pin.
#                 dtype= spelling needs transformers>=4.56.
#   tokenizers:   transformers 5.17.0's dependency_versions_table AND its
#                 Requires-Dist both say tokenizers>=0.23.1,<0.24.0, and its
#                 dependency_versions_check.py enforces it at import time.
#   peft:         unsloth Requires-Dist peft!=0.11.0,>=0.18.0; our exact pin
#                 0.21.2 also satisfies transformers' table (peft>=0.19.1).
#   bitsandbytes: unsloth Requires-Dist
#                 bitsandbytes!=0.46.0,!=0.48.0,>=0.45.5; floor >=0.49.2 is
#                 the Blackwell sm_120 floor (older bnb silently misbehaves
#                 on sm_120).
#   accelerate:   transformers 5.17.0 table: accelerate>=1.1.0 (unsloth
#                 needs >=0.34.1). device_map="auto" is ancient.
#   datasets:     trl 1.13.0 Requires-Dist forces datasets>=4.7.0 (no extra
#                 marker, unconditional); unsloth caps datasets<5.0.0.
#                 unsloth's !=4.0.*,!=4.1.0,!=4.4.*,!=4.5.0 exclusions all
#                 fall below 4.7.0, so >=4.7.0,<5.0.0 covers them.
PINS = {
    # pip name:       (low, high, excludes, import name, why)
    "torch":        ("2.7", "2.15.0", [], "torch",
                     ">=2.7: first torch line with cu128 wheels (Blackwell "
                     "sm_120); <2.15.0: unsloth 2026.10.3 metadata cap"),
    "unsloth":      ("2026.10.3", None, [], "unsloth",
                     "our exact pin; single-GPU SFT/GRPO kernels"),
    "trl":          ("1.13.0", "1.14.0", [], "trl",
                     "unsloth caps trl<=1.13.0; 1.13.0 SFT/GRPOConfig API"),
    "transformers": ("5.17.0", "5.18.0", [], "transformers",
                     "unsloth caps transformers<=5.17.0; dtype= spelling"),
    "tokenizers":   ("0.23.1", "0.24.0", [], "tokenizers",
                     "transformers 5.17.0 import-time pin"),
    "peft":         ("0.18.0", None, ["0.11.0"], "peft",
                     "unsloth needs >=0.18.0,!=0.11.0 (our pin: 0.21.2)"),
    "bitsandbytes": ("0.49.2", None, ["0.46.0", "0.48.0"], "bitsandbytes",
                     ">=0.49.2: sm_120 floor; unsloth excludes "
                     "0.46.0/0.48.0"),
    "accelerate":   ("1.1.0", None, [], "accelerate",
                     "transformers 5.17.0 table (unsloth needs >=0.34.1)"),
    "datasets":     ("4.7.0", "5.0.0", [], "datasets",
                     "trl 1.13.0 forces >=4.7.0; unsloth caps <5.0.0"),
}


def _parse(v):
    """'2026.10.3' -> (2026, 10, 3); non-numeric suffixes ignored."""
    parts = []
    for p in re.split(r"[.\-+_]", str(v)):
        m = re.match(r"(\d+)", p)
        parts.append(int(m.group(1)) if m else 0)
    return tuple(parts)


def _version_excluded(ver, excludes):
    """True if ver matches an exclusion like '0.11.0' or '4.0.*'."""
    for exc in excludes:
        exc = exc.strip()
        if exc.endswith(".*"):
            prefix = _parse(exc[:-2])
            if _parse(ver)[:len(prefix)] == prefix:
                return True
        elif _parse(ver) == _parse(exc):
            return True
    return False


def _in_range(ver, low, high, excludes=()):
    v = _parse(ver)
    if low is not None and v < _parse(low):
        return False
    if high is not None and v >= _parse(high):
        return False
    if _version_excluded(ver, excludes):
        return False
    return True


_CLAUSE_RE = re.compile(r"(>=|<=|==|!=|~=|>|<)\s*([A-Za-z0-9.*+\-_!]+)")
_REQ_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9._-]+(?:\[[^\]]*\])?)\s*(?P<specs>.*?)\s*$")


def _parse_requirement(req):
    """'pytest>=7.2.0,<9.0.0' -> ('pytest', [('>=','7.2.0'),('<','9.0.0')]).

    transformers' dependency table values EMBED the package name
    (e.g. "tokenizers>=0.23.1,<0.24.0"), so the name must be split off
    first -- concatenating key + value double-counts it.
    """
    m = _REQ_RE.match(req)
    if not m:
        return req.strip(), []
    return m.group("name"), _CLAUSE_RE.findall(m.group("specs"))


def _clause_ok(ver, op, want):
    v, w = _parse(ver), _parse(want)
    if op == "==":
        if want.endswith(".*"):
            prefix = _parse(want[:-2])
            return v[:len(prefix)] == prefix
        return v == w
    if op == "!=":
        if want.endswith(".*"):
            prefix = _parse(want[:-2])
            return v[:len(prefix)] != prefix
        return v != w
    if op == "~=":  # compatible release: >=w, == w[0] (PEP 440)
        return v >= w and v[:1] == w[:1]
    cmp = (v > w) - (v < w)
    return {">=": cmp >= 0, "<=": cmp <= 0, ">": cmp > 0, "<": cmp < 0}[op]


def _requirement_ok(ver, req):
    """True if installed version `ver` satisfies requirement string `req`."""
    _, clauses = _parse_requirement(req)
    return all(_clause_ok(ver, op, want) for op, want in clauses)


def _installed_version(import_name):
    try:
        mod = importlib.import_module(import_name)
    except Exception as e:  # noqa: BLE001 -- any import failure is a problem
        return None, f"cannot import ({type(e).__name__}: {e})"
    ver = getattr(mod, "__version__", None)
    if ver is None:
        try:
            ver = _md.version(import_name)
        except Exception:
            ver = "unknown"
    return ver, None


def _dist_version(dist_name):
    """Installed version of a distribution (None if not installed)."""
    try:
        return _md.version(dist_name)
    except Exception:  # noqa: BLE001
        return None


def check(verbose=True):
    """-> (ok: bool, problems: [str]). Never raises on a broken ML stack."""
    problems = []
    notes = []

    # 1. torch + CUDA -----------------------------------------------------
    torch_ver, err = _installed_version("torch")
    if err:
        problems.append(f"torch: {err} -- install torch with CUDA 12.8 "
                        "first, from pytorch.org")
    else:
        low, high, excludes, _, why = PINS["torch"]
        if not _in_range(torch_ver, low, high, excludes):
            problems.append(
                f"torch {torch_ver} is outside the pinned range "
                f">={low},<{high} -- ({why})")
        try:
            import torch
            if not torch.cuda.is_available():
                problems.append("torch imports but torch.cuda.is_available() "
                                "is False -- no CUDA GPU visible to this "
                                "Python (wrong torch build or no GPU)")
            else:
                cc = torch.cuda.get_device_capability(0)
                if cc[0] < 9:
                    problems.append(
                        f"GPU compute capability {cc[0]}.{cc[1]} < 9.0 -- "
                        "this pipeline targets Blackwell sm_120; older "
                        "cards may fail in Unsloth kernels")
        except Exception as e:  # noqa: BLE001
            problems.append(f"torch.cuda check failed: {e}")

    # 2. pinned packages ---------------------------------------------------
    for pip_name, (low, high, excludes, import_name, why) in PINS.items():
        if pip_name == "torch":
            continue
        ver, err = _installed_version(import_name)
        if err:
            problems.append(f"{pip_name}: {err} -- pip install "
                            f"'{pip_name}>={low}' ({why})")
        elif ver != "unknown" and not _in_range(ver, low, high, excludes):
            hi = f",<{high}" if high else ""
            exc = "".join(f",!={e}" for e in excludes)
            problems.append(
                f"{pip_name} {ver} is outside the pinned range "
                f">={low}{hi}{exc} -- run: "
                f"pip install '{pip_name}>={low}{hi}' ({why})")

    # 3. transformers' own import-time checks -------------------------------
    # Mirror dependency_versions_check.py exactly: it enforces ONLY
    # pkgs_to_check_at_runtime (the full table includes dev/test-only deps
    # like pytest that are never checked on import). Each table value embeds
    # the package name, so parse it as a requirement string.
    try:
        from transformers.dependency_versions_check import \
            pkgs_to_check_at_runtime
        from transformers.dependency_versions_table import deps as _deps
        tf_ver = _dist_version("transformers") or "?"
        for pkg in pkgs_to_check_at_runtime:
            if pkg not in _deps:
                continue
            req = _deps[pkg]
            name, _ = _parse_requirement(req)
            if pkg == "python":
                got = platform.python_version()
            else:
                # transformers only version-checks tokenizers/accelerate
                # when they are actually installed; both are required by
                # our PINS above anyway, so a missing one is already a
                # problem -- here we just mirror the version check.
                got = _dist_version(name)
                if got is None:
                    continue
            if not _requirement_ok(got, req):
                problems.append(
                    f"transformers {tf_ver} hard-checks '{req}' at import "
                    f"time but {got} is installed -- run: "
                    f"pip install '{req}' (otherwise `import transformers` "
                    "itself raises ImportError)")
    except Exception as e:  # noqa: BLE001
        # transformers missing/broken is already reported in check 2;
        # anything else here is unexpected but must not mask real results.
        notes.append(f"could not mirror transformers' import-time checks: {e}")

    # 4. attention backend (informational only -- never a failure) ----------
    try:
        import xformers
        try:
            from xformers.ops import fmha  # noqa: F401
            notes.append(f"xformers {xformers.__version__}: CUDA ops load "
                         "(fast attention available)")
        except Exception as e:  # noqa: BLE001
            notes.append(f"xformers {xformers.__version__} imports but its "
                         f"CUDA ops do NOT load ({e}); Unsloth falls back "
                         "to a slower attention backend -- training still "
                         "works, just slower. Reinstall xformers built for "
                         "your exact torch+CUDA if you want the speed back.")
    except Exception:  # noqa: BLE001
        notes.append("xformers not importable; Unsloth will use SDPA/eager "
                     "attention (slower but functional)")
    try:
        import flash_attn  # noqa: F401
        notes.append("flash_attn imports (FlashAttention available)")
    except Exception:  # noqa: BLE001
        notes.append("flash_attn not importable; Unsloth falls back to "
                     "xformers/SDPA (see above)")

    ok = not problems
    if verbose:
        print("check_env: " + ("OK -- GPU stack looks good."
                               if ok else "PROBLEMS FOUND:"))
        for p in problems:
            print(f"  - {p}")
        for n in notes:
            print(f"  (note) {n}")
        if not ok:
            print("\nFix with: pip install -r requirements-gpu.txt "
                  "(after installing torch+CUDA 12.8 from pytorch.org), "
                  "then re-run python check_env.py")
    return ok, problems


def require():
    """Fail fast with a clear message if the environment is broken.

    Import-safe: called by train_sft.py / train_grpo.py / eval.py before
    any heavy imports, so users see *this* instead of transformers'
    internal version-check ImportError."""
    ok, problems = check(verbose=True)
    if not ok:
        raise SystemExit(
            "check_env: refusing to run with a broken ML stack "
            "(see above). Fix the installs, then retry.")


def _self_test():
    """Stdlib-only sanity checks for the version helpers (runs anywhere)."""
    assert _parse("2026.10.3") == (2026, 10, 3)
    assert _parse("0.22.0") < _parse("0.23.1")
    assert _in_range("0.22.1", "0.22.0", "0.23.1")
    assert not _in_range("0.21.4", "0.22.0", "0.23.1")
    assert not _in_range("0.23.1", "0.22.0", "0.23.1")
    assert _in_range("4.57.2", "4.55", None)
    # exclusions
    assert _version_excluded("0.11.0", ["0.11.0"])
    assert _version_excluded("4.0.2", ["4.0.*", "4.1.0"])
    assert not _version_excluded("4.2.0", ["4.0.*", "4.1.0", "4.4.*"])
    assert not _in_range("0.11.0", "0.18.0", None, ["0.11.0"])
    # requirement parsing: table values embed the package name
    assert _parse_requirement("pytest>=7.2.0,<9.0.0") == (
        "pytest", [(">=", "7.2.0"), ("<", "9.0.0")])
    assert _parse_requirement("tokenizers>=0.23.1,<0.24.0") == (
        "tokenizers", [(">=", "0.23.1"), ("<", "0.24.0")])
    assert _parse_requirement("av") == ("av", [])
    assert not _requirement_ok("9.1.1", "pytest>=7.2.0,<9.0.0")
    assert _requirement_ok("8.3.4", "pytest>=7.2.0,<9.0.0")
    assert _requirement_ok("0.23.1", "tokenizers>=0.23.1,<0.24.0")
    assert not _requirement_ok("0.24.0", "tokenizers>=0.23.1,<0.24.0")
    assert not _requirement_ok("0.22.0", "tokenizers>=0.23.1,<0.24.0")
    assert _requirement_ok("0.1.91", "sentencepiece>=0.1.91,!=0.1.92")
    assert not _requirement_ok("0.1.92", "sentencepiece>=0.1.91,!=0.1.92")
    print("check_env.py self-test OK")


if __name__ == "__main__":
    _self_test()
    ok, _ = check(verbose=True)
    sys.exit(0 if ok else 1)
