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

### Municipal Energy & Vehicles
- `municipal_energy.csv`: Municipal building energy consumption data
- `TruroVehicles.csv`: Vehicle census data by quarter and type
  - Source: [MassDOT Vehicle Census](https://geodot-massdot.hub.arcgis.com/pages/vehicle-census)
  - Contains registered vehicle counts by municipality
- `vehicles_factors.csv`: Vehicle emission calculation factors (MPG, miles/year, etc.)
- `emission_factors.csv`: Emission factors for various fuel types

### Cape Light Compact (CLC) Data

**Data Source:** [Cape Light Compact Customer Profile Viewer](https://viewer.dnv.com/macustomerprofile/entity/1444/report/2078)

Navigate to: **Residential: Electric and Gas Executive Summaries**

**To download the data:**

1. **CLC Participation Data** (`clc_participation.csv`):
   - Click on "Municipality" tab
   - Export participation rate data by year

2. **Census Statistics** (`clc_census.csv`):
   - Click on "Census Statistics" tab
   - Export census data (currently 2023 data)
   - Includes housing tenure, vacancy status, heating fuel types, etc.

3. **Heat Pump Installation** (`clc_heat_pump_installation.csv`):
   - Navigate to "Electrification and Heating" → "By Municipality"
   - Export heat pump installation data by year

Save all downloaded CSV files to the `data/` folder before running the dashboard.

### Residential & Commercial Energy Data

**Assessors Data Source:** Truro Assessors Database (property characteristics, HVAC types, fuel types, square footage)

**Additional Energy Usage Data:**
- [Mass Save Data - Geographic Savings by Town](https://www.masssavedata.com/Public/GeographicSavings)
- This website provides actual energy consumption data by municipality in Massachusetts
- Can be used to validate or refine the heating consumption benchmarks used in emissions calculations
- Includes electricity and natural gas usage (note: Truro has no natural gas service)

### Assessors Database
- `TRURO_Assessors original_2020-12-17-2019.xls`: Property data including HVAC systems, fuel types, and square footage
- Used to estimate residential and commercial heating emissions

