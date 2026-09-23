"""Theory panel content for the Couette flow app.

Derives the velocity profile from torque balance and geometric/physical
arguments only. Rendered by the app with st.markdown (KaTeX).
"""

THEORY_MD = r"""
## The setup

A Newtonian fluid of viscosity $\mu$ fills the annulus between two infinitely
long concentric cylinders of radii $R_1 < R_2$. The inner cylinder rotates with
angular velocity $\Omega_1$, the outer with $\Omega_2$ (counter-rotation is
allowed — just use a negative sign). We look for the steady velocity field.

**Assumptions, stated physically rather than as PDEs:**

1. **Steady.** Nothing changes with time; the cylinders have been spinning long
   enough that start-up transients are gone.
2. **Axisymmetric and purely azimuthal.** By the rotational symmetry of the
   apparatus, the flow at a given radius $r$ looks the same at every angle
   $\theta$, and there is no reason for fluid to move radially inward/outward
   or axially up/down — so $\mathbf{v} = v_\theta(r)\,\hat{\boldsymbol\theta}$.
   (⚠️ This is the one place a Navier–Stokes argument would normally sneak in:
   see *Where Navier–Stokes would enter* below.)
3. **No-slip.** Fluid in contact with each wall moves at the wall's speed:
   $v_\theta(R_1) = \Omega_1 R_1$, $v_\theta(R_2) = \Omega_2 R_2$.
4. **Newtonian fluid.** Shear stress is proportional to shear rate,
   $\tau = \mu\,\dot\gamma$ — our single material assumption.

## Step 1 — Torque balance: the stress field from pure statics

Forget the fluid's motion for a moment and think about **angular momentum**.
Pick any imaginary cylindrical surface of radius $r$ (with $R_1 < r < R_2$)
and axial length $L$, coaxial with the cylinders.

In steady rotation, the shell of fluid inside this surface cannot accumulate
angular momentum — if more torque flowed in across the surface than out,
that shell would spin up, contradicting steadiness. Hence the torque
transmitted across *every* such surface is one and the same value $M$.

Torque = (tangential force) × (lever arm). The tangential force on the
surface is the shear stress $\tau_{r\theta}(r)$ times the surface area
$2\pi r L$, and the lever arm about the axis is $r$:

$$
M \;=\; \tau_{r\theta}(r)\,(2\pi r L)\,r \qquad\Longrightarrow\qquad
\boxed{\;\tau_{r\theta}(r) \;=\; \frac{M}{2\pi L\,r^2}\;}
$$

This is the whole trick. **The shear stress must fall as $1/r^2$, by geometry
and steadiness alone** — no constitutive law, no differential equation, no
Navier–Stokes. The inner wall, with its smaller area *and* shorter lever arm,
carries the highest stress: $\tau(R_1)/\tau(R_2) = (R_2/R_1)^2$.

## Step 2 — What "shear rate" means for rotating shells: a geometric argument

Shear rate measures how fast neighbouring layers of fluid slide past each
other. Picture two thin cylindrical shells at radii $r$ and $r + dr$,
rotating with angular velocities $\omega(r)$ and $\omega(r) + d\omega$.

Focus on a small marked patch on the inner shell. In a short time $dt$ the
outer shell rotates ahead of it by the angle difference $d\omega\,dt$, so the
two patches slide apart by the arc length

$$
\text{slip distance} \;=\; r\,(d\omega)\,dt .
$$

This slip happens across the radial separation $dr$, so the rate of shearing
(slip velocity per unit separation) is

$$
\boxed{\;\dot\gamma(r) \;=\; r\,\frac{d\omega}{dr}\;}
$$

Two remarks that make this feel inevitable rather than formal:

- **Rigid-body rotation produces no shear.** If $d\omega = 0$ the shells never
  slide — the formula gives $\dot\gamma = 0$ automatically. A spinning solid
  disk is not "shearing" itself.
- **In terms of $v_\theta = r\omega$:** since
  $\frac{dv_\theta}{dr} = \omega + r\frac{d\omega}{dr}$, we get the familiar
  form $\dot\gamma = \frac{dv_\theta}{dr} - \frac{v_\theta}{r}$. The
  $-v_\theta/r$ term is just the correction that subtracts out rigid rotation:
  a profile $v_\theta \propto r$ (solid-body spin) has $dv_\theta/dr = v_\theta/r$
  and hence zero shear, exactly as intuition demands.

## Step 3 — Newton's law: the single material assumption

For a Newtonian fluid, shear stress is proportional to shear rate:

$$
\tau_{r\theta} \;=\; \mu\,\dot\gamma \;=\; \mu\,r\,\frac{d\omega}{dr}.
$$

Combined with the torque balance from Step 1:

$$
\mu\,r\,\frac{d\omega}{dr} \;=\; \frac{M}{2\pi L\,r^2}
\qquad\Longrightarrow\qquad
\boxed{\;\frac{d\omega}{dr} \;=\; \frac{M}{2\pi\mu L\,r^3}\;}
$$

> **Where Navier–Stokes would enter (flagged, as promised).** The
> $\theta$-component of the Navier–Stokes equations for this flow reduces to
> $\frac{d}{dr}\!\left(r^2 \tau_{r\theta}\right) = 0$ — which is *exactly* the
> torque-balance statement of Step 1, dressed in PDE notation. We are not
> dodging physics by skipping it; we derived the same statement directly from
> "no angular-momentum accumulation," which is all the PDE was saying. The
> genuinely extra assumption we made instead is Step 0's premise — steady,
> purely azimuthal flow — which Navier–Stokes would normally be invoked to
> *justify* from symmetry. We take it as a physical postulate for laminar
> viscometric flow and check its limits honestly in *Caveats* below.

## Step 4 — Integrate and apply no-slip

Integrating once,

$$
\omega(r) \;=\; -\frac{M}{4\pi\mu L\,r^2} \;+\; C,
$$

and it is convenient to write this as $\omega(r) = A + B/r^2$. No-slip at
the walls, $\omega(R_1) = \Omega_1$ and $\omega(R_2) = \Omega_2$, gives two
equations for $A$ and $B$:

$$
\boxed{\;
\begin{aligned}
A &= \frac{\Omega_2 R_2^2 - \Omega_1 R_1^2}{R_2^2 - R_1^2}, \\
B &= \frac{R_1^2 R_2^2\,(\Omega_1 - \Omega_2)}{R_2^2 - R_1^2}.
\end{aligned}
\;}
$$

## Results

**Velocity profile** (this app's main output):

$$
\boxed{\;v_\theta(r) \;=\; A\,r \;+\; \frac{B}{r}\;}, \qquad
\boxed{\;\omega(r) \;=\; A \;+\; \frac{B}{r^2}\;}
$$

**Shear-stress distribution** (from Step 1 — note it never needed $A$ or $B$):

$$
\boxed{\;\tau_{r\theta}(r) \;=\; -\,\frac{T/L}{2\pi\,r^2}\;}
$$

where $T/L$ is the torque per unit length the inner cylinder must exert on
the fluid,

$$
\boxed{\;\frac{T}{L} \;=\; 4\pi\mu\,B \;=\;
4\pi\mu\,\frac{R_1^2 R_2^2}{R_2^2 - R_1^2}\,(\Omega_1 - \Omega_2)\;}.
$$

The minus sign in $\tau_{r\theta}$ is a sign convention (positive $\tau_{r\theta}$
pulls the $+r$ face of a fluid element in the $+\theta$ direction); the
*magnitude* $|\tau| \propto 1/r^2$ is the physical content. Wall values:

$$
|\tau(R_1)| \;=\; \frac{T/L}{2\pi R_1^2}, \qquad
|\tau(R_2)| \;=\; \frac{T/L}{2\pi R_2^2}.
$$

## Sanity checks (the derivation passes them all)

- **Solid-body rotation** ($\Omega_1 = \Omega_2 = \Omega$): then $B = 0$,
  $A = \Omega$, so $v_\theta = \Omega r$ and $\tau \equiv 0$, $T = 0$. The
  fluid spins as a rigid body with no shear — exactly right, and a good
  test that the $1/r$ term carries *all* the shearing motion.
- **Fixed outer cylinder** ($\Omega_2 = 0$): the classic viscometer case.
  $\omega(r) = \Omega_1 \frac{R_1^2}{R_2^2 - R_1^2}\left(\frac{R_2^2}{r^2} - 1\right)$,
  fastest at the inner wall, decaying outward.
- **Narrow gap** ($R_2 - R_1 \ll R_1$): zoom into the thin gap and the curvature
  disappears — the profile becomes the **linear plane-Couette profile**
  $v \approx \Omega_1 R_1 + (\text{const})\cdot(r - R_1)$, i.e. simple shear
  between parallel plates. The app's test suite checks this limit numerically.

## Caveats — where the picture breaks down

- **Laminar only.** Above a critical rotation rate the flow goes unstable to
  **Taylor vortices** (stacked toroidal rolls) — the "purely azimuthal" premise
  of Step 0 fails and this profile no longer describes reality. For a
  viscometer, stay at modest speeds.
- **End effects ignored.** Real cylinders are finite; near the top and bottom
  the flow turns around and is not purely azimuthal. The formulas describe the
  long-cylinder interior.
- **Steady state.** Start-up from rest involves a diffusive transient
  ($\sim \rho R_1^2/\mu$ timescale); the profile above is the long-time limit.
"""
