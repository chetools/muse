//! Feed flash, ported from the Python reference (../python/feed.py).
//!
//! The feed is a liquid at its stated temperature and pressure, let
//! down isenthalpically to the column pressure. The split is a
//! Rachford–Rice equilibrium calculation coupled to an enthalpy
//! balance. Enthalpies are molar, relative to the liquid at
//! T_REF = 298.15 K. All quantities in SI units.

use crate::mixtures::Mixture;

pub const T_REF: f64 = 298.15;

/// Result of flashing the feed to the column pressure.
#[derive(Clone, Debug)]
pub struct Flash {
    /// Vapour fraction of the flashed feed (dimensionless).
    pub psi: f64,
    /// Flash temperature, K.
    pub t: f64,
    /// Liquid mole fractions after the flash.
    pub x: Vec<f64>,
    /// Vapour mole fractions after the flash.
    pub y: Vec<f64>,
    /// Feed molar enthalpy, J/mol.
    pub h: f64,
}

fn h_liq(mix: &Mixture, t: f64, comp: &[f64]) -> f64 {
    comp.iter().zip(mix.cp.iter()).map(|(c, cp)| c * cp).sum::<f64>() * (t - T_REF)
}

fn h_vap(mix: &Mixture, t: f64, comp: &[f64]) -> f64 {
    comp.iter()
        .zip(mix.cp.iter().zip(mix.lam.iter()))
        .map(|(c, (cp, lam))| c * (cp * (t - T_REF) + lam))
        .sum()
}

/// Equilibrium split of overall composition `z` at (t, p):
/// returns (psi, x, y). Iterates the Rachford–Rice equation with the
/// equilibrium ratios re-evaluated at the current liquid composition —
/// the reference algorithm exactly (50 outer iterations, 60 bisection
/// iterations, 1e-12 convergence test).
fn flash_at_t(mix: &Mixture, z: &[f64], t: f64, p: f64) -> (f64, Vec<f64>, Vec<f64>) {
    let nc = mix.nc();
    let mut x = z.to_vec();
    let mut psi = 0.5f64;
    let mut k = vec![0.0; nc];
    for _ in 0..50 {
        mix.k_values(&x, t, p, &mut k);
        let (mut lo, mut hi) = (0.0f64, 1.0f64);
        for _ in 0..60 {
            let mid = 0.5 * (lo + hi);
            let g: f64 = z
                .iter()
                .zip(k.iter())
                .map(|(zc, kc)| zc * (kc - 1.0) / (1.0 + mid * (kc - 1.0)))
                .sum();
            if g > 0.0 {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        let psi_new = 0.5 * (lo + hi);
        let x_new: Vec<f64> = z
            .iter()
            .zip(k.iter())
            .map(|(zc, kc)| zc / (1.0 + psi_new * (kc - 1.0)))
            .collect();
        let dx = x_new
            .iter()
            .zip(x.iter())
            .map(|(a, b)| (a - b).abs())
            .fold(0.0f64, f64::max);
        let converged = dx < 1e-12 && (psi_new - psi).abs() < 1e-12;
        psi = psi_new;
        x = x_new;
        if converged {
            break;
        }
    }
    mix.k_values(&x, t, p, &mut k);
    let y: Vec<f64> = x.iter().zip(k.iter()).map(|(xc, kc)| xc * kc).collect();
    (psi, x, y)
}

/// Flash the feed from its stated conditions to the column pressure.
/// The feed may be a liquid, an equilibrium two-phase mixture, or a
/// vapour at its stated conditions; its enthalpy is the
/// equilibrium-mixture enthalpy there, as in the reference.
pub fn feed_flash(
    mix: &Mixture,
    z: &[f64],
    t_feed: f64,
    p_feed: f64,
    p_col: f64,
) -> Result<Flash, String> {
    let (t_bub_feed, _) = mix.bubble_point(z, p_feed);
    let h_f = if t_feed <= t_bub_feed {
        h_liq(mix, t_feed, z)
    } else {
        let (t_dew_feed, _) = mix.dew_point(z, p_feed);
        if t_feed >= t_dew_feed {
            h_vap(mix, t_feed, z)
        } else {
            let (psi_in, x_in, y_in) = flash_at_t(mix, z, t_feed, p_feed);
            (1.0 - psi_in) * h_liq(mix, t_feed, &x_in)
                + psi_in * h_vap(mix, t_feed, &y_in)
        }
    };
    let (t_bub, y_bub) = mix.bubble_point(z, p_col);
    let (t_dew, x_dew) = mix.dew_point(z, p_col);
    if h_f <= h_liq(mix, t_bub, z) {
        // Subcooled at the column pressure too: no flash.
        return Ok(Flash { psi: 0.0, t: t_feed, x: z.to_vec(), y: y_bub, h: h_f });
    }
    if h_f >= h_vap(mix, t_dew, z) {
        return Ok(Flash { psi: 1.0, t: t_feed, x: x_dew, y: z.to_vec(), h: h_f });
    }
    let resid = |t: f64| {
        let (psi, x, y) = flash_at_t(mix, z, t, p_col);
        let h = (1.0 - psi) * h_liq(mix, t, &x) + psi * h_vap(mix, t, &y);
        (h - h_f, psi, x, y)
    };
    let (mut lo, mut hi) = (t_bub, t_dew);
    let (flo, _, _, _) = resid(lo);
    for _ in 0..60 {
        let mid = 0.5 * (lo + hi);
        let (fm, _, _, _) = resid(mid);
        if (fm > 0.0) == (flo > 0.0) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    let t = 0.5 * (lo + hi);
    let (_, psi, x, y) = resid(t);
    Ok(Flash { psi, t, x, y, h: h_f })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::mixtures::alkanes;

    #[test]
    fn two_phase_and_vapour_feeds() {
        let mix = alkanes();
        let z = [0.4, 0.3, 0.3];
        let (tb, _) = mix.bubble_point(&z, 150.0);
        let (td, _) = mix.dew_point(&z, 150.0);
        let r = feed_flash(&mix, &z, tb + 10.0, 150.0, 150.0).unwrap();
        assert!((r.psi - 0.520).abs() < 0.01, "psi={}", r.psi);
        let r2 = feed_flash(&mix, &z, td + 15.0, 150.0, 150.0).unwrap();
        assert!((r2.psi - 1.0).abs() < 1e-9, "psi={}", r2.psi);
        let r0 = feed_flash(&mix, &z, tb - 10.0, 150.0, 150.0).unwrap();
        assert_eq!(r0.psi, 0.0);
    }
}
