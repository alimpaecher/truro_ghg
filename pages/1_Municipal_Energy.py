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

    # Debug: Show columns to help identify the correct column names
    st.write("Available columns:", df.columns.tolist())

    # Convert usage_end to datetime for proper sorting (if column exists)
    if 'usage_end' in df.columns:
        df['usage_end_date'] = pd.to_datetime(df['usage_end'])
        df = df.sort_values('usage_end_date')
    else:
        st.warning("Column 'usage_end' not found. Skipping date sorting.")

    # Get most recent fiscal year data
    most_recent_year = df['fiscal_year'].max()
    current_year_data = df[df['fiscal_year'] == most_recent_year]

    # Get previous fiscal year for comparison
    previous_year = df[df['fiscal_year'] < most_recent_year]['fiscal_year'].max()
    previous_year_data = df[df['fiscal_year'] == previous_year]

    # Calculate totals for current year
    current_mtco2e = current_year_data['mtco2e'].sum()
    current_mmbtu = current_year_data['mmbtu'].sum()
    current_cost = current_year_data['cost'].sum()

    # Calculate totals for previous year
    previous_mtco2e = previous_year_data['mtco2e'].sum()
    previous_mmbtu = previous_year_data['mmbtu'].sum()
    previous_cost = previous_year_data['cost'].sum()

    # Display current year metrics
    st.subheader(f"Current Fiscal Year ({int(most_recent_year)}) Totals")
    col1, col2, col3 = st.columns(3)
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
    with col3:
        delta_cost = current_cost - previous_cost
        st.metric(
            label="Total Cost",
            value=f"${current_cost:,.2f}",
            delta=f"${delta_cost:,.2f} from FY{int(previous_year)}"
        )

    # Filters
    st.subheader("Filters")
    col1, col2 = st.columns(2)

    with col1:
        # Filter by facility category
        all_categories = sorted(df['facility_category'].unique().tolist())
        selected_categories = st.multiselect(
            "Select facility categories:",
            options=all_categories,
            default=all_categories
        )

    with col2:
        # Filter by account fuel type
        all_fuel_types = sorted(df['account_fuel'].unique().tolist())
        selected_fuel_types = st.multiselect(
            "Select fuel types:",
            options=all_fuel_types,
            default=all_fuel_types
        )

    # Filter data
    filtered_df = df[
        (df['facility_category'].isin(selected_categories)) &
        (df['account_fuel'].isin(selected_fuel_types))
    ]

    if len(filtered_df) > 0:
        # Aggregate by fiscal year for time series
        yearly_emissions = filtered_df.groupby('fiscal_year')['mtco2e'].sum().reset_index()
        yearly_energy = filtered_df.groupby('fiscal_year')['mmbtu'].sum().reset_index()
        yearly_cost = filtered_df.groupby('fiscal_year')['cost'].sum().reset_index()

        # Create emissions chart by fiscal year
        st.subheader("Total mtCO2e Emissions by Fiscal Year")
        fig_emissions = go.Figure()
        fig_emissions.add_trace(go.Scatter(
            x=yearly_emissions['fiscal_year'],
            y=yearly_emissions['mtco2e'],
            mode='lines+markers',
            name='mtCO2e',
            fill='tozeroy'
        ))
        fig_emissions.update_layout(
            xaxis_title="Fiscal Year",
            yaxis_title="mtCO2e",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_emissions, use_container_width=True)

        # Create energy usage chart
        st.subheader("Total Energy Usage (MMBtu) by Fiscal Year")
        fig_energy = go.Figure()
        fig_energy.add_trace(go.Scatter(
            x=yearly_energy['fiscal_year'],
            y=yearly_energy['mmbtu'],
            mode='lines+markers',
            name='MMBtu',
            fill='tozeroy'
        ))
        fig_energy.update_layout(
            xaxis_title="Fiscal Year",
            yaxis_title="MMBtu",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_energy, use_container_width=True)

        # Create cost chart
        st.subheader("Total Cost by Fiscal Year")
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Scatter(
            x=yearly_cost['fiscal_year'],
            y=yearly_cost['cost'],
            mode='lines+markers',
            name='Cost',
            fill='tozeroy'
        ))
        fig_cost.update_layout(
            xaxis_title="Fiscal Year",
            yaxis_title="Cost ($)",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_cost, use_container_width=True)

        # Breakdown by facility category
        st.subheader("Emissions by Facility Category (Current Fiscal Year)")
        category_emissions = current_year_data.groupby('facility_category')['mtco2e'].sum().reset_index()
        category_emissions = category_emissions.sort_values('mtco2e', ascending=False)

        fig_category = go.Figure()
        fig_category.add_trace(go.Bar(
            x=category_emissions['facility_category'],
            y=category_emissions['mtco2e'],
            name='mtCO2e'
        ))
        fig_category.update_layout(
            xaxis_title="Facility Category",
            yaxis_title="mtCO2e",
            height=400
        )
        st.plotly_chart(fig_category, use_container_width=True)

        # Breakdown by fuel type
        st.subheader("Emissions by Fuel Type (Current Fiscal Year)")
        fuel_emissions = current_year_data.groupby('account_fuel')['mtco2e'].sum().reset_index()
        fuel_emissions = fuel_emissions.sort_values('mtco2e', ascending=False)

        fig_fuel = go.Figure()
        fig_fuel.add_trace(go.Bar(
            x=fuel_emissions['account_fuel'],
            y=fuel_emissions['mtco2e'],
            name='mtCO2e',
            marker_color='lightcoral'
        ))
        fig_fuel.update_layout(
            xaxis_title="Fuel Type",
            yaxis_title="mtCO2e",
            height=400
        )
        st.plotly_chart(fig_fuel, use_container_width=True)

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

        # Display data preview
        st.subheader("Data Preview")
        st.dataframe(filtered_df.drop('usage_end_date', axis=1))

        # Download option
        st.subheader("Download Data")
        csv = filtered_df.drop('usage_end_date', axis=1).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name="municipal_energy_data.csv",
            mime="text/csv"
        )
    else:
        st.warning("No data available for the selected filters.")
