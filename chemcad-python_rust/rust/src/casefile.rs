//! Data-driven case files (JSON), Antoine, Henry, regular-solution
//! and Chao-Seader / Grayson-Streed correlations, and Arrhenius
//! kinetics as data. Mirror of the Python modules casefile.py and
//! thermo_extra.py; same symbol definitions apply there: temperature
//! T in kelvin (K), pressure P in pascal (Pa), critical temperature
//! Tc in kelvin (K), critical pressure Pc in pascal (Pa), acentric
//! factor omega (dimensionless), Henry constant H in pascal (Pa),
//! molar volume in m3/mol, solubility parameter in (J/m3)^0.5,
//! Antoine coefficients [A, B, C] with log10(Psat / Pa) = A - B/(T+C),
//! Arrhenius pre-exponential factor a_r and activation energy ea in
//! J/mol giving a rate in mol/(m3 s) from concentrations in mol/m3.
//! Zero external dependencies: the JSON parser below handles the
//! case-file subset (objects, arrays, strings, numbers, booleans,
//! null). A case kij matrix is applied to the EOS through
//! CubicEOS::with_kij (Round 2 fix).

use crate::activity::{gamma_margules, gamma_nrtl, gamma_uniquac,
                      gamma_van_laar, gamma_wilson};
use crate::eos::{CubicEOS, EosKind, R};
use crate::flash::{flash_tp, FlashResult};
use crate::unifac::gamma_unifac;

#[derive(Debug, Clone, PartialEq)]
pub enum Json {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

impl Json {
    pub fn get(&self, key: &str) -> Option<&Json> {
        match self {
            Json::Obj(pairs) => pairs.iter().find(|(k, _)| k == key)
                .map(|(_, v)| v),
            _ => None,
        }
    }
    pub fn as_f64(&self) -> f64 {
        match self { Json::Num(v) => *v, _ => 0.0 }
    }
    pub fn as_arr(&self) -> Vec<Json> {
        match self { Json::Arr(a) => a.clone(), _ => Vec::new() }
    }
    pub fn as_str(&self) -> String {
        match self { Json::Str(s) => s.clone(), _ => String::new() }
    }
    pub fn vec_f64(&self) -> Vec<f64> {
        self.as_arr().iter().map(|v| v.as_f64()).collect()
    }
    pub fn mat_f64(&self) -> Vec<Vec<f64>> {
        self.as_arr().iter().map(|v| v.vec_f64()).collect()
    }
}

struct Parser<'a> { b: &'a [u8], i: usize }
impl<'a> Parser<'a> {
    fn ws(&mut self) {
        while self.i < self.b.len() && (self.b[self.i] as char).is_whitespace() {
            self.i += 1;
        }
    }
    fn value(&mut self) -> Json {
        self.ws();
        match self.b[self.i] as char {
            '{' => {
                self.i += 1;
                let mut pairs = Vec::new();
                loop {
                    self.ws();
                    if self.b[self.i] as char == '}' { self.i += 1; break; }
                    let k = match self.value() { Json::Str(s) => s, _ => String::new() };
                    self.ws();
                    self.i += 1; // colon
                    let v = self.value();
                    pairs.push((k, v));
                    self.ws();
                    if self.b[self.i] as char == ',' { self.i += 1; }
                }
                Json::Obj(pairs)
            }
            '[' => {
                self.i += 1;
                let mut items = Vec::new();
                loop {
                    self.ws();
                    if self.b[self.i] as char == ']' { self.i += 1; break; }
                    items.push(self.value());
                    self.ws();
                    if self.b[self.i] as char == ',' { self.i += 1; }
                }
                Json::Arr(items)
            }
            '"' => {
                self.i += 1;
                let mut s = String::new();
                while self.b[self.i] as char != '"' {
                    if self.b[self.i] as char == '\\' {
                        self.i += 1;
                        match self.b[self.i] as char {
                            'n' => s.push('\n'),
                            't' => s.push('\t'),
                            'r' => s.push('\r'),
                            c => s.push(c),
                        }
                    } else {
                        s.push(self.b[self.i] as char);
                    }
                    self.i += 1;
                }
                self.i += 1;
                Json::Str(s)
            }
            't' => { self.i += 4; Json::Bool(true) }
            'f' => { self.i += 5; Json::Bool(false) }
            'n' => { self.i += 4; Json::Null }
            _ => {
                let start = self.i;
                while self.i < self.b.len()
                    && "-+0123456789.eE".contains(self.b[self.i] as char) {
                    self.i += 1;
                }
                Json::Num(std::str::from_utf8(&self.b[start..self.i])
                    .unwrap().parse().unwrap_or(0.0))
            }
        }
    }
}

