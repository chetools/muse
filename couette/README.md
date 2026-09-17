# Couette flow between concentric cylinders 🌀

Streamlit web app that calculates and visualizes the steady laminar velocity
profile of a Newtonian fluid between rotating concentric cylinders.

- **Inputs** — inner/outer radii, rotation rates (rpm, negative = counter-rotation),
  viscosity (presets for water and glycerol, or custom).
- **Outputs** — azimuthal velocity profile $v_\\theta(r)$, shear-stress
  distribution $\\tau_{r\\theta}(r) \\propto 1/r^2$, torque per unit length
  (computed, not prescribed), wall shear stresses, and a cross-section vector
  field of the annulus.
- **Theory panel** — full derivation from torque balance and geometric/physical
  arguments, deliberately avoiding Navier–Stokes; flags the one place an NS
  assumption would normally sneak in, and covers limiting cases (narrow gap →
  plane Couette, fixed outer cylinder, solid-body rotation) plus caveats
  (Taylor vortices, end effects).

## Run locally

```bash
pip install -r requirements.txt
streamlit run couette/app.py
```

## Tests

```bash
pytest tests/test_couette_physics.py -v
```

The suite includes hand-verified anchors (torque, wall shear stresses,
mid-gap velocity for R₁=50 mm, R₂=100 mm, Ω₁=10 rad/s, μ=1 mPa·s),
no-slip checks, the solid-body-rotation zero-shear check, the narrow-gap
plane-Couette limit, and input validation.
