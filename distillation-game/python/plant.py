"""Integrated plant model for the distillation game (reference).

One dynamic model joining the tray column (column.py), the flooded
condenser below the reflux drum, the riser lift, the cooling loop, the
steam chest, and the relief valve (overhead.py). Students set valve
openings; every flow follows from an opening and a pressure difference.
All quantities in SI units.

Structure and closures (SPEC Section 2 and Amendment A4):

- Pressures. The column vapour space and the condenser vapour space are
  separate inventories joined by the condenser inlet valve; each
  pressure follows the ideal-gas law in a fixed vapour volume (the
  condenser vapour volume shrinks as liquid floods it). The drum
  pressure is the bubble pressure of the drum liquid at its
  temperature: vapour admitted through the hot vapour bypass condenses
  into the drum liquid and warms it, which raises the drum pressure and
  backs condensate up into the condenser; with the bypass closed, cold
  condensate inflow cools the drum liquid and the drum pressure falls,
  so drainage speeds up. This is the flooded-condenser control
  mechanism of the reference papers, carried by the equations.
- Column internals. Constant molal overflow within each section, with
  the section flows set at each instant by the boundary flows: boilup
  from the reboiler duty, reflux and distillate from the drum valves,
  bottoms from the reboiler valve. Tray holdups are constant; the
  reboiler, condenser, and drum holdups are states (levels).
- Feed. As in column.py: a liquid at its stated temperature and
  pressure, flashed isenthalpically to the column pressure (feed.py).
  Feed settings can be changed during a run (a disturbance or the feed
  post), through set_feed.

Nomenclature (in addition to column.py and overhead.py)
------------
P_col    column pressure, kPa (state, through its vapour inventory)
P_cond   condenser pressure, kPa (state)
P_drum   drum pressure, kPa (from the drum liquid state)
P_chest  steam chest pressure, kPa (state)
T_drum   drum liquid temperature, K (state)
T_tank   cooling-loop surge tank temperature, K (state)
W_in     vapour flow through the condenser inlet valve, mol/s
W_bp     vapour flow through the hot vapour bypass, mol/s (signed:
         positive from the column toward the drum)
C_r      condensation rate in the condenser, mol/s
open_*   valve openings, percent (pump and makeup as fractions)

Valve sizing constants, vapour volumes, elevations, the steam supply
pressure, the tank heat loss, and the downstream pressure are ASSUMED
game design values, stated here and in Amendment A4. The default
mixture for the integrated plant is the alkane mixture; the overhead
relations in overhead.py carry its properties.
"""

import math

import numpy as np

import overhead as oh
from column import Column
from feed import feed_flash
from mixtures import ALKANES

R_GAS = 8.314            # J/(mol K)
V_COL = 6.0              # m^3, column vapour volume, assumed
V_COND_TOTAL = 0.45      # m^3, condenser total volume, assumed
M_COND_MAX = 2000.0      # mol, condenser liquid capacity (overhead.py)
MOLAR_VOL_LIQ = 1.459e-4  # m^3/mol, mean liquid molar volume, assumed
V_CHEST = 0.5            # m^3, steam chest volume, assumed
P_SUPPLY = 900.0         # kPa, steam supply header, assumed
P_DOWN = 100.0           # kPa, product downstream pressure, assumed
LAM_STEAM = 40700.0      # J/mol, steam latent heat (overhead.py)

KV_IN = 46.3428          # vapour-law sizing, condenser inlet valve
KV_BP = 8.8083           # vapour-law sizing, hot vapour bypass valve
KV_REF = 2.4873            # mol/s per sqrt(kPa), reflux valve
SUMP_CAP = 2000.0        # mol, reboiler sump working capacity: liquid
                         # beyond it is counted on the stripping trays
KV_DIST = 0.9085           # mol/s per sqrt(kPa), distillate valve
KV_BOT = 1.6734             # mol/s per sqrt(kPa), bottoms valve
KV_STEAM = 3.6563        # vapour-law sizing, steam flow valve
RC_VAP = 0.40            # choked-flow threshold for the hydrocarbon
                         # vapour valves, as a downstream-to-upstream
                         # pressure ratio: globe trim per ISA 75.01
                         # (F_k * x_T with x_T = 0.72). Below it the
                         # flow depends on upstream pressure alone.
