#!/usr/bin/env python3
"""PFD-102: Linde nitrogen-oxygen air separation unit with crude argon
recovery. Layout per PFD-SPEC-001: traced ChemCAD symbol library v1
where a library glyph exists; multi-stream exchangers, condenser/
reboiler and air filter drawn per ISO 10628-2 under requirement S5.
Stream data are illustrative sample values on a 1000 kmol/h air basis;
every unit balance closes on displayed values within displayed
rounding (verified in check section). Units are stated in every table
heading, so no symbol is used before it is defined in words.
"""
import html, sys
sys.path.insert(0, "/home/hatch/workspace/chemcad-symbol-library/library")
import chemcad_symbols as CS

W, H = 1680, 1190
INK = "#111111"
MAIN_W = 3.4
SUB_W = 1.3
EQ_W = 2.2
FONT = "Arial, Helvetica, sans-serif"
el = []
def add(s): el.append(s)
def line(x1, y1, x2, y2, w=MAIN_W):
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{INK}" stroke-width="{w}"/>')
def path(pts, w=MAIN_W, dash=None):
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{w}"{da}/>')
def arrow(x, y, direction):
    s = 11
    if direction == "R": pts = f"{x},{y - s * 0.62} {x + s * 1.5},{y} {x},{y + s * 0.62}"
    elif direction == "L": pts = f"{x},{y - s * 0.62} {x - s * 1.5},{y} {x},{y + s * 0.62}"
    elif direction == "D": pts = f"{x - s * 0.62},{y} {x},{y + s * 1.5} {x + s * 0.62},{y}"
    else: pts = f"{x - s * 0.62},{y} {x},{y - s * 1.5} {x + s * 0.62},{y}"
    add(f'<polygon points="{pts}" fill="{INK}"/>')
def text(x, y, s, size=14, bold=False, anchor="middle"):
    b = ' font-weight="bold"' if bold else ""
    add(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}"{b} text-anchor="{anchor}" fill="{INK}">{html.escape(s)}</text>')
def stream_no(x, y, n):
    add(f'<polygon points="{x - 19},{y} {x},{y - 14} {x + 19},{y} {x},{y + 14}" fill="white" stroke="{INK}" stroke-width="1.8"/>')
    text(x, y + 5, str(n), size=14, bold=True)
def stream_no_side(x, y, tx_, ty_, n):
    """Diamond beside a short segment, with a 0.25 mm leader (L4)."""
    line(x, y, tx_, ty_, w=1.0)
    stream_no(tx_, ty_, n)
def dot(x, y):
    add(f'<circle cx="{x}" cy="{y}" r="5" fill="{INK}"/>')

# ---------- library symbol placement (as sample PFD-101 rev.1) ----------
def inner_svg(key):
    s = CS.get_svg(key)
    return s[s.index(">") + 1: s.rindex("</svg>")].strip()
def place(key, tx, ty, s, flip=False):
    f = CS.get_frame(key)
    if flip:
        transform = f'translate({tx} {ty}) scale({-s} {s}) translate({-f[2]} {-f[1]})'
    else:
        transform = f'translate({tx} {ty}) scale({s} {s}) translate({-f[0]} {-f[1]})'
    add(f'<g transform="{transform}">{inner_svg(key)}</g>')
def place_valve_rot(cx, cy, s=1.0):
    """Valve_1 rotated 90 degrees clockwise; ports at (cx, cy-20s) and (cx, cy+20s)."""
    add(f'<g transform="translate({cx} {cy}) rotate(90) scale({s}) translate(-565 -565)">{inner_svg("valve_1")}</g>')
def port_sheet(key, tx, ty, s, flip=False):
    f = CS.get_frame(key)
    def m(px, py):
        if flip: return (tx + (f[2] - px) * s, ty + (py - f[1]) * s)
        return (tx + (px - f[0]) * s, ty + (py - f[1]) * s)
    return {name: m(px, py) for name, (px, py) in CS.get_ports(key).items()}

