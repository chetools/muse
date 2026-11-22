"""Dynamic multicomponent column model for the distillation game (reference).

Stages: stage 0 is the reboiler, stages 1..N are trays, and the reflux drum
is carried as a composition state after stage N. Tray 1 is the bottom tray;
the feed enters at the feed stage. All quantities in SI units.

Assumptions (SPEC Sections 3-4 and Amendment A3): equilibrium stages
with the mixture's equilibrium ratios (ideal or activity-coefficient,
see mixtures.py), constant molal overflow, uniform column pressure,
constant stage holdups in this core (level dynamics live in
overhead.py, where the outflows are valve-driven). The feed enters
through the feed flash of feed.py: a liquid at its stated temperature
and pressure, let down isenthalpically to the column pressure.

Nomenclature
------------
N        number of trays (dimensionless)
F        feed molar flow, mol/s
z_c      feed mole fraction of component c (dimensionless)
L_R      reflux (liquid) molar flow in the rectifying section, mol/s
V_R      vapour molar flow in the rectifying section, mol/s
L_S      liquid molar flow in the stripping section, mol/s
V_S      vapour molar flow (boilup) in the stripping section, mol/s
D        distillate molar flow, mol/s
B        bottoms molar flow, mol/s
P        column pressure, kPa
T_j      temperature of stage j, K (bubble point of its liquid)
x_cj     liquid mole fraction of component c on stage j
y_cj     vapour mole fraction of component c leaving stage j
K_cj     equilibrium ratio y_cj / x_cj = Psat_c(T_j) / P
M_j      liquid holdup of stage j, mol
Components are ordered (pentane, hexane, heptane) as in thermo.py.
Flow relations (total condenser), with psi the vapour fraction of the
flashed feed: V_R = L_R + D;  L_S = L_R + (1 - psi) F;
V_S = V_R - psi F;  B = F - D.
"""

import numpy as np

from feed import feed_flash
from mixtures import ALKANES

NC = ALKANES.nc  # kept for callers written against the alkanes default


def psat_np(T):
    """Vapour pressures (kPa) of the default mixture at temperatures T."""
    return ALKANES.psat_np(T)


def bubble_points(x, P):
    """Bubble temperatures and ratios of the default mixture (see
    mixtures.Mixture.bubble_points for the general form)."""
    return ALKANES.bubble_points(x, P)


