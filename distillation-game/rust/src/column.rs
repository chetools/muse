//! Dynamic multicomponent column model, ported from the Python
//! reference (../python/column.py).
//!
//! Stages: stage 0 is the reboiler, stages 1..N are trays, and the
//! reflux drum is carried as a composition state after stage N.
//! Equilibrium stages, constant molal overflow, uniform column
//! pressure, constant stage holdups. Flow relations (total condenser),
//! with psi the vapour fraction of the flashed feed:
//! V_R = L_R + D; L_S = L_R + (1 - psi) F; V_S = V_R - psi F; B = F - D.
//! Vapour traffic is V_S below the feed stage and V_R at and above it.

use crate::feed::{feed_flash, Flash};
use crate::mixtures::Mixture;

/// Solve A x = b by Gaussian elimination with partial pivoting.
/// A is consumed (row-major, n x n). Returns None if singular.
fn solve_linear(mut a: Vec<Vec<f64>>, mut b: Vec<f64>) -> Option<Vec<f64>> {
    let n = b.len();
    for col in 0..n {
        let mut piv = col;
        for r in col + 1..n {
            if a[r][col].abs() > a[piv][col].abs() {
                piv = r;
            }
        }
        if a[piv][col].abs() < 1e-300 {
            return None;
        }
        a.swap(col, piv);
        b.swap(col, piv);
        let d = a[col][col];
        for r in col + 1..n {
            let f = a[r][col] / d;
            if f != 0.0 {
                for c in col..n {
                    a[r][c] -= f * a[col][c];
                }
                b[r] -= f * b[col];
            }
        }
    }
    let mut x = vec![0.0; n];
    for i in (0..n).rev() {
        let mut s = b[i];
        for c in i + 1..n {
            s -= a[i][c] * x[c];
        }
        x[i] = s / a[i][i];
    }
    Some(x)
}

#[derive(Clone, Debug)]
pub struct Column {
    pub mix: Mixture,
    /// Number of trays.
    pub n: usize,
    /// Feed tray index, 1..=N.
    pub feed_stage: usize,
    /// Feed molar flow, mol/s.
    pub f: f64,
    /// Feed mole fractions.
    pub z: Vec<f64>,
    /// Distillate molar flow, mol/s.
    pub d: f64,
    /// Reflux molar flow, mol/s.
    pub l_r: f64,
    /// Column pressure, kPa.
    pub p: f64,
    pub v_r: f64,
    pub l_s: f64,
    pub v_s: f64,
    pub b: f64,
    /// Liquid flow leaving each stage downward, stages 0..=N.
    pub l_out: Vec<f64>,
    /// Vapour flow leaving each stage upward, stages 0..=N.
    pub v_up: Vec<f64>,
    /// Stage holdups, mol, stages 0..=N.
    pub m: Vec<f64>,
    /// Drum holdup, mol.
    pub m_drum: f64,
    pub feed_t: f64,
    pub feed_p: f64,
    pub flash: Flash,
}

