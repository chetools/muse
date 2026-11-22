"""Generate the clarifying figures for the MVR page (v10).

Every figure is an original drawing. Data figures are computed
from python/balance.py; schematics are drawn from the design
basis stated on the page and the cited sources (see the panel
text). Output: figures/*.svg (text kept as text) plus PNG
previews in /tmp for inspection. Style follows
~/workspace/design-guidelines/stem-visual-style.md: one sans
typeface, Okabe-Ito accents, no in-figure titles, direct labels
in place of boxed legends where labels fit.
"""
import re
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "python"))
from balance import psat_kpa, run_model  # noqa: E402

FIGDIR = HERE / "figures"
FIGDIR.mkdir(exist_ok=True)
PREVIEW = Path("/tmp/mvr-fig-previews")
PREVIEW.mkdir(exist_ok=True)

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8.5, "axes.labelsize": 8.5,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "xtick.major.size": 3,
    "ytick.major.size": 3, "xtick.direction": "out",
    "ytick.direction": "out", "axes.spines.top": False,
    "axes.spines.right": False, "lines.linewidth": 1.1,
    "svg.fonttype": "none",
})
INK = "#1b1b1b"
BLUE = "#0072B2"
ORANGE = "#D55E00"
GRAY = "#5a5a5a"
FILM = "#cfe3f2"      # pale blue: liquid film / liquid
VAP = "#f6e3d3"       # pale orange tint: vapour space
WALLC = "#d9d9d9"     # gray: metal wall / casing

DESIGN = run_model()


