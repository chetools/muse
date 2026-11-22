//! Full MESH rigorous tower: Rust port of python/columns_mesh.py.
//!
//! MESH denotes the per-stage equation set solved here: Material
//! balances, Equilibrium relations, Summation equations and
//! entHalpy balances on every stage. Symbols, defined at first
//! use, all quantities in SI units: the stage index j
//! (dimensionless integer) is counted from the bottom, stage 0 is
//! the reboiler, stages 1 to N are trays, where N is the number
//! of trays (dimensionless integer); the total condenser sits
//! above stage N and is not a MESH stage. The component index is
//! i (dimensionless integer) and nc is the number of components
//! (dimensionless integer). x_ij is the liquid mole fraction of
//! component i leaving stage j (dimensionless); y_ij is the
//! vapour mole fraction of component i leaving stage j
//! (dimensionless). T_j is the temperature of stage j in kelvin
//! (K). P_j is the pressure of stage j in pascal (Pa), linear in
//! j between the bottom pressure P_bottom in pascal (Pa) at
//! stage 0 and the top pressure P_top in pascal (Pa) at stage N.
//! L_j is the liquid molar flow leaving stage j downward, in
//! moles per second (mol/s); V_j is the vapour molar flow
//! leaving stage j upward, in mol/s. L_0 is the bottoms product
//! rate in mol/s (an unknown, fixed by the stage equations).
//! The liquid entering stage N from the condenser is the reflux,
//! of rate L_R in mol/s. A feed has molar flow F in mol/s and
//! feed mole fractions z_i (dimensionless); D is the distillate
//! rate in mol/s. K_ij is the equilibrium ratio of component i
//! on stage j (dimensionless). E_j is the Murphree vapour
//! efficiency of stage j (dimensionless), applied component by
//! component with the same E_j for every component on the stage;
//! the reboiler has E_0 = 1. hL_j is the molar enthalpy of the
//! liquid leaving stage j, in joules per mole (J/mol); hV_j is
//! the molar enthalpy of the vapour leaving stage j, in J/mol.
//! Q_reb is the reboiler duty in watts (W); Q_cond is the
//! condenser duty in W (heat removed, reported positive). A
//! liquid side draw on stage j has rate S_Lj in mol/s at
//! composition x_ij; a vapour side draw has rate S_Vj in mol/s
//! at composition y_ij. A pumparound withdraws liquid at rate
//! PA in mol/s from a draw stage, removes a duty Q_PA in W in an
//! external cooler, and returns the liquid to a stage above at
//! the draw-stage composition and at a molar enthalpy lower by
//! Q_PA / PA in J/mol.
//!
//! Thermo is the RaoultThermo of columns.rs (the adapter the
//! Python solver is exercised with in its battery). The solver
//! replaces scipy least_squares with the local
//! Levenberg-Marquardt solver below (Marquardt diagonal
//! scaling), started from the constant-molal-overflow (CMO)
//! solution, as in the Python.
//! Material residuals are scaled by the total feed rate in mol/s
//! and enthalpy residuals by that rate times 30000 J/mol, a
//! latent-heat scale, as in the Python.

use crate::columns::RaoultThermo;
use crate::linalg::solve_lin;

/// A feed stream entering a stage: (stage, flow in mol/s,
/// composition as mole fractions).
pub type FeedSpec = (usize, f64, Vec<f64>);
/// A pumparound: (draw stage, return stage, rate in mol/s,
/// duty in watts (W)).
pub type PumparoundSpec = (usize, usize, f64, f64);

pub struct MeshResult {
    pub x: Vec<Vec<f64>>,
    pub y: Vec<Vec<f64>>,
    pub t: Vec<f64>,
    pub p: Vec<f64>,
    pub l: Vec<f64>,
    pub v: Vec<f64>,
    pub b: f64,
    pub d: f64,
    pub x_bottoms: Vec<f64>,
    pub y_top: Vec<f64>,
    pub x_distillate: Vec<f64>,
    pub q_reboiler: f64,
    pub q_condenser: f64,
    pub t_condenser: f64,
    pub stage_enthalpy_residuals_w: Vec<f64>,
    pub stage_material_residuals_mol_s: Vec<f64>,
    pub max_enthalpy_residual_w: f64,
    pub max_material_residual_mol_s: f64,
    pub max_summation_residual: f64,
    pub overall_balance_residual_mol_s: f64,
    pub solver_cost: f64,
}

// --- CMO initial guess (port of columns.rigorous_tower, total
// condenser, with feeds, liquid draws and pumparounds) ---------

struct CmoResult {
    x: Vec<Vec<f64>>,
    t: Vec<f64>,
    q_reboiler: f64,
}

