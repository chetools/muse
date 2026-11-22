#!/usr/bin/env python3
"""Generate the clarifying figures of the Linde ASU page (v26).

Every figure is an original drawing computed from the page's own model
data: the Clausius-Clapeyron anchors of Eq. (15) and source [40], the
stream states of the diagram, and the compositions stated in the text.
No published figure is reproduced. Output: inline-ready SVG files in
page/figs/ (text as text, width 100%, viewBox preserved), plus PNG
previews in /tmp for inspection.
"""
import pathlib
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, Ellipse
from scipy.optimize import brentq
from scipy.interpolate import PchipInterpolator

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 10, "axes.labelsize": 10.5,
    "xtick.labelsize": 9.5, "ytick.labelsize": 9.5,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 3, "ytick.major.size": 3,
    "xtick.direction": "out", "ytick.direction": "out",
    "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 1.4, "lines.markersize": 5,
    "svg.fonttype": "none",
})

FIGS = pathlib.Path(__file__).parent.parent / "figs"
FIGS.mkdir(exist_ok=True)

C_N2 = "#0072B2"   # Okabe-Ito blue
C_O2 = "#D55E00"   # Okabe-Ito vermillion
C_AR = "#009E73"   # Okabe-Ito green
GREY = "#555555"

R = 8.314  # J/(mol K)

def p_sat(T, Tb, dH):
    """Clausius-Clapeyron vapour pressure (kPa) anchored at the normal
    boiling point Tb (101.325 kPa), Eq. (15) of the Theory panel;
    dH is the latent heat of vaporisation in kJ/mol."""
    return 101.325 * np.exp(-(dH * 1000.0 / R) * (1.0 / T - 1.0 / Tb))

# Anchors of the page (source [40], Theory saturation section)
N2 = dict(Tb=77.4, dH=5.57)
O2 = dict(Tb=90.2, dH=6.82)
AR = dict(Tb=87.3, dH=6.43)

def save(fig, name):
    svg_path = FIGS / f"{name}.svg"
    fig.savefig(svg_path, format="svg")
    fig.savefig(f"/tmp/{name}.png", dpi=150)
    plt.close(fig)
    # normalise the svg root for inline use: width 100%, no fixed height
    t = svg_path.read_text()
    i = t.index("<svg")
    j = t.index(">", i)
    head = t[i:j]
    import re
    head = re.sub(r'width="[^"]*"', 'width="100%"', head)
    head = re.sub(r'\sheight="[^"]*"', '', head)
    if 'role="img"' not in head:
        head += ' role="img"'
    svg_path.write_text(t[:i] + head + t[j:])
    print("wrote", svg_path)

