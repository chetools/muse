"""Verification run for the Column A core (stage report values)."""

import time

import numpy as np

import column_a as ca

KM = 1000.0 / 60.0  # 1 kmol/min in mol/s


def fd_jacobian(z0, u0, p, g):
    """Central finite-difference Jacobian of rhs wrt z."""
    n = len(z0)
    J = np.zeros((n, n))
    for i in range(n):
        h = 1e-6 * max(1.0, abs(z0[i]))
        zp = z0.copy(); zp[i] += h
        zm = z0.copy(); zm[i] -= h
        J[:, i] = (ca.rhs(zp, u0, p, g, np) - ca.rhs(zm, u0, p, g, np)) / (2 * h)
    return J


def main():
    # ---- Column A anchor: N = 39 trays, NT = 41 stages ----
    p = ca.ColumnParams(n_trays=39)
    g = ca.Geometry(p)
    z0, res = ca.steady_state(p, g)
    nt = p.nt
    print(f"ANCHOR NT={nt} feed_stage(0-based)={p.feed_stage}")
    print(f"  xD = {z0[nt-1]:.4f} (source 0.99), xB = {z0[0]:.4f} (source 0.01)")
    print(f"  steady residual max|rhs| = {res:.3e}")

    # autograd Jacobian (open loop) vs finite differences
    import autograd.numpy as anp
    from autograd import jacobian
    t0 = time.time()
    A_open = np.asarray(jacobian(
        lambda zz: ca.rhs(zz, p.u0, p, g, anp))(z0.astype(float)))
    t_jac = time.time() - t0
    Jfd = fd_jacobian(z0, p.u0, p, g)
    err = np.max(np.abs(A_open - Jfd))
    scale = np.max(np.abs(Jfd))
    print(f"  autograd A: {A_open.shape}, time {t_jac:.2f} s; "
          f"max|A - FD| = {err:.3e} (max|A| = {scale:.3e})")

    poles = np.linalg.eigvals(A_open)
    re = np.sort(np.real(poles))[::-1]
    print(f"  rightmost poles (1/s): {re[0]:.3e}, {re[1]:.3e}, {re[2]:.3e}")
    print(f"  dominant pole per min: {re[2]*60:.4e} (source -5.1562e-03)")

    # ---- Configuration gains and RGA at the anchor ----
    published_rga11 = {"LV": 35.1, "DV": 0.45, "LB": 0.56,
                       "DB": float("inf"), "RR": 3.22}
    for config in ca.CONFIGS:
        A, B, C = ca.linearise(z0, p, g, config, "perfect")
        if config == "DB":
            # Singular A (pole at origin): finite gains only for
            # balanced directions, by least squares on A z = -B e.
            ev = np.linalg.eigvals(A)
            print(f"  DB: smallest |pole| = {np.min(np.abs(ev)):.2e} "
                  f"(integrating, published RGA infinite)")
            esplit = np.array([1.0, -1.0, 0.0, 0.0])
            zsplit, *_ = np.linalg.lstsq(A, -B @ esplit, rcond=None)
            print(f"    DB balanced split gains: d xD = {C[0] @ zsplit:+.5f}, "
                  f"d xB = {C[1] @ zsplit:+.5f} per mol/s split")
            exf = np.array([0.0, 0.0, 0.0, 1.0])
            zxf, *_ = np.linalg.lstsq(A, -B @ exf, rcond=None)
            print(f"    DB xF gains: d xD = {C[0] @ zxf:+.4f}, "
                  f"d xB = {C[1] @ zxf:+.4f}")
            continue
        G = ca.steady_gains(A, B, C)
        lam, shortcut = ca.rga(G[:, :2])
        rowsum = np.max(np.abs(lam.sum(axis=1) - 1.0))
        sc_err = abs(lam[0, 0] - shortcut)
        print(f"  {config}: RGA11 = {lam[0,0]:9.3f} "
              f"(published {published_rga11[config]}), "
              f"rowsum err {rowsum:.2e}, shortcut err {sc_err:.2e}")
        if config == "LV":
            Gsrc = G[:, :2] * KM  # per kmol/min, source units
            print(f"    LV gains per kmol/min: "
                  f"[[{Gsrc[0,0]:.3f}, {Gsrc[0,1]:.3f}], "
                  f"[{Gsrc[1,0]:.3f}, {Gsrc[1,1]:.3f}]]")
            print(f"    LV disturbance gains: d xD/dF = {G[0,2]:.5f} "
                  f"per mol/s, d xD/dxF = {G[0,3]:.3f}, "
                  f"d xB/dF = {G[1,2]:.5f}, d xB/dxF = {G[1,3]:.3f}")

    # P-only gains must equal perfect gains at steady state
    A, B, C = ca.linearise(z0, p, g, "LV", "P")
    Gp = ca.steady_gains(A, B, C)
    A2, B2, C2 = ca.linearise(z0, p, g, "LV", "perfect")
    Gf = ca.steady_gains(A2, B2, C2)
    print(f"  LV P-only vs perfect gains: max diff "
          f"{np.max(np.abs(Gp - Gf)):.3e}")

    # ---- Default column: N = 5 trays ----
    p5 = ca.ColumnParams(n_trays=5)
    g5 = ca.Geometry(p5)
    z5, res5 = ca.steady_state(p5, g5)
    nt5 = p5.nt
    print(f"DEFAULT N=5: NT={nt5}, xD = {z5[nt5-1]:.4f}, "
          f"xB = {z5[0]:.4f}, residual {res5:.3e}")
    print(f"  profile x = {np.round(z5[:nt5], 3)}")
    A5, B5, C5 = ca.linearise(z5, p5, g5, "LV", "perfect")
    G5 = ca.steady_gains(A5, B5, C5)
    lam5, _ = ca.rga(G5[:, :2])
    print(f"  LV gains (SI): [[{G5[0,0]:.5f}, {G5[0,1]:.5f}], "
          f"[{G5[1,0]:.5f}, {G5[1,1]:.5f}]], RGA11 = {lam5[0,0]:.3f}")
    t0 = time.time()
    rows, tau_dom = ca.foptd_matrix(A5, B5, C5, G5)
    print(f"  FOPTD fit (LV, N=5), tau_dom = {tau_dom:.1f} s, "
          f"fit time {time.time()-t0:.1f} s")
    names_in = ["L", "V", "F", "xF"]
    names_out = ["xD", "xB"]
    for (i, j, K, tau, theta, e) in rows:
        print(f"    {names_out[i]} <- {names_in[j]:>2}: K = {K:+.5f}, "
              f"tau = {tau:9.1f} s, theta = {theta:8.1f} s, err = {e:5.2f} %")


if __name__ == "__main__":
    main()
