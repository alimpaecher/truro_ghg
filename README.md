# Town of Truro GHG Emissions Dashboard

A Streamlit-based dashboard for visualizing greenhouse gas emissions data from the Town of Truro, including municipal energy consumption and vehicle fleet emissions.

## Features

- **Combined Emissions Overview**: View total emissions from both municipal buildings and vehicles
- **Municipal Energy Analysis**: Detailed breakdown of energy consumption by fuel type
- **Vehicle Fleet Tracking**: Monitor emissions from the municipal vehicle fleet
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