S_TERM = 0.65; S_COMP = 0.28; S_HX = 44 / 112; S_VES = 140 / 180
FEED = port_sheet("feed_1", 56, 337, S_TERM)
COMP = port_sheet("compressor_1", 275, 317.8, S_COMP)
E101 = port_sheet("heat_exchanger_1", 408.4, 326.4, S_HX)
VES = port_sheet("vessel_1", 500, 326.7, S_VES)
EXP = port_sheet("expander_1", 928, 317.8, S_COMP)
E104 = port_sheet("heat_exchanger_1", 1228, 126.4, S_HX)
E106 = port_sheet("heat_exchanger_1", 938.4, 726.4, S_HX)
E105 = port_sheet("heat_exchanger_1", 1358, 121.4, S_HX)
GAN_T = port_sheet("product_1", 30, 107, S_TERM, flip=True)
WAS_T = port_sheet("product_1", 30, 177, S_TERM, flip=True)
GOX_T = port_sheet("product_1", 30, 407, S_TERM, flip=True)
ARG_T = port_sheet("product_1", 1560, 187, S_TERM)
assert abs(FEED["outlet"][1] - 350) < 1 and abs(COMP["suction"][1] - 350) < 1
assert abs(E101["left"][1] - 350) < 1 and abs(VES["inlet"][1] - 350) < 1
assert abs(EXP["inlet"][1] - 350) < 1 and abs(E104["left"][1] - 150) < 1
assert abs(E106["left"][1] - 750) < 1 and abs(E105["bottom"][0] - 1380) < 1

# geometry constants
LP = dict(left=1062.5, right=1107.5, top=145, bottom=385, cx=1085)
HP = dict(left=1062.5, right=1107.5, top=480, bottom=720, cx=1085)
AR = dict(left=1354.5, right=1405.5, top=205, bottom=477, cx=1380)
MHE = dict(left=700, right=810, top=100, bottom=450)
E103B = dict(left=1040, right=1130, top=392, bottom=448)

