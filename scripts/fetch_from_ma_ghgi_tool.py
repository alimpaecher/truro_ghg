"""
Fetch and reshape Truro data from zcranmer/ma-ghgi-tool.

The upstream repo publishes one CSV with every MA municipality × year. We pull
that CSV, filter to Truro, and write:

    data/TruroVehicles.csv                — quarterly vehicle registrations
    data/mass_save.csv                    — residential/commercial IOU electricity (MWh) by year
    data/clc_heat_pump_installation.csv   — cumulative heat pump installations by year

All three merge with existing rows — upstream values replace overlapping keys,
locally-curated rows the upstream hasn't covered are preserved.

Underlying data sources (the upstream repo proxies these — if it ever goes
stale, the refresh instructions in README.md still work):

  - Vehicle census:    https://geodot-massdot.hub.arcgis.com/pages/vehicle-census
  - Mass Save usage:   https://www.masssavedata.com/Public/GeographicSavings
  - Heat pumps:        Cape Light Compact Customer Profile Viewer
                       (https://viewer.dnv.com/macustomerprofile/...)

Usage:
    python scripts/fetch_from_ma_ghgi_tool.py
    python scripts/fetch_from_ma_ghgi_tool.py --only vehicles
    python scripts/fetch_from_ma_ghgi_tool.py --only mass_save
    python scripts/fetch_from_ma_ghgi_tool.py --only heat_pumps
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import urllib.request
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
UPSTREAM_CSV_URL = (
    "https://raw.githubusercontent.com/zcranmer/ma-ghgi-tool/"
    "main/datasets/municipal_emissions.csv"
)

# ma-ghgi-tool vehicle Type → our TruroVehicles.csv Type
VEHICLE_TYPE_MAP = {
    "Electric Vehicle": "Battery Electric",
    "Plug-in Hybrid Electric": "Plug-in Hybrid",
    "Hybrid Electric Vehicle": "Hybrid Electric",
    "Fossil Fuel": "Fossil Fuel",
    # Fuel Cell Electric Vehicle intentionally dropped — not in vehicles_factors.csv,
    # and Truro counts for it are effectively zero.
}

QUARTER_MONTHS = {"01": 1, "04": 4, "07": 7, "10": 10}

VEHICLE_COL_PATTERN = re.compile(
    r"^Count (01|04|07|10) (Electric Vehicle|Plug-in Hybrid Electric|"
    r"Hybrid Electric Vehicle|Fossil Fuel|Fuel Cell Electric Vehicle) "
    r"(Commercial|Municipal|Passenger|State)$"
)


def download_upstream() -> pd.DataFrame:
    print(f"Downloading {UPSTREAM_CSV_URL} ...", flush=True)
    with urllib.request.urlopen(UPSTREAM_CSV_URL, timeout=60) as resp:
        raw = resp.read()
    df = pd.read_csv(io.BytesIO(raw), low_memory=False)
    print(f"  {len(df):,} rows × {len(df.columns):,} cols downloaded.")
    return df


def truro_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["Municipality"].str.strip().str.lower() == "truro"].copy()


# --- Vehicles --------------------------------------------------------------


def reshape_vehicles(truro_df: pd.DataFrame) -> pd.DataFrame:
    """Flatten quarterly count columns into (Quarter, Type, Number) rows."""
    rows = []
    for _, year_row in truro_df.iterrows():
        year = int(year_row["Year"])
        year_short = year % 100

        for col in year_row.index:
            match = VEHICLE_COL_PATTERN.match(col)
            if not match:
                continue
            q_code, ma_ghgi_type, _subcategory = match.groups()
            if ma_ghgi_type not in VEHICLE_TYPE_MAP:
                continue
            value = year_row[col]
            if pd.isna(value):
                continue
            try:
                count = int(float(value))
            except (TypeError, ValueError):
                continue

            our_type = VEHICLE_TYPE_MAP[ma_ghgi_type]
            month = QUARTER_MONTHS[q_code]
            quarter_str = f"{month}/1/{year_short:02d}"
            rows.append({"Quarter": quarter_str, "Type": our_type, "Number": count})

    if not rows:
        return pd.DataFrame(columns=["Quarter", "Type", "Number"])

    expanded = pd.DataFrame(rows)
    # Subcategories (Commercial/Municipal/Passenger/State) collapse via sum
    return (
        expanded.groupby(["Quarter", "Type"], as_index=False)["Number"].sum()
    )


def merge_vehicles(new_df: pd.DataFrame) -> int:
    """Merge new_df into data/TruroVehicles.csv. Returns rows_added."""
    target = DATA_DIR / "TruroVehicles.csv"
    existing = pd.read_csv(target) if target.exists() else pd.DataFrame(
        columns=["Quarter", "Type", "Number"]
    )

    # Annotate rows by upstream-reachable key (Quarter-parsed year)
    def quarter_year(q: str) -> int | None:
        try:
            return pd.to_datetime(q, format="mixed").year
        except Exception:
            return None

    upstream_years = {int(y) for y in new_df["Quarter"].map(quarter_year).dropna().unique()}

    # Keep local rows for years the upstream doesn't cover (e.g. partial current year)
    existing_kept = existing[~existing["Quarter"].map(quarter_year).isin(upstream_years)]

    combined = pd.concat([new_df, existing_kept], ignore_index=True)
    # Dedup (Quarter, Type); upstream rows take precedence because they come first
    combined = combined.drop_duplicates(subset=["Quarter", "Type"], keep="first")
    combined.to_csv(target, index=False)
    return len(combined) - len(existing)


# --- Mass Save -------------------------------------------------------------


MASS_SAVE_COLUMN_MAP = {
    "Residential IOU Electricity (MWh)": "Residential & Low-Income",
    "Commercial & Industrial IOU Electricity (MWh)": "Commercial & Industrial",
}


def reshape_mass_save(truro_df: pd.DataFrame) -> pd.DataFrame:
    """Emit (Year, Sector, Electric_MWh) rows."""
    rows = []
    for _, year_row in truro_df.iterrows():
        year = year_row["Year"]
        if pd.isna(year):
            continue
        year = int(year)
        for col, sector in MASS_SAVE_COLUMN_MAP.items():
            value = year_row.get(col)
            if pd.isna(value):
                continue
            try:
                mwh = float(value)
            except (TypeError, ValueError):
                continue
            rows.append({"Year": year, "Sector": sector, "Electric_MWh": mwh})
    return pd.DataFrame(rows, columns=["Year", "Sector", "Electric_MWh"])


def write_mass_save(new_df: pd.DataFrame) -> int:
    target = DATA_DIR / "mass_save.csv"
    new_df = new_df.sort_values(["Year", "Sector"]).reset_index(drop=True)
    new_df.to_csv(target, index=False)
    return len(new_df)


# --- Heat pumps ------------------------------------------------------------


def _coerce_int(value) -> int | None:
    """Return int(value) if numeric, else None. Upstream uses '*' for suppressed cells."""
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def reshape_heat_pumps(truro_df: pd.DataFrame) -> pd.DataFrame:
    """
    Emit rows matching data/clc_heat_pump_installation.csv's schema:

        <unnamed year>, Installed Heat Pump, Installed Heat Pumps Location

    Upstream "Cumulative heat pumps all (accounts)"  → Installed Heat Pump
    Upstream "Cumulative heat pumps all (locations)" → Installed Heat Pumps Location
    — these match 2021–2023 numbers in the existing file exactly.

    Rows with suppressed ("*") or missing values (pre-2021 for Truro) are dropped.
    """
    rows = []
    for _, year_row in truro_df.iterrows():
        year = _coerce_int(year_row.get("Year"))
        if year is None:
            continue
        accounts = _coerce_int(year_row.get("Cumulative heat pumps all (accounts)"))
        locations = _coerce_int(year_row.get("Cumulative heat pumps all (locations)"))
        if accounts is None or locations is None:
            continue
        rows.append({
            "": year,
            "Installed Heat Pump": accounts,
            "Installed Heat Pumps Location": locations,
        })
    return pd.DataFrame(rows, columns=["", "Installed Heat Pump", "Installed Heat Pumps Location"])


def merge_heat_pumps(new_df: pd.DataFrame) -> int:
    target = DATA_DIR / "clc_heat_pump_installation.csv"
    existing = pd.read_csv(target) if target.exists() else pd.DataFrame(
        columns=["", "Installed Heat Pump", "Installed Heat Pumps Location"]
    )
    before = len(existing)

    if target.exists() and existing.columns[0] != "":
        existing = existing.rename(columns={existing.columns[0]: ""})

    upstream_years = set(new_df[""].tolist())
    existing_kept = existing[~existing[""].isin(upstream_years)]

    combined = pd.concat([new_df, existing_kept], ignore_index=True)
    combined = combined.drop_duplicates(subset=[""], keep="first")
    combined = combined.sort_values("", ascending=False).reset_index(drop=True)
    combined.to_csv(target, index=False)
    return len(combined) - before


# --- CLI -------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=["vehicles", "mass_save", "heat_pumps"],
                        help="Run only one reshape.")
    args = parser.parse_args()

    upstream = download_upstream()
    truro = truro_rows(upstream)
    print(f"Truro rows: {len(truro)} (years {int(truro['Year'].min())}–{int(truro['Year'].max())})")

    targets = [args.only] if args.only else ["vehicles", "mass_save", "heat_pumps"]

    if "vehicles" in targets:
        new_vehicles = reshape_vehicles(truro)
        added = merge_vehicles(new_vehicles)
        print(f"  TruroVehicles.csv: {len(new_vehicles)} upstream rows merged, "
              f"net Δ {added:+d} row(s).")

    if "mass_save" in targets:
        new_ms = reshape_mass_save(truro)
        written = write_mass_save(new_ms)
        print(f"  data/mass_save.csv: {written} row(s) written "
              f"(years {int(new_ms['Year'].min())}–{int(new_ms['Year'].max())}).")

    if "heat_pumps" in targets:
        new_hp = reshape_heat_pumps(truro)
        if new_hp.empty:
            print("  clc_heat_pump_installation.csv: no usable upstream rows (all suppressed/missing).")
        else:
            added = merge_heat_pumps(new_hp)
            print(f"  clc_heat_pump_installation.csv: {len(new_hp)} upstream rows merged, "
                  f"net Δ {added:+d} row(s) "
                  f"(years {int(new_hp[''].min())}–{int(new_hp[''].max())}).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
