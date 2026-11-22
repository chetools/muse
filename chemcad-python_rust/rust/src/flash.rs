//! TP flash: Rust port of python/flash.py (Rachford-Rice with the
//! guarded boundary evaluation, successive substitution on K).

pub fn rachford_rice(z: &[f64], k: &[f64]) -> f64 {
    let f = |psi: f64| -> f64 {
        z.iter()
            .zip(k.iter())
            .map(|(zi, ki)| zi * (ki - 1.0) / (1.0 + psi * (ki - 1.0)))
            .sum()
    };
    let f0 = f(0.0);
    if f0 < 0.0 {
        return 0.0;
    }
    let f1 = f(1.0 - 1e-12);
    if f1 > 0.0 {
        return 1.0;
    }
    let (mut lo, mut hi) = (0.0f64, 1.0f64);
    let mut flo = f0;
    for _ in 0..200 {
        let mid = 0.5 * (lo + hi);
        let fm = f(mid);
        if fm.abs() < 1e-13 {
            return mid;
        }
        if (fm > 0.0) == (flo > 0.0) {
            lo = mid;
            flo = fm;
        } else {
            hi = mid;
        }
    }
    0.5 * (lo + hi)
}

pub struct FlashResult {
    pub psi: f64,
    pub x: Vec<f64>,
    pub y: Vec<f64>,
    pub two_phase: bool,
}

/// kfun(x, y, T, P) -> K values, as in the Python signature.
pub fn flash_tp<F: Fn(&[f64], &[f64], f64, f64) -> Vec<f64>>(
    z: &[f64],
    t: f64,
    p: f64,
    kfun: F,
) -> FlashResult {
    let n = z.len();
    let mut y: Vec<f64> = z.to_vec();
    let mut x: Vec<f64> = z.to_vec();
    let mut psi = 0.5f64;
    let mut two = false;
    for _ in 0..500 {
        let k = kfun(&x, &y, t, p);
        if k.iter().all(|ki| (ki - 1.0).abs() < 1e-12) {
            break;
        }
        let psi_new = rachford_rice(z, &k);
        let x_new: Vec<f64> = (0..n)
            .map(|i| z[i] / (1.0 + psi_new * (k[i] - 1.0)))
            .collect();
        let y_new: Vec<f64> = (0..n).map(|i| k[i] * x_new[i]).collect();
        let dx: f64 = x_new
            .iter()
            .zip(x.iter())
            .map(|(a, b)| (a - b).abs())
            .fold(0.0, f64::max);
        let dy: f64 = y_new
            .iter()
            .zip(y.iter())
            .map(|(a, b)| (a - b).abs())
            .fold(0.0, f64::max);
        x = x_new;
        y = y_new;
        psi = psi_new;
        two = psi > 0.0 && psi < 1.0;
        if dx.max(dy) < 1e-11 {
            break;
        }
    }
    if psi <= 0.0 {
        x = z.to_vec();
        y = z.to_vec();
    } else if psi >= 1.0 {
        y = z.to_vec();
        x = z.to_vec();
    }
    FlashResult {
        psi,
        x,
        y,
        two_phase: two,
    }
}