# ----------------------------------------------------------------------
# Fig. T1 - saturation (vapour pressure) curves for N2 and O2
# ----------------------------------------------------------------------
def fig_saturation():
    T = np.linspace(70, 112, 400)
    pN = p_sat(T, **N2)
    pO = p_sat(T, **O2)
    fig, ax = plt.subplots(figsize=(8.6, 4.9))
    ax.semilogy(T, pN, color=C_N2, ls="-", label="nitrogen, N$_2$")
    ax.semilogy(T, pO, color=C_O2, ls="--", label="oxygen, O$_2$")
    ax.axhline(101.325, color=GREY, lw=0.7, ls=":")
    ax.text(70.6, 122, "atmospheric pressure, 101.325 kPa", fontsize=8.5, color=GREY)
    # anchor points at 1 atm
    ax.plot([77.4], [101.325], "o", color=C_N2, mfc="white", ms=6, mew=1.2)
    ax.annotate("77.4 K", (77.4, 101.325), textcoords="offset points",
                xytext=(-4, -16), fontsize=9, color=C_N2, ha="center")
    ax.plot([90.2], [101.325], "s", color=C_O2, mfc="white", ms=6, mew=1.2)
    ax.annotate("90.2 K", (90.2, 101.325), textcoords="offset points",
                xytext=(2, -16), fontsize=9, color=C_O2, ha="center")
    # column operating points
    ax.plot([96.4], [560], "o", color=C_N2, ms=7)
    ax.annotate("nitrogen condenses:\n96.4 K at 560 kPa (T-101 top)",
                (96.4, 560), textcoords="offset points", xytext=(8, 2),
                fontsize=9, color=C_N2)
    ax.plot([92.7], [130], "s", color=C_O2, ms=7)
    ax.annotate("oxygen boils:\n92.7 K at 130 kPa (T-102 sump)",
                (92.7, 130), textcoords="offset points", xytext=(-118, 10),
                fontsize=9, color=C_O2)
    # favourable gap arrow at p = 300 kPa between the two temperatures
    ax.annotate("", xy=(96.4, 300), xytext=(92.7, 300),
                arrowprops=dict(arrowstyle="<->", color="black", lw=0.9))
    ax.text(94.55, 330, "3.7 K in the\nfavourable direction", fontsize=8.5,
            ha="center")
    ax.set_xlim(70, 112)
    ax.set_ylim(20, 3000)
    ax.set_xlabel("Temperature, $T$ (K)")
    ax.set_ylabel("Vapour pressure, $p^*$ (kPa)")
    ax.legend(loc="lower left", frameon=False, fontsize=9.5,
              bbox_to_anchor=(0.0, 1.01), ncol=2)
    fig.tight_layout()
    save(fig, "fig-t1-saturation")

# ----------------------------------------------------------------------
# Fig. P11 - argon belly: vapour composition profile along T-102
# ----------------------------------------------------------------------
def fig_argon_belly():
    h = np.array([0.0, 0.2, 0.45, 0.7, 0.85, 1.0])
    o2 = PchipInterpolator(h, [99.0, 97.0, 90.0, 55.0, 18.0, 0.5])
    ar = PchipInterpolator(h, [0.0, 2.2, 9.0, 5.5, 1.8, 0.1])
    n2 = PchipInterpolator(h, [1.0, 0.8, 1.0, 39.5, 80.2, 99.4])
    hh = np.linspace(0, 1, 300)
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    ax.plot(o2(hh), hh, color=C_O2, ls="--", label="oxygen, O$_2$")
    ax.plot(ar(hh), hh, color=C_AR, ls="-.", label="argon, Ar")
    ax.plot(n2(hh), hh, color=C_N2, ls="-", label="nitrogen, N$_2$")
    ax.text(62, 0.30, "O$_2$", fontsize=12, color=C_O2, fontweight="bold")
    ax.text(30, 0.90, "N$_2$", fontsize=12, color=C_N2, fontweight="bold")
    ax.text(13.5, 0.30, "Ar", fontsize=12, color=C_AR, fontweight="bold")
    ax.annotate("argon maximum (belly):\n9.0 mol % Ar at the draw",
                xy=(9.0, 0.45), textcoords="offset points", xytext=(18, 26),
                fontsize=9.5, color=C_AR,
                arrowprops=dict(arrowstyle="-", color=C_AR, lw=0.8))
    # entries and the draw, in a side zone right of the composition axis
    ax.plot([100.5, 100.5], [0, 1.02], color=GREY, lw=0.6)
    feeds = [(0.96, "<", "stream 14 in: liquid N$_2$ reflux"),
             (0.62, "<", "stream 17 in: rich liquid"),
             (0.45, ">", "stream 28 out: draw to T-103"),
             (0.28, "<", "stream 9 in: expanded air"),
             (0.06, "<", "stream 29 in: T-103 bottoms return")]
    for hf, mk, lab in feeds:
        ax.plot([102], [hf], marker=mk, color="black", ms=6, clip_on=False)
        ax.text(106, hf, lab, fontsize=8.8, va="center")
    ax.text(50, 0.015, "sump: liquid O$_2$ boils (stream 18 out)",
            fontsize=8.8, ha="center")
    ax.text(3, 0.965, "top: gaseous N$_2$ out (stream 20)", fontsize=8.8)
    ax.set_xlim(0, 172)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_ylim(0, 1.02)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0],
                  ["sump", "lower", "middle", "upper", "top"])
    ax.set_xlabel("Vapour composition (mol %)")
    ax.set_ylabel("Height in T-102")
    ax.text(170, 0.03, "schematic", fontsize=8.5,
            color=GREY, ha="right", style="italic")
    fig.tight_layout()
    save(fig, "fig-p11-argon-belly")


