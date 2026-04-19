"""
Annual data refresh utility for the Truro GHG dashboard.

Run once per year (or whenever a new data point is published) to:
  1. Report which data files are stale (latest year vs. current calendar year)
  2. Attempt automated pulls for sources that expose an API
  3. Print manual step-by-step instructions for sources that don't

Usage:
    python scripts/refresh_data.py            # report + run automated pulls
    python scripts/refresh_data.py --report   # report staleness only; no fetches
    python scripts/refresh_data.py --source vehicles   # run one source

All automated fetches are idempotent: re-running them after success is safe,
and each writes to a temporary location before replacing the target CSV.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# --- Source registry --------------------------------------------------------
# Each source describes: how to probe current state, how to fetch new data
# (or why it can't be automated), and where the canonical URL lives.

MANUAL_INSTRUCTIONS = {
    "clc": (
        "Cape Light Compact Customer Profile Viewer (Qlik dashboard — manual export).\n"
        "  URL: https://viewer.dnv.com/macustomerprofile/entity/1444/report/2078\n"
        "  Report: Residential: Electric and Gas Executive Summaries\n"
        "  Manual exports still needed:\n"
        "    - clc_participation.csv   (Municipality tab → two-pass filter, see README)\n"
        "    - clc_census.csv          (Census Statistics tab)\n"
        "  clc_heat_pump_installation.csv is now auto-fetched via ma-ghgi-tool."
    ),
    "municipal_energy": (
        "Municipal utility bills (internal — no public source).\n"
        "  Export the latest fiscal-year data from the town's accounting system\n"
        "  and append to data/municipal_energy.csv, preserving existing columns:\n"
        "    fiscal_year, account_fuel, mtco2e, ... (see current CSV header)."
    ),
    "solar": (
        "Solar installations data (source TBD — likely MassCEC PTS).\n"
        "  Once the source is confirmed, document and overwrite data/solar_data.csv.\n"
        "  See MassCEC Production Tracking System for candidate data."
    ),
}


def csv_latest_year(path: Path, year_col: str = "Year") -> int | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
    except Exception:
        return None
    candidates = [year_col, "year", "fiscal_year", "Quarter"]
    if df.columns.size and df.columns[0].startswith("Unnamed"):
        candidates.insert(0, df.columns[0])
    for col in candidates:
        if col in df.columns:
            if col == "Quarter":
                dates = pd.to_datetime(df[col], errors="coerce", format="mixed")
                if dates.notna().any():
                    return int(dates.dt.year.max())
            try:
                as_num = pd.to_numeric(df[col], errors="coerce")
                if as_num.notna().any():
                    return int(as_num.max())
            except Exception:
                continue
    return None


def mass_save_latest_year() -> int | None:
    folder = DATA_DIR / "masssaveenergyusage"
    if not folder.exists():
        return None
    years = []
    for f in folder.glob("*.xls"):
        leading = f.name.split(" ", 1)[0]
        if leading.isdigit():
            years.append(int(leading))
    return max(years) if years else None


def report_staleness() -> None:
    """Print a one-screen summary of each data file's latest year."""
    current_year = dt.date.today().year
    mass_save_csv_year = csv_latest_year(DATA_DIR / "mass_save.csv", "Year")
    rows = [
        ("TruroVehicles.csv", csv_latest_year(DATA_DIR / "TruroVehicles.csv", "Quarter"), "ma-ghgi-tool (auto)"),
        ("mass_save.csv", mass_save_csv_year, "ma-ghgi-tool (auto)"),
        ("municipal_energy.csv", csv_latest_year(DATA_DIR / "municipal_energy.csv", "fiscal_year"), "manual"),
        ("clc_participation.csv", csv_latest_year(DATA_DIR / "clc_participation.csv", "Year"), "manual"),
        ("clc_heat_pump_installation.csv", csv_latest_year(DATA_DIR / "clc_heat_pump_installation.csv", "Year"), "ma-ghgi-tool (auto)"),
        ("masssaveenergyusage/ (legacy)", mass_save_latest_year(), "superseded by mass_save.csv"),
        ("truro-population.csv", csv_latest_year(DATA_DIR / "truro-population.csv", "Year"), "UMDI (auto)"),
        ("solar_data.csv", csv_latest_year(DATA_DIR / "solar_data.csv", "Year"), "manual"),
    ]
    print(f"\n=== Data file staleness (current year: {current_year}) ===\n")
    print(f"{'File':<38} {'Latest year':<12} {'Refresh via'}")
    print("-" * 75)
    for name, year, method in rows:
        year_str = str(year) if year is not None else "n/a"
        print(f"{name:<38} {year_str:<12} {method}")
    print()


# --- Automated fetchers -----------------------------------------------------


UMDI_URL_TEMPLATE = (
    "https://donahue.umass.edu/documents/"
    "UMDI_Census_V{vintage}_Subcounty_Estimates.xlsx"
)