fn cmo_tower(
    feeds: &[(usize, f64, Vec<f64>)],
    n_trays: usize,
    d_flow: f64,
    l_r: f64,
    p: f64,
    th: &RaoultThermo,
    draws: &[(usize, f64)],
    pumparounds: &[PumparoundSpec],
) -> CmoResult {
    let nc = feeds[0].2.len();
    let nst = n_trays + 1;
    let f_tot: f64 = feeds.iter().map(|f| f.1).sum();
    let draw_tot: f64 = draws.iter().map(|d| d.1).sum();
    let b_flow = f_tot - d_flow - draw_tot;
    let draw_at = |j: usize| -> f64 {
        draws.iter().filter(|d| d.0 == j).map(|d| d.1).sum()
    };
    let feed_at = |j: usize| -> f64 {
        feeds.iter().filter(|f| f.0 == j).map(|f| f.1).sum()
    };
    let mut l_out = vec![0.0; nst];
    let mut run = l_r;
    for j in (1..nst).rev() {
        run += feed_at(j) - draw_at(j);
        l_out[j] = run;
    }
    l_out[0] = b_flow;
    for &(d_st, r_st, rate, _duty) in pumparounds {
        for j in d_st..r_st {
            l_out[j] -= rate;
        }
    }
    let mut v_up = vec![0.0; nst];
    v_up[nst - 1] = l_r + d_flow;
    for j in 1..nst - 1 {
        let f_above: f64 = feeds.iter().filter(|f| f.0 > j).map(|f| f.1).sum();
        let d_above: f64 = draws.iter().filter(|d| d.0 > j).map(|d| d.1).sum();
        v_up[j] = l_out[j + 1] + d_flow + d_above - f_above;
    }
    if n_trays >= 1 {
        v_up[0] = l_out[1] - b_flow;
    }
    let z0 = feeds[0].2.clone();
    let mut x: Vec<Vec<f64>> = vec![z0; nst];
    let relax = 0.6f64;
    for _sweep in 0..500 {
        let t: Vec<f64> = (0..nst).map(|j| th.bubble_t(&x[j], p)).collect();
        let k: Vec<Vec<f64>> = (0..nst).map(|j| th.k(&x[j], t[j], p)).collect();
        let mut x_new = vec![vec![0.0; nc]; nst];
        for c in 0..nc {
            let mut a = vec![vec![0.0; nst]; nst];
            let mut rhs = vec![0.0; nst];
            for j in 0..nst {
                a[j][j] += l_out[j] + v_up[j] * k[j][c] + draw_at(j);
                if j < nst - 1 {
                    a[j][j + 1] -= l_out[j + 1];
                } else {
                    a[j][j] -= l_r * k[j][c];
                }
                if j > 0 {
                    a[j][j - 1] -= v_up[j - 1] * k[j - 1][c];
                }
                for &(st, fl, ref zc) in feeds {
                    if st == j {
                        rhs[j] -= fl * zc[c];
                    }
                }
            }
            let rhsn: Vec<f64> = rhs.iter().map(|v| -v).collect();
            let sol = solve_lin(&a, &rhsn).unwrap();
            for j in 0..nst {
                x_new[j][c] = sol[j];
            }
        }
        let mut err = 0.0f64;
        for j in 0..nst {
            let s: f64 = x_new[j].iter().map(|v| v.max(0.0)).sum();
            for c in 0..nc {
                x_new[j][c] = x_new[j][c].max(0.0) / s;
                err = err.max((x_new[j][c] - x[j][c]).abs());
            }
        }
        for j in 0..nst {
            let mut row: Vec<f64> = (0..nc)
                .map(|c| relax * x_new[j][c] + (1.0 - relax) * x[j][c])
                .collect();
            let s: f64 = row.iter().sum();
            for v in row.iter_mut() {
                *v /= s;
            }
            x[j] = row;
        }
        if err < 1e-10 {
            break;
        }
    }
    let t: Vec<f64> = (0..nst).map(|j| th.bubble_t(&x[j], p)).collect();
    let k: Vec<Vec<f64>> = (0..nst).map(|j| th.k(&x[j], t[j], p)).collect();
    let hl: Vec<f64> = (0..nst).map(|j| th.h_liq(&x[j], t[j])).collect();
    let hv: Vec<f64> = (0..nst)
        .map(|j| {
            let mut yv: Vec<f64> = (0..nc).map(|c| k[j][c] * x[j][c]).collect();
            let s: f64 = yv.iter().sum();
            for v in yv.iter_mut() {
                *v /= s;
            }
            th.h_vap(&yv, t[j])
        })
        .collect();
    let qr = b_flow * hl[0] + v_up[0] * hv[0] - l_out[1] * hl[1];
    CmoResult { x, t, q_reboiler: qr }
}

// --- MESH tower -------------------------------------------------