pub fn parse_json(text: &str) -> Json {
    Parser { b: text.as_bytes(), i: 0 }.value()
}

pub fn antoine_psat(coeffs: &[f64], t: f64) -> f64 {
    10f64.powf(coeffs[0] - coeffs[1] / (t + coeffs[2]))
}

pub fn henry_constant(h_ref: f64, t_ref: f64, b_h: f64, t: f64) -> f64 {
    h_ref * (b_h * (1.0 / t - 1.0 / t_ref)).exp()
}

pub fn gamma_regular_solution(x: &[f64], t: f64, mv: &[f64],
                              deltas: &[f64]) -> Vec<f64> {
    let den: f64 = x.iter().zip(mv).map(|(a, b)| a * b).sum();
    let phi: Vec<f64> = x.iter().zip(mv).map(|(a, b)| a * b / den).collect();
    let dbar: f64 = phi.iter().zip(deltas).map(|(a, b)| a * b).sum();
    (0..x.len()).map(|i| (mv[i] * (deltas[i] - dbar).powi(2) / (R * t)).exp())
        .collect()
}

fn poly(coeffs: &[f64], tr: f64, pr: f64) -> f64 {
    let c = |i: usize| if i < coeffs.len() { coeffs[i] } else { 0.0 };
    c(0) + c(1) / tr + c(2) * tr + c(3) * tr * tr + c(4) * pr
        + c(5) * tr * pr + c(6) * pr * pr
}

pub fn chao_seader_ln_nu(t: f64, p: f64, tc: &[f64], pc: &[f64],
                         omega: &[f64], c0: &[f64], c1: &[f64]) -> Vec<f64> {
    (0..tc.len()).map(|i| {
        poly(c0, t / tc[i], p / pc[i]) + omega[i] * poly(c1, t / tc[i], p / pc[i])
    }).collect()
}

pub fn arrhenius_rate(a_r: f64, ea: f64, orders: &[f64], c: &[f64],
                      t: f64) -> f64 {
    let mut r = a_r * (-ea / (R * t)).exp();
    for i in 0..orders.len() {
        if orders[i] != 0.0 { r *= c[i].max(0.0).powf(orders[i]); }
    }
    r
}

#[derive(Debug, Clone)]
pub struct Reaction {
    pub nu: Vec<f64>,
    pub a_r: Option<f64>,
    pub ea: f64,
    pub orders: Vec<f64>,
}

#[derive(Debug, Clone)]
pub struct Case {
    pub names: Vec<String>,
    pub tc: Vec<f64>,
    pub pc: Vec<f64>,
    pub omega: Vec<f64>,
    pub cp: Vec<Vec<f64>>,
    pub antoine: Vec<Vec<f64>>,
    pub hf: Vec<f64>,
    pub gf: Vec<f64>,
    pub lam_ref: Vec<f64>,
    pub t_ref_lam: Vec<f64>,
    pub molar_volume: Vec<f64>,
    pub solubility: Vec<f64>,
    pub unifac_groups: Vec<Vec<f64>>,
    pub model: String,
    pub eos_kind: String,
    pub tau: Vec<Vec<f64>>,
    pub b_mat: Vec<Vec<f64>>,
    pub alpha: Vec<Vec<f64>>,
    pub r_par: Vec<f64>,
    pub q_par: Vec<f64>,
    pub du: Vec<Vec<f64>>,
    pub lambda: Vec<Vec<f64>>,
    pub a12: f64,
    pub a21: f64,
    pub unifac_r: Vec<f64>,
    pub unifac_q: Vec<f64>,
    pub unifac_a: Vec<Vec<f64>>,
    pub solute: Vec<bool>,
    pub henry: Vec<Vec<f64>>,
    pub coeffs0: Vec<f64>,
    pub coeffs1: Vec<f64>,
    pub kij: Vec<Vec<f64>>,
    pub reactions: Vec<Reaction>,
}

