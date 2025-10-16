import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_data

st.title("Town of Truro Vehicle Data")

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

