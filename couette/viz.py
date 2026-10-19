"""Matplotlib visualizations for the Couette app (kept importable for testing).

Symbols, defined before use (SI units):
    R1: inner cylinder radius [m]; R2: outer cylinder radius [m]
    w1, w2: angular velocities of the inner and outer cylinders [rad/s]
    N1, N2: the same rotation rates as entered by the user [rpm]
    n_rings: number of interior rings of arrows; n_theta: arrows per ring
"""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = "DejaVu Sans"

from couette import physics as P  # noqa: E402


def vector_field_figure(R1, R2, N1, N2, w1, w2, R1_mm, R2_mm,
                        n_rings=4, n_theta=24, arrow_frac=0.55):
    """Cross-section (top view) of the annulus with tangential velocity arrows.

    Arrow length is proportional to local speed; the longest arrow is capped at
    arrow_frac (default 0.55) of the tightest grid spacing so arrows cannot
    overlap each other. Larger fractions give bolder, more visible arrows;
    inspect the rendered figure and tune per use.
    Returns the matplotlib Figure (caller closes it).

    Grid construction, step by step (shapes annotated; with the defaults
    every 2-D array below has shape (n_theta, n_rings) = (24, 4)):
    """
    # Ring radii: n_rings + 2 points spanning [R1, R2], dropping the two
    # endpoints (the walls themselves carry no arrows) -> shape (n_rings,).
    # Physically these are the radii of the concentric fluid shells sampled.
    rr = np.linspace(R1, R2, n_rings + 2)[1:-1]      # interior rings
    # Azimuthal stations around each ring, endpoint excluded so the
    # 2*pi station does not duplicate 0 -> shape (n_theta,).
    th = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    # Polar grid: Rg[i, j] is the radius and Tg[i, j] the angle of arrow
    # station (i, j).  meshgrid pairs every angle with every radius, so
    # both outputs have shape (n_theta, n_rings).
    Rg, Tg = np.meshgrid(rr, th)
    # Polar-to-cartesian conversion, element-wise on the (n_theta, n_rings)
    # grid: X and Y are the arrow base positions [m] in the cross-section.
    X, Y = Rg * np.cos(Tg), Rg * np.sin(Tg)
    # Tangential velocity at each station [m/s], shape (n_theta, n_rings):
    # P.tangential_velocity broadcasts over the grid, one value per radius.
    vv = P.tangential_velocity(Rg, R1, R2, w1, w2)
    vmax = float(np.max(np.abs(vv)))
    # Sign of the local rotation (+1 counter-clockwise, -1 clockwise,
    # 0 where the fluid is instantaneously at rest), same shape as vv.
    sgn = np.sign(vv)
    # Unit direction of the local velocity: the tangent to the circle is
    # (-sin(theta), cos(theta)) for counter-clockwise motion; multiplying
    # by sgn flips it where the fluid runs clockwise.  U, V are
    # dimensionless, shape (n_theta, n_rings).
    U = -np.sin(Tg) * sgn
    V = np.cos(Tg) * sgn
    # Tightest grid spacing [m]: radial gap between neighbouring rings
    # (dr) versus arc length between neighbouring stations on the
    # innermost ring (arc_min).  Capping the longest arrow at arrow_frac
    # of the smaller keeps every arrow shorter than the distance to its
    # neighbours, so arrows cannot overlap.
    dr = (R2 - R1) / (n_rings + 1)
    arc_min = rr[0] * (2 * np.pi / n_theta)
    Lmax = arrow_frac * min(dr, arc_min)
    # Arrow length per station [m], shape (n_theta, n_rings): proportional
    # to the local speed, normalized by the maximum so the fastest fluid
    # gets exactly Lmax.  The vmax > 0 guard avoids division by zero when
    # both cylinders are stationary (then every arrow has zero length).
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
    # Quiver: (X, Y) bases, (U*L, V*L) arrow vectors [m]; colour encodes
    # |v_theta| [m/s] on the viridis sequential scale (readable in
    # grayscale), so speed is double-encoded as length and colour.
    # scale_units="xy" with scale=1.0 makes one data unit equal one arrow
    # unit: arrow lengths are true to the metre scale of the axes.
    # Dark edges on every arrow: viridis's bright-yellow top end is nearly
    # invisible against the pale-blue annulus fill, so each arrow carries a
    # thin dark-navy edge (the figure's structure colour) for contrast.
    # One shared normalization for arrows and colorbar: quiver would otherwise
    # autoscale its colours to the arrow data range [min|vv|, vmax], so the
    # darkest arrow would wear the colour the bar labels 0 m/s.
    cnorm = plt.Normalize(0, vmax)
    ax.quiver(X, Y, U * L, V * L, np.abs(vv), cmap="viridis", norm=cnorm,
              scale=1.0, scale_units="xy", width=0.012 * R2,
              headwidth=4.2, headlength=5.0, zorder=3,
              edgecolor="#1f3a5f", linewidth=0.3)
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=cnorm, cmap="viridis"),
                      ax=ax, shrink=0.75, pad=0.02)
    cb.set_label("|vθ| [m/s]")
    ax.text(0, 0, f"R₁={R1_mm:g} mm\n{N1:g} rpm", ha="center", va="center",
            fontsize=10, color="#1f3a5f", zorder=5)
    ax.text(0, -1.08 * R2, f"R₂={R2_mm:g} mm, {N2:g} rpm",
            ha="center", va="top", fontsize=10, color="#1f3a5f")
    return fig
