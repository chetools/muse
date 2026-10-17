# /// script
# dependencies = ["numpy", "matplotlib", "plotly"]
# ///

"""Couette flow: the computation, step by step.

An editable companion to the Couette flow Streamlit app. Each cell performs
one transformation of the computation and displays its intermediate result,
so every array shape and every physical assumption stays visible. Written
for chemical engineers: the prose explains what each operation means
physically, not just what it does in code.

Run on MoLab (signed in) via the self-contained generated variant
couette/notebook/code_walkthrough_molab.py (physics inlined by
couette/notebook/build_wasm_inline.py --molab), because the MoLab GitHub
mirror serves a single file with no repository checkout. The single-file
WASM export likewise carries the physics module inlined by
couette/notebook/build_wasm_inline.py, because sibling imports
do not resolve in single-file WASM builds. This source variant imports
the `couette` package from the repository and is for local development.
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import math
    import sys
    from pathlib import Path
    import numpy as np
    import plotly.graph_objects as go
    import matplotlib.pyplot as plt
    """Steady laminar Newtonian Couette flow between concentric cylinders.

    Symbols, defined before use (SI units):
        R1: inner cylinder radius [m]
        R2: outer cylinder radius [m]
        w1: angular velocity of the inner cylinder [rad/s]
        w2: angular velocity of the outer cylinder [rad/s]
        mu: dynamic viscosity of the fluid [Pa.s]
        r: radial coordinate, R1 <= r <= R2 [m]
        omega(r): angular velocity of the fluid at radius r [rad/s]
        v_theta(r): azimuthal (tangential) velocity of the fluid at r [m/s]
        tau(r): shear stress, r-theta component, at radius r [Pa]
        gamma_dot(r): shear rate at radius r [1/s]
        T/L: torque per unit axial length exerted by the inner cylinder on the
            fluid [N.m/m]
        A, B: integration constants in omega(r) = A + B / r**2;
            A in [rad/s], B in [rad.m^2/s]

    The velocity field is derived from a torque balance alone — no Navier-Stokes
    equations are invoked:

    1. In steady rotation no cylindrical shell of fluid can accumulate angular
       momentum, so the torque transmitted across every r = const surface is the
       same value M.  With wall area 2*pi*r*L and lever arm r:

           tau(r) = M / (2*pi*L*r**2)

    2. The shear rate between neighbouring shells rotating at omega(r) is found
       geometrically: in time dt the shell at r+dr slides past the shell at r by
       r*d(omega)*dt over the radial separation dr, so

           gamma_dot = r * d(omega)/dr = dv_theta/dr - v_theta/r

       (rigid-body rotation, d(omega) = 0, produces no shear, as it must not).

    3. Newton's law of viscosity, tau = mu * gamma_dot, is the single constitutive
       assumption.  Together with (1):

           r * d(omega)/dr = M / (2*pi*mu*L*r**2)

       which integrates to  omega(r) = A + B / r**2.  No-slip at the walls,
       omega(R1) = w1 and omega(R2) = w2, fixes A and B:

           A = (w2*R2**2 - w1*R1**2) / (R2**2 - R1**2)
           B = R1**2 * R2**2 * (w1 - w2) / (R2**2 - R1**2)

       Physical reading: A is the solid-body-rotation part (the whole fluid
       turning together at A rad/s carries no shear); B is the
       differential-rotation part (B = 0 means no shear anywhere, because then
       gamma_dot = -2*B/r**2 = 0).

    Sign convention: tau_rtheta is positive when, on the outward (+r) face of a
    fluid element, it pulls the fluid in the +theta direction.  The torque per
    unit length T/L reported here is the torque the inner cylinder must exert on
    the fluid (positive when driving it in the +theta sense); the shear stress is
    then  tau(r) = -(T/L) / (2*pi*r**2).

    Array-shape convention used by every profile function below: the radius
    argument r may be a scalar or a numpy array of shape (n,) holding n radial
    positions [m]; the returned array has the same shape (n,) with one value per
    input radius.  Scalar parameters (R1, R2, w1, w2, mu) broadcast against r
    in the usual numpy way, so each output element depends only on the
    corresponding input radius.
    """




    def validate(R1, R2, w1, w2, mu):
        """Check inputs; raise ValueError with a plain message on bad input.

        Physical meaning of the checks: the annulus geometry requires a
        positive inner radius (R1 > 0) and an outer radius strictly outside
        it (R2 > R1); a real (Newtonian) fluid has positive dynamic viscosity
        (mu > 0).  Rotation rates w1, w2 may be zero, positive
        (counter-clockwise seen from above) or negative (clockwise).
        All inputs are scalars here; finiteness is checked element-wise so a
        NaN or inf can never silently propagate into a profile.
        """
        for name, val in (("R1", R1), ("R2", R2), ("mu", mu)):
            if not np.isfinite(val):
                raise ValueError(f"{name} must be a finite number, got {val!r}.")
        for name, val in (("w1", w1), ("w2", w2)):
            if not np.isfinite(val):
                raise ValueError(f"{name} must be a finite number, got {val!r}.")
        if R1 <= 0:
            raise ValueError(f"Inner radius R1 must be positive, got {R1}.")
        if R2 <= R1:
            raise ValueError(f"Outer radius R2 ({R2}) must exceed inner radius R1 ({R1}).")
        if mu <= 0:
            raise ValueError(f"Viscosity mu must be positive, got {mu}.")


    def coefficients(R1, R2, w1, w2):
        """Return (A, B) with omega(r) = A + B / r**2.  Inputs validated.

        A [rad/s] and B [rad.m^2/s] are scalars fixed by the no-slip boundary
        conditions omega(R1) = w1 and omega(R2) = w2: the fluid layer touching
        each wall moves with that wall.  Solving those two linear equations
        for A and B gives the expressions evaluated below.
        """
        validate(R1, R2, w1, w2, mu=1.0)
        den = R2**2 - R1**2
        A = (w2 * R2**2 - w1 * R1**2) / den
        B = R1**2 * R2**2 * (w1 - w2) / den
        return A, B


    def _check_r(r, R1, R2):
        # Accept a scalar or an array of shape (n,); return a float array of
        # shape (n,) (0-d for scalar input).  Every element must lie inside
        # the annulus [R1, R2]: evaluating outside the fluid domain is a
        # caller error, and failing loudly here beats returning nonsense.
        r = np.asarray(r, dtype=float)
        if np.any(r < R1) or np.any(r > R2):
            raise ValueError("Evaluation radius r must lie inside the annulus [R1, R2].")
        return r


    def angular_velocity(r, R1, R2, w1, w2):
        """Angular velocity omega(r) [rad/s] of the fluid.

        r: scalar or array of shape (n,) [m]; returns same shape [rad/s].
        Each output element is A + B / r_i**2 for the corresponding input
        radius r_i: the 1/r**2 term is the differential-rotation part, so
        the fluid shears most where r is smallest (near the inner wall).
        """
        A, B = coefficients(R1, R2, w1, w2)
        r = _check_r(r, R1, R2)
        return A + B / r**2


    def tangential_velocity(r, R1, R2, w1, w2):
        """Azimuthal velocity v_theta(r) = r * omega(r) [m/s].

        r: scalar or array of shape (n,) [m]; returns same shape [m/s].
        Multiplication by r converts angular velocity [rad/s] to the linear
        speed of the fluid at that radius — the quantity a probe fixed in the
        laboratory would measure.
        """
        r = _check_r(np.asarray(r, dtype=float), R1, R2)
        return r * angular_velocity(r, R1, R2, w1, w2)


    def shear_rate(r, R1, R2, w1, w2):
        """Shear rate gamma_dot(r) = r * d(omega)/dr [1/s] (signed).

        r: scalar or array of shape (n,) [m]; returns same shape [1/s].
        Differentiating omega(r) = A + B/r**2 gives d(omega)/dr = -2*B/r**3,
        and multiplying by r yields -2*B/r**2: the shear rate falls as
        1/r**2, strongest at the inner wall.  The sign follows the sign of
        (w2 - w1): shearing one way when the inner cylinder outruns the
        outer, the other way for counter-rotation.
        """
        _, B = coefficients(R1, R2, w1, w2)
        r = _check_r(r, R1, R2)
        return -2.0 * B / r**2


    def torque_per_length(R1, R2, w1, w2, mu):
        """Torque per unit axial length [N.m/m] the inner cylinder exerts on the
        fluid.  Positive when driving the fluid in the +theta sense (w1 > w2).

        All inputs scalar; returns a scalar.  From the torque balance,
        tau(r) = -(T/L)/(2*pi*r**2), and Newton's law at the inner wall,
        tau(R1) = mu * gamma_dot(R1) = mu * (-2*B/R1**2); eliminating
        tau(R1) gives T/L = 4*pi*mu*B.  Torque is therefore proportional to
        viscosity and to the differential-rotation constant B: no relative
        rotation (B = 0) means no torque, as expected.
        """
        validate(R1, R2, w1, w2, mu)
        _, B = coefficients(R1, R2, w1, w2)
        return 4.0 * math.pi * mu * B


    def shear_stress(r, R1, R2, w1, w2, mu):
        """Shear stress tau_rtheta(r) [Pa] (signed; see module docstring).

        r: scalar or array of shape (n,) [m]; returns same shape [Pa].
        Falls as 1/r**2 — a direct consequence of the torque balance,
        independent of the velocity profile details: the same torque crosses
        every cylindrical shell, but the shell area grows with r, so the
        stress (torque per area per lever arm) must decay as 1/r**2.
        """
        validate(R1, R2, w1, w2, mu)
        r = _check_r(r, R1, R2)
        return -torque_per_length(R1, R2, w1, w2, mu) / (2.0 * math.pi * r**2)


    def rpm_to_rad_s(n_rpm):
        """Convert revolutions per minute to rad/s (sign preserved).

        n_rpm: scalar or array of shape (n,) [rpm]; returns same shape
        [rad/s].  One revolution is 2*pi radians and one minute is 60 s, so
        the factor is 2*pi/60; the sign is preserved so negative rpm
        (clockwise) stays negative in rad/s.
        """
        return np.asarray(n_rpm, dtype=float) * 2.0 * math.pi / 60.0
    import types as _types
    P = _types.SimpleNamespace(
        _check_r=_check_r,
        angular_velocity=angular_velocity,
        coefficients=coefficients,
        rpm_to_rad_s=rpm_to_rad_s,
        shear_rate=shear_rate,
        shear_stress=shear_stress,
        tangential_velocity=tangential_velocity,
        torque_per_length=torque_per_length,
        validate=validate,
    )
    return P, go, math, mo, np, plt


@app.cell
def _(mo):
    mo.md(r"""
    # Couette flow: the computation, step by step

    Companion to the Couette flow app. Each cell below performs **one**
    transformation and displays its intermediate result, so the focus
    stays on the calculation and how it breaks down. To experiment, edit
    an input value in the inputs cell and re-run: every downstream cell
    recomputes.

    To run: after the page finishes loading, execute all cells once via
    the command palette ("Re-run all cells") — cells do not run on load
    by themselves.

    Symbols, defined before use (SI units):

    - $R_1$: inner cylinder radius [m]; $R_2$: outer cylinder radius [m]
    - $w_1$, $w_2$: angular velocities of the inner and outer cylinders [rad/s]
    - $\mu$: dynamic viscosity of the fluid [Pa·s]
    - $r$: radial coordinate, $R_1 \le r \le R_2$ [m]
    - $\omega(r)$: angular velocity of the fluid at radius $r$ [rad/s]
    - $v_\theta(r)$: azimuthal (tangential) velocity of the fluid at $r$ [m/s]
    - $\tau(r)$: shear stress (r–theta component) at radius $r$ [Pa]
    - $\dot{\gamma}(r)$: shear rate at radius $r$ [1/s]
    - $T/L$: torque per unit axial length the inner cylinder exerts on the
      fluid [N·m/m]
    - $A$, $B$: constants in $\omega(r) = A + B/r^2$;
      $A$ in [rad/s], $B$ in [rad·m²/s]
    """)
    return


@app.cell
def _():
    # Inputs, exactly as entered in the app (millimetres, rpm, mPa·s).
    # No widgets: the focus stays on the calculation. To experiment,
    # edit a value and re-run — every downstream cell recomputes.
    R1_mm = 50.0    # inner radius [mm]
    R2_mm = 100.0   # outer radius [mm]
    N1 = 60.0       # inner cylinder speed [rpm]; negative = clockwise
    N2 = 0.0        # outer cylinder speed [rpm]
    mu_mPas = 1.0   # dynamic viscosity [mPa·s]; water at 20 °C
    return R1_mm, R2_mm, N1, N2, mu_mPas


@app.cell
def _(P, mo, R1_mm, R2_mm, N1, N2, mu_mPas):
    # Unit conversion, one line per quantity: the physics is done in SI
    # (metres, rad/s, Pa·s). rpm_to_rad_s preserves the sign, so negative
    # rpm stays clockwise.
    R1 = R1_mm / 1000.0
    R2 = R2_mm / 1000.0
    mu = mu_mPas / 1000.0
    w1 = float(P.rpm_to_rad_s(N1))
    w2 = float(P.rpm_to_rad_s(N2))
    # Geometry guard: an annulus needs 0 < R1 < R2 (and finite, positive
    # viscosity). Raises ValueError with a plain message otherwise.
    P.validate(R1, R2, w1, w2, mu)
    mo.md(
        f"R1 = {R1} m, R2 = {R2} m, mu = {mu} Pa·s, "
        f"w1 = {w1:.4f} rad/s, w2 = {w2:.4f} rad/s"
    )
    return R1, R2, mu, w1, w2


@app.cell
def _(P, R1, R2, mo, w1, w2):
    # The no-slip boundary conditions (fluid at each wall moves with that
    # wall) fix the two constants in omega(r) = A + B/r**2. A is the
    # solid-body-rotation part [rad/s]; B is the differential-rotation part
    # [rad·m²/s] — B = 0 would mean no shear anywhere.
    A = (w2 * R2**2 - w1 * R1**2) / (R2**2 - R1**2)
    B = R1**2 * R2**2 * (w1 - w2) / (R2**2 - R1**2)
    A_pkg, B_pkg = P.coefficients(R1, R2, w1, w2)
    assert abs(A - A_pkg) < 1e-12 and abs(B - B_pkg) < 1e-12
    mo.md(
        r"""
        $\omega(r) = A + B/r^2$ with
        """
        f"$A = {A:.6f}$ rad/s, $B = {B:.6f}$ rad·m²/s "
        "(identical to the package values)."
    )
    return A, B


@app.cell
def _(R1, R2, mo, np):
    # Radial grid: 400 points spanning the annulus [R1, R2] -> shape (400,).
    # Every profile below is evaluated on this one grid, so each output
    # array also has shape (400,) with element i belonging to radius r[i].
    r = np.linspace(R1, R2, 400)
    mo.md(f"Grid: {r.shape[0]} points from r = {r[0]:.4f} m to r = {r[-1]:.4f} m")
    return (r,)


@app.cell
def _(A, B, P, R1, R2, mo, np, r, w1, w2):
    # omega(r) = A + B / r**2, evaluated element-wise on the (400,) grid.
    # The division and addition broadcast the scalars A and B against the
    # array r: output element i is A + B / r[i]**2.
    om = A + B / r**2
    # No-slip self-check: the fluid at each wall must move with that wall.
    assert abs(om[0] - w1) < 1e-9 and abs(om[-1] - w2) < 1e-9
    om_pkg = P.angular_velocity(r, R1, R2, w1, w2)
    assert np.allclose(om, om_pkg, rtol=1e-12)
    mo.md(
        f"omega shape {om.shape}: {om[0]:.4f} rad/s at the inner wall, "
        f"{om[-1]:.4f} rad/s at the outer wall (no-slip holds, matches package)."
    )
    return (om,)


@app.cell
def _(P, R1, R2, go, np, om, r, w1, w2):
    # Tangential velocity v_theta = r * omega(r): element-wise product of the
    # (400,) radius grid with the (400,) angular-velocity array. Multiplying
    # by r converts [rad/s] to the linear speed [m/s] a stationary probe
    # would measure.
    v = r * om
    v_pkg = P.tangential_velocity(r, R1, R2, w1, w2)
    assert np.allclose(v, v_pkg, rtol=1e-12)
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=r * 1000, y=v, mode="lines", name="v(r)",
                               line=dict(width=3)))
    fig_v.update_layout(title="Azimuthal velocity profile",
                        xaxis_title="r [mm]", yaxis_title="v [m/s]",
                        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
                        height=420, margin=dict(l=10, r=130, t=50, b=10))
    fig_v
    return


@app.cell
def _(B, P, R1, R2, mo, np, r, w1, w2):
    # Shear rate gamma_dot = r * d(omega)/dr. Differentiating
    # omega = A + B/r**2 gives d(omega)/dr = -2*B/r**3, so
    # gamma_dot = -2*B/r**2: it falls as 1/r**2, strongest at the inner
    # wall, and its sign follows (w2 - w1).
    gdot = -2.0 * B / r**2
    gdot_pkg = P.shear_rate(r, R1, R2, w1, w2)
    assert np.allclose(gdot, gdot_pkg, rtol=1e-12)
    mo.md(
        f"Shear-rate shape {gdot.shape}: {gdot[0]:.4f} 1/s at the inner wall, "
        f"{gdot[-1]:.4f} 1/s at the outer wall (matches package)."
    )
    return


@app.cell
def _(P, R1, R2, math, mo, mu, w1, w2):
    # Torque per unit axial length [N·m/m]: from the torque balance,
    # tau(r) = -(T/L)/(2*pi*r**2), and Newton's law at the inner wall,
    # tau(R1) = mu * gamma_dot(R1) = mu * (-2*B/R1**2). Eliminating
    # tau(R1) gives T/L = 4*pi*mu*B: torque is proportional to viscosity
    # and to the differential-rotation constant B.
    T_L = 4.0 * math.pi * mu * P.coefficients(R1, R2, w1, w2)[1]
    T_L_pkg = P.torque_per_length(R1, R2, w1, w2, mu)
    assert abs(T_L - T_L_pkg) < 1e-18
    mo.md(f"T/L = {T_L:.6e} N·m/m (matches package).")
    return (T_L,)


@app.cell
def _(P, R1, R2, T_L, go, mu, np, r, w1, w2):
    # Shear stress tau(r) = -(T/L) / (2*pi*r**2): the scalar torque is
    # broadcast against the (400,) grid, so each element is the stress at
    # that radius. The 1/r**2 fall is pure geometry — the same torque
    # crosses every cylindrical shell, but the shell area grows with r.
    tau = -T_L / (2.0 * np.pi * r**2)
    tau_pkg = P.shear_stress(r, R1, R2, w1, w2, mu)
    assert np.allclose(tau, tau_pkg, rtol=1e-12)
    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(x=r * 1000, y=tau, mode="lines", name="tau(r)",
                               line=dict(width=3, color="firebrick")))
    fig_t.update_layout(title="Shear-stress distribution",
                        xaxis_title="r [mm]", yaxis_title="tau [Pa]",
                        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
                        height=420, margin=dict(l=10, r=130, t=50, b=10))
    fig_t
    return


@app.cell
def _(P, mo):
    # Anchor check: hand-verified values (R1 = 0.05 m, R2 = 0.10 m,
    # w1 = 10 rad/s, w2 = 0, mu = 1e-3 Pa·s). Every number below was
    # computed by hand independently of this code; the cell fails loudly
    # if any of them stops matching.
    R1a, R2a, w1a, w2a, mua = 0.05, 0.10, 10.0, 0.0, 1e-3
    assert abs(P.torque_per_length(R1a, R2a, w1a, w2a, mua)
               - 4.1887902047863905e-4) / 4.1887902047863905e-4 < 1e-12
    assert abs(P.shear_stress(R1a, R1a, R2a, w1a, w2a, mua)
               - (-0.026666666666666665)) / 0.026666666666666665 < 1e-12
    assert abs(P.shear_stress(R2a, R1a, R2a, w1a, w2a, mua)
               - (-0.006666666666666666)) / 0.006666666666666666 < 1e-12
    assert abs(P.tangential_velocity(0.075, R1a, R2a, w1a, w2a)
               - 0.19444444444444445) / 0.19444444444444445 < 1e-12
    mo.md(
        "Anchor check passed: T/L = 4.18879e-4 N·m/m, wall stresses "
        "-0.0266667 Pa and -0.00666667 Pa, v(0.075 m) = 0.194444 m/s."
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Limiting cases: does the formula behave?

    Three sanity checks a chemical engineer runs on any new correlation.
    The cells below evaluate each one numerically.
    """)
    return