# ----------------------------------------------------------------------
# Fig. P9 - T-x-y lenses for N2-O2 and Ar-O2 at 130 kPa (Raoult's law)
# ----------------------------------------------------------------------
def _lens(P, volatile, other):
    """Bubble and dew curves at pressure P (kPa) for a binary of the
    volatile component against the other, ideal solution, Eq. (15)."""
    xs = np.linspace(0, 1, 121)
    Tbub, Tdew = [], []
    for x in xs:
        f = lambda T: x * p_sat(T, **volatile) + (1 - x) * p_sat(T, **other) - P
        Tbub.append(brentq(f, 60, 130))
    for y in xs:
        g = lambda T: 1.0 / (y / p_sat(T, **volatile) + (1 - y) / p_sat(T, **other)) - P
        Tdew.append(brentq(g, 60, 130))
    return xs, np.array(Tbub), np.array(Tdew)

def fig_txy():
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.6), sharey=True)
    # (a) N2-O2
    ax = axes[0]
    xs, Tb, Td = _lens(130.0, N2, O2)
    ax.plot(xs, Tb, color=C_N2, ls="-")
    ax.plot(xs, Td, color=C_N2, ls="--")
    ax.text(0.03, 80.6, "bubble curve\n(liquid)", fontsize=8.8, color=C_N2)
    ax.text(0.60, 89.6, "dew curve (vapour)", fontsize=8.8, color=C_N2)
    # one equilibrium contact at liquid x = 0.40
    x0 = 0.40
    T0 = brentq(lambda T: x0 * p_sat(T, **N2) + (1 - x0) * p_sat(T, **O2) - 130.0, 60, 130)
    y0 = x0 * p_sat(T0, **N2) / 130.0
    ax.plot([x0, y0], [T0, T0], color="black", lw=0.9)
    ax.plot([x0], [T0], "o", color="black", ms=5)
    ax.plot([y0], [T0], "o", color="black", mfc="white", ms=5)
    ax.annotate(f"liquid $x$ = 0.40", (x0, T0), textcoords="offset points",
                xytext=(-64, -14), fontsize=8.8)
    ax.annotate(f"vapour $y$ = {y0:.2f}", (y0, T0), textcoords="offset points",
                xytext=(4, 5), fontsize=8.8)
    ax.annotate("one equilibrium\ncontact", xy=((x0 + y0) / 2, T0),
                textcoords="offset points", xytext=(-6, 14), fontsize=8.8,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.set_xlabel("Mole fraction of nitrogen, $x$ (liquid) and $y$ (vapour)")
    ax.set_ylabel("Temperature, $T$ (K)")
    ax.set_title("(a) nitrogen–oxygen, $\\alpha \\approx 3.6$ at 90 K",
                 fontsize=10, loc="left")
    ax.set_xlim(0, 1)
    # (b) Ar-O2
    ax = axes[1]
    xs, Tb, Td = _lens(130.0, AR, O2)
    ax.plot(xs, Tb, color=C_AR, ls="-")
    ax.plot(xs, Td, color=C_AR, ls="--")
    ax.text(0.05, 90.6, "bubble", fontsize=8.8, color=C_AR)
    ax.text(0.55, 92.0, "dew", fontsize=8.8, color=C_AR)
    ax.set_xlabel("Mole fraction of argon, $x$ (liquid) and $y$ (vapour)")
    ax.set_title("(b) argon–oxygen, $\\alpha \\approx 1.34$ at 90 K",
                 fontsize=10, loc="left")
    ax.set_xlim(0, 1)
    axes[0].set_ylim(78, 95)
    fig.tight_layout()
    save(fig, "fig-p9-txy")

# ----------------------------------------------------------------------
# Fig. P6 - main heat exchanger temperature profiles (schematic)
# ----------------------------------------------------------------------
def fig_mhe_profiles():
    x = np.linspace(0, 1, 200)          # 0 = cold end, 1 = warm end
    hot = 102 + 191 * x ** 1.5          # feed air, stream 5 -> 6
    cold = 84 + 206 * x ** 1.8          # products composite, 18-20 -> 21-23
    fig, ax = plt.subplots(figsize=(8.6, 4.9))
    ax.plot(x, hot, color=C_O2, ls="--")
    ax.plot(x, cold, color=C_N2, ls="-")
    ax.text(0.52, 198, "feed air, stream 5 → stream 6", fontsize=10, color=C_O2)
    ax.text(0.33, 96, "cold products, streams 18–20 → 21–23", fontsize=10, color=C_N2)
    ax.text(0.03, 282, "warm-end approach $\\approx$ 3 K:\n293 K against 290 K", fontsize=9.5)
    ax.annotate("air in (stream 5): 293 K", xy=(1, 293),
                textcoords="offset points", xytext=(-132, 12), fontsize=9.5)
    ax.annotate("products out (streams 21–23): 290 K", xy=(1, 290),
                textcoords="offset points", xytext=(-200, -20), fontsize=9.5)
    ax.annotate("air out (stream 6): 102 K, then divides:\n800 kmol/h (stream 7) to T-101,\n200 kmol/h (stream 8) to turbine X-101",
                xy=(0, 102), textcoords="offset points", xytext=(8, 14), fontsize=9.5)
    ax.annotate("cold products in (streams 18–20): 84 K\n(flow-weighted mean of 94, 82 and 81 K)",
                xy=(0, 84), textcoords="offset points", xytext=(6, -28), fontsize=9.5)
    ax.set_xlim(-0.02, 1.06)
    ax.set_ylim(60, 320)
    ax.set_xticks([0, 0.5, 1.0], ["cold end", "middle", "warm end"])
    ax.set_xlabel("Position along E-102")
    ax.set_ylabel("Temperature, $T$ (K)")
    ax.text(0.985, 0.03, "schematic", transform=ax.transAxes, fontsize=8.5,
            color=GREY, ha="right", style="italic")
    fig.tight_layout()
    save(fig, "fig-p6-mhe-profiles")

# ----------------------------------------------------------------------
# Fig. P4 - molecular sieve unit: layered bed cross-section + cycle
# ----------------------------------------------------------------------
def _vessel(ax, x0, w, y0, h, regen):
    # shell
    ax.add_patch(Rectangle((x0, y0), w, h, fill=False, lw=1.2, color="black"))
    ax.add_patch(Ellipse((x0 + w / 2, y0 + h), w, 0.36, fill=False, lw=1.2, color="black"))
    ax.add_patch(Ellipse((x0 + w / 2, y0), w, 0.36, fill=False, lw=1.2, color="black"))
    # layers: alumina below (first in flow), 13X above; support grid at base
    ax.add_patch(Rectangle((x0 + 0.04, y0 + 0.10), w - 0.08, 0.16,
                           facecolor="#dddddd", edgecolor="black", lw=0.6))
    ax.add_patch(Rectangle((x0 + 0.04, y0 + 0.26), w - 0.08, h * 0.36,
                           facecolor="#E69F00", alpha=0.45, edgecolor="black", lw=0.6))
    ax.add_patch(Rectangle((x0 + 0.04, y0 + 0.26 + h * 0.36), w - 0.08, h * 0.40,
                           facecolor="#56B4E9", alpha=0.55, edgecolor="black", lw=0.6))
    return

def fig_sieve():
    fig, ax = plt.subplots(figsize=(8.6, 5.9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.6)
    ax.axis("off")
    y0, h, w = 3.0, 3.4, 1.7
    # Vessel A (adsorbing): air up from the bottom
    _vessel(ax, 1.1, w, y0, h, regen=False)
    ax.annotate("", xy=(1.95, y0 - 0.05), xytext=(1.95, y0 - 0.75),
                arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text(1.02, y0 - 0.42, "air in\n(stream 4)", ha="right", va="center", fontsize=9.5)
    ax.annotate("", xy=(1.95, y0 + h + 0.85), xytext=(1.95, y0 + h + 0.18),
                arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text(1.95, y0 + h + 0.95, "purified air out (stream 5)", ha="center", fontsize=9.5)
    ax.text(1.95, y0 - 1.08, "vessel A: adsorbing", ha="center", fontsize=10, fontweight="bold")
    # layer labels with leaders (right of vessel A)
    ax.annotate("zeolite 13X layer:\nremoves carbon dioxide", xy=(2.84, y0 + 0.26 + h * 0.56),
                xytext=(3.15, y0 + 2.6), fontsize=9.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.annotate("activated alumina layer:\nremoves water vapour", xy=(2.84, y0 + 0.26 + h * 0.18),
                xytext=(3.15, y0 + 1.5), fontsize=9.5,
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.annotate("support grid", xy=(2.84, y0 + 0.18), xytext=(3.15, y0 + 0.55),
                fontsize=9.5, arrowprops=dict(arrowstyle="-", lw=0.7))
    # Vessel B (regenerating): heated waste nitrogen down from the top
    _vessel(ax, 6.6, w, y0, h, regen=True)
    ax.annotate("", xy=(7.45, y0 + h + 0.18), xytext=(7.45, y0 + h + 0.85),
                arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text(7.45, y0 + h + 0.95, "heated waste nitrogen in", ha="center", fontsize=9.5)
    ax.annotate("", xy=(7.45, y0 - 0.75), xytext=(7.45, y0 - 0.05),
                arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text(8.42, y0 - 0.42, "to vent", ha="left", va="center", fontsize=9.5)
    ax.text(7.45, y0 - 1.08, "vessel B: regenerating", ha="center", fontsize=10, fontweight="bold")
    # cycle strip
    ax.text(0.2, 1.58, "one switchover cycle (on-line period 4–10 h per vessel):", fontsize=9.5)
    for row, (lab, first) in enumerate([("A", "adsorb"), ("B", "regen")]):
        yy = 1.14 - row * 0.52
        ax.text(0.2, yy + 0.13, f"vessel {lab}", fontsize=9.5, va="center")
        for k in range(2):
            is_ads = (first == "adsorb") == (k == 0)
            ax.add_patch(Rectangle((1.6 + k * 3.9, yy), 3.9, 0.42,
                                   facecolor="#56B4E9" if is_ads else "#dddddd",
                                   edgecolor="black", lw=0.7))
            ax.text(1.6 + k * 3.9 + 1.95, yy + 0.21,
                    "adsorbing" if is_ads else "regenerating",
                    ha="center", va="center", fontsize=9.5)
    ax.annotate("", xy=(9.6, 0.24), xytext=(1.6, 0.24),
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(9.6, 0.02, "time", fontsize=9, ha="right")
    fig.tight_layout()
    save(fig, "fig-p4-sieve")

# ----------------------------------------------------------------------
# Fig. P7 - turbine versus valve expansion on a T-s schematic for air
# ----------------------------------------------------------------------
def fig_ts():
    fig, ax = plt.subplots(figsize=(8.6, 4.9))
    # schematic vapour dome for air, closed at the critical point
    # (132.6 K); both boundaries meet at s = 3.9 (schematic scale)
    T_ctl = np.array([78, 88, 98, 108, 120, 132.6])
    s_liq = PchipInterpolator(T_ctl, [1.9, 2.2, 2.5, 2.85, 3.3, 3.9])
    s_vap = PchipInterpolator(T_ctl, [5.9, 5.02, 4.86, 4.68, 4.32, 3.9])
    T_dome = np.linspace(78, 132.6, 200)
    ax.plot(s_liq(T_dome), T_dome, color=GREY, lw=1.1)
    ax.plot(s_vap(T_dome), T_dome, color=GREY, lw=1.1)
    ax.plot([3.9], [132.6], "o", color=GREY, ms=4)
    ax.text(1.55, 96, "liquid", fontsize=9.5, color=GREY, ha="center")
    ax.text(3.45, 118, "liquid + vapour", fontsize=9.5, color=GREY, ha="center")
    ax.text(8.1, 118, "vapour", fontsize=9.5, color=GREY, ha="center")
    ax.text(3.9, 136.5, "critical point of air, $\\approx$ 132.6 K", fontsize=8.8,
            color=GREY, ha="center")
    # state A: stream 8, 102 K, 568 kPa, just right of the vapour boundary
    # (the cooled air is approximately at its dew point, Process text)
    sA = 5.05
    ax.plot([sA], [102], "o", color="black", ms=6)
    ax.annotate("stream 8: 102 K, 568 kPa", xy=(sA, 102),
                textcoords="offset points", xytext=(-158, 6), fontsize=9.5)
    # isentropic limit: vertical to 84 K, where the path reaches the
    # vapour boundary (dew point at 138 kPa, 84.4 K by equation of
    # state) and condensation would begin
    ax.plot([sA, sA], [102, 84], color=GREY, lw=1.0, ls=":")
    ax.plot([sA], [84], "o", color=GREY, ms=5, mfc="white")
    ax.annotate("isentropic limit: 84 K\n(reversible path reaches\nthe vapour boundary)",
                xy=(sA, 84), textcoords="offset points", xytext=(-158, -6),
                fontsize=9.5, color=GREY)
    # actual turbine path: entropy rises, outlet is stream 9 at 91 K
    sB = sA + 0.35
    ax.annotate("", xy=(sB, 91.6), xytext=(sA, 101.4),
                arrowprops=dict(arrowstyle="->", lw=1.4, color=C_N2))
    ax.plot([sB], [91], "o", color=C_N2, ms=6)
    ax.annotate("stream 9: 91 K, 138 kPa\nturbine X-101:\nwork leaves with the shaft",
                xy=(sB, 91), textcoords="offset points", xytext=(16, -38),
                fontsize=9.5, color=C_N2)
    # isenthalpic throttling: to 94 K at larger s (equation of state;
    # at 102 K the Joule-Thomson effect is far stronger than at
    # ordinary temperatures)
    sC = sA + 0.85
    ax.plot([sA, sA + 0.3, sC], [102, 97.5, 94.0], color=C_O2, ls="--", lw=1.3)
    ax.plot([sC], [94.0], "s", color=C_O2, ms=6)
    ax.annotate("valve (isenthalpic): 94 K, 138 kPa\nno work recovered",
                xy=(sC, 94.0), textcoords="offset points", xytext=(12, -16),
                fontsize=9.5, color=C_O2)
    # work area between the turbine and valve paths
    ax.fill([sA, sB, sC], [102, 91, 94.0], color=C_N2, alpha=0.10, lw=0)
    ax.text(sA + 0.30, 98.5, "work\nrecovered", fontsize=8.8, color=C_N2, ha="center")
    ax.set_xlim(1.2, 8.6)
    ax.set_ylim(78, 142)
    ax.set_xticks([])
    ax.set_xlabel("Specific entropy, $s$ (kJ/(kg K)) — schematic scale")
    ax.set_ylabel("Temperature, $T$ (K)")
    ax.text(0.985, 0.03, "schematic", transform=ax.transAxes, fontsize=8.5,
            color=GREY, ha="right", style="italic")
    fig.tight_layout()
    save(fig, "fig-p7-ts")

if __name__ == "__main__":
    fig_saturation()
    fig_argon_belly()
    fig_txy()
    fig_mhe_profiles()
    fig_sieve()
    fig_ts()