impl Case {
    pub fn from_json(root: &Json) -> Case {
        let comps = root.get("components").map(|v| v.as_arr())
            .unwrap_or_default();
        let th = root.get("thermo").cloned()
            .unwrap_or(Json::Obj(Vec::new()));
        let getv = |c: &Json, k: &str| c.get(k).map(|v| v.as_f64())
            .unwrap_or(0.0);
        let tau_or = |k: &str| th.get(k).map(|v| v.mat_f64())
            .unwrap_or_default();
        let unifac = th.get("unifac").cloned()
            .unwrap_or(Json::Obj(Vec::new()));
        let reactions = root.get("reactions").map(|v| v.as_arr())
            .unwrap_or_default().iter().map(|r| {
                let arr = r.get("arrhenius");
                Reaction {
                    nu: r.get("nu").map(|v| v.vec_f64()).unwrap_or_default(),
                    a_r: arr.and_then(|a| a.get("A")).map(|v| v.as_f64()),
                    ea: arr.and_then(|a| a.get("Ea")).map(|v| v.as_f64())
                        .unwrap_or(0.0),
                    orders: arr.and_then(|a| a.get("orders"))
                        .map(|v| v.vec_f64()).unwrap_or_default(),
                }
            }).collect();
        Case {
            names: comps.iter().map(|c| c.get("name")
                .map(|v| v.as_str()).unwrap_or_default()).collect(),
            tc: comps.iter().map(|c| getv(c, "Tc")).collect(),
            pc: comps.iter().map(|c| getv(c, "Pc")).collect(),
            omega: comps.iter().map(|c| getv(c, "omega")).collect(),
            cp: comps.iter().map(|c| c.get("cp").map(|v| v.vec_f64())
                .unwrap_or_else(|| vec![0.0; 4])).collect(),
            antoine: comps.iter().map(|c| c.get("antoine")
                .map(|v| v.vec_f64()).unwrap_or_default()).collect(),
            hf: comps.iter().map(|c| getv(c, "Hf")).collect(),
            gf: comps.iter().map(|c| getv(c, "Gf")).collect(),
            lam_ref: comps.iter().map(|c| getv(c, "lam_ref")).collect(),
            t_ref_lam: comps.iter().enumerate().map(|(i, c)| {
                c.get("T_ref_lam").map(|v| v.as_f64())
                    .unwrap_or_else(|| getv(c, "Tc"))
            }).collect(),
            molar_volume: comps.iter().map(|c| getv(c, "molar_volume")).collect(),
            solubility: comps.iter().map(|c| getv(c, "solubility")).collect(),
            unifac_groups: comps.iter().map(|c| c.get("unifac_groups")
                .map(|v| v.vec_f64()).unwrap_or_default()).collect(),
            model: th.get("model").map(|v| v.as_str())
                .unwrap_or_else(|| "eos".into()),
            eos_kind: th.get("eos_kind").map(|v| v.as_str())
                .unwrap_or_else(|| "PR".into()),
            tau: tau_or("tau"),
            b_mat: tau_or("b"),
            alpha: tau_or("alpha"),
            r_par: th.get("r").map(|v| v.vec_f64()).unwrap_or_default(),
            q_par: th.get("q").map(|v| v.vec_f64()).unwrap_or_default(),
            du: tau_or("du"),
            lambda: tau_or("Lambda"),
            a12: th.get("A12").map(|v| v.as_f64()).unwrap_or(0.0),
            a21: th.get("A21").map(|v| v.as_f64()).unwrap_or(0.0),
            unifac_r: unifac.get("R").map(|v| v.vec_f64()).unwrap_or_default(),
            unifac_q: unifac.get("Q").map(|v| v.vec_f64()).unwrap_or_default(),
            unifac_a: unifac.get("a").map(|v| v.mat_f64()).unwrap_or_default(),
            solute: th.get("solute").map(|v| v.as_arr().iter()
                .map(|b| matches!(b, Json::Bool(true))).collect())
                .unwrap_or_default(),
            henry: tau_or("henry"),
            coeffs0: th.get("coeffs0").map(|v| v.vec_f64()).unwrap_or_default(),
            coeffs1: th.get("coeffs1").map(|v| v.vec_f64()).unwrap_or_default(),
            kij: tau_or("kij"),
            reactions,
        }
    }

