import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_vehicle_data

# Page configuration
st.set_page_config(
    page_title="Town of Truro GHG Dashboard",
    page_icon="🌍",
    layout="wide"
)

# Configuration
SPREADSHEET_ID = "1sVrJGf34KkzQJ4jv2yrqNMp7j4ghZRlX7wt2Bxk-vz8"
ENERGY_SHEET_GID = "1784785583"

st.title("Town of Truro GHG Emissions Dashboard")

@st.cache_data(ttl=600)
def load_energy_data():
    """Load data from Municipal Energy sheet."""
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={ENERGY_SHEET_GID}"
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Error loading energy data: {str(e)}")
        return None

# Load both datasets
vehicles_df = load_vehicle_data()
energy_df = load_energy_data()

if vehicles_df is not None and energy_df is not None:
    st.success("Successfully loaded data from both sources")

    # Process vehicles data
    # Convert Quarter to datetime
    vehicles_df['Quarter_Date'] = pd.to_datetime(vehicles_df['Quarter'])

    # Filter to only January quarters (Q1 of each year represents the previous year's final number)
    vehicles_df['Month'] = vehicles_df['Quarter_Date'].dt.month
    vehicles_q1 = vehicles_df[vehicles_df['Month'] == 1].copy()

    # Extract year and use previous year as the calendar year
    vehicles_q1['year'] = vehicles_q1['Quarter_Date'].dt.year - 1

    # Sum tCO2e by year for vehicles
    vehicles_yearly = vehicles_q1.groupby('year')['tCo2e'].sum().reset_index()
    vehicles_yearly.columns = ['year', 'vehicles_tco2e']

    # Process energy data
    # Filter out incomplete 2025 data
    energy_df = energy_df[energy_df['fiscal_year'] < 2025]

    # Sum mtCO2e by year for municipal buildings (assuming fiscal_year represents the calendar year)
    energy_yearly = energy_df.groupby('fiscal_year')['mtco2e'].sum().reset_index()
    energy_yearly.columns = ['year', 'municipal_buildings_mtco2e']

    # Merge the two datasets on year
    combined_df = pd.merge(vehicles_yearly, energy_yearly, on='year', how='outer')
    combined_df = combined_df.sort_values('year')
    combined_df = combined_df.fillna(0)

    # Filter to start from 2019 (when vehicle data begins)
    combined_df = combined_df[combined_df['year'] >= 2019]

    # Calculate total emissions
    combined_df['total_tco2e'] = combined_df['vehicles_tco2e'] + combined_df['municipal_buildings_mtco2e']

    # Display current year metrics
    most_recent_year = combined_df['year'].max()
    current_year = combined_df[combined_df['year'] == most_recent_year].iloc[0]
    previous_year = combined_df[combined_df['year'] == most_recent_year - 1].iloc[0]

    st.subheader(f"Year {int(most_recent_year)} Totals")
    col1, col2, col3 = st.columns(3)

    with col1:
        delta_vehicles = current_year['vehicles_tco2e'] - previous_year['vehicles_tco2e']
        st.metric(
            label="Vehicles tCO2e",
            value=f"{current_year['vehicles_tco2e']:.2f}",
            delta=f"{delta_vehicles:.2f}"
        )

    with col2:
        delta_buildings = current_year['municipal_buildings_mtco2e'] - previous_year['municipal_buildings_mtco2e']
        st.metric(
            label="Municipal Buildings mtCO2e",
            value=f"{current_year['municipal_buildings_mtco2e']:.2f}",
            delta=f"{delta_buildings:.2f}"
        )

    with col3:
        delta_total = current_year['total_tco2e'] - previous_year['total_tco2e']
        st.metric(
            label="Total tCO2e",
            value=f"{current_year['total_tco2e']:.2f}",
            delta=f"{delta_total:.2f}"
        )

    # Create combined emissions chart
    st.subheader("Total Emissions Over Time")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=combined_df['year'],
        y=combined_df['municipal_buildings_mtco2e'],
        name='Municipal Buildings',
        mode='lines',
        stackgroup='one',
        fillcolor='rgba(255, 127, 80, 0.5)'
    ))

    fig.add_trace(go.Scatter(
        x=combined_df['year'],
        y=combined_df['vehicles_tco2e'],
        name='Vehicles',
        mode='lines',
        stackgroup='one',
        fillcolor='rgba(70, 130, 180, 0.5)'
    ))

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="tCO2e / mtCO2e",
        hovermode='x unified',
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show breakdown table
    st.subheader("Emissions Breakdown by Year")
    display_df = combined_df[['year', 'vehicles_tco2e', 'municipal_buildings_mtco2e', 'total_tco2e']].copy()
    display_df.columns = ['Year', 'Vehicles (tCO2e)', 'Municipal Buildings (mtCO2e)', 'Total (tCO2e)']
    st.dataframe(display_df.sort_values('Year', ascending=False), hide_index=True)

    # Download option
    st.subheader("Download Data")
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Combined Data as CSV",
        data=csv,
        file_name="combined_emissions_data.csv",
        mime="text/csv"
    )
else:
    st.error("Unable to load one or both data sources. Please check the configuration.")
