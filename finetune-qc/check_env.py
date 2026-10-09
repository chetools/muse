#!/usr/bin/env python3
"""Preflight environment check for the QC fine-tuning GPU pipeline.

Run it before (or instead of debugging) the training scripts:
    python check_env.py

`train_sft.py`, `train_grpo.py`, and `eval.py` all call `require()` on
import, so a broken environment fails here with an actionable message
instead of a cryptic ImportError from inside `transformers` (e.g. the
`tokenizers>=0.22.0,<=0.23.0 is required` version-pin error).

Checks:
  * torch imports and a CUDA GPU is visible;
  * every GPU-stack package imports AND satisfies its pinned version range;
  * the version pins that `transformers` itself enforces (its
    dependency_versions_table, e.g. the tokenizers range) are satisfied by
    what is actually installed.

Exit status 0 = good to go; 1 = prints exactly what to install/fix.
Stdlib only, so this module imports even when the ML stack is broken.
"""
import importlib
import importlib.metadata as _md
import re
import sys

# Pinned, mutually compatible versions (kept in sync with
# requirements-gpu.txt). (low_inclusive, high_exclusive); None = unbounded.
# Verified 2026-10-09 against unsloth 2026.10.3's dependency metadata,
# transformers 5.17.0's dependency_versions_table, and the trl 1.13.0
# trainer sources.
PINS = {
    # pip name:        (low, high, import name, why it matters)
    "torch":        ("2.7", "2.15.0", "torch",
                     "CUDA 12.8 Blackwell (sm_120); unsloth caps torch<2.15"),
    "unsloth":      ("2026.10.3", None, "unsloth",
                     "single-GPU SFT/GRPO kernels (its metadata pins the rest)"),
    "trl":          ("1.13.0", "1.14.0", "trl",
                     "unsloth caps trl<=1.13.0; SFTConfig/processing_class API"),
    "transformers": ("5.17.0", "5.18.0", "transformers",
                     "unsloth caps transformers<=5.17.0; dtype= spelling"),
    "peft":         ("0.18.0", None,   "peft",
                     "LoRA adapters (unsloth needs >=0.18.0)"),
    "accelerate":   ("1.10",  None,   "accelerate",   "device_map='auto'"),
    "datasets":     ("3.6",   "5.0.0", "datasets",
                     "JSONL dataset builders (unsloth caps <5.0.0)"),
    "tokenizers":   ("0.23.1", "0.24.0", "tokenizers",
                     "must satisfy transformers 5.17.0's own pin (import-time check)"),
}


def _parse(v):
    """'2026.10.3' -> (2026, 10, 3); non-numeric suffixes ignored."""
    parts = []
    for p in re.split(r"[.\-+_]", str(v)):
        m = re.match(r"(\d+)", p)
        parts.append(int(m.group(1)) if m else 0)
    return tuple(parts)


def _in_range(ver, low, high):
    v = _parse(ver)
    if low is not None and v < _parse(low):
        return False
    if high is not None and v >= _parse(high):
        return False
    return True


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


def check(verbose=True):
    """-> (ok: bool, problems: [str]). Never raises on a broken ML stack."""
    problems = []

    # 1. torch + CUDA -----------------------------------------------------
    torch_ver, err = _installed_version("torch")
    if err:
        problems.append(f"torch: {err} -- install torch with CUDA 12.8 "
                        "first, from pytorch.org")
    else:
        if not _in_range(torch_ver, *PINS["torch"][:2]):
            problems.append(
                f"torch {torch_ver} is older than {PINS['torch'][0]} -- "
                "upgrade for Blackwell (sm_120) kernels")
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
    for pip_name, (low, high, import_name, why) in PINS.items():
        if pip_name == "torch":
            continue
        ver, err = _installed_version(import_name)
        if err:
            problems.append(f"{pip_name}: {err} -- pip install "
                            f"'{pip_name}>={low}' ({why})")
        elif ver != "unknown" and not _in_range(ver, low, high):
            hi = f",<{high}" if high else ""
            problems.append(
                f"{pip_name} {ver} is outside the pinned range "
                f">={low}{hi} -- run: pip install '{pip_name}>={low}{hi}' "
                f"({why})")

    # 3. transformers' own dependency table --------------------------------
    # transformers hard-fails at import time when e.g. tokenizers is out of
    # range; surface that here with the exact spec it enforces.
    try:
        from transformers.dependency_versions_table import deps as _deps
        for dep_pkg, spec in _deps.items():
            dep_ver, err = _installed_version(dep_pkg)
            if err or dep_ver in (None, "unknown"):
                continue
            ok = True
            for clause in spec.split(","):
                clause = clause.strip()
                m = re.match(r"(>=|<=|==|!=|>|<)\s*(.+)", clause)
                if not m:
                    continue
                op, want = m.groups()
                cmp = (_parse(dep_ver) > _parse(want)) - (
                    _parse(dep_ver) < _parse(want))
                ok = ok and {"==": cmp == 0, "!=": cmp != 0,
                             ">=": cmp >= 0, "<=": cmp <= 0,
                             ">": cmp > 0, "<": cmp < 0}[op]
            if not ok:
                problems.append(
                    f"transformers requires {dep_pkg}{spec} but {dep_ver} "
                    f"is installed -- run: pip install '{dep_pkg}{spec}' "
                    "(this is the classic cryptic-ImportError cause)")
    except Exception as e:  # noqa: BLE001
        problems.append(f"could not read transformers' dependency table: {e}")

    ok = not problems
    if verbose:
        print("check_env: " + ("OK -- GPU stack looks good."
                               if ok else "PROBLEMS FOUND:"))
        for p in problems:
            print(f"  - {p}")
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
    print("check_env.py self-test OK")


if __name__ == "__main__":
    _self_test()
    ok, _ = check(verbose=True)
    sys.exit(0 if ok else 1)