/// Solve the MESH tower. `efficiency` is a slice of length 1
/// (a scalar Murphree efficiency applied to every tray) or of
/// length n_trays + 1 giving E_j per stage (entry 0 is ignored,
/// the reboiler is an equilibrium stage). `p_bottom` defaults
/// to `p_top` when None. Draws are (stage, rate in mol/s) with
/// stage a tray index 1..=n_trays. Extra feeds are saturated-
/// liquid feeds as FeedSpec entries.
#[allow(clippy::too_many_arguments)]
pub fn mesh_tower(
    z_feed: &[f64],
    f: f64,
    n_trays: usize,
    feed_stage: usize,
    d_flow: f64,
    l_r: f64,
    th: &RaoultThermo,
    p_top: f64,
    p_bottom: Option<f64>,
    efficiency: &[f64],
    liquid_draws: &[(usize, f64)],
    vapour_draws: &[(usize, f64)],
    pumparounds: &[PumparoundSpec],
    extra_feeds: &[FeedSpec],
) -> MeshResult {
    let p_bottom = p_bottom.unwrap_or(p_top);
    let nc = z_feed.len();
    let n = n_trays;
    let nst = n + 1;
    let mut eff: Vec<f64> = if efficiency.len() == 1 {
        vec![efficiency[0]; nst]
    } else {
        assert_eq!(efficiency.len(), nst, "efficiency list must have n_trays+1 entries");
        efficiency.to_vec()
    };
    eff[0] = 1.0;
    let p_prof: Vec<f64> = (0..nst)
        .map(|j| {
            p_bottom + (p_top - p_bottom) * if n > 0 { j as f64 / n as f64 } else { 0.0 }
        })
        .collect();
    // Merge feeds on the same stage (flow-weighted composition).
    let mut feeds: Vec<FeedSpec> = Vec::new();
    let add_feed = |feeds: &mut Vec<FeedSpec>, st: usize, fl: f64, zc: &[f64]| {
        if let Some(e) = feeds.iter_mut().find(|e| e.0 == st) {
            let pf = e.1;
            for i in 0..nc {
                e.2[i] = (pf * e.2[i] + fl * zc[i]) / (pf + fl);
            }
            e.1 = pf + fl;
        } else {
            feeds.push((st, fl, zc.to_vec()));
        }
    };
    add_feed(&mut feeds, feed_stage, f, z_feed);
    for (st, fl, zc) in extra_feeds {
        add_feed(&mut feeds, *st, *fl, zc);
    }
    let f_tot: f64 = feeds.iter().map(|e| e.1).sum();
    let mut sl = vec![0.0; nst];
    for &(st, rate) in liquid_draws {
        assert!((1..=n).contains(&st), "liquid draw stage out of range");
        sl[st] += rate;
    }
    let mut sv = vec![0.0; nst];
    for &(st, rate) in vapour_draws {
        assert!((1..=n).contains(&st), "vapour draw stage out of range");
        sv[st] += rate;
    }
    for &(d_st, r_st, _rate, _duty) in pumparounds {
        assert!(1 <= d_st && d_st < r_st && r_st <= n, "pumparound stages out of range");
    }
    let v_top = d_flow + l_r + sv[n];
    let feed_h: Vec<f64> = feeds
        .iter()
        .map(|(st, _fl, zc)| {
            let tb = th.bubble_t(zc, p_prof[*st]);
            th.h_liq(zc, tb)
        })
        .collect();
    let feed_idx = |feeds: &Vec<FeedSpec>, j: usize| -> Option<usize> {
        feeds.iter().position(|e| e.0 == j)
    };

    // Initial guess from the CMO tower at the mean pressure.
    let p_mean = 0.5 * (p_top + p_bottom);
    let cmo_draws: Vec<(usize, f64)> = (0..nst)
        .filter(|&s| sl[s] > 0.0)
        .map(|s| (s, sl[s]))
        .collect();
    let cmo = cmo_tower(&feeds, n, d_flow, l_r, p_mean, th, &cmo_draws, pumparounds);
    let mut x0: Vec<Vec<f64>> = cmo.x.clone();
    for j in 0..nst {
        for v in x0[j].iter_mut() {
            *v = v.max(1e-9);
        }
        let s: f64 = x0[j].iter().sum();
        for v in x0[j].iter_mut() {
            *v /= s;
        }
    }
    let t0 = cmo.t.clone();
    let mut l0g = vec![0.0; nst];
    let mut run = l_r;
    for j in (1..nst).rev() {
        run += feed_idx(&feeds, j).map(|i| feeds[i].1).unwrap_or(0.0) - sl[j];
        l0g[j] = run;
    }
    let sl_tot: f64 = sl.iter().sum();
    let sv_tot: f64 = sv.iter().sum();
    l0g[0] = (f_tot - d_flow - sl_tot - sv_tot).max(0.05 * f_tot);
    let mut v0g = vec![v_top; nst];
    for j in 1..nst - 1 {
        let f_above: f64 = feeds.iter().filter(|e| e.0 > j).map(|e| e.1).sum();
        v0g[j] = l0g[j + 1] + d_flow + sv[j + 1..].iter().sum::<f64>()
            + sl[j + 1..].iter().sum::<f64>() - f_above;
    }
    v0g[0] = if n >= 1 { (l0g[1] - l0g[0]).max(0.05 * f_tot) } else { v_top };

    let nx = nst * nc;
    let nl = nst; // L_0 .. L_N
    let nv = n; // V_0 .. V_{N-1}; V_N is fixed
    let e_scale = (f_tot * 30000.0).max(1.0);

    let profiles = |x: &Vec<Vec<f64>>, t: &Vec<f64>| {
        let k: Vec<Vec<f64>> = (0..nst).map(|j| th.k(&x[j], t[j], p_prof[j])).collect();
        let mut y = vec![vec![0.0; nc]; nst];
        for i in 0..nc {
            y[0][i] = k[0][i] * x[0][i];
        }
        for j in 1..nst {
            for i in 0..nc {
                y[j][i] = (1.0 - eff[j]) * y[j - 1][i] + eff[j] * k[j][i] * x[j][i];
            }
        }
        let hl: Vec<f64> = (0..nst).map(|j| th.h_liq(&x[j], t[j])).collect();
        let hv: Vec<f64> = (0..nst).map(|j| th.h_vap(&y[j], t[j])).collect();
        (k, y, hl, hv)
    };

    let residuals = |v: &[f64]| -> Vec<f64> {
        let mut x = vec![vec![0.0; nc]; nst];
        for j in 0..nst {
            for i in 0..nc {
                x[j][i] = v[j * nc + i];
            }
        }
        let t: Vec<f64> = v[nx..nx + nst].to_vec();
        let l: Vec<f64> = v[nx + nst..nx + nst + nl].to_vec();
        let mut vv: Vec<f64> = v[nx + nst + nl..nx + nst + nl + nv].to_vec();
        vv.push(v_top);
        let qr = v[v.len() - 1];
        let (_k, y, hl, hv) = profiles(&x, &t);
        let t_cond = th.bubble_t(&y[n], p_prof[n]);
        let h_reflux = th.h_liq(&y[n], t_cond);
        let mut res: Vec<f64> = Vec::with_capacity(nst * (nc + 3));
        for j in 0..nst {
            let mut inflow = vec![0.0; nc];
            let mut inflow_h = 0.0f64;
            if j < n {
                for i in 0..nc {
                    inflow[i] += l[j + 1] * x[j + 1][i];
                }
                inflow_h += l[j + 1] * hl[j + 1];
            } else {
                for i in 0..nc {
                    inflow[i] += l_r * y[n][i];
                }
                inflow_h += l_r * h_reflux;
            }
            if j > 0 {
                for i in 0..nc {
                    inflow[i] += vv[j - 1] * y[j - 1][i];
                }
                inflow_h += vv[j - 1] * hv[j - 1];
            }
            if let Some(fi) = feed_idx(&feeds, j) {
                let (_st, fl, ref zc) = feeds[fi];
                for i in 0..nc {
                    inflow[i] += fl * zc[i];
                }
                inflow_h += fl * feed_h[fi];
            }
            let mut out = vec![0.0; nc];
            for i in 0..nc {
                out[i] = l[j] * x[j][i] + vv[j] * y[j][i] + sl[j] * x[j][i] + sv[j] * y[j][i];
            }
            let mut out_h = (l[j] + sl[j]) * hl[j] + (vv[j] + sv[j]) * hv[j];
            for &(d_st, r_st, rate, duty) in pumparounds {
                if j == d_st {
                    for i in 0..nc {
                        out[i] += rate * x[j][i];
                    }
                    out_h += rate * hl[j];
                }
                if j == r_st {
                    for i in 0..nc {
                        inflow[i] += rate * x[d_st][i];
                    }
                    inflow_h += rate * (hl[d_st] - duty / rate);
                }
            }
            for i in 0..nc {
                res.push((inflow[i] - out[i]) / f_tot);
            }
            res.push(x[j].iter().sum::<f64>() - 1.0);
            res.push(y[j].iter().sum::<f64>() - 1.0);
            let mut enth = inflow_h - out_h;
            if j == 0 {
                enth += qr;
            }
            res.push(enth / e_scale);
        }
        res
    };

    let mut v0: Vec<f64> = Vec::new();
    for j in 0..nst {
        v0.extend_from_slice(&x0[j]);
    }
    v0.extend_from_slice(&t0);
    v0.extend(l0g.iter().map(|v| v.max(0.01)));
    v0.extend(v0g[..n].iter().map(|v| v.max(0.01)));
    v0.push(cmo.q_reboiler);
    let flow_hi = 10.0 * f_tot + 100.0;
    let mut lo: Vec<f64> = vec![0.0; nx];
    lo.extend(vec![120.0; nst]);
    lo.extend(vec![0.0; nl]);
    lo.extend(vec![0.0; nv]);
    lo.push(-1e8);
    let mut hi: Vec<f64> = vec![1.0; nx];
    hi.extend(vec![950.0; nst]);
    hi.extend(vec![flow_hi; nl]);
    hi.extend(vec![flow_hi; nv]);
    hi.push(1e8);
    for i in 0..v0.len() {
        v0[i] = v0[i].clamp(lo[i] + 1e-9, hi[i] - 1e-9);
    }
    let sol = lm_solve(residuals, &v0, &lo, &hi, 200);
    let fres = residuals(&sol);
    let cost: f64 = 0.5 * fres.iter().map(|v| v * v).sum::<f64>();

    let mut x = vec![vec![0.0; nc]; nst];
    for j in 0..nst {
        for i in 0..nc {
            x[j][i] = sol[j * nc + i].max(0.0);
        }
        let s: f64 = x[j].iter().sum();
        for i in 0..nc {
            x[j][i] /= s;
        }
    }
    let t: Vec<f64> = sol[nx..nx + nst].to_vec();
    let l: Vec<f64> = sol[nx + nst..nx + nst + nl].to_vec();
    let mut vv: Vec<f64> = sol[nx + nst + nl..nx + nst + nl + nv].to_vec();
    vv.push(v_top);
    let qr = sol[sol.len() - 1];
    let (_k, y, hl, hv) = profiles(&x, &t);
    let t_cond = th.bubble_t(&y[n], p_prof[n]);
    let h_reflux = th.h_liq(&y[n], t_cond);
    let qc = (vv[n] - sv[n]) * hv[n] - (l_r + d_flow) * h_reflux;

    // Independent residual recomputation at the returned state.
    let mut stage_enth = vec![0.0; nst];
    let mut stage_mat = vec![0.0; nst];
    for j in 0..nst {
        let mut inflow = vec![0.0; nc];
        let mut inflow_h = 0.0f64;
        if j < n {
            for i in 0..nc {
                inflow[i] += l[j + 1] * x[j + 1][i];
            }
            inflow_h += l[j + 1] * hl[j + 1];
        } else {
            for i in 0..nc {
                inflow[i] += l_r * y[n][i];
            }
            inflow_h += l_r * h_reflux;
        }
        if j > 0 {
            for i in 0..nc {
                inflow[i] += vv[j - 1] * y[j - 1][i];
            }
            inflow_h += vv[j - 1] * hv[j - 1];
        }
        if let Some(fi) = feed_idx(&feeds, j) {
            let (_st, fl, ref zc) = feeds[fi];
            for i in 0..nc {
                inflow[i] += fl * zc[i];
            }
            inflow_h += fl * feed_h[fi];
        }
        let mut out = vec![0.0; nc];
        for i in 0..nc {
            out[i] = l[j] * x[j][i] + vv[j] * y[j][i] + sl[j] * x[j][i] + sv[j] * y[j][i];
        }
        let mut out_h = (l[j] + sl[j]) * hl[j] + (vv[j] + sv[j]) * hv[j];
        for &(d_st, r_st, rate, duty) in pumparounds {
            if j == d_st {
                for i in 0..nc {
                    out[i] += rate * x[j][i];
                }
                out_h += rate * hl[j];
            }
            if j == r_st {
                for i in 0..nc {
                    inflow[i] += rate * x[d_st][i];
                }
                inflow_h += rate * (hl[d_st] - duty / rate);
            }
        }
        stage_mat[j] = (0..nc).map(|i| (inflow[i] - out[i]).abs()).fold(0.0, f64::max);
        stage_enth[j] = inflow_h - out_h + if j == 0 { qr } else { 0.0 };
    }
    let b_flow = l[0];
    let overall = f_tot - (b_flow + d_flow + sl_tot + sv_tot);
    let mut y_top_v = y[n].clone();
    let sy: f64 = y_top_v.iter().sum();
    for v in y_top_v.iter_mut() {
        *v /= sy;
    }
    let max_sum = (0..nst)
        .map(|j| {
            (x[j].iter().sum::<f64>() - 1.0)
                .abs()
                .max((y[j].iter().sum::<f64>() - 1.0).abs())
        })
        .fold(0.0, f64::max);
    MeshResult {
        x_bottoms: x[0].clone(),
        x_distillate: y_top_v.clone(),
        y_top: y_top_v,
        x,
        y,
        t,
        p: p_prof,
        l,
        v: vv,
        b: b_flow,
        d: d_flow,
        q_reboiler: qr,
        q_condenser: qc,
        t_condenser: t_cond,
        max_enthalpy_residual_w: stage_enth.iter().map(|v| v.abs()).fold(0.0, f64::max),
        max_material_residual_mol_s: stage_mat.iter().cloned().fold(0.0, f64::max),
        stage_enthalpy_residuals_w: stage_enth,
        stage_material_residuals_mol_s: stage_mat,
        max_summation_residual: max_sum,
        overall_balance_residual_mol_s: overall,
        solver_cost: cost,
    }
}

