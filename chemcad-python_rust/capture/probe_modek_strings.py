"""Scan ChemCAD program DLLs for the K-value model name table.

Prints, per file, the byte offsets of candidate model-name strings
so the ordering of the table can be compared against the known
modek anchors (Grayson-Streed=2, Peng-Robinson=9, NRTL=10,
Amine=12). Pure file scan; no COM, no ChemCAD run.
"""
import os
import sys

ROOT = r"C:\Program Files (x86)\Chemstations\CHEMCAD NXT"
NAMES = [b"Chao", b"Grayson", b"ESSO", b"BWRS", b"SAFT", b"ESD",
         b"Peng", b"NRTL", b"UNIQUAC", b"UNIFAC", b"Wilson",
         b"Amine", b"PPAQ", b"Flory", b"VTPR", b"SRK", b"Ideal",
         b"Margules", b"van Laar", b"Henry", b"Sour", b"TEG",
         b"Hiranuma", b"Regular", b"Predictive", b"Modified"]


def scan(path):
    try:
        data = open(path, "rb").read()
    except OSError:
        return
    hits = {}
    for n in NAMES:
        # ASCII and UTF-16LE forms
        for enc, key in ((n, n.decode()), (n.decode().encode("utf-16-le"),
                                          n.decode() + "/u16")):
            i = data.find(enc)
            if i >= 0:
                hits.setdefault(key, []).append(i)
    if len(hits) >= 6:
        print("FILE", path, flush=True)
        for k in sorted(hits, key=lambda k: min(hits[k])):
            print("  ", k, hits[k][:4], flush=True)


def main():
    for dirpath, _dirs, files in os.walk(ROOT):
        for f in files:
            if f.lower().endswith((".dll", ".exe")):
                scan(os.path.join(dirpath, f))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