@app.cell
def _(P, mo, np):
    # Case 1 — solid-body rotation: both cylinders turn together
    # (w1 = w2). Then B = 0, so the shear rate and the shear stress are
    # zero everywhere, and v(r) = w1 * r is a straight line through the
    # origin: the fluid turns as a rigid block, which shears nothing.
    w = 5.0
    _, B_sb = P.coefficients(0.05, 0.10, w, w)
    r_sb = np.linspace(0.05, 0.10, 5)
    mo.md(
        f"w1 = w2 = {w} rad/s: B = {B_sb:.2e} (zero), "
        f"max |shear stress| = {np.max(np.abs(P.shear_stress(r_sb, 0.05, 0.10, w, w, 1e-3))):.2e} Pa, "
        f"v(r)/r = {P.tangential_velocity(r_sb, 0.05, 0.10, w, w) / r_sb} "
        "(constant, as rigid rotation demands)."
    )
    return


@app.cell
def _(P, mo):
    # Case 2 — narrow gap: when the gap d = R2 - R1 is tiny compared with
    # R1, curvature stops mattering and the profile must approach plane
    # Couette flow: v linear in r between the wall speeds. Here the gap is
    # 1% of R1; the midpoint velocity is checked against the linear
    # interpolation between the wall speeds.
    R1n, R2n = 0.10, 0.101
    w1n, w2n = 10.0, 0.0
    rmid = 0.5 * (R1n + R2n)
    v_mid = P.tangential_velocity(rmid, R1n, R2n, w1n, w2n)
    v_linear = 0.5 * (w1n * R1n + w2n * R2n)
    mo.md(
        f"Narrow gap (d/R1 = {(R2n - R1n) / R1n:.3f}): computed v(mid) = {v_mid:.6f} m/s, "
        f"linear interpolation = {v_linear:.6f} m/s, "
        f"relative deviation = {abs(v_mid - v_linear) / v_linear:.2e}."
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## The vector-field figure, array by array

    The app draws one arrow per station on a polar grid. The cells below
    rebuild that grid one operation at a time, printing every shape.
    With the defaults, each 2-D array has shape (24, 4): 24 angular
    stations around each of 4 interior rings.
    """)
    return


@app.cell
def _(R1, R2, mo, np):
    # Ring radii: 6 points spanning [R1, R2], dropping the two endpoints
    # (the walls themselves carry no arrows) -> shape (4,). These are the
    # radii of the concentric fluid shells sampled by the figure.
    rr = np.linspace(R1, R2, 4 + 2)[1:-1]
    mo.md(f"rr shape {rr.shape}: {np.round(rr * 1000, 1)} mm")
    return (rr,)


@app.cell
def _(mo, np):
    # Azimuthal stations around each ring, endpoint excluded so the 2*pi
    # station does not duplicate 0 -> shape (24,).
    th = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    mo.md(f"th shape {th.shape}: first {np.round(th[:4], 3)} rad …")
    return (th,)


@app.cell
def _(mo, np, rr, th):
    # meshgrid pairs every angle with every radius: Rg[i, j] is the radius
    # and Tg[i, j] the angle of arrow station (i, j). Both outputs have
    # shape (24, 4) = (n_theta, n_rings).
    Rg, Tg = np.meshgrid(rr, th)
    mo.md(f"Rg shape {Rg.shape}, Tg shape {Tg.shape}")
    return Rg, Tg


@app.cell
def _(Rg, Tg, mo, np):
    # Polar-to-cartesian, element-wise on the (24, 4) grid: X and Y are the
    # arrow base positions [m] in the cross-section plane.
    X, Y = Rg * np.cos(Tg), Rg * np.sin(Tg)
    mo.md(f"X shape {X.shape}: corner values {np.round(X[:2, :2] * 1000, 1)} mm")
    return X, Y


@app.cell
def _(P, R1, R2, Rg, mo, np, w1, w2):
    # Tangential velocity at each station [m/s], shape (24, 4):
    # tangential_velocity broadcasts over the grid, one value per radius.
    # sgn is the local sense of rotation: +1 counter-clockwise,
    # -1 clockwise, 0 where the fluid is instantaneously at rest.
    vv = P.tangential_velocity(Rg, R1, R2, w1, w2)
    vmax = float(np.max(np.abs(vv)))
    sgn = np.sign(vv)
    mo.md(
        f"vv shape {vv.shape}, max |v| = {vmax:.4f} m/s; "
        f"rotation sense takes values {np.unique(sgn)}."
    )
    return sgn, vmax, vv


@app.cell
def _(Tg, mo, np, sgn):
    # Unit direction of the local velocity: the tangent to the circle is
    # (-sin(theta), cos(theta)) for counter-clockwise motion; multiplying
    # by sgn flips it where the fluid runs clockwise. U and V are
    # dimensionless, shape (24, 4).
    U = -np.sin(Tg) * sgn
    V = np.cos(Tg) * sgn
    mo.md(
        f"U, V shape {U.shape}; |direction| = "
        f"{np.round(np.sqrt(U**2 + V**2)[0, :4], 6)} (unit vectors)."
    )
    return U, V


@app.cell
def _(R1, R2, mo, np, rr, vmax, vv):
    # Tightest grid spacing [m]: radial gap between neighbouring rings (dr)
    # versus arc length between neighbouring stations on the innermost
    # ring (arc_min). Capping the longest arrow at 55% of the smaller keeps
    # every arrow shorter than the distance to its neighbours, so arrows
    # cannot overlap. L is the per-station arrow length [m], shape (24, 4),
    # proportional to local speed; the vmax > 0 guard avoids division by
    # zero when both cylinders are stationary.
    dr = (R2 - R1) / (4 + 1)
    arc_min = rr[0] * (2 * np.pi / 24)
    Lmax = 0.55 * min(dr, arc_min)
    L = Lmax * np.abs(vv) / vmax if vmax > 0 else np.zeros_like(vv)
    mo.md(
        f"dr = {dr * 1000:.2f} mm, arc_min = {arc_min * 1000:.2f} mm, "
        f"Lmax = {Lmax * 1000:.2f} mm; L shape {L.shape}."
    )
    return (L,)


@app.cell
def _(L, R1, R2, U, V, X, Y, np, plt, vmax, vv):
    # The figure: quiver draws one arrow per station with base (X, Y) and
    # vector (U*L, V*L) [m]; colour encodes |v| [m/s] on viridis, so speed
    # is double-encoded as length and colour. scale_units="xy" with
    # scale=1.0 keeps arrow lengths true to the metre scale of the axes.
    fig, ax = plt.subplots(figsize=(6.4, 6.4), dpi=130)
    ax.set_aspect("equal")
    ax.set_xlim(-1.15 * R2, 1.15 * R2)
    ax.set_ylim(-1.15 * R2, 1.15 * R2)
    ax.axis("off")
    ax.add_patch(plt.Circle((0, 0), R2, color="#dbe7f3", zorder=0))
    ax.add_patch(plt.Circle((0, 0), R1, color="white", zorder=1))
    ax.add_patch(plt.Circle((0, 0), R2, fill=False, ec="#1f3a5f", lw=2.5, zorder=4))
    ax.add_patch(plt.Circle((0, 0), R1, fill=False, ec="#1f3a5f", lw=2.5, zorder=4))
    # Dark edges on every arrow: viridis's bright-yellow top end is nearly
    # invisible against the pale-blue annulus fill.
    # One shared normalization for arrows and colorbar: quiver would otherwise
    # autoscale its colours to the arrow data range, so the darkest arrow
    # would wear the colour the bar labels 0 m/s.
    cnorm = plt.Normalize(0, vmax)
    ax.quiver(X, Y, U * L, V * L, np.abs(vv), cmap="viridis", norm=cnorm,
              scale=1.0, scale_units="xy", width=0.012 * R2,
              headwidth=4.2, headlength=5.0, zorder=3,
              edgecolor="#1f3a5f", linewidth=0.3)
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=cnorm, cmap="viridis"),
                      ax=ax, shrink=0.75, pad=0.02)
    cb.set_label("|v| [m/s]")
    fig
    return


if __name__ == "__main__":
    app.run()