def save(fig, name):
    fig.savefig(FIGDIR / f"{name}.svg", bbox_inches="tight",
                pad_inches=0.02)
    # Matplotlib embeds each label's source (including mathtext
    # such as $\Delta T_{BPE}$) in XML comments; strip them so the
    # page build's unrendered-mathematics check sees only the
    # rendered output.
    svg_path = FIGDIR / f"{name}.svg"
    svg = svg_path.read_text(encoding="utf-8")
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    svg_path.write_text(svg, encoding="utf-8")
    fig.savefig(PREVIEW / f"{name}.png", dpi=170,
                bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("wrote", name)


# ---------------------------------------------------------- Fig. T1
def fig_t1_psat():
    """Saturation pressure of water, Eq. (2), with the three lifts."""
    fig, ax = plt.subplots(figsize=(6.3, 3.9))
    t = np.linspace(50, 110, 241)
    ax.plot(t, [psat_kpa(x) for x in t], color=BLUE, lw=1.4)
    pairs = [(60.0, GRAY), (80.0, ORANGE), (100.0, GRAY)]
    for t_evap, colour in pairs:
        r = run_model(t_evap_c=t_evap)
        t1, t2 = r["t_sat1_c"], r["t_cond_c"]
        p1, p2 = r["p1_kpa"], r["p2_kpa"]
        ax.plot([t1, t2], [p1, p2], ":", color=colour, lw=0.9)
        ax.plot([t1], [p1], "o", ms=4.5, color=colour)
        ax.plot([t2], [p2], "s", ms=4.5, color=colour,
                fillstyle="none", mew=1.1)
        ratio_xy = (91.5, 59.0) if t_evap == 80.0 else (t2 + 2.5,
                                                        p2 + 7)
        ax.annotate(f"$r_p$ = {r['pressure_ratio']:.2f}",
                    xy=(t2, p2), xytext=ratio_xy,
                    color=colour, fontsize=8.5)
    r = DESIGN
    ax.annotate("suction, 78 °C, 43.6 kPa",
                xy=(r["t_sat1_c"], r["p1_kpa"]),
                xytext=(52, 62), color=ORANGE, fontsize=8.5,
                arrowprops=dict(arrowstyle="-", color=ORANGE, lw=0.7))
    ax.annotate("discharge, 88 °C, 64.9 kPa",
                xy=(r["t_cond_c"], r["p2_kpa"]),
                xytext=(86, 96), color=ORANGE, fontsize=8.5,
                arrowprops=dict(arrowstyle="-", color=ORANGE, lw=0.7))
    ax.annotate("60 °C evaporator", xy=(58, 18.1), xytext=(50, 26),
                color=GRAY, fontsize=8)
    ax.annotate("100 °C evaporator", xy=(98, 94.3), xytext=(93, 76),
                color=GRAY, fontsize=8)
    ax.set_xlim(48, 112)
    ax.set_ylim(0, 150)
    ax.set_xlabel("Temperature, $T$ (°C)")
    ax.set_ylabel("Saturation pressure, $p^{sat}$ (kPa)")
    save(fig, "fig_t1_psat")


# ---------------------------------------------------------- Fig. T2
def fig_t2_ladder():
    """The 10 K lift as a temperature ladder at the design basis."""
    fig, ax = plt.subplots(figsize=(6.3, 4.3))
    x0, x1 = 0.30, 0.55
    levels = [
        (78.0, "saturation temperature of pure water\n"
               "at the separator pressure, 78 °C", INK, "-", "top"),
        (80.0, "solution boiling temperature, 80 °C", INK, "-",
         "bottom"),
        (88.0, "condensing temperature, 88 °C", INK, "-", "center"),
        (128.9, "compressor discharge temperature,\n128.9 °C "
                "(superheated)", GRAY, "--", "center"),
    ]
    for temp, label, colour, ls, va in levels:
        ax.plot([x0, x1], [temp, temp], ls, color=colour, lw=1.3)
        ytxt = temp + (1.6 if va == "bottom" else
                       -1.6 if va == "top" else 0.0)
        ax.annotate(label, xy=(x1 + 0.015, ytxt),
                    va="bottom" if va == "bottom" else
                    "top" if va == "top" else "center",
                    fontsize=8.5, color=colour)

    def bracket(ta, tb, label, x, colour=INK, ls="-"):
        ax.plot([x, x], [ta, tb], ls, color=colour, lw=0.9)
        ax.plot([x, x + 0.018], [ta, ta], color=colour, lw=0.9)
        ax.plot([x, x + 0.018], [tb, tb], color=colour, lw=0.9)
        ax.annotate(label, xy=(x - 0.012, (ta + tb) / 2),
                    ha="right", va="center", fontsize=8.5,
                    color=colour)

    bracket(78.0, 80.0, "$\\Delta T_{BPE}$ = 2 K", 0.27)
    bracket(80.0, 87.0, "$\\Delta T_{tr}$ = 7 K", 0.27)
    bracket(87.0, 88.0, "$\\Delta T_{loss}$ = 1 K", 0.20)
    bracket(88.0, 128.9, "discharge\nsuperheat\n40.9 K", 0.27,
            colour=GRAY, ls="--")
    ax.plot([x0, x1], [87, 87], color=INK, lw=0.5, ls=(0, (2, 2)))
    ax.set_xlim(0, 1.02)
    ax.set_ylim(72, 136)
    ax.set_xticks([])
    ax.set_ylabel("Temperature (°C)")
    ax.spines["bottom"].set_visible(False)
    save(fig, "fig_t2_ladder")


# ---------------------------------------------------------- Fig. T3
def _wall_panel(ax, fouled):
    """Temperature profile across the tube wall; one panel."""
    if not fouled:
        layers = [(0.0, 1.0, FILM, "condensing\nfilm"),
                  (1.0, 2.0, WALLC, "tube\nwall"),
                  (2.0, 3.0, FILM, "boiling\nfilm")]
        prof = [(0.0, 88.0), (1.0, 86.6), (2.0, 84.6), (3.0, 80.0)]
        title = "a  Clean"
    else:
        layers = [(0.0, 1.0, FILM, "condensing\nfilm"),
                  (1.0, 2.0, WALLC, "tube\nwall"),
                  (2.0, 2.7, "#b58950", "scale"),
                  (2.7, 3.7, FILM, "boiling\nfilm")]
        prof = [(0.0, 90.0), (1.0, 88.6), (2.0, 86.6), (2.7, 82.6),
                (3.7, 80.0)]
        title = "b  Fouled (scale on the boiling side)"
    for xa, xb, colour, label in layers:
        ax.axvspan(xa, xb, color=colour, alpha=0.55, lw=0)
        ax.axvline(xa, color=INK, lw=0.6)
        ax.annotate(label, xy=((xa + xb) / 2, 77.2), ha="center",
                    va="top", fontsize=7.5)
    ax.axvline(layers[-1][1], color=INK, lw=0.6)
    xs = [p[0] for p in prof]
    ys = [p[1] for p in prof]
    ax.plot(xs, ys, color=ORANGE, lw=1.4, marker="o", ms=3.5)
    ax.annotate(f"{prof[0][1]:.0f} °C", xy=(prof[0][0], prof[0][1]),
                xytext=(prof[0][0] + 0.06, prof[0][1] + 0.7),
                fontsize=8.5)
    ax.annotate("80 °C", xy=(prof[-1][0], prof[-1][1]),
                xytext=(prof[-1][0] - 0.62, prof[-1][1] + 0.7),
                fontsize=8.5)
    if fouled:
        ax.annotate("$\\Delta T_{scale}$ = 2 K\n(illustrative)",
                    xy=(2.35, 93.9), fontsize=8, ha="center")
    ax.set_ylim(76, 96)
    ax.set_xticks([])
    ax.set_title(title, loc="left", fontsize=9, fontweight="bold")
    return layers[-1][1]


def fig_t3_wall():
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 3.6),
                             sharey=True)
    xmax = _wall_panel(axes[0], fouled=False)
    axes[0].set_xlim(-0.1, xmax + 0.1)
    xmax = _wall_panel(axes[1], fouled=True)
    axes[1].set_xlim(-0.1, xmax + 0.1)
    axes[0].set_ylabel("Temperature (°C)")
    fig.subplots_adjust(wspace=0.12)
    save(fig, "fig_t3_wall")


