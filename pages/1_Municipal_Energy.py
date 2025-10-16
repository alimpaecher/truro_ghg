import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuration
SPREADSHEET_ID = "1sVrJGf34KkzQJ4jv2yrqNMp7j4ghZRlX7wt2Bxk-vz8"
SHEET_GID = "1784785583"  # Municipal Energy sheet GID

st.title("Municipal Energy Data")

@st.cache_data(ttl=600)
def load_energy_data():
    """Load Municipal Energy data from publicly accessible Google Sheet."""
    try:
        # Construct the export URL for CSV format
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={SHEET_GID}"

        # Read the CSV directly into a DataFrame
        df = pd.read_csv(url)
        return df

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Load the data
df = load_energy_data()

if df is not None:
    st.success(f"Successfully loaded {len(df)} rows from the Municipal Energy sheet")

    # Convert usage_end to datetime for proper sorting (if column exists)
    if 'usage_end' in df.columns:
        df['usage_end_date'] = pd.to_datetime(df['usage_end'])
        df = df.sort_values('usage_end_date')

    # Filter out 2025 data (incomplete year) and data before 2009
    df = df[(df['fiscal_year'] >= 2009) & (df['fiscal_year'] < 2025)]

    # Remove fuel types that have zero emissions across all years
    fuel_totals = df.groupby('account_fuel')['mtco2e'].sum()
    non_zero_fuels = fuel_totals[fuel_totals > 0].index.tolist()
    df = df[df['account_fuel'].isin(non_zero_fuels)]

    # Get most recent fiscal year data (should be 2024 now)
    most_recent_year = df['fiscal_year'].max()
    current_year_data = df[df['fiscal_year'] == most_recent_year]

    # Get previous fiscal year for comparison
    previous_year = df[df['fiscal_year'] < most_recent_year]['fiscal_year'].max()
    previous_year_data = df[df['fiscal_year'] == previous_year]

    # Calculate totals for current year
    current_mtco2e = current_year_data['mtco2e'].sum()
    current_mmbtu = current_year_data['mmbtu'].sum()

    # Calculate totals for previous year
    previous_mtco2e = previous_year_data['mtco2e'].sum()
    previous_mmbtu = previous_year_data['mmbtu'].sum()

    # Display current year metrics
    st.subheader(f"Most Recent Complete Fiscal Year ({int(most_recent_year)}) Totals")
    col1, col2 = st.columns(2)
    with col1:
        delta_mtco2e = current_mtco2e - previous_mtco2e
        st.metric(
            label="Total mtCO2e",
            value=f"{current_mtco2e:.2f}",
            delta=f"{delta_mtco2e:.2f} from FY{int(previous_year)}"
        )
    with col2:
        delta_mmbtu = current_mmbtu - previous_mmbtu
        st.metric(
            label="Total MMBtu",
            value=f"{current_mmbtu:.2f}",
            delta=f"{delta_mmbtu:.2f} from FY{int(previous_year)}"
        )

    # Use all data (no filters)
    filtered_df = df

    if len(filtered_df) > 0:
        # Emissions by fuel type over time (stacked area chart)
        st.subheader("Emissions by Fuel Type Over Time")

        # Group by fiscal year and fuel type
        fuel_yearly = filtered_df.groupby(['fiscal_year', 'account_fuel'])['mtco2e'].sum().reset_index()

        # Pivot for stacked area chart
        pivot_fuel = fuel_yearly.pivot(index='fiscal_year', columns='account_fuel', values='mtco2e')
        pivot_fuel = pivot_fuel.fillna(0)

        fig_fuel_time = go.Figure()

        for fuel_type in pivot_fuel.columns:
            fig_fuel_time.add_trace(go.Scatter(
                x=pivot_fuel.index,
                y=pivot_fuel[fuel_type],
                name=fuel_type,
                mode='lines',
                stackgroup='one',
                fillcolor='rgba' + str(tuple(list(hash(fuel_type) % 256 for _ in range(3)) + [0.5])),
            ))

        fig_fuel_time.update_layout(
            xaxis_title="Fiscal Year",
            yaxis_title="mtCO2e",
            hovermode='x unified',
            height=500
        )
        st.plotly_chart(fig_fuel_time, use_container_width=True)

    else:
        st.warning("No data available for the selected filters.")