# ---------- sheet frame and headings ----------
add(f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>')
add(f'<rect x="18" y="18" width="{W - 36}" height="{H - 36}" fill="none" stroke="{INK}" stroke-width="2.4"/>')
text(60, 78, "PROCESS FLOW DIAGRAM", size=27, bold=True, anchor="start")
text(60, 108, "Linde nitrogen–oxygen air separation unit with crude argon recovery  |  Sample values", size=14, anchor="start")

# cold box boundary (dashed, auxiliary weight)
add(f'<rect x="690" y="85" width="955" height="705" fill="none" stroke="{INK}" stroke-width="1.3" stroke-dasharray="10 7"/>')
text(1632, 108, "Cold box", size=13, bold=True, anchor="end")

# ---------- streams ----------
STREAMS = {}
ALL_SEG_LISTS = []
def stream(n, pts):
    STREAMS.setdefault(n, []).append(pts)
    ALL_SEG_LISTS.append((n, pts))
    path(pts)

stream(1, [FEED["outlet"], (150, 350)])
stream(2, [(215, 350), COMP["suction"]])
stream(3, [COMP["discharge"], E101["left"]])
stream(4, [E101["right"], VES["inlet"]])
stream(5, [VES["outlet"], (MHE["left"], 350)])
stream(6, [(MHE["right"], 350), (895, 350)])
stream(7, [(895, 350), (895, 640), (HP["left"], 640)])
stream(8, [(895, 350), EXP["inlet"]])
stream(9, [EXP["outlet"], (LP["left"], 350)])
stream(10, [(HP["cx"], HP["top"]), (HP["cx"], E103B["bottom"])])
stream(11, [(E103B["right"], 420), (1165, 420), (1165, 150), E104["left"]])
stream(12, [(1100, E103B["bottom"]), (1100, HP["top"])])
stream(13, [E104["right"], (1350, 150)])
stream(14, [(1350, 150), (1350, 165)])
stream(15, [(1350, 195), (LP["right"], 195)])
stream(16, [(HP["cx"], HP["bottom"]), (HP["cx"], 750), E106["right"]])
stream(17, [E106["left"], (845, 750), (845, 500)])
stream(18, [(845, 470), (845, 300), (LP["left"], 300)])
stream(19, [(E103B["left"], 420), (MHE["right"], 420)])
stream(20, [(LP["left"], 190), (MHE["right"], 190)])
stream(21, [(LP["cx"], LP["top"]), (LP["cx"], 120), (MHE["right"], 120)])
stream(22, [(MHE["left"], 420), GOX_T["inlet_edge"]])
stream(23, [(MHE["left"], 190), WAS_T["inlet_edge"]])
stream(24, [(MHE["left"], 120), GAN_T["inlet_edge"]])
stream(25, [(AR["cx"], AR["top"]), E105["bottom"]])
stream(26, [E105["right"], (1560, 145), (1560, 200)])
stream(27, [(1560, 200), (1430, 200), (1430, 215), (AR["right"], 215)])
stream(28, [(1560, 200), ARG_T["inlet_edge"]])
stream(29, [(LP["right"], 285), (1300, 285), (1300, 440), (AR["left"], 440)])
stream(30, [(AR["left"], 470), (1210, 470), (1210, 380), (LP["right"], 380)])
dot(895, 350); dot(1560, 200)

# utility stubs (subsidiary weight, not numbered streams)
line(430, 374, 430, 408, w=SUB_W); arrow(430, 394, "U")
text(442, 404, "Cooling water", size=11.5, anchor="start")
line(1250, 126, 1250, 102, w=SUB_W); arrow(1250, 112, "D")
line(960, 774, 960, 786, w=SUB_W); arrow(960, 782, "U")
text(972, 784, "Waste nitrogen in", size=11.5, anchor="start")
line(1330, 145, E105["left"][0], 145, w=SUB_W); arrow(1344, 145, "R")

# flow arrows at inlets and on long runs
for x, y, d in [(125, 350, "R"), (245, 350, "R"), (368, 350, "R"), (476, 350, "R"),
                (670, 350, "R"), (852, 350, "R"), (1022, 350, "R"),
                (980, 640, "R"), (1085, 462, "U"), (1100, 466, "D"),
                (1165, 300, "U"), (1200, 150, "R"), (1310, 150, "R"),
                (1250, 195, "L"), (1033, 750, "L"), (891, 750, "L"),
                (845, 620, "U"), (950, 300, "R"), (925, 420, "L"),
                (936, 190, "L"), (947, 120, "L"), (400, 420, "L"),
                (400, 190, "L"), (400, 120, "L"), (1380, 186, "U"),
                (1480, 145, "R"), (1495, 200, "L"), (1200, 285, "R"),
                (1300, 360, "D"), (1280, 470, "L"), (1210, 425, "U")]:
    arrow(x, y, d)

# ---------- custom symbols (ISO 10628-2 forms, requirement S5) ----------
# F-101 air filter: rectangle with internal mesh lines
add(f'<rect x="150" y="323" width="65" height="54" fill="white" stroke="{INK}" stroke-width="{EQ_W}"/>')
for gx in (163, 176, 189, 202):
    line(gx, 323, gx, 377, w=1.0)
# E-102 main heat exchanger: multi-stream plate-fin box
add(f'<rect x="{MHE["left"]}" y="{MHE["top"]}" width="110" height="350" fill="white" stroke="{INK}" stroke-width="{EQ_W}"/>')
path([(716, 425), (736, 125), (756, 425), (776, 125), (794, 425)], w=1.0)
# E-103 main condenser/reboiler: integrated box between the columns
add(f'<rect x="{E103B["left"]}" y="{E103B["top"]}" width="90" height="56" fill="white" stroke="{INK}" stroke-width="{EQ_W}"/>')
line(1052, 436, 1118, 404, w=1.0); line(1052, 404, 1118, 436, w=1.0)

# ---------- library symbols ----------
place("feed_1", 56, 337, S_TERM)
place("compressor_1", 275, 317.8, S_COMP)
place("heat_exchanger_1", 408.4, 326.4, S_HX)
place("vessel_1", 500, 326.7, S_VES)
place("expander_1", 928, 317.8, S_COMP)
place("scds_1", 1062.5, 145, 0.75)
place("scds_1", 1062.5, 480, 0.75)
place("scds_1", 1354.5, 205, 0.85)
place("heat_exchanger_1", 1228, 126.4, S_HX)
place("heat_exchanger_1", 938.4, 726.4, S_HX)
place("heat_exchanger_1", 1358, 121.4, S_HX)
place_valve_rot(845, 485)
place_valve_rot(1350, 180)
place("product_1", 30, 107, S_TERM, flip=True)
place("product_1", 30, 177, S_TERM, flip=True)
place("product_1", 30, 407, S_TERM, flip=True)
place("product_1", 1560, 187, S_TERM)

# stream number diamonds (L4: on a horizontal segment; side placement for short segments)
for x, y, n in [(125, 350, 1), (245, 350, 2), (368, 350, 3), (476, 350, 4),
                (670, 350, 5), (852, 350, 6), (980, 640, 7), (1022, 350, 9),
                (1196, 150, 11), (1311, 150, 13), (1250, 195, 15),
                (1033, 750, 16), (891, 750, 17), (950, 300, 18),
                (925, 420, 19), (936, 190, 20), (947, 120, 21),
                (400, 420, 22), (400, 190, 23), (400, 120, 24),
                (1480, 145, 26), (1495, 200, 27), (1589, 200, 28),
                (1200, 285, 29), (1280, 470, 30)]:
    stream_no(x, y, n)
stream_no_side(908, 350, 905, 315, 8)
stream_no_side(1085, 464, 1005, 470, 10)
stream_no_side(1100, 464, 1167, 464, 12)
path([(1350, 150), (1350, 120), (1331, 120)], w=1.0); stream_no(1312, 120, 14)
stream_no_side(1380, 178, 1436, 178, 25)

# ---------- equipment tags and product names ----------
text(60, 330, "Fresh air", size=13.5, bold=True, anchor="start")
text(182, 300, "F-101", size=16, bold=True); text(182, 318, "Air filter", size=12.5)
text(302, 282, "C-101", size=16, bold=True); text(302, 300, "Main air compressor", size=12.5)
text(430, 285, "E-101", size=16, bold=True); text(430, 303, "Aftercooler", size=12.5)
text(500, 285, "V-101", size=16, bold=True, anchor="start"); text(500, 303, "Molecular sieve adsorber (twin)", size=12.5, anchor="start")
text(822, 140, "E-102", size=16, bold=True, anchor="start"); text(822, 158, "Main heat exchanger", size=12.5, anchor="start")
text(955, 402, "X-101", size=16, bold=True)
text(1050, 260, "T-102", size=16, bold=True, anchor="end"); text(1050, 278, "Low-pressure column", size=12.5, anchor="end")
text(1050, 600, "T-101", size=16, bold=True, anchor="end"); text(1050, 618, "Pressure column", size=12.5, anchor="end")
text(1030, 435, "E-103", size=16, bold=True, anchor="end"); text(1030, 453, "Condenser / reboiler", size=12.5, anchor="end")
text(1250, 215, "E-104", size=15, bold=True)
text(1445, 100, "E-105", size=16, bold=True, anchor="start")
text(1445, 300, "T-103", size=16, bold=True, anchor="start"); text(1445, 318, "Crude argon column", size=12.5, anchor="start")
text(960, 697, "E-106", size=16, bold=True); text(960, 715, "Rich liquid subcooler", size=12.5)
text(838, 492, "VLV-101", size=13, bold=True, anchor="end")
text(1335, 230, "VLV-102", size=13, bold=True, anchor="end")
text(180, 144, "Gaseous nitrogen", size=13.5, bold=True, anchor="start")
text(180, 214, "Waste nitrogen", size=13.5, bold=True, anchor="start")
text(180, 444, "Gaseous oxygen", size=13.5, bold=True, anchor="start")
text(1595, 130, "Crude argon", size=13.5, bold=True)

# ---------- equipment summary (empty south-west area) ----------
text(60, 478, "Equipment summary", size=14.5, bold=True, anchor="start")
equip_l = [("F-101", "Air filter"), ("C-101", "Main air compressor"), ("E-101", "Aftercooler"),
           ("V-101", "Molecular sieve adsorber (twin)"), ("E-102", "Main heat exchanger (multi-stream)"),
           ("X-101", "Expansion turbine"), ("E-103", "Main condenser / reboiler"), ("E-104", "Nitrogen subcooler")]
equip_r = [("E-105", "Crude argon condenser"), ("E-106", "Rich liquid subcooler"),
           ("T-101", "Pressure column"), ("T-102", "Low-pressure column"),
           ("T-103", "Crude argon column"), ("VLV-101", "Rich liquid throttle valve"),
           ("VLV-102", "Nitrogen throttle valve")]
for r, (tag, name) in enumerate(equip_l):
    yy = 502 + r * 24
    text(60, yy, tag, size=12, bold=True, anchor="start"); text(140, yy, name, size=12, anchor="start")
for r, (tag, name) in enumerate(equip_r):
    yy = 502 + r * 24
    text(380, yy, tag, size=12, bold=True, anchor="start"); text(472, yy, name, size=12, anchor="start")

text(60, 706, "Notes: E-105 is cooled by rich liquid. E-104 and E-106 are cooled by waste nitrogen.", size=11.5, anchor="start")

# ---------- stream table (two blocks of 15) ----------
# (n, flow kmol/h, temp degC, pressure kPa, N2 mol%, O2 mol%, Ar mol%, phase)
streams = [
    (1, "1000", "20", "101", "78.0", "21.0", "1.0", "Vapour"),
    (2, "1000", "20", "100", "78.0", "21.0", "1.0", "Vapour"),
    (3, "1000", "175", "625", "78.0", "21.0", "1.0", "Vapour"),
    (4, "1000", "22", "600", "78.0", "21.0", "1.0", "Vapour"),
    (5, "1000", "20", "590", "78.0", "21.0", "1.0", "Vapour"),
    (6, "1000", "−171", "568", "78.0", "21.0", "1.0", "Vapour"),
    (7, "800", "−171", "568", "78.0", "21.0", "1.0", "Vapour"),
    (8, "200", "−171", "568", "78.0", "21.0", "1.0", "Vapour"),
    (9, "200", "−182", "138", "78.0", "21.0", "1.0", "Vapour"),
    (10, "600", "−178", "560", "97.0", "2.0", "1.0", "Vapour"),
    (11, "400", "−178", "555", "97.0", "2.0", "1.0", "Liquid"),
    (12, "200", "−178", "550", "97.0", "2.0", "1.0", "Liquid"),
    (13, "400", "−186", "545", "97.0", "2.0", "1.0", "Liquid"),
    (14, "400", "−186", "540", "97.0", "2.0", "1.0", "Liquid"),
    (15, "400", "−192", "130", "97.0", "2.0", "1.0", "Liquid"),
    (16, "400", "−174", "558", "59.0", "40.0", "1.0", "Liquid"),
    (17, "400", "−181", "552", "59.0", "40.0", "1.0", "Liquid"),
    (18, "400", "−184", "138", "59.0", "40.0", "1.0", "Two-phase"),
    (19, "200", "−179", "130", "1.0", "99.0", "0.0", "Vapour"),
    (20, "290", "−185", "125", "96.6", "3.1", "0.3", "Vapour"),
    (21, "500", "−192", "120", "99.5", "0.5", "0.0", "Vapour"),
    (22, "200", "20", "115", "1.0", "99.0", "0.0", "Vapour"),
    (23, "290", "20", "105", "96.6", "3.1", "0.3", "Vapour"),
    (24, "500", "20", "110", "99.5", "0.5", "0.0", "Vapour"),
    (25, "30", "−184", "124", "5.0", "5.0", "90.0", "Vapour"),
    (26, "30", "−184", "120", "5.0", "5.0", "90.0", "Liquid"),
    (27, "20", "−184", "120", "5.0", "5.0", "90.0", "Liquid"),
    (28, "10", "−184", "120", "5.0", "5.0", "90.0", "Liquid"),
    (29, "100", "−172", "130", "1.0", "90.0", "9.0", "Vapour"),
    (30, "90", "−176", "128", "0.6", "99.4", "0.0", "Liquid"),
]
heads = ["Stream", "Flow rate (kmol/h)", "Temperature (°C)", "Pressure (kPa)",
         "Nitrogen (mol %)", "Oxygen (mol %)", "Argon (mol %)", "Phase"]
colw = [46, 104, 104, 92, 92, 92, 84, 86]
rowh = 18
text(60, 824, "Stream table — flow rates, temperatures, pressures and compositions are sample values", size=14.5, bold=True, anchor="start")
for blk, x0 in enumerate((60, 860)):
    ty = 838
    add(f'<rect x="{x0}" y="{ty}" width="{sum(colw)}" height="{rowh * 16}" fill="none" stroke="{INK}" stroke-width="1.4"/>')
    cx = x0
    for wdt, htxt in zip(colw, heads):
        text(cx + wdt / 2, ty + 13, htxt, size=10, bold=True); cx += wdt
    for i in range(1, 16):
        add(f'<line x1="{x0}" y1="{ty + rowh * i}" x2="{x0 + sum(colw)}" y2="{ty + rowh * i}" stroke="{INK}" stroke-width="0.6"/>')
    cx = x0
    for wdt in colw[:-1]:
        cx += wdt
        add(f'<line x1="{cx}" y1="{ty}" x2="{cx}" y2="{ty + rowh * 16}" stroke="{INK}" stroke-width="0.6"/>')
    for r, row in enumerate(streams[blk * 15:(blk + 1) * 15]):
        cx = x0
        for c, val in enumerate(row):
            text(cx + colw[c] / 2, ty + rowh * (r + 1) + 13, str(val), size=10.5, bold=(c == 0)); cx += colw[c]

# ---------- title strip ----------
add(f'<rect x="60" y="1132" width="1560" height="34" fill="none" stroke="{INK}" stroke-width="1.6"/>')
text(74, 1155, "Linde air separation unit — PFD-102", size=13.5, bold=True, anchor="start")
text(840, 1155, "Sample process flow diagram  |  Stream values are sample values, not a converged simulation", size=12)
text(1606, 1155, "Drawn: Muse  |  2026-10-24  |  Revision 0  |  Sheet 1 of 1", size=12, anchor="end")

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
       + "\n".join(el) + "\n</svg>\n")