// --- Local Levenberg-Marquardt solver ---------------------------
// The crate solver of linalg.rs damps with lambda * (1 + diag),
// which stalls on this system: the reboiler duty in watts (W)
// enters its enthalpy residual scaled by 1 / (feed rate times
// 30000 J/mol), so its Jacobian column is orders of magnitude
// smaller than the composition columns and the unit diagonal
// dominates it. This local solver damps with lambda * diag
// (Marquardt scaling, the analogue of the x_scale="jac" used by
// the Python scipy solve), with bounds applied by clamping.

fn lm_solve<F: Fn(&[f64]) -> Vec<f64>>(
    f: F,
    x0: &[f64],
    lo: &[f64],
    hi: &[f64],
    max_iter: usize,
) -> Vec<f64> {
    let n = x0.len();
    let mut x: Vec<f64> = x0.to_vec();
    let mut fx = f(&x);
    let m = fx.len();
    let mut cost: f64 = fx.iter().map(|v| v * v).sum();
    let mut lambda = 1e-3f64;
    for _ in 0..max_iter {
        if cost < 1e-26 {
            break;
        }
        let mut jac = vec![vec![0.0; n]; m];
        for j in 0..n {
            let h = 1e-6 * (1.0 + x[j].abs());
            let mut xp = x.clone();
            let mut xm = x.clone();
            xp[j] += h;
            xm[j] -= h;
            let fp = f(&xp);
            let fm = f(&xm);
            for i in 0..m {
                jac[i][j] = (fp[i] - fm[i]) / (2.0 * h);
            }
        }
        let mut jtj = vec![vec![0.0; n]; n];
        let mut jtf = vec![0.0; n];
        for i in 0..m {
            for j in 0..n {
                jtf[j] += jac[i][j] * fx[i];
                for k in j..n {
                    jtj[j][k] += jac[i][j] * jac[i][k];
                }
            }
        }
        for j in 0..n {
            for k in j + 1..n {
                jtj[k][j] = jtj[j][k];
            }
        }
        let mut improved = false;
        for _try in 0..50 {
            let mut a = jtj.clone();
            for j in 0..n {
                a[j][j] += lambda * jtj[j][j].max(1e-30);
            }
            let rhs: Vec<f64> = jtf.iter().map(|v| -v).collect();
            match solve_lin(&a, &rhs) {
                Some(dx) => {
                    let xn: Vec<f64> = (0..n)
                        .map(|j| (x[j] + dx[j]).clamp(lo[j], hi[j]))
                        .collect();
                    let fn_ = f(&xn);
                    let cn: f64 = fn_.iter().map(|v| v * v).sum();
                    if cn < cost {
                        let rel_step: f64 = (0..n)
                            .map(|j| (xn[j] - x[j]).abs() / (1.0 + x[j].abs()))
                            .fold(0.0, f64::max);
                        x = xn;
                        fx = fn_;
                        cost = cn;
                        lambda = (lambda * 0.3).max(1e-14);
                        improved = true;
                        if rel_step < 1e-14 && cost < 1e-22 {
                            return x;
                        }
                        break;
                    } else {
                        lambda *= 10.0;
                    }
                }
                None => {
                    lambda *= 10.0;
                }
            }
        }
        if !improved {
            break;
        }
    }
    x
}