RC_STEAM = 0.35          # the same threshold for the steam valve
REFLUX_DROP = 4.0        # m, drum outlet elevation above the top tray
DIST_DROP = 6.0          # m, drum outlet elevation above product grade
M_DRUM_MAX = 3000.0      # mol, drum liquid capacity, assumed
DRUM_HEIGHT = 1.2        # m, drum liquid height at capacity, assumed
M_REB_MAX = 4000.0       # mol, reboiler capacity, assumed
REB_HEIGHT = 1.0         # m, reboiler liquid height at capacity, assumed

CP_WATER = 4186.0        # J/(kg K), cooling water
MU_MAX = 10.0            # kg/s, makeup flow at full opening, assumed
UA_TANK = 8000.0         # W/K, surge tank ambient loss, assumed
T_AMB = 298.0            # K, ambient and makeup supply temperature

VALVES = ("inlet", "bypass", "outlet", "reflux", "distillate",
          "bottoms", "steam_valve")

# Feed valve and its flow controller (SPEC A18): the feed flow is set
# by a valve on the feed line, driven by the pressure drop between the
# feed supply and the column. KV_FEED passes 10 mol/s at a 60 percent
# opening with a 100 kPa drop (feed supply 250 kPa, column 150 kPa).
# In automatic mode a controller moves the opening toward the value
# the valve equation requires for the setpoint, with a first-order
# lag of FEED_TAU seconds; in manual mode the opening is set directly.
KV_FEED = 2.0
KV_FEED_VAP = 10.0     # vapour-branch sizing for a vapour feed,
                         # five times the liquid sizing at the
                         # nominal point (assumed)
FEED_TAU = 4.0
P_FEED_NOM = 250.0


def _vap_factor(P_up, P_dn, rc):
    """Choked-flow factor for a vapour valve: the square root of
    the difference of the squared pressures, with the downstream
    pressure floored at the fraction rc of the upstream, in units
    of 100 kPa. Zero when the downstream is at or above the
    upstream."""
    dn = max(P_dn, rc * P_up)
    return math.sqrt(max(P_up * P_up - dn * dn, 0.0)) / 100.0


def _vap_flow(K, opening_pct, P_up, P_dn, rc):
    """Vapour molar flow through a valve (one-directional)."""
    if opening_pct <= 0.0 or P_up <= 0.0:
        return 0.0
    return K * (opening_pct / 100.0) * _vap_factor(P_up, P_dn, rc)


def _sqrt_flow(K, opening_pct, drive_kPa):
    """Valve molar flow: sizing constant times opening times the square
    root of the positive part of the driving pressure difference."""
    if opening_pct <= 0.0 or drive_kPa <= 0.0:
        return 0.0
    return K * (opening_pct / 100.0) * math.sqrt(drive_kPa)