    pub fn load_str(text: &str) -> Case {
        Case::from_json(&parse_json(text))
    }

    pub fn eos(&self) -> CubicEOS {
        let kind = if self.eos_kind == "SRK" { EosKind::SRK } else { EosKind::PR };
        CubicEOS::with_kij(kind, self.tc.clone(), self.pc.clone(),
                           self.omega.clone(), self.kij.clone())
    }

    pub fn psat_list(&self, t: f64) -> Vec<f64> {
        self.antoine.iter().map(|c| antoine_psat(c, t)).collect()
    }

    pub fn gamma(&self, x: &[f64], t: f64) -> Vec<f64> {
        let n = x.len();
        match self.model.as_str() {
            "nrtl" => {
                let tau = if !self.b_mat.is_empty() {
                    self.b_mat.iter().map(|row| row.iter()
                        .map(|v| v / t).collect()).collect()
                } else { self.tau.clone() };
                gamma_nrtl(x, &tau, &self.alpha)
            }
            "uniquac" => {
                let tau = if !self.du.is_empty() {
                    self.du.iter().map(|row| row.iter()
                        .map(|v| (-v / (R * t)).exp()).collect()).collect()
                } else { self.tau.clone() };
                gamma_uniquac(x, &self.r_par, &self.q_par, &tau)
            }
            "wilson" => gamma_wilson(x, &self.lambda),
            "van_laar" => gamma_van_laar(x, self.a12, self.a21),
            "margules" => gamma_margules(x, self.a12, self.a21),
            "unifac" => gamma_unifac(x, t, &self.unifac_groups,
                                     &self.unifac_r, &self.unifac_q,
                                     &self.unifac_a),
            "regular_solution" => gamma_regular_solution(
                x, t, &self.molar_volume, &self.solubility),
            _ => vec![1.0; n],
        }
    }

    pub fn k_values(&self, x: &[f64], y: &[f64], t: f64, p: f64) -> Vec<f64> {
        match self.model.as_str() {
            "eos" => self.eos().k_values(x, y, t, p),
            "chao_seader" => {
                let ln_nu = chao_seader_ln_nu(t, p, &self.tc, &self.pc,
                                              &self.omega, &self.coeffs0,
                                              &self.coeffs1);
                let phi_v = self.eos().phi(y, t, p, true);
                (0..x.len()).map(|i| ln_nu[i].exp() / phi_v[i]).collect()
            }
            "henry" => {
                let g = self.gamma(x, t);
                let ps = self.psat_list(t);
                (0..x.len()).map(|i| {
                    if i < self.solute.len() && self.solute[i] {
                        henry_constant(self.henry[i][0], self.henry[i][1],
                                       self.henry[i][2], t) / p
                    } else { g[i] * ps[i] / p }
                }).collect()
            }
            _ => {
                let g = self.gamma(x, t);
                let ps = self.psat_list(t);
                (0..x.len()).map(|i| g[i] * ps[i] / p).collect()
            }
        }
    }

    pub fn flash(&self, z: &[f64], t: f64, p: f64) -> FlashResult {
        flash_tp(z, t, p, |x, y, tt, pp| self.k_values(x, y, tt, pp))
    }

    pub fn rate(&self, rxn: usize, c: &[f64], t: f64) -> f64 {
        let r = &self.reactions[rxn];
        arrhenius_rate(r.a_r.unwrap_or(0.0), r.ea, &r.orders, c, t)
    }
}