impl Column {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        mix: Mixture,
        n_trays: usize,
        feed_stage: usize,
        f: f64,
        z: Vec<f64>,
        d: f64,
        l_r: f64,
        p: f64,
        m_tray: f64,
        m_reb: f64,
        m_drum: f64,
        feed_t: Option<f64>,
        feed_p: Option<f64>,
    ) -> Result<Column, String> {
        if feed_stage < 1 || feed_stage > n_trays {
            return Err("feed stage must be a tray".into());
        }
        if z.len() != mix.nc() {
            return Err("feed composition does not match the mixture".into());
        }
        // Feed state: default is a saturated liquid at the column
        // pressure; otherwise flash from the stated conditions.
        let (feed_t, feed_p) = match feed_t {
            None => {
                let (tb, _) = mix.bubble_point(&z, p);
                (tb, p)
            }
            Some(t) => (t, feed_p.unwrap_or(p)),
        };
        let flash = feed_flash(&mix, &z, feed_t, feed_p, p)?;
        let psi = flash.psi;
        let v_r = l_r + d;
        let l_s = l_r + (1.0 - psi) * f;
        let v_s = v_r - psi * f;
        let b = f - d;
        if b <= 0.0 {
            return Err("distillate flow must be below feed flow".into());
        }
        if v_s <= 0.0 {
            return Err("flashed feed vapour exceeds the boilup".into());
        }
        let nst = n_trays + 1;
        let mut l_out = vec![0.0; nst];
        let mut v_up = vec![0.0; nst];
        for j in 0..nst {
            l_out[j] = if j == 0 {
                b
            } else if j <= feed_stage {
                l_s
            } else {
                l_r
            };
            v_up[j] = if j < feed_stage { v_s } else { v_r };
        }
        let mut m = vec![m_tray; nst];
        m[0] = m_reb;
        Ok(Column {
            mix,
            n: n_trays,
            feed_stage,
            f,
            z,
            d,
            l_r,
            p,
            v_r,
            l_s,
            v_s,
            b,
            l_out,
            v_up,
            m,
            m_drum,
            feed_t,
            feed_p,
            flash,
        })
    }

    /// The default column of the reference: alkanes, 12 trays, feed at
    /// stage 6, 10 mol/s of (0.40, 0.30, 0.30), D = 4, L_R = 5,
    /// 150 kPa.
    pub fn default_alkanes() -> Column {
        Column::new(
            crate::mixtures::alkanes(),
            12,
            6,
            10.0,
            vec![0.40, 0.30, 0.30],
            4.0,
            5.0,
            150.0,
            200.0,
            1000.0,
            500.0,
            None,
            None,
        )
        .expect("default column parameters are valid")
    }

    pub fn nst(&self) -> usize {
        self.n + 1
    }

    fn nc(&self) -> usize {
        self.mix.nc()
    }

    /// Component molar flows (mol/s) entering at the feed stage: the
    /// liquid part of the flashed feed plus the vapour part.
    pub fn feed_source(&self) -> Vec<f64> {
        let psi = self.flash.psi;
        (0..self.nc())
            .map(|c| {
                (1.0 - psi) * self.f * self.flash.x[c] + psi * self.f * self.flash.y[c]
            })
            .collect()
    }

    /// Time derivatives of all composition states.
    /// `x_stages` is flat (nst x nc); `x_drum` has nc entries.
    /// Returns (dx_stages flat, dx_drum).
    pub fn rhs(&self, x_stages: &[f64], x_drum: &[f64]) -> (Vec<f64>, Vec<f64>) {
        let nc = self.nc();
        let nst = self.nst();
        // Equilibrium ratios per stage.
        let mut k_all = vec![0.0; nst * nc];
        for j in 0..nst {
            let xj = &x_stages[j * nc..(j + 1) * nc];
            let (_, k) = self.mix.bubble_point_k(xj, self.p);
            k_all[j * nc..(j + 1) * nc].copy_from_slice(&k);
        }
        let mut net = vec![0.0; nst * nc];
        for j in 0..nst {
            for c in 0..nc {
                let liq_j = self.l_out[j] * x_stages[j * nc + c];
                let vap_j = self.v_up[j] * k_all[j * nc + c] * x_stages[j * nc + c];
                let mut v = -liq_j - vap_j;
                if j + 1 < nst {
                    v += self.l_out[j + 1] * x_stages[(j + 1) * nc + c];
                } else {
                    v += self.l_r * x_drum[c];
                }
                if j > 0 {
                    v += self.v_up[j - 1] * k_all[(j - 1) * nc + c] * x_stages[(j - 1) * nc + c];
                }
                net[j * nc + c] = v;
            }
        }
        let src = self.feed_source();
        for c in 0..nc {
            net[self.feed_stage * nc + c] += src[c];
        }
        let mut dx = vec![0.0; nst * nc];
        for j in 0..nst {
            for c in 0..nc {
                dx[j * nc + c] = net[j * nc + c] / self.m[j];
            }
        }
        let mut dx_drum = vec![0.0; nc];
        for c in 0..nc {
            let y_top = k_all[(nst - 1) * nc + c] * x_stages[(nst - 1) * nc + c];
            dx_drum[c] =
                (self.v_r * y_top - (self.l_r + self.d) * x_drum[c]) / self.m_drum;
        }
        (dx, dx_drum)
    }

    fn rhs_flat(&self, s: &[f64]) -> Vec<f64> {
        let nc = self.nc();
        let nst = self.nst();
        let (dx, dd) = self.rhs(&s[..nst * nc], &s[nst * nc..]);
        let mut out = dx;
        out.extend_from_slice(&dd);
        out
    }

    /// Equilibrium vapour of the top stage = distillate composition.
    pub fn distillate_composition(&self, x_stages: &[f64]) -> Vec<f64> {
        let nc = self.nc();
        let top = &x_stages[(self.nst() - 1) * nc..];
        let (_, k) = self.mix.bubble_point_k(top, self.p);
        top.iter().zip(k.iter()).map(|(x, kc)| x * kc).collect()
    }

    fn solve_component(&self, kc: &[f64], c: usize) -> Vec<f64> {
        let nst = self.nst();
        let mut a = vec![vec![0.0; nst]; nst];
        let mut rhs = vec![0.0; nst];
        let src = self.feed_source();
        for j in 0..nst {
            a[j][j] += self.l_out[j] + self.v_up[j] * kc[j];
            if j < self.n {
                a[j][j + 1] -= self.l_out[j + 1];
            } else {
                a[j][j] -= self.l_r * kc[j];
            }
            if j > 0 {
                a[j][j - 1] -= self.v_up[j - 1] * kc[j - 1];
            }
            if j == self.feed_stage {
                rhs[j] -= src[c];
            }
        }
        // Python returns solve(A, -rhs).
        let neg: Vec<f64> = rhs.iter().map(|v| -v).collect();
        solve_linear(a, neg).expect("component balance system is nonsingular")
    }

    /// Steady stage compositions and temperatures.
    ///
    /// Method mirrors the reference: one fixed-point sweep of the
    /// linear component balances for a physical initial profile;
    /// stiff integration to 30,000 s (here implicit Euler with growing
    /// steps and Newton solves, where the reference uses BDF — the
    /// integration only has to get close); then the same Newton polish
    /// on the right-hand side (finite-difference Jacobian, step
    /// halving), repeated in cycles until the right-hand side is
    /// negligible. The polished root is path-independent, which is
    /// what the parity battery checks.
    /// Returns (x flat nst x nc, T per stage).
    pub fn steady_state(&self) -> (Vec<f64>, Vec<f64>) {
        let nc = self.nc();
        let nst = self.nst();
        // Initial profile: one component sweep at the feed-composition
        // equilibrium ratios.
        let mut x = vec![0.0; nst * nc];
        for j in 0..nst {
            x[j * nc..(j + 1) * nc].copy_from_slice(&self.z);
        }
        let mut k_col = vec![0.0; nst * nc];
        for j in 0..nst {
            let (_, kk) = self.mix.bubble_point_k(&x[j * nc..(j + 1) * nc], self.p);
            k_col[j * nc..(j + 1) * nc].copy_from_slice(&kk);
        }
        for c in 0..nc {
            let kc: Vec<f64> = (0..nst).map(|j| k_col[j * nc + c]).collect();
            let xc = self.solve_component(&kc, c);
            for j in 0..nst {
                x[j * nc + c] = xc[j];
            }
        }
        let drum = self.distillate_composition(&x);
        let mut s = x;
        s.extend_from_slice(&drum);

        for _cycle in 0..3 {
            s = self.integrate(s, 30000.0);
            s = self.polish(s);
            let r = self.rhs_flat(&s);
            if r.iter().map(|v| v.abs()).fold(0.0f64, f64::max) < 1e-10 {
                break;
            }
        }
        let xf = s[..nst * nc].to_vec();
        let mut temps = vec![0.0; nst];
        for j in 0..nst {
            let (t, _) = self.mix.bubble_point_k(&xf[j * nc..(j + 1) * nc], self.p);
            temps[j] = t;
        }
        (xf, temps)
    }

    /// Implicit-Euler integration with growing steps; each step is
    /// solved by Newton iteration on s - s_old - dt * rhs(s) = 0 with
    /// a finite-difference Jacobian. A step that fails to converge is
    /// retried at half size.
    fn integrate(&self, mut s: Vec<f64>, t_end: f64) -> Vec<f64> {
        let n = s.len();
        let mut t = 0.0f64;
        let mut dt = 1.0f64;
        while t < t_end {
            dt = dt.min(t_end - t);
            let s_old = s.clone();
            let mut cand = s_old.clone();
            let mut ok = false;
            for _ in 0..25 {
                let r = self.rhs_flat(&cand);
                let mut g = vec![0.0; n];
                for i in 0..n {
                    g[i] = cand[i] - s_old[i] - dt * r[i];
                }
                if g.iter().map(|v| v.abs()).fold(0.0f64, f64::max) < 1e-11 {
                    ok = true;
                    break;
                }
                // Jacobian of g: I - dt * J_rhs.
                let mut a = vec![vec![0.0; n]; n];
                for i in 0..n {
                    let h = 1e-7 * cand[i].abs().max(1.0);
                    let mut sp = cand.clone();
                    sp[i] += h;
                    let rp = self.rhs_flat(&sp);
                    for row in 0..n {
                        a[row][i] = -dt * (rp[row] - r[row]) / h;
                    }
                    a[i][i] += 1.0;
                }
                let neg: Vec<f64> = g.iter().map(|v| -v).collect();
                match solve_linear(a, neg) {
                    Some(step) => {
                        for i in 0..n {
                            cand[i] += step[i];
                        }
                    }
                    None => break,
                }
            }
            if ok {
                s = cand;
                t += dt;
                dt = (dt * 1.6).min(2000.0);
            } else {
                dt *= 0.5;
                if dt < 1e-6 {
                    break;
                }
            }
        }
        s
    }

    /// Newton polish on rhs(s) = 0, as in the reference: finite-
    /// difference Jacobian (h = 1e-7 * max(1, |s_i|)), step halving
    /// (up to 25 halvings) requiring a decrease in max |rhs|, up to
    /// 40 iterations.
    fn polish(&self, mut s: Vec<f64>) -> Vec<f64> {
        let n = s.len();
        for _ in 0..40 {
            let r = self.rhs_flat(&s);
            let base = r.iter().map(|v| v.abs()).fold(0.0f64, f64::max);
            if base < 1e-11 {
                break;
            }
            let mut a = vec![vec![0.0; n]; n];
            for i in 0..n {
                let h = 1e-7 * s[i].abs().max(1.0);
                let mut sp = s.clone();
                sp[i] += h;
                let rp = self.rhs_flat(&sp);
                for row in 0..n {
                    a[row][i] = (rp[row] - r[row]) / h;
                }
            }
            let neg: Vec<f64> = r.iter().map(|v| -v).collect();
            let step = match solve_linear(a, neg) {
                Some(v) => v,
                None => break,
            };
            let mut lam = 1.0f64;
            let mut improved = false;
            for _ in 0..25 {
                let cand: Vec<f64> =
                    s.iter().zip(step.iter()).map(|(si, di)| si + lam * di).collect();
                let rc = self.rhs_flat(&cand);
                if rc.iter().map(|v| v.abs()).fold(0.0f64, f64::max) < base {
                    s = cand;
                    improved = true;
                    break;
                }
                lam *= 0.5;
            }
            if !improved {
                break;
            }
        }
        s
    }
}