class Column:
    """Steady solver and dynamic right-hand side for the tray column."""

    def __init__(self, n_trays=12, feed_stage=6, F=10.0,
                 z=(0.40, 0.30, 0.30), D=4.0, L_R=5.0, P=150.0,
                 M_tray=200.0, M_reb=1000.0, M_drum=500.0,
                 mixture=ALKANES, feed_T=None, feed_P=None):
        if not (1 <= feed_stage <= n_trays):
            raise ValueError("feed stage must be a tray")
        self.mix = mixture
        self.N = n_trays
        self.feed_stage = feed_stage  # tray index, 1..N
        self.F = float(F)
        self.z = np.asarray(z, dtype=float)
        if self.z.size != self.mix.nc:
            raise ValueError("feed composition does not match the mixture")
        self.D = float(D)
        self.L_R = float(L_R)
        self.P = float(P)
        # Feed state: default is a saturated liquid at the column
        # pressure. Otherwise the feed (a liquid at feed_T and feed_P)
        # is flashed to the column pressure; see feed.py.
        if feed_T is None:
            feed_T, _ = self.mix.bubble_point(tuple(self.z), self.P)
            feed_P = self.P
        elif feed_P is None:
            feed_P = self.P
        self.feed_T = float(feed_T)
        self.feed_P = float(feed_P)
        self.flash = feed_flash(self.mix, self.z, self.feed_T,
                                self.feed_P, self.P)
        psi = self.flash["psi"]
        self.V_R = self.L_R + self.D
        self.L_S = self.L_R + (1.0 - psi) * self.F
        self.V_S = self.V_R - psi * self.F
        self.B = self.F - self.D
        if self.B <= 0:
            raise ValueError("distillate flow must be below feed flow")
        if self.V_S <= 0:
            raise ValueError("flashed feed vapour exceeds the boilup")
        # Stage indexing 0..N (0 = reboiler). L_out[j] is the liquid flow
        # leaving stage j toward the stage below: the bottoms flow for the
        # reboiler, the stripping-section flow for the feed stage and the
        # trays below it, the rectifying-section flow above the feed stage.
        # V_up[j] is the vapour flow leaving stage j upward: the boilup
        # V_S below the feed stage, the rectifying flow V_R at and above
        # it (the flashed feed vapour joins the traffic at the feed
        # stage). The two coincide for a saturated-liquid feed. (An
        # earlier version used V_R on every stage, overstating the
        # stripping-section vapour traffic by psi*F for a flashing feed;
        # the overall balances closed either way, which is why the error
        # survived the first battery. Found 2026-11-21 during the Rust
        # port.)
        idx = np.arange(self.N + 1)
        self.L_out = np.where(idx == 0, self.B,
                              np.where(idx <= feed_stage, self.L_S, self.L_R))
        self.V_up = np.where(idx < feed_stage, self.V_S, self.V_R)
        holdups = np.full(self.N + 1, float(M_tray))
        holdups[0] = float(M_reb)
        self.M = holdups
        self.M_drum = float(M_drum)

    def feed_source(self):
        """Component molar flows (mol/s) entering at the feed stage:
        the liquid part of the flashed feed at its liquid composition
        plus the vapour part at its vapour composition."""
        psi = self.flash["psi"]
        return ((1.0 - psi) * self.F * np.asarray(self.flash["x"])
                + psi * self.F * np.asarray(self.flash["y"]))

    # -- steady state ----------------------------------------------------
    def steady_state(self):
        """Steady stage compositions.

        Method, in three steps: one fixed-point sweep of the linear
        component balances (see _solve_component, whose per-component
        solve is exact for fixed equilibrium ratios) for a physical
        initial profile; implicit (BDF) integration of the dynamic
        equations, which is stable but leaves a slowly decaying tail;
        and a Newton polish on the dynamic right-hand side, which
        converges quadratically once the integration is close. (Plain
        successive substitution on the ratios diverges on this column:
        shifts grew past 1e13 within 60 sweeps in testing, while the
        per-component linear solve itself is exact to 1e-15.)
        Returns (x, T): x shape (N+1, NC) stage liquid mole fractions,
        T shape (N+1,) stage temperatures in K. The distillate composition
        is the equilibrium vapour of the top stage.
        """
        from scipy.integrate import solve_ivp

        nst = self.N + 1
        x = np.tile(self.z, (nst, 1))
        _, K = self.mix.bubble_points(x, self.P)
        for c in range(self.mix.nc):
            x[:, c] = self._solve_component(K[:, c], c)
        drum = self.distillate_composition(x)

        def rhs_flat(t, s):
            dx, dd = self.rhs(s[:nst * self.mix.nc].reshape(nst, self.mix.nc), s[nst * self.mix.nc:])
            return np.concatenate([dx.ravel(), dd])

        s0 = np.concatenate([x.ravel(), drum])
        s = s0
        # Alternate BDF integration with a Newton polish (finite-difference
        # Jacobian, step halving) until the right-hand side is negligible.
        # One cycle suffices at moderate compositions; extreme-purity
        # configurations needed a second cycle in testing.
        for _cycle in range(3):
            sol = solve_ivp(rhs_flat, (0.0, 30000.0), s, method="BDF",
                            rtol=1e-9, atol=1e-11)
            if not sol.success:
                raise RuntimeError("steady_state integration failed")
            s = sol.y[:, -1]
            for _ in range(40):
                r = rhs_flat(0.0, s)
                if np.max(np.abs(r)) < 1e-11:
                    break
                J = np.empty((s.size, s.size))
                for i in range(s.size):
                    h = 1e-7 * max(1.0, abs(s[i]))
                    sp = s.copy()
                    sp[i] += h
                    J[:, i] = (rhs_flat(0.0, sp) - r) / h
                step = np.linalg.solve(J, -r)
                lam = 1.0
                base = np.max(np.abs(r))
                for _ in range(25):
                    cand = s + lam * step
                    if np.max(np.abs(rhs_flat(0.0, cand))) < base:
                        s = cand
                        break
                    lam *= 0.5
                else:
                    break  # no improving step; another BDF cycle may help
            if np.max(np.abs(rhs_flat(0.0, s))) < 1e-10:
                break
        else:
            raise RuntimeError("steady_state did not converge")
        x = s[:nst * self.mix.nc].reshape(nst, self.mix.nc)
        T, _ = self.mix.bubble_points(x, self.P)
        return x, T

    def _solve_component(self, Kc, c):
        """Steady compositions of one component given its ratios Kc."""
        nst = self.N + 1
        A = np.zeros((nst, nst))
        rhs = np.zeros(nst)
        for j in range(nst):
            # out: liquid down + vapour up
            A[j, j] += self.L_out[j] + self.V_up[j] * Kc[j]
            # in: liquid from stage above
            if j < self.N:
                A[j, j + 1] -= self.L_out[j + 1]
            else:
                # reflux enters with the drum composition, which at steady
                # state equals the top-stage vapour composition Kc*x_N:
                A[j, j] -= self.L_R * Kc[j]
            # in: vapour from stage below
            if j > 0:
                A[j, j - 1] -= self.V_up[j - 1] * Kc[j - 1]
            # feed enters at the feed stage (a tray, stage index = number)
            if j == self.feed_stage:
                rhs[j] -= self.feed_source()[c]
        return np.linalg.solve(A, -rhs)

    # -- dynamics ----------------------------------------------------------
    def rhs(self, x_stages, x_drum):
        """Time derivatives of all composition states.

        x_stages: (N+1, NC) stage liquid mole fractions.
        x_drum: (NC,) drum liquid mole fractions.
        Returns (dx_stages, dx_drum), per second. Holdups are constant in
        this core, so each stage obeys M_j dx_cj/dt = net molar inflow of
        component c.
        """
        x = np.asarray(x_stages, dtype=float)
        T, K = self.mix.bubble_points(x, self.P)
        y = K * x
        nst = self.N + 1
        # Component flows: liquid leaving each stage downward, vapour up.
        liq = self.L_out[:, None] * x          # (nst, NC)
        vap = self.V_up[:, None] * y
        net = np.zeros_like(x)
        # liquid in from above (stage j+1), with drum liquid entering the top
        net[:-1] += liq[1:]
        net[-1] += self.L_R * np.asarray(x_drum, dtype=float)
        # vapour in from below (stage j-1)
        net[1:] += vap[:-1]
        # out of each stage
        net -= liq + vap
        # feed at the feed stage
        net[self.feed_stage] += self.feed_source()
        dx = net / self.M[:, None]
        # Drum: condensed top vapour in, reflux + distillate out.
        dx_drum = (self.V_R * y[-1]
                   - (self.L_R + self.D) * np.asarray(x_drum)) / self.M_drum
        return dx, dx_drum

    def distillate_composition(self, x_stages):
        """Equilibrium vapour of the top stage = distillate composition."""
        _, K = self.mix.bubble_points(np.asarray(x_stages)[-1:], self.P)
        return (K * np.asarray(x_stages)[-1:])[0]
