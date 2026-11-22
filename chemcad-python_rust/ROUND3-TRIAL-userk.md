# Round 3 Trial — K-tables and Polynomial User-K

Symbols: temperature T in kelvin (K); pressure P in pascal (Pa);
equilibrium ratio K_i (dimensionless) for component i
(dimensionless integer index).

## What was built

New files only; no existing file was edited.

- `python/thermo_userk.py` — two caller-data models:
  - `KTable(T_grid, P_grid, K_table)`: K_i supplied as data on a
    rectangular T/P grid, `K_table[i][j][k]` at `T_grid[j]` and
    `P_grid[k]`. Methods `log_k_values(T, P)`, `k_values(T, P)`,
    and `kfun(x, y, T, P)` (the library K-function adapter;
    composition arguments are unused, a table carries no
    composition dependence). `k_table_from_data(data)` builds one
    from a case-data style dict.
  - `PolyUserK(coeffs)`: ln K_i as a polynomial with the fixed
    basis 1, T, T^2, 1/T, P, T P; `coeffs[i]` is
    `[a0, a1, a2, a3, a4, a5]` with a0 dimensionless, a1 in 1/K,
    a2 in 1/K^2, a3 in K, a4 in 1/Pa, a5 in 1/(K Pa); missing
    trailing coefficients are zero. Same three methods, plus
    `poly_userk_from_data(data)`.
  - No chemical name or fitted coefficient is in the library
    code (grep for 9 common component names: 0 hits). All data
    is caller input. Validation raises ValueError for empty or
    non-increasing grids, ragged tables, non-positive or
    non-finite table values, over-long coefficient lists, and
    non-positive T or P for the polynomial.

- `python/test_userk.py` — battery, 25 checks, all synthetic
  inputs supplied in the battery itself.

## Interpolation scheme

Bilinear in ln K_i as a function of T and P: linear in T, linear
in P, neither coordinate log-transformed. For the cell
containing (T, P), with u the fractional position in T
(dimensionless) and v the fractional position in P
(dimensionless), ln K_i is the (1-u)(1-v), u(1-v), (1-u)v, uv
weighted sum of the four corner ln values. A single-point axis
reduces the scheme to linear interpolation in the remaining
coordinate and requires an exact match on the single-point
coordinate.

Extrapolation is never silent: T outside the temperature grid
or P outside the pressure grid raises ValueError. The battery
asserts this on both axes, on both sides, and for a
single-point-axis mismatch.

## Test results

`python/test_userk.py`: 25 PASS, FAILURES: none.

- Node recovery at all 4 grid nodes: exact to 1e-12 relative
  (returned values 1.0, 0.5, 2.0, 3.0000000000000004,
  6.0, 7.999999999999998 against the table entries).
- Midpoint (T = 350 K, P = 200000 Pa): component 0
  K = 2.449489742783 against the hand value (1·2·3·6)^(1/4) =
  2.449489742783; component 1 K = 1.414213562373 against
  (0.5·0.5·2·8)^(1/4) = 1.414213562373.
- Quarter point in T (T = 325 K, P = 100000 Pa):
  K = 1.316074012952, matching exp(0.25 ln 3).
- Single-temperature-axis midpoint: K = 2.828427124746,
  matching sqrt(2·4).
- Out-of-grid raises: 5 checks (T low/high, P low/high,
  single-axis mismatch). Invalid-input raises: non-positive K,
  non-increasing grid, ragged table.
- Polynomial recovery of a known synthetic 3-component
  coefficient set at 3 state points, against an independently
  written-out evaluation: exact to 1e-12 relative; e.g. at
  T = 300 K, P = 200000 Pa, K = [9.57670256975541,
  0.7659283383646487, 3.4903429574618414]. Constant-coefficient
  component returns exp(1.25) = 3.490342957462 at every state.
- Single-component edge cases pass for both models, including
  through the `kfun` adapter.

Existing battery re-run to confirm nothing broke:
`python/test_phase2_eos_flash.py`: 8 PASS, FAILURES: none
(PR phi = 0.999974 at 100 Pa; flash balance residual
5.55e-17; vapour fraction psi = 0.7245).

## ChemCAD capture needed to anchor this (not done here)

No ChemCAD was used in this trial and no queue job was added.
To anchor these two data formats against ChemCAD as oracle, a
later queued capture would need:

1. One mixture and one ChemCAD case whose K-value model is set
   to the K-table / user-K route (model code recorded in the
   fixture, as with the earlier modek findings), with the table
   or polynomial data entered in ChemCAD identical to the data
   supplied to this module — a case counts only if the data
   sets are identical.
2. TP-flash captures on a T/P grid that includes table nodes
   and off-node midpoints, frozen as fixtures in SI units
   (T in K, P in Pa), so node recovery and the bilinear
   midpoint can be checked against ChemCAD values rather than
   against the input table itself — that distinction is what
   would show whether ChemCAD interpolates ln K bilinearly in
   T and P, or uses a different scheme (for example linear K,
   or log P as a coordinate). If ChemCAD's scheme differs, the
   scheme in this module must be changed to match, not the
   tolerance widened.
3. For polynomial user-K: captures at enough distinct (T, P)
   points to separate the 1/T, T, T^2, P, and T P terms, with
   the entered coefficients recorded in the fixture.

Until that capture is done, both models are local-code only:
structurally verified, not ChemCAD-verified.
