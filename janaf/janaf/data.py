"""Data access layer: loads the derived-coefficient Parquet files and the
SQLite metadata catalog. Streamlit caching is applied by the app, not here."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sqlite3

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


@lru_cache(maxsize=1)
def load_coeffs() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "janaf_coeffs.parquet")


@lru_cache(maxsize=1)
def load_phase_changes() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "phase_changes.parquet")


@lru_cache(maxsize=1)
def load_antoine() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "antoine.parquet")


@lru_cache(maxsize=1)
def species_catalog() -> pd.DataFrame:
    con = sqlite3.connect(DATA_DIR / "metadata.sqlite")
    df = pd.read_sql("SELECT * FROM species ORDER BY formula", con)
    con.close()
    return df


@lru_cache(maxsize=1)
def dataset_info() -> dict:
    con = sqlite3.connect(DATA_DIR / "metadata.sqlite")
    df = pd.read_sql("SELECT key, value FROM dataset_info", con)
    con.close()
    return dict(zip(df["key"], df["value"]))


@lru_cache(maxsize=1)
def provenance_table() -> pd.DataFrame:
    con = sqlite3.connect(DATA_DIR / "metadata.sqlite")
    df = pd.read_sql("SELECT * FROM provenance ORDER BY formula, section", con)
    con.close()
    return df


def phases_for(formula: str) -> list[str]:
    df = load_coeffs()
    return sorted(df.loc[df["formula"] == formula, "phase"].unique().tolist())


def segments_for(formula: str, phase: str) -> pd.DataFrame:
    df = load_coeffs()
    sub = df[(df["formula"] == formula) & (df["phase"] == phase)]
    return sub.sort_values("t_min").reset_index(drop=True)


def get_segment(formula: str, phase: str, T: float) -> pd.Series:
    """Return the coefficient segment valid at T, else raise OutOfRangeError."""
    from .shomate import OutOfRangeError  # deferred to avoid circular import
    segs = segments_for(formula, phase)
    if segs.empty:
        raise OutOfRangeError(
            f"No {phase}-phase data for {formula} in this dataset.", [])
    hit = segs[(segs["t_min"] <= T) & (T <= segs["t_max"])]
    if hit.empty:
        # ref298 records only match essentially at 298.15 K
        ref = segs[segs["kind"] == "ref298"]
        if not ref.empty and abs(T - 298.15) <= 0.05:
            return ref.iloc[0]
        ranges = [f"{r.t_min:.0f}–{r.t_max:.0f} K" for r in segs.itertuples()]
        raise OutOfRangeError(
            f"T = {T:.2f} K is outside the valid range for {formula} "
            f"({phase}). Valid: {', '.join(ranges)}. No extrapolation "
            f"is performed.", ranges)
    seg = hit.iloc[0]
    if seg["kind"] == "ref298" and abs(T - 298.15) > 0.05:
        raise OutOfRangeError(
            f"{formula} ({phase}): only 298.15 K reference data are "
            f"available in the public WebBook (temperature-dependent Cp "
            f"is in NIST/TRC subscription tables).", ["298.15 K only"])
    return seg
