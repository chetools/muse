"""Steady laminar Newtonian Couette flow between concentric cylinders.

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

Sign convention: tau_rtheta is positive when, on the outward (+r) face of a
fluid element, it pulls the fluid in the +theta direction.  The torque per
unit length T/L reported here is the torque the inner cylinder must exert on
the fluid (positive when driving it in the +theta sense); the shear stress is
then  tau(r) = -(T/L) / (2*pi*r**2).
"""

import math

import numpy as np


def validate(R1, R2, w1, w2, mu):
    """Check inputs; raise ValueError with a plain message on bad input."""
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
    """Return (A, B) with omega(r) = A + B / r**2.  Inputs validated."""
    validate(R1, R2, w1, w2, mu=1.0)
    den = R2**2 - R1**2
    A = (w2 * R2**2 - w1 * R1**2) / den
    B = R1**2 * R2**2 * (w1 - w2) / den
    return A, B


def _check_r(r, R1, R2):
    r = np.asarray(r, dtype=float)
    if np.any(r < R1) or np.any(r > R2):
        raise ValueError("Evaluation radius r must lie inside the annulus [R1, R2].")
    return r


def angular_velocity(r, R1, R2, w1, w2):
    """Angular velocity omega(r) [rad/s] of the fluid."""
    A, B = coefficients(R1, R2, w1, w2)
    r = _check_r(r, R1, R2)
    return A + B / r**2


def tangential_velocity(r, R1, R2, w1, w2):
    """Azimuthal velocity v_theta(r) = r * omega(r) [m/s]."""
    r = _check_r(np.asarray(r, dtype=float), R1, R2)
    return r * angular_velocity(r, R1, R2, w1, w2)


def shear_rate(r, R1, R2, w1, w2):
    """Shear rate gamma_dot(r) = r * d(omega)/dr [1/s] (signed)."""
    _, B = coefficients(R1, R2, w1, w2)
    r = _check_r(r, R1, R2)
    return -2.0 * B / r**2


def torque_per_length(R1, R2, w1, w2, mu):
    """Torque per unit axial length [N*m/m] the inner cylinder exerts on the
    fluid.  Positive when driving the fluid in the +theta sense (w1 > w2)."""
    validate(R1, R2, w1, w2, mu)
    _, B = coefficients(R1, R2, w1, w2)
    return 4.0 * math.pi * mu * B


def shear_stress(r, R1, R2, w1, w2, mu):
    """Shear stress tau_rtheta(r) [Pa] (signed; see module docstring).

    Falls as 1/r**2 — a direct consequence of the torque balance, independent
    of the velocity profile details.
    """
    validate(R1, R2, w1, w2, mu)
    r = _check_r(r, R1, R2)
    return -torque_per_length(R1, R2, w1, w2, mu) / (2.0 * math.pi * r**2)


def rpm_to_rad_s(n_rpm):
    """Convert revolutions per minute to rad/s (sign preserved)."""
    return np.asarray(n_rpm, dtype=float) * 2.0 * math.pi / 60.0
