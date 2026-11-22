"""Round-3 batch column: dynamic MESH batch distillation with
per-tray liquid holdup (ChemCAD BATC, itype 50, in dynamic form).

Symbols, defined at first use: still-pot total amount W in moles
(mol); pot liquid mole fraction of component i, x_pot_i
(dimensionless); tray index j, an integer from 1 to N where N is
the number of trays (dimensionless count); per-tray liquid holdup
H_j in mol; tray liquid mole fraction x_j_i (dimensionless);
vapour mole fraction y_j_i leaving a stage in equilibrium with
its liquid (dimensionless); boil-up rate V_b in mol/s; reflux
ratio R_r (dimensionless, reflux flow / distillate flow);
distillate rate D in mol/s, D = V_b / (R_r + 1); liquid downflow
L in mol/s, L = R_r * D; time t in seconds (s); relative
volatility alpha_i (dimensionless, per component).

Formulation (MESH, dynamic):
- Material (M): the state is the component holdup vector of the
  pot and of every tray, n_j_i in mol. For tray j,
    d n_j_i / dt = L * x_{j+1,i} + V_b * y_{j-1,i}
                   - L * x_{j,i} - V_b * y_{j,i},
  with the condenser liquid (composition y_{N,i}, total
  condenser) entering tray N in place of L * x_{N+1,i}, and the
  pot vapour y_{0,i} entering tray 1. For the pot,
    d n_pot_i / dt = L * x_{1,i} - V_b * y_{0,i}
  (for N = 0 the pot receives its own condensate reflux and the
  equation reduces to d n_pot_i / dt = -D * y_{0,i}).
  Total holdup of every tray is constant under these flows, so
  H_j is a state whose total is conserved and whose composition
  evolves; the pot total falls at rate D.
- Equilibrium (E): y_j = thermo.equilibrium_y(x_j) on every
  stage. The thermo object is caller-supplied; it must provide
  equilibrium_y(x) returning a mole-fraction list. The adapter
  ConstRelVolThermo in this module provides the constant
  relative volatility form y_i = alpha_i x_i / sum_k(alpha_k
  x_k). Any caller object with the same method works.
- Summation (S): mole fractions on every stage sum to 1 by the
  normalisation inside the equilibrium relation and by tracking
  component amounts rather than fractions.
- Enthalpy / hydraulics (H): replaced by the operating
  specification, as in the Round-2 simple model: constant
  boil-up V_b and constant reflux ratio R_r (constant molal
  overflow), so stage temperatures are not state variables. If
  the thermo object also provides bubble_T(x) returning a
  temperature in kelvin (K), stage temperatures are reported as
  diagnostics; the adapter here does not, and none are reported.
  This is a dynamic MESH column under a CMO operating
  specification, not a full energy-balance MESH column; that
  scope is stated, not hidden.

Integration: scipy solve_ivp, Radau (implicit, suited to the
stiff small-holdup limit), with a terminal event when the pot
mole fraction of component 0 reaches x_stop from above, or
integration to t_max when x_stop is None.
All parameters are caller data; no chemical identity is
embedded.
"""
import numpy as np
from scipy.integrate import solve_ivp


class ConstRelVolThermo:
    """Constant relative volatility thermo adapter.

    alpha is a list of relative volatilities alpha_i
    (dimensionless), one per component, supplied by the caller.
    equilibrium_y(x) returns y_i = alpha_i x_i / sum_k(alpha_k
    x_k) as a list of mole fractions (dimensionless).
    """

    def __init__(self, alpha):
        self.alpha = [float(a) for a in alpha]

    def equilibrium_y(self, x):
        ax = [self.alpha[i] * float(x[i]) for i in range(len(x))]
        s = sum(ax)
        return [v / s for v in ax]


def _as_thermo(thermo_or_alpha):
    if hasattr(thermo_or_alpha, "equilibrium_y"):
        return thermo_or_alpha
    return ConstRelVolThermo(thermo_or_alpha)


