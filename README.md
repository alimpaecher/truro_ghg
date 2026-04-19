# Town of Truro GHG Emissions Dashboard

A Streamlit-based dashboard for visualizing greenhouse gas emissions data from the Town of Truro, including municipal energy consumption and vehicle fleet emissions.

## Features

- **Combined Emissions Overview**: View total emissions from both municipal buildings and vehicles
- **Municipal Energy Analysis**: Detailed breakdown of energy consumption by fuel type
- **Vehicle Fleet Tracking**: Monitor emissions from the municipal vehicle fleet
- **CLC Participation Tracking**: Cape Light Compact participation rates, census data, and heat pump installations
- **Interactive Charts**: Visualize trends over time with Plotly
- **Data Export**: Download processed data as CSV files

## Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)

## Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv myenv
source myenv/bin/activate
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Dashboard

1. Ensure your virtual environment is activated:
```bash
source myenv/bin/activate
```

2. Run the Streamlit application:
```bash
streamlit run Home.py
```

3. The dashboard will automatically open in your default web browser at `http://localhost:8501`

## Data Sources

All data files are stored in the `data/` folder as CSV files.

### Vehicles (`TruroVehicles.csv`)

Quarterly vehicle registrations by type.

- **Original source:** [MassDOT Vehicle Census](https://geodot-massdot.hub.arcgis.com/pages/vehicle-census) (registered vehicle counts by municipality, published quarterly).
- **How we pull it:** via the community-maintained mirror
  [zcranmer/ma-ghgi-tool](https://github.com/zcranmer/ma-ghgi-tool/blob/main/datasets/municipal_emissions.csv),
  which aggregates MassDOT + Mass Save data for every MA town into a single
  CSV. `scripts/fetch_from_ma_ghgi_tool.py` downloads that CSV, extracts
  Truro rows, and reshapes them into `TruroVehicles.csv` format.
- **If the mirror goes stale:** fall back to downloading directly from the
  MassDOT Vehicle Census link above and appending rows to `TruroVehicles.csv`
  with columns `Quarter, Type, Number`.

### Supporting factors (static)
- `vehicles_factors.csv`: Vehicle emission calculation factors (MPG, miles/year, etc.)
- `emission_factors.csv`: Emission factors for various fuel types

### Mass Save IOU Electricity (`mass_save.csv`)

Residential and commercial IOU electricity usage (MWh) by year.

- **Original source:** [Mass Save Geographic Savings Report](https://www.masssavedata.com/Public/GeographicSavings).
- **How we pull it:** via the same [zcranmer/ma-ghgi-tool mirror](https://github.com/zcranmer/ma-ghgi-tool)
  (same `scripts/fetch_from_ma_ghgi_tool.py` invocation). The mirror
  consolidates Mass Save's per-year exports into one table.
- **Legacy files** in `data/masssaveenergyusage/*.xls` are still read by
  `load_mass_save_data()` as a fallback if `data/mass_save.csv` is absent,
  but new refreshes should go through the fetch script.
- **If the mirror goes stale:** download each missing year's Geographic Report
  from Mass Save (save as `YYYY Geographic Report - Exported on MM-DD-YYYY.xls`
  into `data/masssaveenergyusage/`), then delete `data/mass_save.csv` so the
  loader falls back to reading the `.xls` files.

### Cape Light Compact (CLC) Data

**Data Source:** [Cape Light Compact Customer Profile Viewer](https://viewer.dnv.com/macustomerprofile/entity/1444/report/2078)

Navigate to: **Residential: Electric and Gas Executive Summaries**

**To download the data:**

1. **CLC Participation Data** (`clc_participation.csv`):

   This file is assembled in **two passes** because the Qlik dashboard only
   exposes the historical time series and the current-year detail columns via
   separate filter selections.

   **Pass A — historical participation rate (one row per year):**
   1. Click the **Municipality** tab.
   2. Click **Open Filter Pane**.
   3. Filter **Municipality** → `Truro`.
   4. Filter **Year** → select **all years**.
   5. Export. Use this for the `Cumulative Location Participation Rate %` column
      (one value per year).

   **Pass B — current-year-only columns:**
   1. Keep the Municipality tab + Truro filter.
   2. Re-filter **Year** → **just the current year**.
   3. Export. From this row, copy:
      - `Active Locations`
      - `Average Participation Rate %`
      - `Repeat Participation %`

   **Assemble:** Append one new row to `data/clc_participation.csv` with:
   ```
   Year,Active Locations,Cumulative Location Participation Rate %,Average Participation Rate %,Repeat Participation %
   ```
   The loader at [data_loader.py](data_loader.py) only strips `%` from the
   cumulative column; the other two percentage columns are kept as strings and
   can be rendered as-is.

2. **Census Statistics** (`clc_census.csv`):
   - Click on "Census Statistics" tab
   - Export census data (currently 2023 data)
   - Includes housing tenure, vacancy status, heating fuel types, etc.

3. **Heat Pump Installation** (`clc_heat_pump_installation.csv`):
   - **Auto-fetched** — `scripts/fetch_from_ma_ghgi_tool.py` pulls the
     "Cumulative heat pumps all (accounts/locations)" columns from the
     [zcranmer/ma-ghgi-tool](https://github.com/zcranmer/ma-ghgi-tool) mirror
     (numbers match the CLC export exactly for 2021–2023; 2024+ tracked).
   - **This is the file that gates baseline-year advancement** for projections.
   - **Manual fallback** — if the mirror goes stale: in the CLC viewer,
     navigate to "Electrification and Heating" → "By Municipality" and export.

Save all downloaded CSV files to the `data/` folder before running the dashboard.

### Assessors Database
- `TRURO_Assessors original_2020-12-17-2019.xls`: Property data including HVAC systems, fuel types, and square footage
- Used to estimate residential and commercial heating emissions