# ---------------------------------------------------------- Fig. T4
def fig_t4_ts():
    """The vapour cycle on a temperature-entropy diagram (schematic)."""
    fig, ax = plt.subplots(figsize=(6.3, 4.4))
    tt = np.linspace(45, 130, 200)
    s_left = 4.6 - 3.1 * ((138 - tt) / 93) ** 1.5
    s_right = 4.6 + 4.0 * ((138 - tt) / 93) ** 1.2
    ax.plot(s_left, tt, color=GRAY, lw=1.0)
    ax.plot(s_right, tt, color=GRAY, lw=1.0)
    cap_t = np.linspace(0, np.pi, 40)
    ax.plot(4.665 + 0.145 * np.cos(cap_t), 130 + 4.0 * np.sin(cap_t),
            color=GRAY, lw=1.0)
    ax.annotate("saturation dome\n(schematic)", xy=(4.665, 137.5),
                ha="center", fontsize=8, color=GRAY)

    def s_sat_vap(temp):
        return 4.6 + 4.0 * ((138 - temp) / 93) ** 1.2

    def s_sat_liq(temp):
        return 4.6 - 3.1 * ((138 - temp) / 93) ** 1.5

    p1 = (s_sat_vap(78.0), 78.0)          # saturated vapour, separator
    p2s = (p1[0], 116.6)                  # isentropic discharge
    p2 = (p1[0] + 0.52, 128.9)            # actual discharge
    p3 = (s_sat_vap(88.0), 88.0)          # saturated vapour, condensing
    p4 = (s_sat_liq(88.0), 88.0)          # saturated condensate
    p5 = (s_sat_liq(63.0) - 0.15, 63.0)   # condensate to preheater
    # compression: isentropic (solid vertical) and actual (dashed)
    ax.plot([p1[0], p2s[0]], [p1[1], p2s[1]], color=BLUE, lw=1.3)
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=ORANGE, lw=1.3,
            ls="--")
    # desuperheating, condensation, condensate leg
    ax.plot([p2[0], p3[0]], [p2[1], p3[1]], color=INK, lw=1.3)
    ax.plot([p3[0], p4[0]], [p3[1], p4[1]], color=INK, lw=1.3)
    ax.plot([p4[0], p5[0]], [p4[1], p5[1]], color=INK, lw=1.3)
    for pt in (p1, p2s, p2, p3, p4, p5):
        ax.plot([pt[0]], [pt[1]], "o", ms=4, color=INK)
    halo = dict(facecolor="white", edgecolor="none", pad=0.6)
    ax.annotate("1  saturated vapour,\n78 °C, 43.6 kPa", xy=p1,
                xytext=(4.55, 58), fontsize=8, ha="center",
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.annotate("2s  isentropic discharge,\n116.6 °C", xy=p2s,
                xytext=(6.45, 120.5), fontsize=8, bbox=halo)
    ax.annotate("2  actual discharge,\n128.9 °C", xy=p2,
                xytext=(7.75, 130), fontsize=8)
    ax.annotate("3  saturated vapour,\n88 °C, 64.9 kPa", xy=p3,
                xytext=(6.72, 95.5), fontsize=8, bbox=halo)
    ax.annotate("4  condensate,\n88 °C", xy=p4, xytext=(3.0, 93),
                fontsize=8)
    ax.annotate("5  condensate to\npreheater, 63 °C", xy=p5,
                xytext=(1.55, 45.5), fontsize=8)
    ax.annotate("isentropic", xy=(p1[0] - 0.14, 100), fontsize=8,
                color=BLUE, ha="right")
    ax.annotate("actual", xy=(p1[0] + 0.34, 103), fontsize=8,
                color=ORANGE)
    ax.annotate("desuperheating", xy=(7.38, 110), fontsize=8)
    ax.annotate("condensation at 88 °C", xy=(5.0, 82.5),
                fontsize=8, ha="center")
    ax.annotate("$\\mathrm{COP}_{Carnot}$ = 36.1\n"
                "model COP = 24.1", xy=(1.1, 122), fontsize=8.5)
    ax.set_xlim(0.4, 9.6)
    ax.set_ylim(40, 148)
    ax.set_xlabel("Specific entropy, $s$ (kJ/(kg K)), schematic scale")
    ax.set_ylabel("Temperature, $T$ (°C)")
    save(fig, "fig_t4_ts")


# ---------------------------------------------------------- Fig. P3
def fig_p3_cutaway():
    """Falling-film evaporator cutaway: distributor, film, demister."""
    fig, ax = plt.subplots(figsize=(5.6, 7.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14.6)
    ax.axis("off")
    lw = 1.2
    # shell side (heating vapour) tint: only outside the tubes
    for xa, xb in ((2.0, 3.0), (4.1, 5.9), (7.0, 8.0)):
        ax.add_patch(Rectangle((xa, 2.3), xb - xa, 6.9,
                               facecolor=VAP, edgecolor="none",
                               zorder=0))
    # vessel shell
    ax.plot([2, 2, 8, 8], [1.2, 12.1, 12.1, 1.2], color=INK, lw=lw)
    dome = np.linspace(0, np.pi, 60)
    ax.plot(5 + 3 * np.cos(dome), 12.1 + 0.85 * np.sin(dome),
            color=INK, lw=lw)
    # vapour outlet and demister pad in the head
    ax.plot([4.65, 4.65, 5.35, 5.35], [13.9, 12.95, 12.95, 13.9],
            color=INK, lw=lw)
    ax.annotate("", xy=(5.0, 14.35), xytext=(5.0, 13.55),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("vapour out to the compressor (stream 3)",
                xy=(5.45, 13.6), fontsize=8.5)
    ax.add_patch(Rectangle((2.25, 11.35), 5.5, 0.42,
                           facecolor="#ffffff", edgecolor=INK, lw=0.9,
                           hatch="xxx", zorder=3))
    ax.annotate("demister pad (mesh)", xy=(2.2, 11.56),
                xytext=(0.1, 12.6), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    # feed inlet
    ax.plot([0.7, 2.0], [10.55, 10.55], color=INK, lw=lw)
    ax.annotate("", xy=(1.95, 10.55), xytext=(1.1, 10.55),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("feed in\n(stream 2)", xy=(0.1, 10.9), fontsize=8.5)
    # distributor tray and ferrules
    ax.add_patch(Rectangle((2.3, 9.95), 5.4, 0.5, facecolor=FILM,
                           edgecolor=INK, lw=0.9, zorder=2))
    ax.annotate("feed distributor (tray)", xy=(7.7, 10.2),
                xytext=(8.15, 10.2), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    tubes = [3.55, 6.45]
    for cx in tubes:
        ax.add_patch(Rectangle((cx - 0.30, 9.45), 0.60, 0.85,
                               facecolor="#ffffff", edgecolor=INK,
                               lw=0.9, zorder=3))
        ax.plot([cx - 0.30, cx - 0.11], [10.3, 10.3], color=INK, lw=1.4)
        ax.plot([cx + 0.11, cx + 0.30], [10.3, 10.3], color=INK, lw=1.4)
    ax.annotate("distributor ferrule,\nnotched rim (one per tube)",
                xy=(3.25, 10.05), xytext=(0.1, 8.3), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    # tube sheet
    ax.add_patch(Rectangle((2.0, 9.2), 6.0, 0.25, facecolor=WALLC,
                           edgecolor=INK, lw=0.9, zorder=2))
    ax.annotate("tube sheet", xy=(8.05, 9.32), fontsize=8.5)
    # tubes: walls, film on the inner wall, vapour core
    for cx in tubes:
        for sgn in (-1, 1):
            ax.plot([cx + sgn * 0.55, cx + sgn * 0.55], [2.3, 9.2],
                    color=INK, lw=lw)
            ax.add_patch(Rectangle(
                (cx + sgn * 0.39 - (0.16 if sgn < 0 else 0), 2.3),
                0.16, 6.9, facecolor="#7fb3dd", edgecolor="none",
                zorder=1))
        ax.annotate("", xy=(cx, 6.6), xytext=(cx, 4.6),
                    arrowprops=dict(arrowstyle="->", color=GRAY,
                                    lw=1.0))
        ax.annotate("", xy=(cx - 0.47, 6.2), xytext=(cx - 0.47, 7.6),
                    arrowprops=dict(arrowstyle="->", color=BLUE,
                                    lw=1.0))
    ax.annotate("liquid film on the\ninner tube wall",
                xy=(2.92, 5.6), xytext=(0.1, 5.9), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.annotate("vapour\ncore", xy=(6.45, 8.15), fontsize=8.5,
                color=GRAY, ha="center")
    ax.annotate("compressed vapour condenses\non the outer tube wall\n"
                "(heating element, stream 4 in;\ncondensate, stream 5 out)",
                xy=(7.62, 6.0), xytext=(8.15, 5.2), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    # sump and concentrate outlet
    ax.add_patch(Rectangle((2.0, 1.55), 6.0, 0.75, facecolor=FILM,
                           edgecolor="none", zorder=0))
    ax.plot([2, 8], [2.3, 2.3], color=INK, lw=0.9)
    ax.annotate("concentrate sump", xy=(5.0, 1.85), fontsize=8.5,
                ha="center")
    ax.plot([4.7, 4.7, 5.3, 5.3], [1.2, 0.45, 0.45, 1.2],
            color=INK, lw=lw)
    ax.annotate("", xy=(5.0, 0.12), xytext=(5.0, 0.9),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("concentrate out (stream 6)", xy=(5.45, 0.55),
                fontsize=8.5)
    save(fig, "fig_p3_cutaway")


# ---------------------------------------------------------- Fig. P6
def fig_p6_map():
    """Compressor map schematic: ratio against inlet volumetric flow."""
    fig, ax = plt.subplots(figsize=(6.3, 4.2))
    q = np.linspace(58, 116, 100)
    speeds = [(0.90, 1.70, 0.0033, "90 % speed"),
              (1.00, 1.86, 0.0037, "100 % speed (design)"),
              (1.10, 2.02, 0.0041, "110 % speed")]
    for frac, a, b, label in speeds:
        r = a - b * q
        ax.plot(q, r, color=BLUE if frac == 1.0 else GRAY,
                lw=1.3 if frac == 1.0 else 0.9)
        ax.annotate(label, xy=(114, a - b * 114), fontsize=8,
                    va="center", color=BLUE if frac == 1.0 else GRAY)
    surge_q = np.array([64, 72, 81])
    surge_r = np.array([1.70 - 0.0033 * 64, 1.86 - 0.0037 * 72,
                        2.02 - 0.0041 * 81])
    ax.plot(surge_q, surge_r, color=ORANGE, lw=1.6, ls="--")
    ax.annotate("surge line", xy=(66, 1.44), fontsize=8.5,
                color=ORANGE)
    ax.plot([100], [1.49], "o", ms=6, color=ORANGE)
    ax.annotate("design point,\n$r_p$ = 1.49", xy=(100, 1.49),
                xytext=(103, 1.36), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.annotate("", xy=(76, 1.86 - 0.0037 * 76), xytext=(98, 1.497),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.1))
    ax.annotate("falling plant demand\nat fixed speed", xy=(80, 1.66),
                fontsize=8.5)
    ax.annotate("anti-surge recycle returns discharge vapour\n"
                "to the suction side, holding the flow up",
                xy=(86, 1.13), fontsize=8)
    ax.annotate("Schematic — not a vendor map", xy=(59, 1.86),
                fontsize=8, style="italic", color=GRAY)
    ax.set_xlim(56, 128)
    ax.set_ylim(1.08, 1.95)
    ax.set_xlabel("Inlet volumetric flow (per cent of design value)")
    ax.set_ylabel("Pressure ratio, $r_p$")
    save(fig, "fig_p6_map")


# ---------------------------------------------------------- Fig. P7
def fig_p7_machine():
    """Single-stage centrifugal MVR compressor, side section."""
    fig, ax = plt.subplots(figsize=(6.3, 4.9))
    ax.set_xlim(0, 12.6)
    ax.set_ylim(0, 9.6)
    ax.axis("off")
    lw = 1.2
    cx = 5.6  # shaft centreline
    # inlet pipe and casing cover
    ax.plot([cx - 0.75, cx - 0.75, cx + 0.75, cx + 0.75],
            [9.3, 8.35, 8.35, 9.3], color=INK, lw=lw)
    ax.annotate("", xy=(cx, 8.5), xytext=(cx, 9.25),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("vapour in (from separator)", xy=(cx + 0.95, 8.9),
                fontsize=8.5)
    cover = Polygon([(cx - 2.5, 7.15), (cx - 0.75, 8.35),
                     (cx + 0.75, 8.35), (cx + 2.5, 7.15)],
                    closed=True, facecolor="#ffffff", edgecolor=INK,
                    lw=lw)
    ax.add_patch(cover)
    ax.annotate("casing cover", xy=(cx - 2.45, 7.8), xytext=(0.1, 8.6),
                fontsize=8.5, arrowprops=dict(arrowstyle="-", lw=0.7))
    # volute casing (section outline) and outlet with diffuser
    ax.add_patch(Rectangle((cx - 2.9, 5.55), 5.8, 1.65,
                           facecolor=VAP, edgecolor=INK, lw=lw))
    ax.plot([cx + 2.9, cx + 3.5, cx + 3.5, cx + 2.9],
            [7.05, 7.35, 6.05, 5.7], color=INK, lw=lw)
    ax.annotate("", xy=(cx + 4.6, 6.7), xytext=(cx + 3.45, 6.7),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("compressed vapour out\n(diffuser and volute outlet)",
                xy=(cx + 3.6, 7.6), fontsize=8.5)
    ax.annotate("volute casing", xy=(cx + 2.95, 5.9), xytext=(9.6, 5.0),
                fontsize=8.5, arrowprops=dict(arrowstyle="-", lw=0.7))
    # impeller: back plate, blades, shroud (side section)
    ax.add_patch(Rectangle((cx - 2.3, 5.95), 4.6, 0.28,
                           facecolor=WALLC, edgecolor=INK, lw=0.9))
    for bx in (-1.85, -1.15, -0.45, 0.45, 1.15, 1.85):
        ax.add_patch(Rectangle((cx + bx - 0.09, 6.23), 0.18, 0.62,
                               facecolor=WALLC, edgecolor=INK, lw=0.7))
    ax.plot([cx - 2.3, cx - 0.55, cx + 0.55, cx + 2.3],
            [7.15, 6.85, 6.85, 7.15], color=INK, lw=0.9)
    ax.annotate("impeller", xy=(cx - 2.2, 6.5), xytext=(0.1, 6.3),
                fontsize=8.5, arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.annotate("", xy=(cx - 1.3, 7.55), xytext=(cx + 0.6, 7.75),
                arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.0,
                                connectionstyle="arc3,rad=0.35"))
    ax.annotate("rotation", xy=(cx + 0.75, 7.8), fontsize=8,
                color=GRAY)
    # shaft, seal, motor
    ax.add_patch(Rectangle((cx - 0.22, 2.6), 0.44, 3.35,
                           facecolor=WALLC, edgecolor=INK, lw=0.9))
    ax.annotate("shaft", xy=(cx + 0.25, 4.6), xytext=(8.6, 4.35),
                fontsize=8.5, arrowprops=dict(arrowstyle="-", lw=0.7))
    for sy in (5.18, 4.92):
        ax.add_patch(Rectangle((cx - 0.5, sy), 1.0, 0.2,
                               facecolor=INK, edgecolor=INK, lw=0.5))
    ax.annotate("shaft seal", xy=(cx - 0.55, 5.05), xytext=(0.1, 4.7),
                fontsize=8.5, arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.add_patch(Rectangle((cx - 1.8, 0.7), 3.6, 1.95,
                           facecolor="#ffffff", edgecolor=INK, lw=lw))
    for fx in np.linspace(cx - 1.45, cx + 1.45, 6):
        ax.plot([fx, fx], [0.85, 2.5], color=GRAY, lw=0.5)
    ax.annotate("high-speed motor", xy=(cx, 1.65), fontsize=8.5,
                ha="center")
    ax.annotate("impeller mounted\ndirectly on the motor shaft",
                xy=(cx - 1.85, 3.1), xytext=(0.1, 2.6), fontsize=8.5)
    # drive cabinet
    ax.add_patch(Rectangle((9.8, 0.7), 2.6, 1.95, facecolor="#ffffff",
                           edgecolor=INK, lw=lw))
    ax.annotate("drive cabinet\n(frequency converter)", xy=(11.1, 1.65),
                fontsize=8, ha="center")
    ax.plot([cx + 1.8, 9.8], [1.1, 1.1], color=GRAY, lw=0.8, ls="--")
    save(fig, "fig_p7_machine")


if __name__ == "__main__":
    fig_t1_psat()
    fig_t2_ladder()
    fig_t3_wall()
    fig_t4_ts()
    fig_p3_cutaway()
    fig_p6_map()
    fig_p7_machine()
