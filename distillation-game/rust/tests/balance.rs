//! Instantaneous balance closure (Amendment A19): the liquid
//! inventories' component derivatives, assembled from the state
//! derivative, equal the boundary flows plus the vapour-storage
//! term (V_R - W_in - W_bp - W_relief) * y_top.
use distgame_engine::plant::Plant;

fn closure_residual(plant: &mut Plant, s: &[f64]) -> (f64, f64) {
    let ds = plant.rhs(s, None);
    let l = &plant.last;
    let nst = 13usize;
    let nc = 3usize;
    let o = (nst + 2) * nc;
    let c_reb = s[o].max(0.0) + s[o + 8].max(0.0);
    let mut d_comp = [0.0; 3];
    for i in 0..nc {
        d_comp[i] += (ds[o] + ds[o + 8]) * s[i] + c_reb.max(1.0) * ds[i];
        for j in 1..nst {
            d_comp[i] += plant.col.m[j] * ds[j * nc + i];
        }
        d_comp[i] += ds[o + 1] * s[nst * nc + i]
            + s[o + 1].clamp(0.0, 2000.0) * ds[nst * nc + i];
        d_comp[i] += ds[o + 2] * s[(nst + 1) * nc + i]
            + s[o + 2].max(1.0) * ds[(nst + 1) * nc + i];
    }
    let f = plant.col.f;
    let mut worst = 0.0f64;
    for i in 0..nc {
        let bd = f * plant.col.z[i] - l.d * l.x_drum[i] - l.b * s[i]
            - l.w_relief * l.y_top[i];
        let vap_store = (l.v_r - l.w_in - l.w_bp - l.w_relief) * l.y_top[i];
        worst = worst.max((d_comp[i] - bd + vap_store).abs());
    }
    (worst, l.flash_frac)
}

#[test]
fn component_balances_close() {
    let mut plant = Plant::new();
    let s0 = plant.state0.clone();
    let (res_nom, _) = closure_residual(&mut plant, &s0);
    assert!(res_nom < 1e-6, "nominal residual {res_nom:e}");
    // Constructed hot-pool state: negative margin, riser flashing.
    let mut s_hot = s0.clone();
    s_hot[48] = 250.0;
    s_hot[49] = 250.0;
    s_hot[51] = 335.0;
    s_hot[52] = 315.0;
    let (res_hot, flash) = closure_residual(&mut plant, &s_hot);
    assert!(flash > 0.05, "flash fraction {flash}");
    assert!(res_hot < 1e-6, "hot-pool residual {res_hot:e}");
}
