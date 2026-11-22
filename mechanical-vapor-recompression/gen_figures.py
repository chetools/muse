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
    """Falling-film evaporator cutaway (v11 redraw).

    Arrangement after the GEA Wiegand falling-film section:
    distribution head and tray at the top, film and vapour in
    co-current downflow inside the tubes, separation in the
    chamber at the bottom, demister pads at the entrances of
    the riser channels beside the heating shell, vapour out
    at the top. Five tubes at close pitch in an open shell
    space (one pale tint for the whole shell side, no blocks).
    """
    fig, ax = plt.subplots(figsize=(5.6, 7.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14.6)
    ax.axis("off")
    lw = 1.2
    # shell side (heating vapour) tint: one continuous space
    ax.add_patch(Rectangle((2.5, 3.55), 5.0, 5.65,
                           facecolor=VAP, edgecolor="none", zorder=0))
    # vessel shell: walls, bottom (gap at the outlet), dome
    ax.plot([2, 2], [1.2, 12.1], color=INK, lw=lw)
    ax.plot([8, 8], [1.2, 12.1], color=INK, lw=lw)
    ax.plot([2, 4.7], [1.2, 1.2], color=INK, lw=lw)
    ax.plot([5.3, 8], [1.2, 1.2], color=INK, lw=lw)
    dome = np.linspace(0, np.pi, 60)
    ax.plot(5 + 3 * np.cos(dome), 12.1 + 0.85 * np.sin(dome),
            color=INK, lw=lw)
    ax.plot([2, 8], [12.1, 12.1], color=INK, lw=0.7)
    # vapour riser channels beside the shell (inner walls)
    for rx in (2.5, 7.5):
        ax.plot([rx, rx], [3.3, 11.5], color=INK, lw=0.9)
    ax.plot([2.5, 2.0], [11.5, 11.5], color=INK, lw=0.9)
    ax.plot([7.5, 8.0], [11.5, 11.5], color=INK, lw=0.9)
    for rx, ays in ((2.25, (4.6, 7.4)), (7.75, (6.4, 10.2))):
        for ay in ays:
            ax.annotate("", xy=(rx, ay + 0.75), xytext=(rx, ay),
                        arrowprops=dict(arrowstyle="->", color=GRAY,
                                        lw=1.0))
    # vapour outlet at the top of the head
    ax.plot([4.65, 4.65, 5.35, 5.35], [13.9, 12.95, 12.95, 13.9],
            color=INK, lw=lw)
    ax.annotate("", xy=(5.0, 14.35), xytext=(5.0, 13.55),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("vapour out to the compressor (stream 3)",
                xy=(5.45, 13.6), fontsize=8.5)
    ax.annotate("vapour head", xy=(5.0, 12.42), fontsize=8.5,
                color=GRAY, ha="center")
    # feed inlet into the distribution chamber
    ax.plot([0.7, 2.55], [10.55, 10.55], color=INK, lw=lw)
    ax.annotate("", xy=(2.45, 10.55), xytext=(1.1, 10.55),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("feed in\n(stream 2)", xy=(0.1, 10.9), fontsize=8.5)
    # distributor tray and ferrules (one per tube)
    tubes = [3.35, 4.175, 5.0, 5.825, 6.65]
    ax.add_patch(Rectangle((2.55, 9.95), 4.9, 0.5, facecolor=FILM,
                           edgecolor=INK, lw=0.9, zorder=2))
    ax.annotate("feed distributor (tray)", xy=(7.5, 10.2),
                xytext=(8.15, 10.2), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    for cx in tubes:
        ax.add_patch(Rectangle((cx - 0.30, 9.45), 0.60, 0.85,
                               facecolor="#ffffff", edgecolor=INK,
                               lw=0.9, zorder=3))
        ax.plot([cx - 0.30, cx - 0.11], [10.3, 10.3], color=INK,
                lw=1.4)
        ax.plot([cx + 0.11, cx + 0.30], [10.3, 10.3], color=INK,
                lw=1.4)
    ax.annotate("distributor ferrule,\nnotched rim (one per tube)",
                xy=(3.05, 10.0), xytext=(0.1, 8.35), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    # tube sheets
    ax.add_patch(Rectangle((2.5, 9.2), 5.0, 0.25, facecolor=WALLC,
                           edgecolor=INK, lw=0.9, zorder=2))
    ax.add_patch(Rectangle((2.5, 3.3), 5.0, 0.25, facecolor=WALLC,
                           edgecolor=INK, lw=0.9, zorder=2))
    ax.annotate("tube sheet", xy=(8.05, 9.32), fontsize=8.5)
    # tubes: walls, film on the inner wall, vapour core; film and
    # vapour both flow DOWN (co-current falling film)
    for i, cx in enumerate(tubes):
        for sgn in (-1, 1):
            ax.plot([cx + sgn * 0.30, cx + sgn * 0.30], [3.55, 9.2],
                    color=INK, lw=lw)
            ax.add_patch(Rectangle(
                (cx + sgn * 0.30 - (0.15 if sgn < 0 else 0), 3.55),
                0.15, 5.65, facecolor="#7fb3dd", edgecolor="none",
                zorder=1))
        if i in (0, 2, 4):
            ax.annotate("", xy=(cx - 0.225, 6.1),
                        xytext=(cx - 0.225, 7.5),
                        arrowprops=dict(arrowstyle="->", color=BLUE,
                                        lw=1.0))
            ax.annotate("", xy=(cx, 6.1), xytext=(cx, 7.5),
                        arrowprops=dict(arrowstyle="->", color=GRAY,
                                        lw=1.0))
    ax.annotate("liquid film on the\ninner tube wall",
                xy=(3.12, 7.3), xytext=(0.1, 6.7), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.annotate("vapour core: vapour formed\nflows down with the film",
                xy=(3.32, 5.2), xytext=(0.1, 4.35), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    # shell-side nozzles (drawn through the riser channel wall)
    ax.add_patch(Rectangle((7.4, 8.4), 1.25, 0.3, facecolor="#ffffff",
                           edgecolor=INK, lw=0.9, zorder=3))
    ax.annotate("", xy=(7.75, 8.55), xytext=(8.5, 8.55),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("compressed vapour in (stream 4),\n"
                "condenses on the outer tube walls",
                xy=(7.42, 8.0), xytext=(8.15, 7.55), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.add_patch(Rectangle((7.4, 3.8), 1.25, 0.3, facecolor="#ffffff",
                           edgecolor=INK, lw=0.9, zorder=3))
    ax.annotate("", xy=(8.5, 3.95), xytext=(7.75, 3.95),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("condensate out (stream 5)", xy=(8.78, 3.9),
                fontsize=8.5)
    ax.annotate("vapour riser: disengaged vapour\n"
                "rises outside the heating shell",
                xy=(7.72, 6.4), xytext=(8.15, 5.55), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    # separator space at the bottom: mixture in, liquid pool,
    # vapour turns to the risers across the demister pads
    ax.annotate("film and vapour leave\nthe tube bottoms together",
                xy=(5.0, 3.06), fontsize=7.5, ha="center", color=GRAY)
    for xa, xb in ((4.2, 2.85), (5.8, 7.15)):
        ax.annotate("", xy=(xb, 2.50), xytext=(xa, 2.50),
                    arrowprops=dict(arrowstyle="->", color=GRAY,
                                    lw=1.0))
    for px in (2.02, 7.52):
        ax.add_patch(Rectangle((px, 2.92), 0.46, 0.34,
                               facecolor="#ffffff", edgecolor=INK,
                               lw=0.9, hatch="xxx", zorder=3))
    ax.annotate("demister pads (mesh),\nat the riser entrances",
                xy=(2.26, 3.05), xytext=(0.1, 1.95), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.add_patch(Rectangle((2.0, 1.55), 6.0, 0.65, facecolor=FILM,
                           edgecolor="none", zorder=0))
    ax.plot([2, 8], [2.2, 2.2], color=INK, lw=0.6)
    ax.annotate("concentrate sump", xy=(5.0, 1.86), fontsize=8.5,
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
    """Single-stage centrifugal MVR compressor, meridional section.

    v11 redraw: the section follows the standard centrifugal
    stage diagram (axial inlet, impeller eye, curved blades
    between hub and shroud, vaneless diffuser, volute casing),
    in the vertical direct-drive arrangement of the Piller
    VapoFan [16]. A front-view inset shows the spiral volute
    and the tangential discharge, which a section cannot show.
    v12: the inset marks the impeller centre with the same
    dash-dot centreline as the section, so the axis reads
    identically in both views.
    """
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, 10.4)
    ax.axis("off")
    lw = 1.2
    cx = 4.6  # shaft centreline
    # One centreline mark for the machine axis, used identically
    # in the section and in the front-view inset (v12).
    cl_ls = (0, (6, 3, 1, 3))
    ax.plot([cx, cx], [0.4, 10.25], color=GRAY, lw=0.5, ls=cl_ls)
    # inlet pipe and casing cover (curved, converging to the eye)
    ax.plot([cx - 0.62, cx - 0.62, cx + 0.62, cx + 0.62],
            [10.15, 9.0, 9.0, 10.15], color=INK, lw=lw)
    ax.annotate("", xy=(cx, 9.2), xytext=(cx, 10.0),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("vapour in (from separator)", xy=(cx + 0.85, 9.62),
                fontsize=8.5)
    tt = np.linspace(0, 1, 40)
    for sgn in (-1, 1):
        ax.plot(cx + sgn * (0.62 + 2.23 * tt ** 1.5),
                9.0 - 1.4 * tt, color=INK, lw=lw)
    cover = Polygon(
        [(cx - 0.62, 9.0)]
        + [(cx - (0.62 + 2.23 * t ** 1.5), 9.0 - 1.4 * t) for t in tt]
        + [(cx + (0.62 + 2.23 * t ** 1.5), 9.0 - 1.4 * t)
           for t in tt[::-1]] + [(cx + 0.62, 9.0)],
        closed=True, facecolor="#ffffff", edgecolor="none", zorder=0)
    ax.add_patch(cover)
    ax.annotate("casing cover", xy=(cx - 2.5, 8.15),
                xytext=(0.1, 8.65), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    # volute casing in section: outline around impeller + diffuser
    ax.add_patch(Rectangle((cx - 2.85, 6.15), 5.7, 1.45,
                           facecolor="#ffffff", edgecolor=INK, lw=lw,
                           zorder=1))
    ax.annotate("volute casing", xy=(cx - 2.8, 6.32),
                xytext=(0.1, 5.55), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    # impeller profiles (offsets from the centreline, one side;
    # mirrored). Passage bounded by shroud (top) and hub (bottom).
    shroud_r = np.array([0.62, 1.05, 1.55, 2.05])
    shroud_y = np.array([8.62, 8.30, 7.80, 7.35])
    hub_r = np.array([0.52, 0.85, 1.40, 2.05])
    hub_y = np.array([7.90, 7.45, 7.02, 6.80])
    fine = np.linspace(0, 1, 60)
    # impeller body (hub and back plate) as metal under the passages
    hr_f = np.interp(fine, np.linspace(0, 1, 4), hub_r)
    hy_f = np.interp(fine, np.linspace(0, 1, 4), hub_y)
    body = Polygon(
        [(cx - r, y) for r, y in zip(hr_f[::-1], hy_f[::-1])]
        + [(cx + r, y) for r, y in zip(hr_f, hy_f)]
        + [(cx + 2.05, 6.78), (cx - 2.05, 6.78)],
        closed=True, facecolor="#e3e3e3", edgecolor="none", zorder=2)
    ax.add_patch(body)
    for sgn in (-1, 1):
        sr = np.interp(fine, np.linspace(0, 1, 4), shroud_r)
        sy = np.interp(fine, np.linspace(0, 1, 4), shroud_y)
        hr = np.interp(fine, np.linspace(0, 1, 4), hub_r)
        hy = np.interp(fine, np.linspace(0, 1, 4), hub_y)
        passage = Polygon(
            [(cx + sgn * r, y) for r, y in zip(sr, sy)]
            + [(cx + sgn * r, y) for r, y in zip(hr[::-1], hy[::-1])],
            closed=True, facecolor=VAP, edgecolor="none", zorder=2.5)
        ax.add_patch(passage)
        shroud_metal = Polygon(
            [(cx + sgn * r, y) for r, y in zip(sr, sy)]
            + [(cx + sgn * r, y - 0.13) for r, y in
               zip(sr[::-1], sy[::-1])],
            closed=True, facecolor="#e3e3e3", edgecolor="none",
            zorder=2.6)
        ax.add_patch(shroud_metal)
        ax.plot(cx + sgn * sr, sy, color=INK, lw=1.1, zorder=3)
        ax.plot(cx + sgn * sr, sy - 0.13, color=INK, lw=0.6, zorder=3)
        ax.plot(cx + sgn * hr, hy, color=INK, lw=1.1, zorder=3)
        # curved blades: lines across the passage, leaning back
        for tb in (0.30, 0.55, 0.80):
            r1 = np.interp(tb, fine, hr)
            y1 = np.interp(tb, fine, hy)
            r2 = np.interp(min(tb + 0.07, 1.0), fine, sr)
            y2 = np.interp(min(tb + 0.07, 1.0), fine, sy)
            ax.plot([cx + sgn * r1, cx + sgn * r2], [y1, y2],
                    color=INK, lw=1.0, zorder=3)
        # flow path: down the eye, turning radial, out at the rim
        for ta, tb_ in ((0.12, 0.45), (0.55, 0.88)):
            rm = (np.interp(tb_, fine, sr) + np.interp(tb_, fine, hr)) / 2
            ym = (np.interp(tb_, fine, sy) + np.interp(tb_, fine, hy)) / 2
            r0 = (np.interp(ta, fine, sr) + np.interp(ta, fine, hr)) / 2
            y0 = (np.interp(ta, fine, sy) + np.interp(ta, fine, hy)) / 2
            ax.annotate("", xy=(cx + sgn * rm, ym),
                        xytext=(cx + sgn * r0, y0),
                        arrowprops=dict(arrowstyle="->", color=BLUE,
                                        lw=1.1), zorder=4)
        ax.annotate("", xy=(cx + sgn * 2.62, 7.07),
                    xytext=(cx + sgn * 2.12, 7.07),
                    arrowprops=dict(arrowstyle="->", color=BLUE,
                                    lw=1.1), zorder=4)
    # back plate and hub
    ax.add_patch(Rectangle((cx - 2.05, 6.52), 4.10, 0.26,
                           facecolor=WALLC, edgecolor=INK, lw=0.9,
                           zorder=3))
    ax.add_patch(Rectangle((cx - 0.30, 5.90), 0.60, 0.62,
                           facecolor=WALLC, edgecolor=INK, lw=0.9,
                           zorder=3))
    ax.annotate("impeller",
                xy=(cx - 1.55, 7.6), xytext=(0.1, 6.95), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.annotate("vaneless diffuser", xy=(cx + 2.48, 7.07),
                xytext=(7.55, 8.35), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    # discharge duct (diffuser outlet of the volute), to the right
    ax.plot([cx + 2.85, cx + 4.30], [7.45, 7.60], color=INK, lw=lw)
    ax.plot([cx + 2.85, cx + 4.30], [6.55, 6.40], color=INK, lw=lw)
    ax.annotate("", xy=(cx + 4.90, 7.0), xytext=(cx + 4.25, 7.0),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("compressed vapour out\n(stream 4)", xy=(cx + 2.95, 5.80),
                fontsize=8.5)
    # shaft, seal, motor
    ax.add_patch(Rectangle((cx - 0.20, 2.55), 0.40, 3.35,
                           facecolor=WALLC, edgecolor=INK, lw=0.9))
    ax.annotate("shaft", xy=(cx + 0.24, 4.55), xytext=(7.6, 4.5),
                fontsize=8.5, arrowprops=dict(arrowstyle="-", lw=0.7))
    for sy in (5.52, 5.26):
        ax.add_patch(Rectangle((cx - 0.48, sy), 0.96, 0.19,
                               facecolor=INK, edgecolor=INK, lw=0.5))
    ax.annotate("shaft seal", xy=(cx - 0.52, 5.38), xytext=(0.1, 4.62),
                fontsize=8.5, arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.add_patch(Rectangle((cx - 1.8, 0.65), 3.6, 1.95,
                           facecolor="#ffffff", edgecolor=INK, lw=lw))
    for fx in np.linspace(cx - 1.45, cx + 1.45, 6):
        ax.plot([fx, fx], [0.80, 2.45], color=GRAY, lw=0.5)
    ax.annotate("high-speed motor", xy=(cx, 1.60), fontsize=8.5,
                ha="center")
    ax.annotate("impeller mounted\ndirectly on the motor shaft",
                xy=(cx - 1.85, 3.05), xytext=(0.1, 2.62), fontsize=8.5)
    # front-view inset: spiral volute, tangential discharge.
    # The spiral grows counter-clockwise from the tongue at the
    # right and leaves at full radius through the vertical duct.
    ix, iy = 10.70, 4.55
    th = np.linspace(0, 2 * np.pi, 140)
    rr = 0.78 + 0.40 * th / (2 * np.pi)
    ax.plot(ix + rr * np.cos(th), iy + rr * np.sin(th), color=INK,
            lw=1.2)
    ax.add_patch(plt.Circle((ix, iy), 0.68, facecolor="none",
                            edgecolor=GRAY, lw=0.9, ls="--"))
    # The machine axis in the inset carries the same dash-dot
    # centreline mark as the section, crossing at the impeller
    # centre and extending slightly beyond the impeller circle;
    # the volute spiral grows around that centre (v12).
    ax.plot([ix - 0.85, ix + 0.85], [iy, iy], color=GRAY, lw=0.5,
            ls=cl_ls, zorder=1)
    ax.plot([ix, ix], [iy - 0.85, iy + 0.85], color=GRAY, lw=0.5,
            ls=cl_ls, zorder=1)
    ax.plot([ix], [iy], "o", ms=3, color=INK)
    ax.annotate("", xy=(ix + 0.30, iy + 0.68), xytext=(ix - 0.38, iy + 0.60),
                arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.0,
                                connectionstyle="arc3,rad=0.4"))
    duct_x = ix + 1.18
    ax.plot([duct_x - 0.24, duct_x - 0.24], [iy - 0.05, iy + 1.55],
            color=INK, lw=lw)
    ax.plot([duct_x + 0.24, duct_x + 0.24], [iy + 0.35, iy + 1.55],
            color=INK, lw=lw)
    ax.annotate("", xy=(duct_x, iy + 1.5), xytext=(duct_x, iy + 0.45),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.annotate("front view: spiral volute growing\n"
                "around the impeller centre,\n"
                "tangential discharge",
                xy=(ix, iy - 1.62), fontsize=8.5, ha="center")
    ax.annotate("impeller (dashed)", xy=(ix - 0.62, iy - 0.35),
                xytext=(7.45, 3.90), fontsize=8,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    # drive cabinet
    ax.add_patch(Rectangle((9.8, 0.65), 2.6, 1.95, facecolor="#ffffff",
                           edgecolor=INK, lw=lw))
    ax.annotate("drive cabinet\n(frequency converter)", xy=(11.1, 1.60),
                fontsize=8, ha="center")
    ax.plot([cx + 1.8, 9.8], [1.05, 1.05], color=GRAY, lw=0.8, ls="--")
    save(fig, "fig_p7_machine")



if __name__ == "__main__":
    fig_t1_psat()
    fig_t2_ladder()
    fig_t3_wall()
    fig_t4_ts()
    fig_p3_cutaway()
    fig_p6_map()
    fig_p7_machine()