class Plant:
    """The integrated plant, initialised at the nominal steady state.

    The initial openings reproduce the column steady-state flows at the
    nominal pressures. The integrated plant's own equilibrium sits
    modestly below that point: at fixed nominal openings the column
    pressure settles from 150 kPa toward about 130 kPa over roughly
    15 minutes, with inventory migrating slowly into the reboiler and
    drum, while the distillate composition holds at the steady value.
    Attempts to solve for the exact equilibrium directly (Newton and
    structured iterations on the coupled residuals) proved fragile
    against the valve square roots, the condensation minimum, and a
    degenerate drum root at which the drainage has collapsed; the
    measured drift is recorded in test_plant.py instead, and the
    settling is part of what the autopilot and the students correct.
    """

    def __init__(self, column=None, T_supply=T_AMB):
        if column is None:
            # The nominal feed arrives as a saturated liquid at the
            # column pressure; its supply pressure, P_FEED_NOM, is
            # what drives it through the feed valve.
            t_bub_nom, _ = ALKANES.bubble_point((0.40, 0.30, 0.30),
                                                150.0)
            column = Column(feed_T=t_bub_nom, feed_P=P_FEED_NOM)
        self.col = column
        if self.col.mix is not ALKANES:
            raise ValueError("the integrated plant currently carries "
                             "the alkane mixture (overhead.py properties)")
        self.mix = self.col.mix
        self.nc = self.mix.nc
        self.nst = self.col.N + 1
        self.T_supply = float(T_supply)
        # Scenario fault flag: with the relief path isolated, vapour
        # generation has no outlet and the vessel ruptures. With a
        # functioning relief this cannot happen: the maximum credible
        # generation (full 900 kPa steam, no cooling) is about
        # 17 mol/s, below the 25 mol/s relief capacity, because the
        # reboiler temperature rises with pressure and closes the
        # steam-side temperature difference (SPEC Amendment A6).
        self.relief_blocked = False
        # Feed flow control: automatic at the nominal setpoint, the
        # effective opening starting at its nominal value.
        self.feed_setpoint = 10.0
        self.feed_auto = True
        self.feed_op_eff = 50.0
        self._feed_valve_state()
        x_ss, _ = self.col.steady_state()
        self.x_drum0 = self.col.distillate_composition(x_ss)
        # Nominal boundary state (Amendment A4): the condenser runs
        # about 15 kPa above the drum; that difference lifts the
        # condensate up the riser.
        self.P_col0 = self.col.P
        self.P_cond0 = self.col.P - 2.0
        self.P_drum0 = self.col.P - 10.0
        self.M_c0 = 800.0
        self.M_drum0 = 1500.0
        self.M_reb0 = self.col.M[0]
        self.M_strip0 = float(np.sum(
            self.col.M[1:self.col.feed_stage + 1]))
        self.T_tank0 = 307.0
        T_drum0, _ = self.mix.bubble_point(tuple(self.x_drum0),
                                            self.P_drum0)
        self.T_drum0 = T_drum0
        # Steam chest at the pressure whose saturation temperature gives
        # the nominal boilup through the reboiler.
        T_all, K_all = self.mix.bubble_points(x_ss, self.col.P)
        T_reb0 = float(T_all[0])
        y_reb0 = K_all[0] * x_ss[0]
        Q_nom = self.col.V_S * float(np.dot(y_reb0, self.mix.lam))
        self._Q_nom = Q_nom
        T_steam0 = T_reb0 + Q_nom / (900.0 * 12.0)
        self.P_chest0 = self._steam_pressure(T_steam0)
        self.openings = self._nominal_openings(x_ss)
        self._flash_cache = (None, None)
        self._Q_cond = Q_nom
        self.last = {}
        self.state0 = self._pack(x_ss, self.x_drum0.copy(),
                                 self.x_drum0.copy())

    @staticmethod
    def _steam_pressure(T_sat):
        """Invert overhead.steam_saturation_T by bisection."""
        lo, hi = 50.0, 2000.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if oh.steam_saturation_T(mid) < T_sat:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def _nominal_openings(self, x_ss):
        """Openings that reproduce the nominal flows at the nominal
        pressures, each solved from its valve equation."""
        col = self.col
        T_w_out = self.T_tank0 + self._Q_nom / (0.5 * oh.W_REF * CP_WATER)
        C_r, _, T_cond, flooded = oh.condensation_rate(
            tuple(self.x_drum0), self.P_cond0, self.T_tank0, T_w_out,
            self.M_c0, 0.5, 50.0)
        T_pool = oh.pool_temperature(T_cond, self.T_tank0, flooded)
        # Bypass at 1 percent opening: the vapour admitted through the
        # bypass condenses in the drum and warms its liquid, so even a
        # small standing opening moves the drum pressure materially.
        W_bp = _vap_flow(KV_BP, 1.0, self.P_col0, self.P_drum0, RC_VAP)
        W_in = col.V_R - W_bp
        delivered, raw, margin, _ = oh.drainage(
            tuple(self.x_drum0), self.P_cond0, self.P_drum0, self.M_c0,
            T_pool, 100.0)
        open_out = 100.0 * (W_in / raw) if raw > 0 else 100.0
        head_drum = oh.RHO_LIQ * oh.G * (
            REFLUX_DROP + (self.M_drum0 / M_DRUM_MAX) * DRUM_HEIGHT) / 1000.0
        open_ref = 100.0 * col.L_R / (KV_REF * math.sqrt(
            max(self.P_drum0 + head_drum - self.P_col0, 0.01)))
        head_dist = oh.RHO_LIQ * oh.G * (
            DIST_DROP + (self.M_drum0 / M_DRUM_MAX) * DRUM_HEIGHT) / 1000.0
        open_dist = 100.0 * col.D / (KV_DIST * math.sqrt(
            max(self.P_drum0 + head_dist - P_DOWN, 0.01)))
        head_reb = oh.RHO_LIQ * oh.G * (
            (self.M_reb0 / M_REB_MAX) * REB_HEIGHT) / 1000.0
        open_bot = 100.0 * col.B / (KV_BOT * math.sqrt(
            max(self.P_col0 + head_reb - P_DOWN, 0.01)))
        P_reg = 400.0
        W_steam = self._Q_nom / LAM_STEAM
        open_steam = 100.0 * W_steam / (KV_STEAM * _vap_factor(
            P_reg, self.P_chest0, RC_STEAM))
        return {
            "inlet": 100.0 * W_in / (KV_IN * _vap_factor(
                self.P_col0, self.P_cond0, RC_VAP)),
            "bypass": 1.0,
            "outlet": open_out,
            "reflux": open_ref,
            "distillate": open_dist,
            "bottoms": open_bot,
            "steam_reg_set": P_reg,
            "steam_valve": open_steam,
            "pump": 0.5,
            "makeup": 5.0 / MU_MAX,
            "feed": 50.0,
        }

    # -- state packing -----------------------------------------------------
    def _pack(self, x_stages, x_pool, x_drum, M_reb=None, M_c=None,
              M_drum=None, P_col=None, P_cond=None, P_chest=None,
              T_tank=None, T_drum=None, M_strip=None):
        return np.concatenate([
            np.asarray(x_stages, dtype=float).ravel(),
            np.asarray(x_pool, dtype=float),
            np.asarray(x_drum, dtype=float),
            [self.M_reb0 if M_reb is None else M_reb,
             self.M_c0 if M_c is None else M_c,
             self.M_drum0 if M_drum is None else M_drum,
             self.P_col0 if P_col is None else P_col,
             self.P_cond0 if P_cond is None else P_cond,
             self.P_chest0 if P_chest is None else P_chest,
             self.T_tank0 if T_tank is None else T_tank,
             self.T_drum0 if T_drum is None else T_drum,
             self.M_strip0 if M_strip is None else M_strip],
        ])

    def _unpack(self, s):
        n = self.nst * self.nc
        x = s[:n].reshape(self.nst, self.nc)
        x_pool = s[n:n + self.nc]
        x_drum = s[n + self.nc:n + 2 * self.nc]
        rest = s[n + 2 * self.nc:]
        keys = ("M_reb", "M_c", "M_drum", "P_col", "P_cond", "P_chest",
                "T_tank", "T_drum", "M_strip")
        return x, x_pool, x_drum, dict(zip(keys, rest))

    @staticmethod
    def _clean(comp):
        comp = np.clip(np.asarray(comp, dtype=float), 0.0, None)
        total = comp.sum()
        return comp / total if total > 0 else comp

    def _feed_valve_state(self):
        """Cache what the feed valve law needs about the feed at its
        own conditions: its vapour pressure at its temperature (the
        flashing cap for a liquid feed) and whether it is a vapour
        at its supply pressure."""
        col = self.col
        z = np.asarray(col.z, dtype=float)
        gamma_f = self.mix.gamma_np(z.reshape(1, self.nc),
                                    np.array([col.feed_T]))[0]
        self._feed_pv = float(np.sum(
            z * gamma_f * self.mix.psat(np.asarray(col.feed_T))))
        flash_sup = feed_flash(self.mix, tuple(col.z), col.feed_T,
                               col.feed_P, col.feed_P)
        self._feed_psi_sup = float(flash_sup["psi"])

    def set_feed(self, F=None, z=None, feed_T=None, feed_P=None):
        """Change the feed during a run (disturbance or feed post).

        F addresses the flow setpoint: the feed flow itself is made by
        the feed valve from the supply-to-column pressure drop, under
        automatic control unless the valve has been taken to manual.
        """
        if F is not None:
            self.feed_setpoint = float(F)
            self.feed_auto = True
        if z is not None:
            self.col.z = np.asarray(z, dtype=float)
        if feed_T is not None:
            self.col.feed_T = float(feed_T)
        if feed_P is not None:
            self.col.feed_P = float(feed_P)
        self._flash_cache = (None, None)
        self._feed_valve_state()

    def _feed_flash(self, P_col):
        cached_P, flash = self._flash_cache
        if cached_P is None or abs(P_col - cached_P) > 1.0:
            flash = feed_flash(self.mix, self.col.z, self.col.feed_T,
                               self.col.feed_P, P_col)
            self._flash_cache = (P_col, flash)
        return flash

    # -- dynamics ------------------------------------------------------------
    def rhs(self, s, openings=None):
        """Time derivatives of the full state. Also records the boundary
        flows and display quantities in self.last."""
        op = dict(self.openings)
        if openings:
            op.update(openings)
        col = self.col
        x, x_pool, x_drum, st = self._unpack(np.asarray(s, dtype=float))
        x = np.array([self._clean(row) for row in x])
        x_pool = self._clean(x_pool)
        x_drum = self._clean(x_drum)
        M_reb = max(st["M_reb"], 1.0)
        # Empty-vessel availability: a vessel's liquid outflows (and
        # the reboiler's boil-up) fade out over the last 50 mol of
        # holdup, so an inventory can reach zero but never go
        # negative. Above 50 mol the factor is 1 and normal operation
        # is untouched.
        a_reb = min(1.0, max(st["M_reb"], 0.0) / 50.0)
        a_drum = min(1.0, max(st["M_drum"], 0.0) / 50.0)
        a_pool = min(1.0, max(st["M_c"], 0.0) / 50.0)
        # The boil-up fades on the stripping section's liquid as a
        # whole (sump plus the liquid held on the stripping trays,
        # M_strip): when the sump runs dry the trays drain through
        # it and keep the tubes covered until the section is dry.
        C_reb = max(st["M_reb"], 0.0) + max(st["M_strip"], 0.0)
        a_boil = min(1.0, C_reb / 50.0)
        M_c = min(max(st["M_c"], 0.0), M_COND_MAX)
        M_drum = max(st["M_drum"], 1.0)
        P_col = max(st["P_col"], 20.0)
        P_cond = max(st["P_cond"], 20.0)
        P_chest = max(st["P_chest"], 20.0)
        T_tank, T_drum = st["T_tank"], st["T_drum"]

        # Drum pressure from the drum liquid state.
        gamma_d = self.mix.gamma_np(x_drum.reshape(1, self.nc),
                                    np.asarray(T_drum))[0]
        P_drum = float(np.sum(x_drum * gamma_d
                              * self.mix.psat(np.asarray(T_drum))))

        # Stage equilibrium at the column pressure.
        T_st, K = self.mix.bubble_points(x, P_col)
        y = K * x
        y_top = y[-1]

        # Feed flow from the feed valve. A liquid feed is capped by
        # flashing: the effective downstream pressure is the higher
        # of the column pressure and the feed's vapour pressure at
        # its temperature. A feed that is a vapour at its supply
        # pressure follows the vapour valve law.
        op_feed = self.feed_op_eff if self.feed_auto else op["feed"]
        if self._feed_psi_sup >= 1.0:
            col.F = _vap_flow(KV_FEED_VAP, op_feed, col.feed_P, P_col, RC_VAP)
        else:
            col.F = _sqrt_flow(KV_FEED, op_feed,
                               col.feed_P - max(P_col, self._feed_pv))
        self.last_feed = (col.F, op_feed)

        # Feed flash at the current column pressure (cached).
        flash = self._feed_flash(P_col)
        psi = flash["psi"]
        feed_src = ((1.0 - psi) * col.F * np.asarray(flash["x"])
                    + psi * col.F * np.asarray(flash["y"]))

        # Reboiler: duty from the steam chest, boilup from the duty.
        Q_reb, T_steam = oh.reboiler_duty(float(T_st[0]), P_chest)
        lam_vap_reb = float(np.dot(y[0], self.mix.lam))
        V_S = Q_reb / lam_vap_reb if lam_vap_reb > 0 else 0.0
        V_S *= a_boil
        V_R = V_S + psi * col.F

        # Overhead vapour valves (bypass signed).
        W_in = _vap_flow(KV_IN, op["inlet"], P_col, P_cond, RC_VAP)
        if P_col >= P_drum:
            W_bp = _vap_flow(KV_BP, op["bypass"], P_col, P_drum, RC_VAP)
        else:
            W_bp = -_vap_flow(KV_BP, op["bypass"], P_drum, P_col, RC_VAP)

        # Condenser: duty-limited condensation. The water outlet
        # temperature and the duty are solved self-consistently within
        # the evaluation (a fixed-point iteration, three passes), so
        # the right-hand side is a pure function of the state. (An
        # earlier version carried the previous evaluation's duty,
        # which made the right-hand side path-dependent.)
        circ = op["pump"] * oh.W_REF
        M_vap_cond = P_cond * 1000.0 * max(
            V_COND_TOTAL - M_c * MOLAR_VOL_LIQ, 0.02) \
            / (R_GAS * max(T_st[-1], 250.0))
        lam_top_mix = float(np.dot(y_top, self.mix.lam))
        T_w_out = T_tank
        C_r = Q_max = T_cond = flooded = 0.0
        for _ in range(3):
            C_r, Q_max, T_cond, flooded = oh.condensation_rate(
                tuple(y_top), P_cond, T_tank, T_w_out, M_c, op["pump"],
                W_in + M_vap_cond / 60.0)
            if circ > 0.1:
                T_w_out = T_tank + C_r * lam_top_mix / (circ * CP_WATER)
        Q_cond = C_r * lam_top_mix
        T_pool = oh.pool_temperature(T_cond, T_tank, flooded)

        # Riser drainage to the drum.
        delivered, raw, margin, flash_frac = oh.drainage(
            tuple(x_pool), P_cond, P_drum, M_c, T_pool, op["outlet"])
        delivered *= a_pool
        raw *= a_pool
        _, K_pool_drum = self.mix.bubble_points(
            x_pool.reshape(1, self.nc), max(P_drum, 20.0))
        y_pool_eq = K_pool_drum[0] * x_pool
        # Material-side condensation: the duty-limited rate C_r may
        # exceed the vapour inflow W_in by drawing on the condenser
        # vapour space (that draw is what the pressure derivative
        # represents), but the liquid inventories can only be
        # credited with the vapour that actually arrives; the rest
        # of the inflow passes through to the drum as vapour. This
        # keeps the overall and component balances exact.
        C_r_mat = min(C_r, W_in)
        vap_pass = W_in - C_r_mat
        # Riser split, conserving: of the raw riser flow at x_pool,
        # the flashed fraction leaves as vapour at the equilibrium
        # composition y_pool_eq; the residual liquid (composition
        # x_res) partly reaches the drum (delivered) and partly
        # falls back, staying in the pool.
        vap_flash = raw * flash_frac
        if raw > 0.0 and flash_frac > 0.0:
            x_res = (x_pool - flash_frac * y_pool_eq) / (1.0 - flash_frac)
        else:
            x_res = x_pool

        # Drum and reboiler liquid valves.
        head_drum_level = oh.RHO_LIQ * oh.G * (
            (M_drum / M_DRUM_MAX) * DRUM_HEIGHT) / 1000.0
        L_R = _sqrt_flow(KV_REF, op["reflux"],
                         P_drum + head_drum_level
                         + oh.RHO_LIQ * oh.G * REFLUX_DROP / 1000.0 - P_col)
        L_R *= a_drum
        D = _sqrt_flow(KV_DIST, op["distillate"],
                       P_drum + head_drum_level
                       + oh.RHO_LIQ * oh.G * DIST_DROP / 1000.0 - P_DOWN)
        D *= a_drum
        head_reb = oh.RHO_LIQ * oh.G * (
            (M_reb / M_REB_MAX) * REB_HEIGHT) / 1000.0
        B = _sqrt_flow(KV_BOT, op["bottoms"], P_col + head_reb - P_DOWN)
        B *= a_reb
        L_S = L_R + (1.0 - psi) * col.F

        # Steam chest.
        P_reg = min(op["steam_reg_set"], P_SUPPLY)
        W_steam = _vap_flow(KV_STEAM, op["steam_valve"], P_reg, P_chest, RC_STEAM)
        dP_chest = (R_GAS * oh.steam_saturation_T(P_chest) / V_CHEST
                    * (W_steam - Q_reb / LAM_STEAM) / 1000.0)

        # Relief (zero when the scenario isolates the relief path).
        W_relief = 0.0 if self.relief_blocked else oh.relief_flow(P_col)

        # ---- composition derivatives -------------------------------------
        nst = self.nst
        L_out = np.where(np.arange(nst) == 0, B,
                         np.where(np.arange(nst) <= col.feed_stage,
                                  L_S, L_R))
        # Vapour leaving a stage upward: the stripping flow below the
        # feed stage; the feed stage and above carry the rectifying
        # flow (the flashed feed vapour joins at the feed stage).
        V_up = np.where(np.arange(nst) < col.feed_stage, V_S, V_R)
        liq = L_out[:, None] * x
        vap = V_up[:, None] * y
        net = np.zeros_like(x)
        net[:-1] += liq[1:]
        net[-1] += L_R * x_drum
        net[1:] += vap[:-1]
        net -= liq + vap
        net[col.feed_stage] += feed_src
        net_reb = L_S - B - V_S
        # The sump and the stripping-tray reserve are one pool for
        # inventory: the sump fills first up to SUMP_CAP and drains
        # first; the reserve takes the rest. dM_reb + dM_strip is
        # always net_reb, so the balance stays exact.
        if net_reb >= 0.0:
            dM_reb = net_reb if st["M_reb"] < SUMP_CAP else 0.0
        else:
            dM_reb = net_reb if st["M_reb"] > 0.0 else 0.0
        dM_strip = net_reb - dM_reb
        dx = np.empty_like(x)
        dx[1:] = net[1:] / col.M[1:, None]
        dx[0] = (net[0] - x[0] * net_reb) / max(C_reb, 1.0)

        dM_c = C_r_mat - delivered - vap_flash
        if M_c > 1.0:
            dx_pool = (C_r_mat * y_top - delivered * x_res
                       - vap_flash * y_pool_eq
                       - x_pool * dM_c) / M_c
        else:
            dx_pool = (y_top - x_pool) * max(C_r_mat, 0.0)

        drum_in = delivered + vap_flash + vap_pass
        bp_in = W_bp if W_bp > 0 else 0.0
        bp_out = -W_bp if W_bp < 0 else 0.0
        gamma_y_drum = gamma_d * self.mix.psat(np.asarray(T_drum)) / P_drum
        y_drum = gamma_y_drum * x_drum
        dM_drum = drum_in + bp_in - bp_out - L_R - D
        drum_mol_in = (delivered * x_res + vap_flash * y_pool_eq
                       + vap_pass * y_top
                       + bp_in * y_top - bp_out * y_drum
                       - (L_R + D) * x_drum)
        dx_drum = (drum_mol_in - x_drum * dM_drum) / M_drum
        # Drum temperature: cold condensate in, latent heat from vapour
        # that condenses in the drum (riser flash vapour and bypass
        # inflow), latent heat carried out by vapour drawn back.
        lam_pool = float(np.dot(y_pool_eq, self.mix.lam))
        lam_top = float(np.dot(y_top, self.mix.lam))
        heat = (delivered * oh.CP_LIQ * (T_pool - T_drum)
                + vap_flash * (oh.CP_LIQ * (T_pool - T_drum) + lam_pool)
                + vap_pass * (oh.CP_LIQ * (T_cond - T_drum) + lam_top)
                + bp_in * lam_top - bp_out * lam_top)
        dT_drum = heat / max(M_drum * oh.CP_LIQ, 1.0)

        # ---- pressure derivatives -----------------------------------------
        dP_col = (R_GAS * T_st[-1] / V_COL
                  * (V_R - W_in - W_bp - W_relief) / 1000.0)
        V_vap_c = max(V_COND_TOTAL - M_c * MOLAR_VOL_LIQ, 0.02)
        dP_cond = (R_GAS * T_cond / V_vap_c * (W_in - C_r) / 1000.0)

        # ---- cooling tank ---------------------------------------------------
        makeup = op["makeup"] * MU_MAX
        dT_tank = oh.cooling_tank_rhs(T_tank, T_w_out, circ, makeup,
                                      self.T_supply) \
            - UA_TANK * (T_tank - T_AMB) / (2000.0 * CP_WATER)

        ds = np.concatenate([dx.ravel(), dx_pool, dx_drum,
                             [dM_reb, dM_c, dM_drum, dP_col, dP_cond,
                              dP_chest, dT_tank, dT_drum, dM_strip]])
        self.last = {
            "P_col": P_col, "P_cond": P_cond, "P_drum": P_drum,
            "P_chest": P_chest, "T_drum": T_drum, "T_tank": T_tank,
            "T_w_out": T_w_out, "T_cond": T_cond, "T_pool": T_pool,
            "T_top": float(T_st[-1]), "T_reb": float(T_st[0]),
            "V_S": V_S, "V_R": V_R, "L_R": L_R, "L_S": L_S, "D": D,
            "B": B, "W_in": W_in, "W_bp": W_bp, "C_r": C_r_mat,
            "drainage": delivered, "drainage_raw": raw,
            "margin": margin, "flash_frac": flash_frac,
            "flooded": flooded, "Q_reb": Q_reb, "Q_cond": Q_cond,
            "W_steam": W_steam, "W_relief": W_relief,
            "M_reb": M_reb, "M_c": M_c, "M_drum": M_drum,
            "F": col.F, "feed_op": op_feed,
            "feed_setpoint": self.feed_setpoint,
            "feed_auto": self.feed_auto,
            "x_drum": x_drum.copy(), "x_pool": x_pool.copy(),
            "y_top": y_top.copy(), "psi": psi,
            "ruptured": P_col >= oh.P_RUPTURE,
            "relief_lifting": W_relief > 0.0,
            "high_pressure_alarm": P_col >= 0.9 * oh.P_RELIEF_SET,
        }
        return ds

    def outputs(self, s, openings=None):
        """Display quantities at a state (evaluates the right-hand side
        once to refresh flows; the derivative is discarded)."""
        self.rhs(s, openings)
        out = dict(self.last)
        x, _, _, _ = self._unpack(np.asarray(s, dtype=float))
        out["x_stages"] = x
        out["distillate_x"] = out["x_drum"]
        out["bottoms_x"] = self._clean(x[0])
        out["drum_level_frac"] = out["M_drum"] / M_DRUM_MAX
        out["condenser_flooded_frac"] = out["flooded"]
        out["reboiler_level_frac"] = out["M_reb"] / M_REB_MAX
        return out

    def step(self, s, dt, openings=None):
        """Advance the state by dt seconds (fourth-order Runge-Kutta
        with internal substeps of at most 0.05 s)."""
        s = np.asarray(s, dtype=float)
        if self.feed_auto:
            _, _, _, st = self._unpack(s)
            P_col = max(st["P_col"], 20.0)
            if self._feed_psi_sup >= 1.0:
                law = _vap_factor(self.col.feed_P, P_col, RC_VAP)
                if law > 0.0025:
                    target = 100.0 * self.feed_setpoint / (
                        KV_FEED_VAP * law)
                else:
                    target = 100.0
            else:
                dP = self.col.feed_P - max(P_col, self._feed_pv)
                if dP > 0.25:
                    target = 100.0 * self.feed_setpoint / (
                        KV_FEED * math.sqrt(dP))
                else:
                    target = 100.0
            target = min(100.0, max(0.0, target))
            self.feed_op_eff += (target - self.feed_op_eff) * (
                1.0 - math.exp(-dt / FEED_TAU))
        n_sub = max(1, int(math.ceil(dt / 0.05)))
        h = dt / n_sub
        for _ in range(n_sub):
            k1 = self.rhs(s, openings)
            k2 = self.rhs(s + 0.5 * h * k1, openings)
            k3 = self.rhs(s + 0.5 * h * k2, openings)
            k4 = self.rhs(s + h * k3, openings)
            s = s + (h / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        return s