def batch_column_mesh(x_pot0, W0, thermo, n_trays, tray_holdup,
                      tray_x0, R_r, V_b, x_stop=None, t_max=1e5,
                      rtol=1e-8, atol=1e-11, n_out=200):
    """Run the dynamic batch column.

    x_pot0: initial pot composition (mole fractions). W0:
    initial pot amount in mol. thermo: caller thermo object (or
    a list of relative volatilities, wrapped in
    ConstRelVolThermo). n_trays: tray count N. tray_holdup:
    per-tray holdup H_j in mol, a scalar (same for all trays) or
    a list of length N. tray_x0: initial tray composition, one
    composition (applied to every tray) or a list of N
    compositions. R_r: reflux ratio. V_b: boil-up rate in mol/s.
    x_stop: stop when the pot mole fraction of component 0 falls
    to this value (None: run to t_max). t_max in s.
    Returns a dict: t (final time, s), W (final pot amount,
    mol), x_pot, tray_x (list of compositions), tray_holdups
    (list, mol), D_total (mol taken off), xD_avg (cumulative
    average distillate composition), distillate_amounts (mol per
    component), y_D_final (instantaneous final distillate
    composition), and history (sampled t, x_pot_0, y_D_0,
    xD_avg_0 lists).
    """
    thermo = _as_thermo(thermo)
    x_pot0 = np.asarray(x_pot0, dtype=float)
    nc = len(x_pot0)
    N = int(n_trays)
    if np.isscalar(tray_holdup):
        H = [float(tray_holdup)] * N
    else:
        H = [float(h) for h in tray_holdup]
    if N and np.ndim(tray_x0) == 1:
        tray_init = [np.asarray(tray_x0, dtype=float)] * N
    elif N:
        tray_init = [np.asarray(v, dtype=float) for v in tray_x0]
    else:
        tray_init = []
    D = V_b / (R_r + 1.0)
    L = R_r * D

    # State: pot amounts, tray amounts (N x nc), cumulative
    # distillate amounts.
    y0 = list(x_pot0 * W0)
    for j in range(N):
        y0.extend(list(tray_init[j] * H[j]))
    y0.extend([0.0] * nc)
    y0 = np.array(y0, dtype=float)
    n_pot = nc
    n_tray = N * nc

    def unpack(s):
        pot = s[:n_pot]
        trays = [s[n_pot + j * nc: n_pot + (j + 1) * nc]
                 for j in range(N)]
        dcum = s[n_pot + n_tray:]
        return pot, trays, dcum

    def rhs(t, s):
        pot, trays, _ = unpack(s)
        W = pot.sum()
        x_pot = pot / W if W > 0 else x_pot0
        y_pot = np.array(thermo.equilibrium_y(list(x_pot)))
        xs, ys = [], []
        for j in range(N):
            xj = trays[j] / H[j] if H[j] > 0 else x_pot
            xs.append(xj)
            ys.append(np.array(thermo.equilibrium_y(list(xj))))
        y_top = ys[-1] if N else y_pot
        d = np.zeros_like(s)
        # Pot.
        if N:
            d[:nc] = L * xs[0] - V_b * y_pot
        else:
            d[:nc] = -D * y_pot
        # Trays.
        for j in range(N):
            up_vap = y_pot if j == 0 else ys[j - 1]
            down_liq = y_top if j == N - 1 else xs[j + 1]
            # For the top tray the liquid entering is condensate
            # of composition y_top; for others it is the liquid
            # leaving the tray above.
            d[n_pot + j * nc: n_pot + (j + 1) * nc] = (
                L * down_liq + V_b * up_vap - L * xs[j]
                - V_b * ys[j])
        d[n_pot + n_tray:] = D * y_top
        return d

    events = None
    if x_stop is not None:
        def ev(t, s):
            pot = s[:nc]
            return pot[0] / pot.sum() - x_stop
        ev.terminal = True
        ev.direction = -1
        events = ev
    t_eval = np.linspace(0.0, t_max, int(n_out)) \
        if x_stop is None else None
    sol = solve_ivp(rhs, (0.0, float(t_max)), y0, method="Radau",
                    rtol=rtol, atol=atol, events=events,
                    t_eval=t_eval, dense_output=(x_stop is not None))
    s = sol.y[:, -1]
    pot, trays, dcum = unpack(s)
    W = float(pot.sum())
    tray_x = [list(trays[j] / H[j]) if H[j] > 0 else list(x_pot0)
              for j in range(N)]
    y_top_final = thermo.equilibrium_y(tray_x[-1]) if N else \
        thermo.equilibrium_y(list(pot / W))
    # History from the solution samples (re-sampled evenly when
    # an event stopped the run).
    if x_stop is not None:
        ts = np.linspace(0.0, sol.t[-1], int(n_out))
        ss = sol.sol(ts)
    else:
        ts, ss = sol.t, sol.y
    hist = {"t": [], "x_pot_0": [], "y_D_0": [], "xD_avg_0": []}
    for k in range(ss.shape[1]):
        p_k, tr_k, dc_k = unpack(ss[:, k])
        xk = p_k / p_k.sum()
        xtop = (tr_k[-1] / H[-1]) if N and H[-1] > 0 else xk
        ytop = thermo.equilibrium_y(list(xtop)) if N else \
            thermo.equilibrium_y(list(xk))
        hist["t"].append(float(ts[k]))
        hist["x_pot_0"].append(float(xk[0]))
        hist["y_D_0"].append(float(ytop[0]))
        hist["xD_avg_0"].append(
            float(dc_k[0] / dc_k.sum()) if dc_k.sum() > 0
            else float(ytop[0]))
    return {"t": float(sol.t[-1]), "W": W,
            "x_pot": list(pot / W), "tray_x": tray_x,
            "tray_holdups": H, "D_total": float(dcum.sum()),
            "xD_avg": list(dcum / dcum.sum())
            if dcum.sum() > 0 else [0.0] * nc,
            "distillate_amounts": list(dcum),
            "pot_amounts": list(pot),
            "tray_amounts": [list(v) for v in trays],
            "y_D_final": list(y_top_final), "history": hist}
