"""User-supplied equilibrium ratios: K-tables and polynomial user-K.

Symbols defined before first use: temperature T in kelvin (K);
pressure P in pascal (Pa); equilibrium ratio K_i = y_i / x_i for
component i (dimensionless), where y_i is the vapour mole fraction
of component i (dimensionless) and x_i is the liquid mole fraction
of component i (dimensionless); natural logarithm of the
equilibrium ratio ln K_i (dimensionless). Component index i
(dimensionless integer), temperature-grid index j (dimensionless
integer), and pressure-grid index k (dimensionless integer) label
entries in the caller-supplied data.

No chemical identity, fitted coefficient, or table value is
embedded in this module. Every number below is caller-supplied
data. This module is not ChemCAD-verified: see the anchoring note
in ROUND3-TRIAL-userk.md.

K-table scheme (the scheme chosen and stated here)
--------------------------------------------------
The caller supplies a rectangular grid: temperatures
T_grid[j] in kelvin (K), strictly increasing; pressures
P_grid[k] in pascal (Pa), strictly increasing; and table values
K_table[i][j][k] (dimensionless, strictly positive). Interpolation
is bilinear in ln K_i as a function of T and P (linear in T,
linear in P; neither T nor P is log-transformed):

    ln K_i(T, P) = (1 - u) (1 - v) ln K_table[i][j][k]
                 + u (1 - v)     ln K_table[i][j + 1][k]
                 + (1 - u) v     ln K_table[i][j][k + 1]
                 + u v           ln K_table[i][j + 1][k + 1],

where u = (T - T_grid[j]) / (T_grid[j + 1] - T_grid[j])
(dimensionless) and v = (P - P_grid[k]) / (P_grid[k + 1] -
P_grid[k]) (dimensionless), for the cell containing (T, P).
At a grid node, u and v are 0 or 1 and the table value is
recovered exactly (up to the exp/ln round trip). A grid with a
single temperature or a single pressure reduces to linear
interpolation in the remaining coordinate, and the single-grid
coordinate must then be matched exactly.

Extrapolation is never silent: a call with T outside
[T_grid[0], T_grid[-1]] or P outside [P_grid[0], P_grid[-1]]
raises ValueError.

Polynomial user-K scheme
------------------------
For component i, ln K_i is a polynomial

    ln K_i(T, P) = a0_i + a1_i T + a2_i T^2 + a3_i / T
                 + a4_i P + a5_i T P,

where the coefficient list for component i is
coeffs[i] = [a0_i, a1_i, a2_i, a3_i, a4_i, a5_i]; a0_i is
dimensionless, a1_i is in 1/K, a2_i is in 1/K^2, a3_i is in K,
a4_i is in 1/Pa, and a5_i is in 1/(K Pa), so every term is
dimensionless. Missing trailing coefficients are treated as
zero. The polynomial is evaluated wherever T > 0 and P > 0;
it carries no validity range of its own, so the caller is
responsible for using it only over the range the coefficients
were fitted to.
"""
import math


def _check_grid_axis(axis, name, unit):
    """Validate one grid axis: at least one finite, strictly
    increasing value. name and unit are labels for messages."""
    if len(axis) == 0:
        raise ValueError(f"{name} grid is empty")
    for v in axis:
        if not math.isfinite(v):
            raise ValueError(f"{name} grid value is not finite ({unit})")
    for j in range(len(axis) - 1):
        if not axis[j + 1] > axis[j]:
            raise ValueError(f"{name} grid is not strictly increasing")


def _bracket(axis, value, name, unit):
    """Return (j, u) with axis[j] <= value <= axis[j + 1] and
    u = (value - axis[j]) / (axis[j + 1] - axis[j]) (dimensionless).

    Raises ValueError outside the axis range: no extrapolation.
    A single-point axis requires an exact match and returns
    (0, 0.0).
    """
    if value < axis[0] or value > axis[-1]:
        raise ValueError(
            f"{name} {value} ({unit}) is outside the table grid "
            f"[{axis[0]}, {axis[-1]}] ({unit}); extrapolation "
            "is not performed")
    if len(axis) == 1:
        return 0, 0.0
    if value == axis[-1]:
        return len(axis) - 2, 1.0
    for j in range(len(axis) - 1):
        if axis[j] <= value <= axis[j + 1]:
            u = (value - axis[j]) / (axis[j + 1] - axis[j])
            return j, u
    raise AssertionError("bracket search failed")  # unreachable