// --- MESH variants (port of python/columns_mesh_variants.py) ----
// Status: locally verified only; no ChemCAD anchor exists for
// these variants. Verification is by the limiting cases and
// balance closures of python/test_mesh_variants.py and the
// parity tests of rust/tests/mesh_parity.rs.

pub struct StripperResult {
    pub x: Vec<Vec<f64>>,
    pub y: Vec<Vec<f64>>,
    pub t: Vec<f64>,
    pub p: Vec<f64>,
    pub l: Vec<f64>,
    pub v: Vec<f64>,
    pub b: f64,
    pub d_vapour: f64,
    pub x_bottoms: Vec<f64>,
    pub y_top: Vec<f64>,
    pub q_reboiler: f64,
    pub stage_enthalpy_residuals_w: Vec<f64>,
    pub stage_material_residuals_mol_s: Vec<f64>,
    pub max_enthalpy_residual_w: f64,
    pub max_material_residual_mol_s: f64,
    pub max_summation_residual: f64,
    pub overall_balance_residual_mol_s: f64,
    pub solver_cost: f64,
}

/// Reboiled stripper in the MESH formulation: stage 0 is the
/// reboiler, stages 1 to N are trays (N given by n_trays), no
/// condenser and no reflux. The feed (flow F in mol/s, mole
/// fractions z_feed) enters the top stage as a saturated liquid.
/// The specification in place of a distillate rate is v_top,
/// the vapour product rate leaving the top stage, in mol/s.
/// `efficiency` is a slice of length 1 (scalar) or n_trays + 1
/// (entry 0 ignored). Pressures are in pascal (Pa), the profile
/// linear between p_bottom (default p_top) and p_top.
pub fn mesh_stripper(
    z_feed: &[f64],
    f: f64,
    n_trays: usize,
    v_top: f64,
    th: &RaoultThermo,
    p_top: f64,
    p_bottom: Option<f64>,
    efficiency: &[f64],
) -> StripperResult {
    let p_bottom = p_bottom.unwrap_or(p_top);
    let nc = z_feed.len();
    let n = n_trays;
    let nst = n + 1;
    let mut eff: Vec<f64> = if efficiency.len() == 1 {
        vec![efficiency[0]; nst]
    } else {
        assert_eq!(efficiency.len(), nst);
        efficiency.to_vec()
    };
    eff[0] = 1.0;
    let p_prof: Vec<f64> = (0..nst)
        .map(|j| p_bottom + (p_top - p_bottom) * if n > 0 { j as f64 / n as f64 } else { 0.0 })
        .collect();
    let tb = th.bubble_t(z_feed, p_prof[n]);
    let feed_h = th.h_liq(z_feed, tb);
    let e_scale = (f * 30000.0).max(1.0);
    let nx = nst * nc;
    let nv = n; // V_0 .. V_{N-1}; V_N = v_top is specified

    let profiles = |x: &Vec<Vec<f64>>, t: &Vec<f64>| {
        let k: Vec<Vec<f64>> = (0..nst).map(|j| th.k(&x[j], t[j], p_prof[j])).collect();
        let mut y = vec![vec![0.0; nc]; nst];
        for i in 0..nc {
            y[0][i] = k[0][i] * x[0][i];
        }
        for j in 1..nst {
            for i in 0..nc {
                y[j][i] = (1.0 - eff[j]) * y[j - 1][i] + eff[j] * k[j][i] * x[j][i];
            }
        }
        let hl: Vec<f64> = (0..nst).map(|j| th.h_liq(&x[j], t[j])).collect();
        let hv: Vec<f64> = (0..nst).map(|j| th.h_vap(&y[j], t[j])).collect();
        (y, hl, hv)
    };
    let balances = |x: &Vec<Vec<f64>>, t: &Vec<f64>, l: &Vec<f64>, vv: &Vec<f64>, qr: f64| {
        let (y, hl, hv) = profiles(x, t);
        let mut mat = vec![vec![0.0; nc]; nst];
        let mut enth = vec![0.0; nst];
        for j in 0..nst {
            let mut inflow = vec![0.0; nc];
            let mut inflow_h = 0.0f64;
            if j < n {
                for i in 0..nc {
                    inflow[i] += l[j + 1] * x[j + 1][i];
                }
                inflow_h += l[j + 1] * hl[j + 1];
            } else {
                for i in 0..nc {
                    inflow[i] += f * z_feed[i];
                }
                inflow_h += f * feed_h;
            }
            if j > 0 {
                for i in 0..nc {
                    inflow[i] += vv[j - 1] * y[j - 1][i];
                }
                inflow_h += vv[j - 1] * hv[j - 1];
            }
            for i in 0..nc {
                mat[j][i] = inflow[i] - (l[j] * x[j][i] + vv[j] * y[j][i]);
            }
            enth[j] = inflow_h - (l[j] * hl[j] + vv[j] * hv[j]) + if j == 0 { qr } else { 0.0 };
        }
        (y, mat, enth)
    };
    let residuals = |v: &[f64]| -> Vec<f64> {
        let mut x = vec![vec![0.0; nc]; nst];
        for j in 0..nst {
            for i in 0..nc {
                x[j][i] = v[j * nc + i];
            }
        }
        let t: Vec<f64> = v[nx..nx + nst].to_vec();
        let l: Vec<f64> = v[nx + nst..nx + 2 * nst].to_vec();
        let mut vv: Vec<f64> = v[nx + 2 * nst..nx + 2 * nst + nv].to_vec();
        vv.push(v_top);
        let (_y, mat, enth) = balances(&x, &t, &l, &vv, v[v.len() - 1]);
        let mut res: Vec<f64> = Vec::with_capacity(nst * (nc + 3));
        for j in 0..nst {
            for i in 0..nc {
                res.push(mat[j][i] / f);
            }
            res.push(x[j].iter().sum::<f64>() - 1.0);
            res.push(_y[j].iter().sum::<f64>() - 1.0);
            res.push(enth[j] / e_scale);
        }
        res
    };
    let mut v0: Vec<f64> = Vec::new();
    for _j in 0..nst {
        v0.extend_from_slice(z_feed);
    }
    v0.extend((0..nst).map(|j| th.bubble_t(z_feed, p_prof[j])));
    let mut l0g = vec![f; nst];
    l0g[0] = (f - v_top).max(0.05 * f);
    v0.extend_from_slice(&l0g);
    v0.extend(vec![v_top; nv]);
    v0.push(v_top * 30000.0);
    let flow_hi = 10.0 * f + 100.0;
    let mut lo: Vec<f64> = vec![0.0; nx];
    lo.extend(vec![120.0; nst]);
    lo.extend(vec![0.0; nst]);
    lo.extend(vec![0.0; nv]);
    lo.push(-1e8);
    let mut hi: Vec<f64> = vec![1.0; nx];
    hi.extend(vec![950.0; nst]);
    hi.extend(vec![flow_hi; nst]);
    hi.extend(vec![flow_hi; nv]);
    hi.push(1e8);
    for i in 0..v0.len() {
        v0[i] = v0[i].clamp(lo[i] + 1e-9, hi[i] - 1e-9);
    }
    let sol = lm_solve(residuals, &v0, &lo, &hi, 200);
    let fres = residuals(&sol);
    let cost: f64 = 0.5 * fres.iter().map(|v| v * v).sum::<f64>();
    let mut x = vec![vec![0.0; nc]; nst];
    for j in 0..nst {
        for i in 0..nc {
            x[j][i] = sol[j * nc + i].max(0.0);
        }
        let s: f64 = x[j].iter().sum();
        for i in 0..nc {
            x[j][i] /= s;
        }
    }
    let t: Vec<f64> = sol[nx..nx + nst].to_vec();
    let l: Vec<f64> = sol[nx + nst..nx + 2 * nst].to_vec();
    let mut vv: Vec<f64> = sol[nx + 2 * nst..nx + 2 * nst + nv].to_vec();
    vv.push(v_top);
    let qr = sol[sol.len() - 1];
    let (y, mat, enth) = balances(&x, &t, &l, &vv, qr);
    let stage_mat: Vec<f64> = mat
        .iter()
        .map(|row| row.iter().map(|v| v.abs()).fold(0.0, f64::max))
        .collect();
    let mut y_top_v = y[n].clone();
    let sy: f64 = y_top_v.iter().sum();
    for v in y_top_v.iter_mut() {
        *v /= sy;
    }
    let max_sum = (0..nst)
        .map(|j| {
            (profiles_sum_x(&x, j) - 1.0)
                .abs()
                .max((profiles_sum_y(&y, j) - 1.0).abs())
        })
        .fold(0.0, f64::max);
    StripperResult {
        x_bottoms: x[0].clone(),
        y_top: y_top_v,
        x,
        y,
        t,
        p: p_prof,
        l: l.clone(),
        v: vv,
        b: l[0],
        d_vapour: v_top,
        q_reboiler: qr,
        max_enthalpy_residual_w: enth.iter().map(|v| v.abs()).fold(0.0, f64::max),
        max_material_residual_mol_s: stage_mat.iter().cloned().fold(0.0, f64::max),
        stage_enthalpy_residuals_w: enth,
        stage_material_residuals_mol_s: stage_mat,
        max_summation_residual: max_sum,
        overall_balance_residual_mol_s: f - l[0] - v_top,
        solver_cost: cost,
    }
}