with open("/home/hatch/workspace/linde-asu/pfd/linde-asu-pfd-v1.svg", "w") as f:
    f.write(svg)
print("SVG written:", len(svg), "bytes")

# ---------- verification ----------
COMP = {}  # stream -> (total, N2, O2, Ar) kmol/h from displayed values
for row in streams:
    n, fl, nn, oo, aa = row[0], float(row[1]), float(row[4]), float(row[5]), float(row[6])
    COMP[n] = (fl, fl * nn / 100, fl * oo / 100, fl * aa / 100)
def bal(name, ins, outs, tol=0.25):
    for i in range(4):
        d = abs(sum(COMP[s][i] for s in ins) - sum(COMP[s][i] for s in outs))
        assert d <= tol, f"{name} component {i} off by {d}"
    print("balance OK:", name)
bal("front end + MHE air pass", [1], [6])
bal("cold air split", [6], [7, 8]); bal("expander", [8], [9])
bal("pressure column", [7, 12], [10, 16]); bal("condenser/reboiler", [10], [11, 12])
bal("nitrogen subcooler", [11], [13]); bal("nitrogen valve", [14], [15])
bal("rich subcooler", [16], [17]); bal("rich valve", [17], [18])
bal("low-pressure column", [9, 15, 18, 30], [19, 20, 21, 29])
bal("argon column", [29, 27], [25, 30]); bal("argon condenser", [25], [26])
bal("argon split", [26], [27, 28])
bal("MHE product passes", [19, 20, 21], [22, 23, 24])
bal("overall", [1], [22, 23, 24, 28])
# identity cross-count (A4)
assert sorted(STREAMS) == list(range(1, 31)), sorted(STREAMS)
assert sorted(r[0] for r in streams) == list(range(1, 31))
print("identity cross-count OK: 30 streams")
# bends
per_stream = {}
for n, pts in ALL_SEG_LISTS: per_stream[n] = per_stream.get(n, 0) + (len(pts) - 2)
print("bends:", per_stream, "total:", sum(per_stream.values()), "max:", max(per_stream.values()))
assert max(per_stream.values()) <= 2
# crossings
def inter(a, b, c, d):
    def o(p, q, r): return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(a, b, c) * o(a, b, d) < 0) and (o(c, d, a) * o(c, d, b) < 0)
