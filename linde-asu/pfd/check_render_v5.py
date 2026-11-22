#!/usr/bin/env python3
"""Rendered-pixel continuity check for the PFD-102 sheet (PFD skill
Section 9.10). Run after render_v5.py with a Python that has PIL and
numpy (the system python3 in the sandbox). Fails (nonzero exit) while
any checked connection shows a white gap over 3 sheet units between
the glyph outline and its line on the rendered sheet."""
import sys
sys.path.insert(0, "/home/hatch/workspace/custom-skills/local-process-flow-diagram-drawing/checks")
from render_gap_check import run_render_check
from PIL import Image

CHECKS = [
    ("T-102 overhead (stream 21)", (1085, 160), (0, -1)),
    ("T-102 bottoms bridge", (1085, 373.75), (0, 1)),
    ("E-103 top bridge", (1085, 392), (0, -1)),
    ("T-102 left stream 20", (1062.5, 190), (-1, 0)),
    ("T-102 left stream 18", (1062.5, 300), (-1, 0)),
    ("T-102 left stream 9", (1062.5, 350), (-1, 0)),
    ("T-102 right stream 15", (1107.5, 235), (1, 0)),
    ("T-102 right stream 29", (1107.5, 285), (1, 0)),
    ("T-102 right stream 30", (1107.5, 340), (1, 0)),
    ("E-103 bottom stream 10", (1085, 448), (0, 1)),
    ("E-103 bottom stream 12", (1100, 448), (0, 1)),
    ("T-101 overhead stream 10", (1085, 495), (0, -1)),
    ("T-101 overhead stream 12", (1100, 497.9), (0, -1)),
    ("T-101 bottoms stream 16", (1085, 708.75), (0, 1)),
    ("T-101 left stream 7", (1062.5, 640), (-1, 0)),
    ("T-103 overhead stream 25", (1380, 222), (0, -1)),
    ("E-105 bottom stream 25", (1380, 167), (0, 1)),
    ("T-103 right stream 27", (1405.5, 250), (1, 0)),
    ("T-103 left stream 29", (1354.5, 300), (-1, 0)),
    ("T-103 left stream 30", (1354.5, 440), (-1, 0)),
]
checks = [{"label": label, "at": at, "outward": out} for label, at, out in CHECKS]
defects = run_render_check(Image.open("linde-asu-pfd-v5.png"), checks)
for label, gap in defects:
    print("RENDER GAP DEFECT", label, "gap", gap, "units")
assert not defects, f"render gap check: {len(defects)} defect(s) - build fails (skill Section 9.10)"
print(f"render gap check OK: 0 defects over {len(checks)} connections (skill Section 9.10)")
