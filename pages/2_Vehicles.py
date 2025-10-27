import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_data

st.title("Vehicles: Registration & Emissions")

# Load the data
df = load_data()

if df is not None:
    # Convert Quarter to datetime for proper sorting
    df['Quarter_Date'] = pd.to_datetime(df['Quarter'])
    df = df.sort_values('Quarter_Date')

    # Get most recent data for each vehicle type
    most_recent_date = df['Quarter_Date'].max()
    current_vehicles = df[df['Quarter_Date'] == most_recent_date]

    # Get previous quarter data for comparison
    previous_date = df[df['Quarter_Date'] < most_recent_date]['Quarter_Date'].max()
    previous_vehicles = df[df['Quarter_Date'] == previous_date]

    # Display current vehicle counts
    st.subheader("Current Vehicle Count (Most Recent Quarter)")
    cols = st.columns(len(current_vehicles))
    for idx, (_, row) in enumerate(current_vehicles.iterrows()):
        with cols[idx]:
            # Calculate change from previous quarter
            prev_count = previous_vehicles[previous_vehicles['Type'] == row['Type']]['Number'].values
            delta = int(row['Number']) - int(prev_count[0]) if len(prev_count) > 0 else 0

            st.metric(
                label=row['Type'],
                value=f"{int(row['Number'])}",
                delta=f"{delta} vehicles"
            )

    # Create stacked line chart
    st.subheader("Vehicle Numbers by Quarter (Stacked)")

    # Multi-select for vehicle types
    all_vehicle_types = df['Type'].unique().tolist()
    selected_types = st.multiselect(
        "Select vehicle types to display:",
        options=all_vehicle_types,
        default=all_vehicle_types
    )

    # Filter data based on selection
    if selected_types:
        filtered_df = df[df['Type'].isin(selected_types)]

        # Pivot data for stacked area chart
        pivot_df = filtered_df.pivot(index='Quarter_Date', columns='Type', values='Number')

        # Create the stacked area chart
        fig = go.Figure()

        for vehicle_type in pivot_df.columns:
            fig.add_trace(go.Scatter(
                x=pivot_df.index,
                y=pivot_df[vehicle_type],
                name=vehicle_type,
                mode='lines',
                stackgroup='one',
                fillcolor='rgba' + str(tuple(list(hash(vehicle_type) % 256 for _ in range(3)) + [0.5])),
            ))

        fig.update_layout(
            title="Vehicle Count by Type Over Time",
            xaxis_title="Quarter",
            yaxis_title="Number of Vehicles",
            hovermode='x unified',
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please select at least one vehicle type to display the chart.")

    # Create tCO2e emissions chart
    st.subheader("Total tCO2e Emissions by Quarter")

    # Filter by selected types for consistency
    if selected_types:
        filtered_emissions_df = df[df['Type'].isin(selected_types)]

        # Pivot data for stacked area chart
        pivot_emissions_df = filtered_emissions_df.pivot(index='Quarter_Date', columns='Type', values='tCo2e')

        # Create the stacked area chart for emissions
        fig_emissions = go.Figure()

        for vehicle_type in pivot_emissions_df.columns:
            fig_emissions.add_trace(go.Scatter(
                x=pivot_emissions_df.index,
                y=pivot_emissions_df[vehicle_type],
                name=vehicle_type,
                mode='lines',
                stackgroup='one',
                fillcolor='rgba' + str(tuple(list(hash(vehicle_type) % 256 for _ in range(3)) + [0.5])),
            ))

        fig_emissions.update_layout(
            title="tCO2e Emissions by Type Over Time",
            xaxis_title="Quarter",
            yaxis_title="tCO2e",
            hovermode='x unified',
            height=500
        )

        st.plotly_chart(fig_emissions, use_container_width=True)
    else:
        st.warning("Please select at least one vehicle type to display the emissions chart.")

    # Add methodology section
    st.markdown("---")
    st.subheader("Methodology: How Vehicle Emissions Are Calculated")

    st.markdown("""
    Vehicle emissions are calculated using a straightforward approach that combines vehicle counts with estimated annual fuel consumption and EPA emission factors.

    ### Calculation Steps:

    **1. Vehicle Count Data**
    - Vehicle registration data by type (Passenger, Light Commercial, Motorcycle, Diesel, etc.) is tracked quarterly
    - Source: [MassDOT Vehicle Census](https://geodot-massdot.hub.arcgis.com/pages/vehicle-census)
    - Contains registered vehicle counts by municipality across Massachusetts

    **2. Annual Mileage & Fuel Efficiency**
    - Each vehicle type is assigned typical values for:
        - **Miles per year**: Average annual mileage (e.g., 12,000 miles for passenger vehicles)
        - **MPG (Miles per gallon)**: Fuel efficiency for gasoline/diesel vehicles
        - **MPkWh (Miles per kilowatt-hour)**: Energy efficiency for electric vehicles
    - Based on typical values for each vehicle type

    **3. Fuel/Energy Consumption Calculation**
    - For gasoline/diesel vehicles: `Gallons used = Miles per year ÷ MPG`
    - For electric vehicles: `kWh used = Miles per year ÷ MPkWh`

    **4. Emission Factors**
    - **Gasoline**: 0.00882 tCO2e per gallon
    - **Diesel**: 0.01030 tCO2e per gallon
    - **Electricity**: 0.000239 tCO2e per kWh (based on regional grid mix)
    - Source: EPA emission factors

    **5. Total Emissions Per Vehicle**
    - `tCO2e per vehicle = (Gallons used × Emission factor) + (kWh used × Emission factor)`

    **6. Total Fleet Emissions**
    - `Total tCO2e = Number of vehicles × tCO2e per vehicle` for each vehicle type
    - Sum across all vehicle types to get total quarterly emissions

    ### Important Notes:
    - **This is an estimate** based on typical driving patterns and fuel efficiency
    - Actual emissions may vary based on:
        - Individual driving behavior and mileage
        - Actual vehicle fuel efficiency (older vs. newer vehicles)
        - Seasonal usage patterns (Truro has many seasonal residents)
        - Electric vehicle adoption (reduces emissions per vehicle)
    - The electricity emission factor reflects the current Massachusetts grid mix, which includes renewable and fossil fuel sources
    - Vehicle count data represents registered vehicles in Truro, not necessarily all active vehicles
    """)

