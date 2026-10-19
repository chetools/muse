//! Hand-rolled small dense linear algebra over `f64`.
//!
//! The crate keeps a deliberately empty dependency tree so that the later
//! WebAssembly build pulls in nothing beyond `core`/`alloc`. The routines
//! here cover everything the estimator needs: fixed 4x4/2x2 operations for
//! the model and the extended Kalman filter, and a variable-size dense
//! matrix with Cholesky factorization for the box-QP active-set solver
//! (`n = 4(H+1) <= 124`). No pivoting beyond partial pivoting in the 4x4
//! inverse; all sizes are known at the call sites.

/// Length-4 vector.
pub type V4 = [f64; 4];
/// 4x4 matrix, row-major.
pub type M4 = [[f64; 4]; 4];
/// Length-2 vector.
pub type V2 = [f64; 2];
/// 2x2 matrix, row-major.
pub type M2 = [[f64; 2]; 2];

/// 4x4 identity matrix.
pub fn m4_eye() -> M4 {
    let mut m = [[0.0; 4]; 4];
    for i in 0..4 {
        m[i][i] = 1.0;
    }
    m
}

/// Element-wise sum of two 4x4 matrices.
pub fn m4_add(a: &M4, b: &M4) -> M4 {
    let mut c = [[0.0; 4]; 4];
    for i in 0..4 {
        for j in 0..4 {
            c[i][j] = a[i][j] + b[i][j];
        }
    }
    c
}

/// Scalar multiple of a 4x4 matrix.
pub fn m4_scale(a: &M4, s: f64) -> M4 {
    let mut c = [[0.0; 4]; 4];
    for i in 0..4 {
        for j in 0..4 {
            c[i][j] = a[i][j] * s;
        }
    }
    c
}

/// Matrix product `C = A B` of two 4x4 matrices.
pub fn m4_mul(a: &M4, b: &M4) -> M4 {
    let mut c = [[0.0; 4]; 4];
    for i in 0..4 {
        for j in 0..4 {
            let mut s = 0.0;
            for k in 0..4 {
                s += a[i][k] * b[k][j];
            }
            c[i][j] = s;
        }
    }
    c
}

/// Matrix product `C = A B^T` of two 4x4 matrices.
pub fn m4_mul_m4t(a: &M4, b: &M4) -> M4 {
    let mut c = [[0.0; 4]; 4];
    for i in 0..4 {
        for j in 0..4 {
            let mut s = 0.0;
            for k in 0..4 {
                s += a[i][k] * b[j][k];
            }
            c[i][j] = s;
        }
    }
    c
}

/// Matrix-vector product `y = A x` for a 4x4 matrix.
pub fn m4_vec(a: &M4, x: &V4) -> V4 {
    let mut y = [0.0; 4];
    for i in 0..4 {
        let mut s = 0.0;
        for j in 0..4 {
            s += a[i][j] * x[j];
        }
        y[i] = s;
    }
    y
}

/// Matrix-vector product `y = A^T x` for a 4x4 matrix.
pub fn m4t_vec(a: &M4, x: &V4) -> V4 {
    let mut y = [0.0; 4];
    for i in 0..4 {
        let mut s = 0.0;
        for j in 0..4 {
            s += a[j][i] * x[j];
        }
        y[i] = s;
    }
    y
}

/// Add the diagonal vector `d` to the diagonal of `m` in place.
pub fn m4_add_diag(m: &mut M4, d: &V4) {
    for i in 0..4 {
        m[i][i] += d[i];
    }
}

/// Element-wise difference of two length-4 vectors.
pub fn v4_sub(a: &V4, b: &V4) -> V4 {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2], a[3] - b[3]]
}

/// Element-wise sum of two length-4 vectors.
pub fn v4_add(a: &V4, b: &V4) -> V4 {
    [a[0] + b[0], a[1] + b[1], a[2] + b[2], a[3] + b[3]]
}

/// Scalar multiple of a length-4 vector.
pub fn v4_scale(a: &V4, s: f64) -> V4 {
    [a[0] * s, a[1] * s, a[2] * s, a[3] * s]
}

/// Analytic inverse of a 2x2 matrix. Panics on a zero determinant.
pub fn m2_inv(m: &M2) -> M2 {
    let det = m[0][0] * m[1][1] - m[0][1] * m[1][0];
    assert!(det != 0.0, "singular 2x2 matrix");
    let s = 1.0 / det;
    [
        [m[1][1] * s, -m[0][1] * s],
        [-m[1][0] * s, m[0][0] * s],
    ]
}

