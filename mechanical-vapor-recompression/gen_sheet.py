"""Generate sheet.svg for the MVR evaporator page.

Stream values are taken from python/balance.py at the design
basis, so the sheet cannot drift from the model. Layout: feed
tank and pump at the left, condensate preheater, falling-film
evaporator with separator in the centre, compressor at the top
right, compressed vapour returning to the calandria.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "python"))
from balance import run_model  # noqa: E402

r = run_model()
E = []  # svg elements


def line(x1, y1, x2, y2, w=2, dash=""):
    E.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
             f'stroke="#1b1b1b" stroke-width="{w}"{dash}/>')


def arrow(x, y, rot=0):
    E.append(f'<path d="M {x} {y} l -9 -4.5 v 9 z" fill="#1b1b1b" '
             f'transform="rotate({rot} {x} {y})"/>')


def text(x, y, s, size=13, anchor="middle", weight="normal"):
    E.append(f'<text x="{x}" y="{y}" font-size="{size}" '
             f'font-family="system-ui,sans-serif" '
             f'font-weight="{weight}" text-anchor="{anchor}">{s}</text>')


def tag(x, y, s):
    text(x, y, s, 12, weight="bold")


def stream_no(x, y, n):
    E.append(f'<circle cx="{x}" cy="{y}" r="10" fill="#ffffff" '
             f'stroke="#0072B2" stroke-width="1.5"/>')
    text(x, y + 4, str(n), 11)


# Feed tank TK-101
E.append('<rect x="50" y="300" width="110" height="110" fill="#f4f6f8" stroke="#1b1b1b" stroke-width="2"/>')
E.append('<path d="M 50 330 Q 80 318 105 330 T 160 330" fill="none" stroke="#0072B2" stroke-width="1.5"/>')
tag(105, 445, "TK-101 feed tank")
# Pump P-101
E.append('<circle cx="105" cy="480" r="20" fill="#ffffff" stroke="#1b1b1b" stroke-width="2"/>')
E.append('<path d="M 92 492 L 105 468 L 118 492 z" fill="none" stroke="#1b1b1b" stroke-width="1.5"/>')
tag(105, 525, "P-101 feed pump")
line(105, 410, 105, 460)
line(105, 500, 105, 545)
line(105, 545, 300, 545)
line(300, 545, 300, 405)
arrow(300, 420, -90)
# Preheater E-101 (shell-and-tube symbol)
E.append('<rect x="255" y="315" width="90" height="90" fill="#ffffff" stroke="#1b1b1b" stroke-width="2"/>')
E.append('<path d="M 265 330 L 335 390 M 265 390 L 335 330" stroke="#1b1b1b" stroke-width="1.2" fill="none"/>')
tag(300, 290, "E-101 condensate preheater")
# Feed line tank -> pump handled; preheater -> evaporator top
line(345, 360, 420, 360)
line(420, 360, 420, 260)
line(420, 260, 470, 260)
arrow(462, 260)
stream_no(200, 545, 1)
stream_no(420, 312, 2)
text(200, 570, "Feed 25,000 kg/h", 12)
# Evaporator body: calandria + falling-film tubes + separator head
E.append('<rect x="470" y="180" width="130" height="300" fill="#ffffff" stroke="#1b1b1b" stroke-width="2"/>')
E.append('<path d="M 470 180 A 65 40 0 0 1 600 180" fill="#f4f6f8" stroke="#1b1b1b" stroke-width="2"/>')
for tx in (495, 520, 545, 570):
    line(tx, 240, tx, 430, 1.2)
E.append('<rect x="470" y="430" width="130" height="14" fill="#dbe7f0" stroke="#1b1b1b" stroke-width="1.2"/>')
text(535, 208, "E-102 falling-film", 12, weight="bold")
text(535, 224, "evaporator", 12, weight="bold")
text(612, 505, "calandria (heating chest) at the side;", 11, anchor="start")
text(612, 522, "separator in the head", 11, anchor="start")
# Concentrate out, bottom
line(535, 480, 535, 560)
line(535, 560, 700, 560)
arrow(690, 560)
stream_no(620, 560, 6)
text(770, 545, "Concentrate", 12)
text(770, 564, "20,000 kg/h", 12)
# Vapour out of separator head to compressor
line(565, 155, 565, 110)
line(565, 110, 800, 110)
line(800, 110, 800, 175)
arrow(800, 165)
stream_no(680, 110, 3)
text(680, 92, "Vapour 5,000 kg/h, 80 °C, 43.6 kPa", 12)
# Demister note on vapour outlet
E.append('<rect x="520" y="128" width="90" height="16" fill="#ffffff" stroke="#1b1b1b" stroke-width="1"/>')
text(565, 140, "demister", 10)
# Compressor K-101
E.append('<circle cx="800" cy="215" r="40" fill="#f4f6f8" stroke="#1b1b1b" stroke-width="2"/>')
E.append('<path d="M 775 235 L 800 190 L 825 235" fill="none" stroke="#1b1b1b" stroke-width="1.5"/>')
tag(800, 285, "K-101 MVR compressor")
text(800, 305, "single-stage centrifugal", 11)
# Compressed vapour down to calandria
line(840, 215, 900, 215)
line(900, 215, 900, 360)
line(900, 360, 600, 360)
arrow(610, 360)
stream_no(900, 290, 4)
text(915, 250, "5,000 kg/h,", 11, anchor="start")
text(915, 266, "129 °C, 64.9 kPa", 11, anchor="start")
# Condensate out of calandria to preheater hot side, then out
line(600, 395, 880, 395)
line(880, 395, 880, 470)
line(880, 470, 345, 470)
arrow(360, 470)
line(255, 470, 170, 470)
line(170, 470, 170, 600)
line(170, 600, 60, 600)
arrow(72, 600)
stream_no(700, 395, 5)
text(700, 380, "Condensate 5,000 kg/h", 12)
text(115, 585, "Condensate out", 12)
# Start-up steam (dashed) into calandria line
line(985, 360, 905, 360, 2, ' stroke-dasharray="6 4"')
arrow(912, 360)
text(985, 340, "start-up steam (dashed)", 11, anchor="end")
# Non-condensable vent from calandria top
line(640, 360, 640, 320)
arrow(640, 328, -90)
text(648, 340, "non-condensable vent", 11, anchor="start")
# CIP note
E.append('<rect x="430" y="580" width="360" height="34" fill="#ffffff" stroke="#1b1b1b" stroke-width="1"/>')
text(442, 601, "Clean-in-place (CIP) connections at the evaporator", 11, anchor="start")
text(62, 580 + 34 - 4, "", 11, anchor="start")
# Title block
E.append('<rect x="820" y="580" width="330" height="50" fill="#ffffff" stroke="#1b1b1b" stroke-width="1.5"/>')
text(985, 601, "Mechanical vapour recompression evaporator", 12, weight="bold")
text(985, 620, "Sample values at the design basis; balance closes", 11)
# Stream table
rows = [
    ("1", "Feed to preheater", "25,000", "75", "101"),
    ("2", "Feed to evaporator", "25,000", "80", "101"),
    ("3", "Vapour to compressor", "5,000", "80", "43.6"),
    ("4", "Compressed vapour", "5,000", "129", "64.9"),
    ("5", "Condensate out", "5,000", "63", "64.9"),
    ("6", "Concentrate out", "20,000", "80", "43.6"),
]
tx, ty = 60, 84
E.append(f'<rect x="{tx-10}" y="{ty-22}" width="360" height="{26*len(rows)+30}" fill="#ffffff" stroke="#1b1b1b" stroke-width="1"/>')
text(tx, ty, "Stream", 11, anchor="start", weight="bold")
text(tx + 60, ty, "Service", 11, anchor="start", weight="bold")
text(tx + 205, ty, "kg/h", 11, weight="bold")
text(tx + 265, ty, "°C", 11, weight="bold")
text(tx + 320, ty, "kPa", 11, weight="bold")
for i, (n, svc, flow, t, p) in enumerate(rows):
    y = ty + 22 + 26 * i
    text(tx, y, n, 11, anchor="start")
    text(tx + 60, y, svc, 11, anchor="start")
    text(tx + 205, y, flow, 11)
    text(tx + 265, y, t, 11)
    text(tx + 320, y, p, 11)

svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 660" '
       'role="img" aria-label="Process flow diagram of a mechanical '
       'vapour recompression evaporator">\n' + "\n".join(E) + "\n</svg>\n")
(HERE / "sheet.svg").write_text(svg, encoding="utf-8")
print("sheet.svg written", len(svg))