class KTable:
    """Equilibrium ratios from a caller-supplied K-table.

    T_grid is the temperature grid in kelvin (K), P_grid is the
    pressure grid in pascal (Pa), and K_table[i][j][k] is the
    equilibrium ratio (dimensionless) of component i at
    T_grid[j] and P_grid[k].
    """

    def __init__(self, T_grid, P_grid, K_table):
        self.T_grid = [float(v) for v in T_grid]
        self.P_grid = [float(v) for v in P_grid]
        _check_grid_axis(self.T_grid, "temperature", "K")
        _check_grid_axis(self.P_grid, "pressure", "Pa")
        if len(K_table) == 0:
            raise ValueError("K_table has no components")
        self.n_comp = len(K_table)
        self._lnK = []
        for i in range(self.n_comp):
            plane = K_table[i]
            if len(plane) != len(self.T_grid):
                raise ValueError(
                    f"K_table[{i}] has {len(plane)} temperature rows, "
                    f"expected {len(self.T_grid)}")
            ln_plane = []
            for j in range(len(plane)):
                row = plane[j]
                if len(row) != len(self.P_grid):
                    raise ValueError(
                        f"K_table[{i}][{j}] has {len(row)} pressure "
                        f"entries, expected {len(self.P_grid)}")
                ln_row = []
                for v in row:
                    v = float(v)
                    if not math.isfinite(v) or v <= 0.0:
                        raise ValueError(
                            "K_table values must be positive and "
                            f"finite, got {v}")
                    ln_row.append(math.log(v))
                ln_plane.append(ln_row)
            self._lnK.append(ln_plane)

    def log_k_values(self, T, P):
        """ln K_i (dimensionless) at T in kelvin (K) and P in
        pascal (Pa), by the bilinear scheme in the module
        docstring. Raises ValueError outside the grid."""
        T = float(T)
        P = float(P)
        if not (math.isfinite(T) and math.isfinite(P)):
            raise ValueError("T and P must be finite")
        j, u = _bracket(self.T_grid, T, "temperature", "K")
        if len(self.P_grid) == 1:
            k, v = 0, 0.0
            _bracket(self.P_grid, P, "pressure", "Pa")
        else:
            k, v = _bracket(self.P_grid, P, "pressure", "Pa")
        j2 = min(j + 1, len(self.T_grid) - 1)
        k2 = min(k + 1, len(self.P_grid) - 1)
        # For a single-point axis the second index equals the
        # first and its weight is zero, so the formula still holds.
        if len(self.T_grid) == 1:
            u = 0.0
        if len(self.P_grid) == 1:
            v = 0.0
        out = []
        for i in range(self.n_comp):
            lnK = self._lnK[i]
            val = ((1.0 - u) * (1.0 - v) * lnK[j][k]
                   + u * (1.0 - v) * lnK[j2][k]
                   + (1.0 - u) * v * lnK[j][k2]
                   + u * v * lnK[j2][k2])
            out.append(val)
        return out

    def k_values(self, T, P):
        """K_i (dimensionless) at T in kelvin (K) and P in
        pascal (Pa). Raises ValueError outside the grid."""
        return [math.exp(v) for v in self.log_k_values(T, P)]

    def kfun(self, x, y, T, P):
        """Adapter with the library K-function signature
        kfun(x, y, T, P) -> K list, where x and y are mole
        fraction lists (dimensionless, unused: a K-table carries
        no composition dependence), T is in kelvin (K), and P is
        in pascal (Pa)."""
        return self.k_values(T, P)


class PolyUserK:
    """Equilibrium ratios from caller-supplied polynomial
    coefficients, using the basis in the module docstring.

    coeffs[i] is the coefficient list for component i:
    [a0_i, a1_i, a2_i, a3_i, a4_i, a5_i] with the units stated
    in the module docstring; missing trailing entries are zero.
    """

    N_TERMS = 6

    def __init__(self, coeffs):
        if len(coeffs) == 0:
            raise ValueError("coeffs has no components")
        self.n_comp = len(coeffs)
        self.coeffs = []
        for i in range(self.n_comp):
            row = [float(v) for v in coeffs[i]]
            if len(row) > self.N_TERMS:
                raise ValueError(
                    f"coeffs[{i}] has {len(row)} entries, at most "
                    f"{self.N_TERMS} are defined by the basis")
            for v in row:
                if not math.isfinite(v):
                    raise ValueError("coeffs values must be finite")
            self.coeffs.append(row + [0.0] * (self.N_TERMS - len(row)))

    def log_k_values(self, T, P):
        """ln K_i (dimensionless) at T in kelvin (K) and P in
        pascal (Pa). Raises ValueError for T <= 0 or P <= 0."""
        T = float(T)
        P = float(P)
        if not (math.isfinite(T) and math.isfinite(P)):
            raise ValueError("T and P must be finite")
        if T <= 0.0:
            raise ValueError("T must be positive (K)")
        if P <= 0.0:
            raise ValueError("P must be positive (Pa)")
        basis = [1.0, T, T * T, 1.0 / T, P, T * P]
        return [sum(c[t] * basis[t] for t in range(self.N_TERMS))
                for c in self.coeffs]

    def k_values(self, T, P):
        """K_i (dimensionless) at T in kelvin (K) and P in
        pascal (Pa)."""
        return [math.exp(v) for v in self.log_k_values(T, P)]

    def kfun(self, x, y, T, P):
        """Adapter with the library K-function signature
        kfun(x, y, T, P) -> K list, where x and y are mole
        fraction lists (dimensionless, unused), T is in kelvin
        (K), and P is in pascal (Pa)."""
        return self.k_values(T, P)


def k_table_from_data(data):
    """Build a KTable from a case-data style dict with keys
    "T_grid" (kelvin, K), "P_grid" (pascal, Pa), and "K_table"
    (dimensionless), as defined in the module docstring."""
    return KTable(data["T_grid"], data["P_grid"], data["K_table"])


def poly_userk_from_data(data):
    """Build a PolyUserK from a case-data style dict with key
    "coeffs", as defined in the module docstring."""
    return PolyUserK(data["coeffs"])
