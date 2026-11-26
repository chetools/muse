#!/usr/bin/env python3
"""Glue for integration/e2e.mjs: run the REAL v22 audit check_package
on one extracted package, with its default transport (real HTTP) pointed
at the REAL worker's /verify-grade through the e2e bridge.

Usage: audit_check.py <audit.py path> <audio path> <html path> <worker base url>
Prints one JSON object of check outcomes on stdout.
"""
import importlib.util
import json
import sys


def main():
    audit_path, audio_path, html_path, base = sys.argv[1:5]
    spec = importlib.util.spec_from_file_location("audit_v22", audit_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg = {"worker_base_url": base}
    res = mod.check_package(audio_path, html_path, cfg)
    keys = [
        "format_ok",
        "audio_fingerprint_ok",
        "transcript_checksum_ok",
        "critique_ok",
        "grade_receipt_ok",
        "grades_match",
        "youtube_id_ok",
        "internally_consistent",
    ]
    print(json.dumps({k: res.get(k) for k in keys}))


if __name__ == "__main__":
    main()
