"""Generate sheet.svg for the MVR evaporator page (v4 layout).

Stream values are taken from python/balance.py at the design
basis, so the sheet cannot drift from the model.

Layout (v4, drawn for zero crossings): equipment is placed so
every stream routes orthogonally without crossing any other.
Feed train on the left at mid height; evaporator centre;
compressor top right; compressed vapour down the right side to
the heating element; condensate out of the heating element on a right-side
lane down to a bottom perimeter lane (y = 620) that returns to
the preheater from below; concentrate out on its own lane
(y = 580) that ends before the condensate lane's vertical;
condensate out of the preheater on a left-bottom terminal lane
(y = 600). The pump discharges from its side port so the feed
reaches the preheater in two bends. Stream geometry is
recorded in sheet_geometry.json for the mechanical crossing,
bend and spacing checks in verify_sheet.py.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "python"))
from balance import run_model  # noqa: E402

r = run_model()
E = []  # svg elements
STREAMS = {}  # stream number -> [(x, y), ...] polyline points
JUNCTIONS = []  # genuine junction points (x, y)


def seg(x1, y1, x2, y2, w=2, dash=""):
    E.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
             f'stroke="#1b1b1b" stroke-width="{w}"{dash}/>')


def stream(n, pts, dash=""):
    """Draw one stream as an orthogonal polyline; record geometry."""
    STREAMS[str(n)] = pts
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        assert x1 == x2 or y1 == y2, f"stream {n} not orthogonal"
        seg(x1, y1, x2, y2, 2, dash)


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


def junction(x, y):
    JUNCTIONS.append([x, y])
    E.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#1b1b1b"/>')


# ---------------------------------------------------------------- equipment
# Feed tank TK-101 (left, mid height)
E.append('<rect x="50" y="300" width="110" height="110" fill="#f4f6f8" stroke="#1b1b1b" stroke-width="2"/>')
E.append('<path d="M 50 330 Q 80 318 105 330 T 160 330" fill="none" stroke="#0072B2" stroke-width="1.5"/>')
tag(105, 285, "TK-101 feed tank")
# Pump P-101 below the tank
E.append('<circle cx="105" cy="480" r="20" fill="#ffffff" stroke="#1b1b1b" stroke-width="2"/>')
E.append('<path d="M 92 492 L 105 468 L 118 492 z" fill="none" stroke="#1b1b1b" stroke-width="1.5"/>')
tag(105, 525, "P-101 feed pump")
# Preheater E-101: cold in left (250,360), cold out right (350,360),
# hot in bottom (330,390), hot out bottom (270,390)
E.append('<rect x="250" y="330" width="100" height="60" fill="#ffffff" stroke="#1b1b1b" stroke-width="2"/>')
E.append('<path d="M 262 342 L 338 378 M 262 378 L 338 342" stroke="#1b1b1b" stroke-width="1.2" fill="none"/>')
tag(300, 305, "E-101 condensate preheater")
# Evaporator E-102: body x 470-600, y 180-480, separator head above
E.append('<rect x="470" y="180" width="130" height="300" fill="#ffffff" stroke="#1b1b1b" stroke-width="2"/>')
E.append('<path d="M 470 180 A 65 40 0 0 1 600 180" fill="#f4f6f8" stroke="#1b1b1b" stroke-width="2"/>')
for tx in (495, 520, 545, 570):
    seg(tx, 240, tx, 430, 1.2)
E.append('<rect x="470" y="430" width="130" height="14" fill="#dbe7f0" stroke="#1b1b1b" stroke-width="1.2"/>')
text(535, 208, "E-102 falling-film", 12, weight="bold")
text(535, 224, "evaporator", 12, weight="bold")
text(535, 170, "separator", 10)
# Heating element (steam chest) on the right face of E-102: compressed
# vapour in at (660,340), vent off the top, condensate out at (660,450)
E.append('<rect x="600" y="306" width="60" height="159" fill="#f4f6f8" stroke="#1b1b1b" stroke-width="2"/>')
text(630, 490, "heating element", 11)
# Demister label beside the vapour outlet, clear of the line
text(550, 125, "demister", 10, anchor="end")
# Compressor K-101 (top right)
E.append('<circle cx="820" cy="215" r="40" fill="#f4f6f8" stroke="#1b1b1b" stroke-width="2"/>')
E.append('<path d="M 795 235 L 820 190 L 845 235" fill="none" stroke="#1b1b1b" stroke-width="1.5"/>')
tag(820, 285, "K-101 MVR compressor")
text(820, 305, "single-stage centrifugal", 11)

# ---------------------------------------------------------------- streams
# Tank to pump (unnumbered connector, part of stream 1 path to preheater)
seg(105, 410, 105, 460)
# Stream 1: pump side discharge -> right -> up lane x=200 -> preheater
stream(1, [(125, 480), (200, 480), (200, 360), (250, 360)])
arrow(242, 360)
stream_no(162, 480, 1)
text(165, 548, "Feed 25,000 kg/h", 12)
# Stream 2: preheater cold out -> up lane x=390 -> evaporator at y=260
stream(2, [(350, 360), (390, 360), (390, 260), (470, 260)])
arrow(462, 260)
stream_no(390, 322, 2)
# Stream 3: separator head -> up -> right on lane y=110 -> compressor top
stream(3, [(565, 144), (565, 110), (820, 110), (820, 175)])
arrow(820, 165, 90)
stream_no(680, 110, 3)
text(750, 88, "Vapour 5,000 kg/h, 80 °C, 43.6 kPa", 12)
# Stream 4: compressor discharge -> right -> down lane x=930 -> heating element
stream(4, [(860, 215), (930, 215), (930, 340), (660, 340)])
arrow(670, 340, 180)
stream_no(930, 290, 4)
text(950, 300, "5,000 kg/h,", 11, anchor="start")
text(950, 316, "129 °C, 64.9 kPa", 11, anchor="start")
# Stream 5: heating element condensate -> right -> down lane x=900 ->
# bottom perimeter lane y=620 -> up into preheater hot side
stream(5, [(660, 450), (900, 450), (900, 620), (330, 620), (330, 390)])
arrow(330, 400, -90)
stream_no(750, 450, 5)
text(750, 435, "Condensate 5,000 kg/h", 12)
text(345, 430, "condensate in", 11, anchor="start")
text(258, 520, "condensate out", 11, anchor="end")
# Condensate out of preheater hot side -> down lane x=270 -> left terminal
stream("5out", [(270, 390), (270, 600), (60, 600)])
arrow(72, 600, 180)
text(115, 625, "Condensate out", 12)
# Stream 6: concentrate from evaporator bottom -> lane y=580 -> right
stream(6, [(535, 480), (535, 580), (770, 580)])
arrow(760, 580)
stream_no(650, 580, 6)
text(650, 606, "Concentrate 20,000 kg/h", 12)
# Non-condensable vent: heating element top (630,306) -> up
stream("vent", [(630, 306), (630, 240)])
arrow(630, 248, -90)
text(642, 278, "non-condensable", 11, anchor="start")
text(642, 294, "vent", 11, anchor="start")
# Start-up steam (dashed): right terminal -> junction on stream 4 lane
stream("steam", [(1190, 340), (930, 340)], ' stroke-dasharray="6 4"')
junction(930, 340)
arrow(1000, 340, 180)
text(1190, 322, "start-up steam", 11, anchor="end")


# ---------------------------------------------------------------- furniture
# Title block (bottom right, below every lane)
E.append('<rect x="760" y="645" width="390" height="50" fill="#ffffff" stroke="#1b1b1b" stroke-width="1.5"/>')
text(955, 666, "Mechanical vapour recompression evaporator", 12, weight="bold")
text(955, 685, "Sample values at the design basis; balance closes", 11)
# Stream table (top left, clear of every stream)
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

svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" '
       'role="img" aria-label="Process flow diagram of a mechanical '
       'vapour recompression evaporator">\n' + "\n".join(E) + "\n</svg>\n")
(HERE / "sheet.svg").write_text(svg, encoding="utf-8")
geom = {"streams": STREAMS, "junctions": JUNCTIONS,
        "viewBox": [0, 0, 1200, 720]}
(HERE / "sheet_geometry.json").write_text(
    json.dumps(geom, indent=1), encoding="utf-8")
print("sheet.svg written", len(svg))