/// Inverse of a 4x4 matrix by Gauss-Jordan elimination with partial
/// pivoting. Panics on a singular matrix.
pub fn m4_inv(m: &M4) -> M4 {
    let mut a = [[0.0; 8]; 4];
    for i in 0..4 {
        for j in 0..4 {
            a[i][j] = m[i][j];
        }
        a[i][4 + i] = 1.0;
    }
    for col in 0..4 {
        let mut piv = col;
        for r in (col + 1)..4 {
            if a[r][col].abs() > a[piv][col].abs() {
                piv = r;
            }
        }
        assert!(a[piv][col] != 0.0, "singular 4x4 matrix");
        a.swap(piv, col);
        let d = a[col][col];
        for j in 0..8 {
            a[col][j] /= d;
        }
        for r in 0..4 {
            if r != col {
                let f = a[r][col];
                for j in 0..8 {
                    a[r][j] -= f * a[col][j];
                }
            }
        }
    }
    let mut inv = [[0.0; 4]; 4];
    for i in 0..4 {
        for j in 0..4 {
            inv[i][j] = a[i][4 + j];
        }
    }
    inv
}

/// Row-major dense square matrix of size `n x n` for the QP layer.
#[derive(Clone, Debug)]
pub struct DMat {
    n: usize,
    d: Vec<f64>,
}

impl DMat {
    /// Zero matrix of size `n x n`.
    pub fn zeros(n: usize) -> Self {
        Self {
            n,
            d: vec![0.0; n * n],
        }
    }

    /// Build from nested row vectors. Panics on ragged input.
    pub fn from_rows(rows: &[Vec<f64>]) -> Self {
        let n = rows.len();
        let mut d = Vec::with_capacity(n * n);
        for r in rows {
            assert_eq!(r.len(), n, "ragged matrix input");
            d.extend_from_slice(r);
        }
        Self { n, d }
    }

    /// Matrix dimension.
    pub fn n(&self) -> usize {
        self.n
    }

    /// Read entry `(i, j)`.
    pub fn get(&self, i: usize, j: usize) -> f64 {
        self.d[i * self.n + j]
    }

    /// Write entry `(i, j)`.
    pub fn set(&mut self, i: usize, j: usize, v: f64) {
        self.d[i * self.n + j] = v;
    }

    /// Add `v` to entry `(i, j)`.
    pub fn add(&mut self, i: usize, j: usize, v: f64) {
        self.d[i * self.n + j] += v;
    }

    /// Matrix-vector product `y = self x`.
    pub fn matvec(&self, x: &[f64]) -> Vec<f64> {
        assert_eq!(x.len(), self.n);
        let n = self.n;
        let mut y = vec![0.0; n];
        for i in 0..n {
            let mut s = 0.0;
            for j in 0..n {
                s += self.d[i * n + j] * x[j];
            }
            y[i] = s;
        }
        y
    }

    /// Replace `self` by `(self + self^T)/2`, removing roundoff asymmetry.
    pub fn symmetrize(&mut self) {
        let n = self.n;
        for i in 0..n {
            for j in (i + 1)..n {
                let v = 0.5 * (self.get(i, j) + self.get(j, i));
                self.set(i, j, v);
                self.set(j, i, v);
            }
        }
    }

    /// Cholesky factorization: returns the lower-triangular `L` with
    /// `L L^T = self`, or `None` when `self` is not positive definite.
    /// Only the lower triangle of `self` is read.
    pub fn cholesky(&self) -> Option<DMat> {
        let n = self.n;
        let mut l = DMat::zeros(n);
        for i in 0..n {
            for j in 0..=i {
                let mut s = self.get(i, j);
                for k in 0..j {
                    s -= l.get(i, k) * l.get(j, k);
                }
                if i == j {
                    if s <= 0.0 {
                        return None;
                    }
                    l.set(i, j, s.sqrt());
                } else {
                    l.set(i, j, s / l.get(j, j));
                }
            }
        }
        Some(l)
    }

    /// Solve `L L^T x = b` given the Cholesky factor `L`.
    pub fn chol_solve(l: &DMat, b: &[f64]) -> Vec<f64> {
        let n = l.n;
        assert_eq!(b.len(), n);
        let mut y = vec![0.0; n];
        for i in 0..n {
            let mut s = b[i];
            for j in 0..i {
                s -= l.get(i, j) * y[j];
            }
            y[i] = s / l.get(i, i);
        }
        let mut x = vec![0.0; n];
        for i in (0..n).rev() {
            let mut s = y[i];
            for j in (i + 1)..n {
                s -= l.get(j, i) * x[j];
            }
            x[i] = s / l.get(i, i);
        }
        x
    }

    /// Solve `self x = b` via Cholesky; `None` if not positive definite.
    pub fn solve_pd(&self, b: &[f64]) -> Option<Vec<f64>> {
        self.cholesky().map(|l| Self::chol_solve(&l, b))
    }
}