def fetch_umdi_population(municipality: str = "Truro") -> pd.DataFrame:
    """
    Fetch annual town population from the UMass Donahue Institute V{year}
    Subcounty Estimates workbook (MA State Data Center's republication of
    the US Census Bureau subcounty Population Estimates Program).

    This is the methodology that matches the existing historical series in
    truro-population.csv — the Census ACS 5-year estimate undercounts small
    seasonal Cape Cod towns by ~40% and is NOT an acceptable substitute.

    The filename embeds a "vintage" year (e.g. V2024). We probe the current
    year back ~3 years until we find one that exists; UMDI typically
    publishes the next vintage in May/June.
    """
    current = dt.date.today().year
    xlsx_bytes = None
    used_vintage = None
    for vintage in range(current, current - 4, -1):
        url = UMDI_URL_TEMPLATE.format(vintage=vintage)
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                xlsx_bytes = resp.read()
                used_vintage = vintage
                break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
    if xlsx_bytes is None:
        raise RuntimeError(
            "No UMDI subcounty estimates workbook found for recent vintages. "
            f"Check {UMDI_URL_TEMPLATE.format(vintage=current)} by hand."
        )

    import io
    raw = pd.read_excel(io.BytesIO(xlsx_bytes),
                        sheet_name="Appendix Annual MCD Estimates",
                        header=None)

    # Row 2 (0-indexed) holds the per-column headers: municipality, county,
    # the two decennial-census columns, the two estimates-base columns,
    # and the annual-estimate years (ints like 2011, 2012, ...). Any column
    # past the last year header (change / rank / percent-change columns)
    # has a non-year label and should be skipped.
    header_row = raw.iloc[2]
    year_cols = {}
    for col_idx, label in header_row.items():
        if isinstance(label, (int, float)) and not pd.isna(label):
            year = int(label)
            if 2000 <= year <= 2100:
                year_cols[year] = col_idx

    data = raw.iloc[3:]
    row = data[data[0].astype(str).str.strip().str.casefold() == municipality.casefold()]
    if row.empty:
        raise RuntimeError(f"{municipality} not found in UMDI V{used_vintage} workbook.")
    row = row.iloc[0]

    records = []
    for year, col_idx in sorted(year_cols.items()):
        val = row[col_idx]
        if pd.notna(val):
            try:
                records.append({"Year": year, "Population": int(val)})
            except (ValueError, TypeError):
                continue
    return pd.DataFrame(records)


def update_population_csv() -> None:
    target = DATA_DIR / "truro-population.csv"
    if not target.exists():
        print(f"  skip: {target} not found")
        return

    existing = pd.read_csv(target)
    existing["Year"] = pd.to_numeric(existing["Year"], errors="coerce").astype("Int64")
    known_years = set(existing["Year"].dropna().astype(int))

    try:
        fetched = fetch_umdi_population()
    except Exception as exc:
        print(f"  UMDI fetch failed: {exc}")
        print("  Falling back to manual update. UMDI publishes the workbook at:")
        print("    https://donahue.umass.edu/business-groups/economic-public-policy-research"
              "/massachusetts-population-estimates-program/population-estimates-by-massachusetts"
              "-geography/by-city-and-town")
        return

    if fetched.empty:
        print("  UMDI workbook had no Truro rows — layout may have changed; inspect by hand.")
        return

    new_rows = fetched[~fetched["Year"].isin(known_years)]
    if new_rows.empty:
        print(f"  Population already up to date (latest: {max(known_years)}).")
        return

    # Preserve existing formatting: Population is stored as a comma-formatted string
    existing["Population"] = existing["Population"].astype(str)
    new_rows = new_rows.copy()
    new_rows["Population"] = new_rows["Population"].map(lambda n: f"{n:,}")

    merged = pd.concat([existing, new_rows[existing.columns]], ignore_index=True)
    merged.to_csv(target, index=False)
    print(f"  Added {len(new_rows)} new year(s) to truro-population.csv: "
          f"{sorted(new_rows['Year'].tolist())}")


def update_from_ma_ghgi_tool() -> None:
    """Pull Truro vehicle census + Mass Save rows via zcranmer/ma-ghgi-tool.

    Defers to scripts/fetch_from_ma_ghgi_tool.py so the reshape logic lives
    in one place.
    """
    import subprocess
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "fetch_from_ma_ghgi_tool.py")],
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print("  fetch_from_ma_ghgi_tool.py exited non-zero. See output above.")


# --- Manual-step printers ---------------------------------------------------


def print_manual(source_key: str) -> None:
    print(f"[{source_key}] manual refresh required")
    for line in MANUAL_INSTRUCTIONS[source_key].splitlines():
        print(f"  {line}")
    print()


# --- CLI --------------------------------------------------------------------


SOURCES = {
    "population": update_population_csv,
    "ma_ghgi_tool": update_from_ma_ghgi_tool,  # vehicles + mass_save
    "clc": lambda: print_manual("clc"),
    "municipal_energy": lambda: print_manual("municipal_energy"),
    "solar": lambda: print_manual("solar"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", action="store_true",
                        help="Only print staleness report; skip fetches.")
    parser.add_argument("--source", choices=sorted(SOURCES.keys()),
                        help="Run one source and exit.")
    args = parser.parse_args()

    report_staleness()
    if args.report:
        return 0

    to_run = [args.source] if args.source else list(SOURCES.keys())
    for key in to_run:
        print(f"--- {key} ---")
        SOURCES[key]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