allsegs = []
for n, pts in ALL_SEG_LISTS:
    for i in range(len(pts) - 1): allsegs.append((n, (pts[i], pts[i + 1])))
cross = []
for i in range(len(allsegs)):
    for j in range(i + 1, len(allsegs)):
        (n1, s1), (n2, s2) = allsegs[i], allsegs[j]
        if n1 != n2 and inter(s1[0], s1[1], s2[0], s2[1]): cross.append((n1, n2))
print("crossings:", len(cross), cross)
Lt = sum(abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]) for _, s in allsegs)
print("total routed length (drawing units):", round(Lt, 1), "= mm at final scale:", round(Lt / 4, 1))
# minimum parallel spacing (overlapping projections only)
smin = 1e9
for i in range(len(allsegs)):
    for j in range(i + 1, len(allsegs)):
        (n1, s1), (n2, s2) = allsegs[i], allsegs[j]
        if n1 == n2: continue
        (a, b), (c, d) = s1, s2
        if a[1] == b[1] and c[1] == d[1]:  # both horizontal
            if min(b[0], d[0]) - max(a[0], c[0]) > 0: smin = min(smin, abs(a[1] - c[1]))
        if a[0] == b[0] and c[0] == d[0]:  # both vertical
            if min(b[1], d[1]) - max(a[1], c[1]) > 0: smin = min(smin, abs(a[0] - c[0]))
print("s_min (drawing units):", smin, "= mm:", smin / 4)