fn profiles_sum_x(x: &[Vec<f64>], j: usize) -> f64 {
    x[j].iter().sum()
}
fn profiles_sum_y(y: &[Vec<f64>], j: usize) -> f64 {
    y[j].iter().sum()
}

pub struct AbsorberResult {
    pub x: Vec<Vec<f64>>,
    pub y: Vec<Vec<f64>>,
    pub t: Vec<f64>,
    pub l: Vec<f64>,
    pub v: Vec<f64>,
    pub gas_out_comp: Vec<f64>,
    pub liquid_out_comp: Vec<f64>,
    pub gas_out_rate_mol_s: f64,
    pub liquid_out_rate_mol_s: f64,
    pub stage_enthalpy_residuals_w: Vec<f64>,
    pub stage_material_residuals_mol_s: Vec<f64>,
    pub max_enthalpy_residual_w: f64,
    pub max_material_residual_mol_s: f64,
    pub max_summation_residual: f64,
    pub overall_balance_residual_mol_s: f64,
    pub solver_cost: f64,
}

/// Absorber (or gas-fed stripper) in the MESH formulation:
/// n_stages stages indexed 0 (bottom) to n_stages - 1 (top),
/// no reboiler, no condenser, adiabatic. The gas feed (flow
/// v_in in mol/s, mole fractions gas_comp, temperature t_gas
/// in kelvin (K)) enters below stage 0; the liquid feed (flow
/// l_in in mol/s, mole fractions liquid_comp, temperature
/// t_liq in K) enters above the top stage. The pressure p in
/// pascal (Pa) is uniform. `efficiency` is a slice of length 1
/// (scalar) or n_stages.
#[allow(clippy::too_many_arguments)]
pub fn mesh_absorber(
    gas_comp: &[f64],
    v_in: f64,
    t_gas: f64,
    liquid_comp: &[f64],
    l_in: f64,
    t_liq: f64,
    n_stages: usize,
    th: &RaoultThermo,
    p: f64,
    efficiency: &[f64],
) -> AbsorberResult {
    let nc = gas_comp.len();
    let n = n_stages;
    let eff: Vec<f64> = if efficiency.len() == 1 {
        vec![efficiency[0]; n]
    } else {
        assert_eq!(efficiency.len(), n);
        efficiency.to_vec()
    };
    let gas_h = th.h_vap(gas_comp, t_gas);
    let liq_h = th.h_liq(liquid_comp, t_liq);
    let f_tot = v_in + l_in;
    let e_scale = (f_tot * 30000.0).max(1.0);
    let nx = n * nc;

    let profiles = |x: &Vec<Vec<f64>>, t: &Vec<f64>| {
        let k: Vec<Vec<f64>> = (0..n).map(|j| th.k(&x[j], t[j], p)).collect();
        let mut y = vec![vec![0.0; nc]; n];
        let mut y_prev: Vec<f64> = gas_comp.to_vec();
        for j in 0..n {
            for i in 0..nc {
                y[j][i] = (1.0 - eff[j]) * y_prev[i] + eff[j] * k[j][i] * x[j][i];
            }
            y_prev = y[j].clone();
        }
        let hl: Vec<f64> = (0..n).map(|j| th.h_liq(&x[j], t[j])).collect();
        let hv: Vec<f64> = (0..n).map(|j| th.h_vap(&y[j], t[j])).collect();
        (y, hl, hv)
    };
    let balances = |x: &Vec<Vec<f64>>, t: &Vec<f64>, l: &Vec<f64>, vv: &Vec<f64>| {
        let (y, hl, hv) = profiles(x, t);
        let mut mat = vec![vec![0.0; nc]; n];
        let mut enth = vec![0.0; n];
        for j in 0..n {
            let mut inflow = vec![0.0; nc];
            let mut inflow_h = 0.0f64;
            if j < n - 1 {
                for i in 0..nc {
                    inflow[i] += l[j + 1] * x[j + 1][i];
                }
                inflow_h += l[j + 1] * hl[j + 1];
            } else {
                for i in 0..nc {
                    inflow[i] += l_in * liquid_comp[i];
                }
                inflow_h += l_in * liq_h;
            }
            if j > 0 {
                for i in 0..nc {
                    inflow[i] += vv[j - 1] * y[j - 1][i];
                }
                inflow_h += vv[j - 1] * hv[j - 1];
            } else {
                for i in 0..nc {
                    inflow[i] += v_in * gas_comp[i];
                }
                inflow_h += v_in * gas_h;
            }
            for i in 0..nc {
                mat[j][i] = inflow[i] - (l[j] * x[j][i] + vv[j] * y[j][i]);
            }
            enth[j] = inflow_h - (l[j] * hl[j] + vv[j] * hv[j]);
        }
        (y, mat, enth)
    };
    let residuals = |v: &[f64]| -> Vec<f64> {
        let mut x = vec![vec![0.0; nc]; n];
        for j in 0..n {
            for i in 0..nc {
                x[j][i] = v[j * nc + i];
            }
        }
        let t: Vec<f64> = v[nx..nx + n].to_vec();
        let l: Vec<f64> = v[nx + n..nx + 2 * n].to_vec();
        let vv: Vec<f64> = v[nx + 2 * n..nx + 3 * n].to_vec();
        let (y, mat, enth) = balances(&x, &t, &l, &vv);
        let mut res: Vec<f64> = Vec::with_capacity(n * (nc + 3));
        for j in 0..n {
            for i in 0..nc {
                res.push(mat[j][i] / f_tot);
            }
            res.push(x[j].iter().sum::<f64>() - 1.0);
            res.push(y[j].iter().sum::<f64>() - 1.0);
            res.push(enth[j] / e_scale);
        }
        res
    };
    let mut v0: Vec<f64> = Vec::new();
    for _j in 0..n {
        v0.extend_from_slice(liquid_comp);
    }
    v0.extend(vec![0.5 * (t_gas + t_liq); n]);
    v0.extend(vec![l_in; n]);
    v0.extend(vec![v_in; n]);
    let flow_hi = 10.0 * f_tot + 100.0;
    let mut lo: Vec<f64> = vec![0.0; nx];
    lo.extend(vec![120.0; n]);
    lo.extend(vec![0.0; n]);
    lo.extend(vec![0.0; n]);
    let mut hi: Vec<f64> = vec![1.0; nx];
    hi.extend(vec![950.0; n]);
    hi.extend(vec![flow_hi; n]);
    hi.extend(vec![flow_hi; n]);
    for i in 0..v0.len() {
        v0[i] = v0[i].clamp(lo[i] + 1e-9, hi[i] - 1e-9);
    }
    let sol = lm_solve(residuals, &v0, &lo, &hi, 200);
    let fres = residuals(&sol);
    let cost: f64 = 0.5 * fres.iter().map(|v| v * v).sum::<f64>();
    let mut x = vec![vec![0.0; nc]; n];
    for j in 0..n {
        for i in 0..nc {
            x[j][i] = sol[j * nc + i].max(0.0);
        }
        let s: f64 = x[j].iter().sum();
        for i in 0..nc {
            x[j][i] /= s;
        }
    }
    let t: Vec<f64> = sol[nx..nx + n].to_vec();
    let l: Vec<f64> = sol[nx + n..nx + 2 * n].to_vec();
    let vv: Vec<f64> = sol[nx + 2 * n..nx + 3 * n].to_vec();
    let (y, mat, enth) = balances(&x, &t, &l, &vv);
    let stage_mat: Vec<f64> = mat
        .iter()
        .map(|row| row.iter().map(|v| v.abs()).fold(0.0, f64::max))
        .collect();
    let mut gas_out = y[n - 1].clone();
    let sg: f64 = gas_out.iter().sum();
    for v in gas_out.iter_mut() {
        *v /= sg;
    }
    let max_sum = (0..n)
        .map(|j| {
            (profiles_sum_x(&x, j) - 1.0)
                .abs()
                .max((profiles_sum_y(&y, j) - 1.0).abs())
        })
        .fold(0.0, f64::max);
    AbsorberResult {
        liquid_out_comp: x[0].clone(),
        gas_out_comp: gas_out,
        x,
        y,
        t,
        l: l.clone(),
        v: vv.clone(),
        gas_out_rate_mol_s: vv[n - 1],
        liquid_out_rate_mol_s: l[0],
        max_enthalpy_residual_w: enth.iter().map(|v| v.abs()).fold(0.0, f64::max),
        max_material_residual_mol_s: stage_mat.iter().cloned().fold(0.0, f64::max),
        stage_enthalpy_residuals_w: enth,
        stage_material_residuals_mol_s: stage_mat,
        max_summation_residual: max_sum,
        overall_balance_residual_mol_s: f_tot - l[0] - vv[n - 1],
        solver_cost: cost,
    }
}
