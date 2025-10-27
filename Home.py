import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_vehicle_data, load_energy_data, load_mass_save_data, calculate_propane_displacement

# Page configuration
st.set_page_config(
    page_title="Town of Truro GHG Dashboard",
    page_icon="🌍",
    layout="wide"
)

st.title("Town of Truro GHG Emissions Dashboard")

# Load all datasets
vehicles_df = load_vehicle_data()
energy_df = load_energy_data()
mass_save_data = load_mass_save_data()
propane_data_tuple = calculate_propane_displacement()

if vehicles_df is not None and energy_df is not None and mass_save_data is not None and propane_data_tuple is not None:
    st.success("Successfully loaded data from all sources")

    propane_results, propane_metadata = propane_data_tuple

    # Process vehicles data
    # Convert Quarter to datetime
    vehicles_df['Quarter_Date'] = pd.to_datetime(vehicles_df['Quarter'])

    # Filter to only January quarters (Q1 of each year represents the previous year's final number)
    vehicles_df['Month'] = vehicles_df['Quarter_Date'].dt.month
    vehicles_q1 = vehicles_df[vehicles_df['Month'] == 1].copy()

    # Extract year and use previous year as the calendar year
    vehicles_q1['year'] = vehicles_q1['Quarter_Date'].dt.year - 1

    # Exclude Battery Electric vehicles and adjust Plug-in Hybrid to avoid double counting with residential electricity
    # Battery Electric: 100% of emissions already counted in residential electricity (home charging)
    # Plug-in Hybrid: ~50% electric (already counted), ~50% gas (keep in vehicle total)
    # Hybrid Electric: Self-charging, no home electricity use, keep 100%

    # Filter out Battery Electric entirely
    vehicles_q1_adjusted = vehicles_q1[vehicles_q1['Type'] != 'Battery Electric'].copy()

    # For Plug-in Hybrid, reduce emissions by 50% (assume half from home charging, half from gasoline)
    vehicles_q1_adjusted.loc[vehicles_q1_adjusted['Type'] == 'Plug-in Hybrid', 'tCo2e'] *= 0.5

    # Sum tCO2e by year for vehicles (excluding electric vehicle home charging)
    vehicles_yearly = vehicles_q1_adjusted.groupby('year')['tCo2e'].sum().reset_index()
    vehicles_yearly.columns = ['year', 'vehicles_tco2e']

    # Process energy data
    # Filter out incomplete 2025 data
    energy_df = energy_df[energy_df['fiscal_year'] < 2025]

    # Separate electric from other fuels
    energy_electric = energy_df[energy_df['account_fuel'] == 'Electric'].groupby('fiscal_year')['mtco2e'].sum().reset_index()
    energy_electric.columns = ['year', 'electric_mtco2e']

    energy_other = energy_df[energy_df['account_fuel'] != 'Electric'].groupby('fiscal_year')['mtco2e'].sum().reset_index()
    energy_other.columns = ['year', 'other_fuels_mtco2e']

    # Sum mtCO2e by year for total municipal buildings
    energy_yearly = energy_df.groupby('fiscal_year')['mtco2e'].sum().reset_index()
    energy_yearly.columns = ['year', 'municipal_buildings_mtco2e']

    # Process residential/commercial energy data
    # Propane emissions
    propane_yearly = propane_results[['Year', 'Remaining_Propane_mtCO2e']].copy()
    propane_yearly.columns = ['year', 'residential_propane_mtco2e']
    propane_yearly['year'] = propane_yearly['year'].astype(int)

    # Residential electricity emissions
    ELECTRIC_EMISSION_FACTOR = 0.000239  # tCO2e per kWh
    residential_electric = mass_save_data[mass_save_data['Sector'] == 'Residential & Low-Income'].copy()
    residential_electric['residential_electric_mtco2e'] = residential_electric['Electric_MWh'] * 1000 * ELECTRIC_EMISSION_FACTOR
    residential_electric_yearly = residential_electric[['Year', 'residential_electric_mtco2e']].copy()
    residential_electric_yearly.columns = ['year', 'residential_electric_mtco2e']
    residential_electric_yearly['year'] = residential_electric_yearly['year'].astype(int)

    # Commercial electricity emissions
    commercial_electric = mass_save_data[mass_save_data['Sector'] == 'Commercial & Industrial'].copy()
    commercial_electric['commercial_electric_mtco2e'] = commercial_electric['Electric_MWh'] * 1000 * ELECTRIC_EMISSION_FACTOR
    commercial_electric_yearly = commercial_electric[['Year', 'commercial_electric_mtco2e']].copy()
    commercial_electric_yearly.columns = ['year', 'commercial_electric_mtco2e']
    commercial_electric_yearly['year'] = commercial_electric_yearly['year'].astype(int)

    # Merge all datasets on year
    combined_df = pd.merge(vehicles_yearly, energy_yearly, on='year', how='outer')
    combined_df = pd.merge(combined_df, energy_electric, on='year', how='left')
    combined_df = pd.merge(combined_df, energy_other, on='year', how='left')
    combined_df = pd.merge(combined_df, propane_yearly, on='year', how='left')
    combined_df = pd.merge(combined_df, residential_electric_yearly, on='year', how='left')
    combined_df = pd.merge(combined_df, commercial_electric_yearly, on='year', how='left')
    combined_df = combined_df.sort_values('year')
    combined_df = combined_df.fillna(0)

    # Filter to start from 2019 (when vehicle data begins)
    combined_df = combined_df[combined_df['year'] >= 2019]

    # For 2024, copy 2023 data for residential propane and electricity
    if 2023 in combined_df['year'].values:
        row_2023 = combined_df[combined_df['year'] == 2023].iloc[0]

        # Check if 2024 exists, if not create it, if yes update it
        if 2024 in combined_df['year'].values:
            # Update existing 2024 row
            combined_df.loc[combined_df['year'] == 2024, 'residential_propane_mtco2e'] = row_2023['residential_propane_mtco2e']
            combined_df.loc[combined_df['year'] == 2024, 'residential_electric_mtco2e'] = row_2023['residential_electric_mtco2e']
            combined_df.loc[combined_df['year'] == 2024, 'commercial_electric_mtco2e'] = row_2023['commercial_electric_mtco2e']
        else:
            # Create new 2024 row
            row_2024 = pd.Series({
                'year': 2024,
                'vehicles_tco2e': 0,
                'municipal_buildings_mtco2e': 0,
                'electric_mtco2e': 0,
                'other_fuels_mtco2e': 0,
                'residential_propane_mtco2e': row_2023['residential_propane_mtco2e'],
                'residential_electric_mtco2e': row_2023['residential_electric_mtco2e'],
                'commercial_electric_mtco2e': row_2023['commercial_electric_mtco2e']
            })
            combined_df = pd.concat([combined_df, pd.DataFrame([row_2024])], ignore_index=True)

    # Calculate total emissions
    combined_df['total_tco2e'] = (combined_df['vehicles_tco2e'] +
                                   combined_df['municipal_buildings_mtco2e'] +
                                   combined_df['residential_propane_mtco2e'] +
                                   combined_df['residential_electric_mtco2e'] +
                                   combined_df['commercial_electric_mtco2e'])

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

    # Add filters for the chart
    all_categories = [
        'Residential Fossil Fuel Heating',
        'Residential Electricity',
        'Commercial Electricity',
        'Municipal Buildings (Other Fuels)',
        'Municipal Buildings (Electric)',
        'Vehicles'
    ]
    selected_categories = st.multiselect(
        "Select categories to display:",
        options=all_categories,
        default=all_categories
    )

    if selected_categories:
        # Stacked Area Chart
        st.markdown("#### Stacked Area Chart")
        fig_stacked = go.Figure()

        # Residential Fossil Fuel Heating
        if 'Residential Fossil Fuel Heating' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['residential_propane_mtco2e'],
                name='Residential Fossil Fuel Heating',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(212, 81, 19, 0.5)'
            ))

        # Residential Electricity
        if 'Residential Electricity' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['residential_electric_mtco2e'],
                name='Residential Electricity',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(6, 167, 125, 0.5)'
            ))

        # Commercial Electricity
        if 'Commercial Electricity' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['commercial_electric_mtco2e'],
                name='Commercial Electricity',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(30, 136, 229, 0.5)'
            ))

        # Municipal Buildings - Other Fuels
        if 'Municipal Buildings (Other Fuels)' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['other_fuels_mtco2e'],
                name='Municipal Buildings (Other Fuels)',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(255, 127, 80, 0.5)'
            ))

        # Municipal Buildings - Electric
        if 'Municipal Buildings (Electric)' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['electric_mtco2e'],
                name='Municipal Buildings (Electric)',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(106, 168, 79, 0.5)'
            ))

        # Vehicles
        if 'Vehicles' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['vehicles_tco2e'],
                name='Vehicles',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(70, 130, 180, 0.5)'
            ))

        fig_stacked.update_layout(
            xaxis_title="Year",
            yaxis_title="mtCO2e",
            hovermode='x unified',
            height=500
        )

        st.plotly_chart(fig_stacked, use_container_width=True)

        # Line Graph
        st.markdown("#### Line Graph")
        fig_line = go.Figure()

        # Residential Fossil Fuel Heating
        if 'Residential Fossil Fuel Heating' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['residential_propane_mtco2e'],
                name='Residential Fossil Fuel Heating',
                mode='lines+markers',
                line=dict(width=3, color='rgb(212, 81, 19)'),
                marker=dict(size=8)
            ))

        # Residential Electricity
        if 'Residential Electricity' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['residential_electric_mtco2e'],
                name='Residential Electricity',
                mode='lines+markers',
                line=dict(width=3, color='rgb(6, 167, 125)'),
                marker=dict(size=8)
            ))

        # Commercial Electricity
        if 'Commercial Electricity' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['commercial_electric_mtco2e'],
                name='Commercial Electricity',
                mode='lines+markers',
                line=dict(width=3, color='rgb(30, 136, 229)'),
                marker=dict(size=8)
            ))

        # Municipal Buildings - Other Fuels
        if 'Municipal Buildings (Other Fuels)' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['other_fuels_mtco2e'],
                name='Municipal Buildings (Other Fuels)',
                mode='lines+markers',
                line=dict(width=3, color='rgb(255, 127, 80)'),
                marker=dict(size=8)
            ))

        # Municipal Buildings - Electric
        if 'Municipal Buildings (Electric)' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['electric_mtco2e'],
                name='Municipal Buildings (Electric)',
                mode='lines+markers',
                line=dict(width=3, color='rgb(106, 168, 79)'),
                marker=dict(size=8)
            ))

        # Vehicles
        if 'Vehicles' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['vehicles_tco2e'],
                name='Vehicles',
                mode='lines+markers',
                line=dict(width=3, color='rgb(70, 130, 180)'),
                marker=dict(size=8)
            ))

        fig_line.update_layout(
            xaxis_title="Year",
            yaxis_title="mtCO2e",
            hovermode='x unified',
            height=500
        )

        st.plotly_chart(fig_line, use_container_width=True)

        # Add warning notes
        st.caption("⚠️ Note: 2024 data for residential fossil fuel heating and residential electricity are estimates based on 2023 values.")
        st.caption("ℹ️ Note: To avoid double counting, Battery Electric vehicle emissions are excluded (assumed charged at home), and Plug-in Hybrid emissions are reduced by 50%. This assumes most EV charging occurs in Truro; charging outside of town would not be captured in residential electricity data. Given current low EV adoption rates, this adjustment has minimal impact on totals.")
    else:
        st.warning("Please select at least one category to display the chart.")

    # Add summary of changes from 2019 to 2023
    st.subheader("2019-2023 Emissions Summary")

    # Get 2019 and 2023 data
    data_2019 = combined_df[combined_df['year'] == 2019].iloc[0]
    data_2023 = combined_df[combined_df['year'] == 2023].iloc[0]

    # Calculate changes
    residential_heating_change = data_2023['residential_propane_mtco2e'] - data_2019['residential_propane_mtco2e']
    residential_electric_change = data_2023['residential_electric_mtco2e'] - data_2019['residential_electric_mtco2e']
    vehicles_change = data_2023['vehicles_tco2e'] - data_2019['vehicles_tco2e']
    commercial_change = data_2023['commercial_electric_mtco2e'] - data_2019['commercial_electric_mtco2e']
    municipal_fuels_change = data_2023['other_fuels_mtco2e'] - data_2019['other_fuels_mtco2e']
    total_change = data_2023['total_tco2e'] - data_2019['total_tco2e']

    # Show key metrics in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🏠 Residential Heating",
            value=f"{data_2023['residential_propane_mtco2e']:.0f} mtCO2e",
            delta=f"{residential_heating_change:.0f} mtCO2e",
            delta_color="inverse"
        )

    with col2:
        st.metric(
            label="⚡ Residential Electric",
            value=f"{data_2023['residential_electric_mtco2e']:.0f} mtCO2e",
            delta=f"{residential_electric_change:.0f} mtCO2e",
            delta_color="inverse"
        )

    with col3:
        st.metric(
            label="🚗 Vehicles",
            value=f"{data_2023['vehicles_tco2e']:.0f} tCO2e",
            delta=f"{vehicles_change:.0f} tCO2e",
            delta_color="inverse"
        )

    with col4:
        st.metric(
            label="📊 Total Emissions",
            value=f"{data_2023['total_tco2e']:.0f} mtCO2e",
            delta=f"{total_change:.0f} mtCO2e",
            delta_color="inverse"
        )

    st.markdown("---")

    # Simplified narrative
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### ✅ Progress: Heat Pump Adoption")
        st.markdown(f"""
        **Residential fossil fuel heating dropped 25.5%** (-926 mtCO2e), reflecting the conversion of **204 properties** to heat pumps through the Cape Light Compact program.

        **Residential electricity increased 21%** (+833 mtCO2e). The largest jump occurred in 2019-2020, which seems unlikely to be primarily from heat pump adoption given the gradual conversion timeline. This may reflect increased full-time occupancy during COVID, though this is unclear.

        **Net residential benefit: -93 mtCO2e**
        """)

    with col_b:
        st.markdown("### ⚠️ Challenge: Vehicle Emissions")
        st.markdown(f"""
        **Vehicle emissions increased 16.5%** (+22 tCO2e). This reflects more vehicles on the road, without sufficient adoption of electric vehicles.

        **Municipal buildings and commercial electricity remained relatively steady**, with minor reductions.

        **Overall: -181 mtCO2e (1.8% reduction) from 2019 to 2023**
        """)

    # Show breakdown table
    st.subheader("Emissions Breakdown by Year")
    display_df = combined_df[[
        'year',
        'residential_propane_mtco2e',
        'residential_electric_mtco2e',
        'commercial_electric_mtco2e',
        'other_fuels_mtco2e',
        'electric_mtco2e',
        'vehicles_tco2e',
        'total_tco2e'
    ]].copy()
    display_df.columns = [
        'Year',
        'Residential Fossil Fuel Heating (mtCO2e)',
        'Residential Electric (mtCO2e)',
        'Commercial Electric (mtCO2e)',
        'Municipal Buildings - Other Fuels (mtCO2e)',
        'Municipal Buildings - Electric (mtCO2e)',
        'Vehicles (mtCO2e)',
        'Total (mtCO2e)'
    ]
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
