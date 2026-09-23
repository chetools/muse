"""Matplotlib visualizations for the Couette app (kept importable for testing)."""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = "DejaVu Sans"

from couette import physics as P  # noqa: E402


def vector_field_figure(R1, R2, N1, N2, w1, w2, R1_mm, R2_mm,
                        n_rings=4, n_theta=24):
    """Cross-section (top view) of the annulus with tangential velocity arrows.

    Arrow length is proportional to local speed; the longest arrow is capped at
    55% of the tightest grid spacing so arrows cannot overlap each other.
    Returns the matplotlib Figure (caller closes it).
    """
    rr = np.linspace(R1, R2, n_rings + 2)[1:-1]      # interior rings
    th = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    Rg, Tg = np.meshgrid(rr, th)
    X, Y = Rg * np.cos(Tg), Rg * np.sin(Tg)
    vv = P.tangential_velocity(Rg, R1, R2, w1, w2)
    vmax = float(np.max(np.abs(vv)))
    sgn = np.sign(vv)
    U = -np.sin(Tg) * sgn
    V = np.cos(Tg) * sgn
    dr = (R2 - R1) / (n_rings + 1)
    arc_min = rr[0] * (2 * np.pi / n_theta)
    Lmax = 0.55 * min(dr, arc_min)
    L = Lmax * np.abs(vv) / vmax if vmax > 0 else np.zeros_like(vv)

    fig, ax = plt.subplots(figsize=(6.4, 6.4), dpi=130)
    ax.set_aspect("equal")
    ax.set_xlim(-1.15 * R2, 1.15 * R2)
    ax.set_ylim(-1.15 * R2, 1.15 * R2)
    ax.axis("off")
    ax.add_patch(plt.Circle((0, 0), R2, color="#dbe7f3", zorder=0))
    ax.add_patch(plt.Circle((0, 0), R1, color="white", zorder=1))
    ax.add_patch(plt.Circle((0, 0), R2, fill=False, ec="#1f3a5f", lw=2.5, zorder=4))
    ax.add_patch(plt.Circle((0, 0), R1, fill=False, ec="#1f3a5f", lw=2.5, zorder=4))
    ax.quiver(X, Y, U * L, V * L, np.abs(vv), cmap="viridis",
              scale=1.0, scale_units="xy", width=0.012 * R2,
              headwidth=4.2, headlength=5.0, zorder=3)
    cb = fig.colorbar(
        plt.cm.ScalarMappable(norm=plt.Normalize(0, vmax), cmap="viridis"),
        ax=ax, shrink=0.75, pad=0.02)
    cb.set_label("|vθ| [m/s]")
    ax.text(0, 0, f"R₁={R1_mm:g} mm\n{N1:g} rpm", ha="center", va="center",
            fontsize=10, color="#1f3a5f", zorder=5)
    ax.text(0, -1.08 * R2, f"R₂={R2_mm:g} mm, {N2:g} rpm",
            ha="center", va="top", fontsize=10, color="#1f3a5f")
    ax.set_title("Cross-section: velocity vector field (top view)",
                 fontsize=13, pad=12)
    return fig
