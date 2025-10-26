import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_clc_participation_data, load_clc_census_data, load_clc_heat_pump_data

st.title("CLC Participation Data")

# Data collection notes
with st.expander("ℹ️ Data Collection Notes"):
    st.markdown("""
    **Data Source:** [Cape Light Compact Customer Profile Viewer](https://viewer.dnv.com/macustomerprofile/entity/1444/report/2078)

    Navigate to: **Residential: Electric and Gas Executive Summaries**

    **Data Collection Instructions:**
    - **CLC Participation Data:** Click on "Municipality" tab
    - **Census Statistics:** Click on "Census Statistics" tab (currently 2023 data)
    - **Heat Pump Installation:** Navigate to "Electrification and Heating" → "By Municipality"

    All data is downloaded as CSV files and stored in the `data/` folder.
    """)

# Load the data
df = load_clc_participation_data()

if df is not None:
    st.success(f"Successfully loaded {len(df)} years of CLC participation data")

    # Display current year metrics
    most_recent_year = df['Year'].max()
    current_data = df[df['Year'] == most_recent_year].iloc[0]
    previous_data = df[df['Year'] == most_recent_year - 1].iloc[0]

    st.subheader(f"Year {int(most_recent_year)} Status")
    col1, col2 = st.columns(2)

    with col1:
        delta_rate = current_data['Cumulative Location Participation Rate %'] - previous_data['Cumulative Location Participation Rate %']
        st.metric(
            label="Cumulative Participation Rate",
            value=f"{current_data['Cumulative Location Participation Rate %']:.2f}%",
            delta=f"{delta_rate:.2f}%"
        )

    with col2:
        delta_locations = current_data['Active Locations'] - previous_data['Active Locations']
        st.metric(
            label="Active Locations",
            value=f"{int(current_data['Active Locations']):,}",
            delta=f"{int(delta_locations):,}"
        )

    # Create line chart for participation rate over time
    st.subheader("Cumulative Location Participation Rate Over Time")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['Year'],
        y=df['Cumulative Location Participation Rate %'],
        mode='lines+markers',
        name='Participation Rate',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8)
    ))

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Participation Rate (%)",
        hovermode='x unified',
        height=500,
        yaxis=dict(range=[0, max(df['Cumulative Location Participation Rate %']) * 1.1])
    )

    st.plotly_chart(fig, use_container_width=True)

    # Calculate year-over-year change
    df_sorted = df.sort_values('Year')
    df_sorted['YoY Change'] = df_sorted['Cumulative Location Participation Rate %'].diff()

    # Create year-over-year change chart
    st.subheader("Year-over-Year Change in Participation Rate")

    fig_yoy = go.Figure()

    fig_yoy.add_trace(go.Bar(
        x=df_sorted['Year'][1:],  # Skip first year since it has no previous year
        y=df_sorted['YoY Change'][1:],
        name='YoY Change',
        marker=dict(
            color=df_sorted['YoY Change'][1:],
            colorscale='RdYlGn',
            showscale=False
        )
    ))

    fig_yoy.update_layout(
        xaxis_title="Year",
        yaxis_title="Change in Participation Rate (percentage points)",
        hovermode='x unified',
        height=400
    )

    st.plotly_chart(fig_yoy, use_container_width=True)

    # Show data table
    st.subheader("Participation Data by Year")
    display_df = df.copy()
    display_df['Cumulative Location Participation Rate %'] = display_df['Cumulative Location Participation Rate %'].apply(lambda x: f"{x:.2f}%")
    st.dataframe(display_df.sort_values('Year', ascending=False), hide_index=True)

# Load and display census data
st.divider()
st.header("Truro Census & Housing Data")

census_df = load_clc_census_data()

if census_df is not None:
    # Extract Truro data (first row)
    truro = census_df.iloc[0]

    # Housing unit breakdown
    st.subheader("Housing Units Breakdown")

    owner_occupied = truro['Tenure Owner-occupied']
    renter_occupied = truro['Tenure Renter-occupied']
    seasonal_vacant = truro['Vacancy status Seasonal, recreational, occasional']
    other_vacant = truro['Vacancy status Other']
    total_units = truro['Units in structure Total']

    # Create comprehensive housing breakdown
    col1, col2 = st.columns([2, 1])

    with col1:
        fig_housing = go.Figure(data=[go.Pie(
            labels=['Owner-occupied', 'Renter-occupied', 'Vacant (Seasonal/Recreational)', 'Vacant (Other)'],
            values=[owner_occupied, renter_occupied, seasonal_vacant, other_vacant],
            hole=0.3,
            marker=dict(colors=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'])
        )])

        fig_housing.update_layout(
            title=f"Total Housing Units: {int(total_units):,}",
            height=450
        )

        st.plotly_chart(fig_housing, use_container_width=True)

    with col2:
        st.markdown("### Summary")
        st.metric("Total Units", f"{int(total_units):,}")
        st.write("")

        st.write("**Occupied:**")
        st.write(f"- Owner: {int(owner_occupied):,} ({owner_occupied/total_units*100:.1f}%)")
        st.write(f"- Renter: {int(renter_occupied):,} ({renter_occupied/total_units*100:.1f}%)")
        st.write(f"- *Subtotal: {int(owner_occupied + renter_occupied):,} ({(owner_occupied + renter_occupied)/total_units*100:.1f}%)*")
        st.write("")

        st.write("**Vacant:**")
        st.write(f"- Seasonal: {int(seasonal_vacant):,} ({seasonal_vacant/total_units*100:.1f}%)")
        st.write(f"- Other: {int(other_vacant):,} ({other_vacant/total_units*100:.1f}%)")
        st.write(f"- *Subtotal: {int(seasonal_vacant + other_vacant):,} ({(seasonal_vacant + other_vacant)/total_units*100:.1f}%)*")

    # Heating fuel breakdown
    st.subheader("Primary Heating Fuel")

    heating_data = {
        'Electricity': truro['Heating fuel Electricity'],
        'Utility Gas': truro['Heating fuel Utility gas'],
        'Delivered Fuels': truro['Heating fuel Delivered fuels'],
        'Other': truro['Heating fuel Other']
    }

    fig_heating = go.Figure(data=[go.Bar(
        x=list(heating_data.keys()),
        y=list(heating_data.values()),
        marker=dict(color=['#06A77D', '#005377', '#D45113', '#F3A712'])
    )])

    fig_heating.update_layout(
        xaxis_title="Heating Fuel Type",
        yaxis_title="Number of Households",
        height=400
    )

    st.plotly_chart(fig_heating, use_container_width=True)

    # Show percentages
    heating_total = truro['Heating fuel Total']
    st.write(f"**Total households:** {int(heating_total):,}")
    for fuel, count in heating_data.items():
        st.write(f"**{fuel}:** {int(count):,} ({count/heating_total*100:.1f}%)")

    # Key insight callout
    vacancy_total = seasonal_vacant + other_vacant
    st.info(f"📊 **Key Insight:** {seasonal_vacant/vacancy_total*100:.1f}% of vacant properties are seasonal/recreational, highlighting Truro's role as a seasonal community. Additionally, {heating_data['Delivered Fuels']/heating_total*100:.1f}% of households use delivered fuels (oil, propane) for heating.")

# Load and display heat pump installation data
st.divider()
st.header("Heat Pump Installation Trends")

heat_pump_df = load_clc_heat_pump_data()

if heat_pump_df is not None:
    # Sort by year for proper display
    heat_pump_df = heat_pump_df.sort_values('Year')

    # Display current year metrics
    most_recent_year = heat_pump_df['Year'].max()
    current_data = heat_pump_df[heat_pump_df['Year'] == most_recent_year].iloc[0]
    previous_data = heat_pump_df[heat_pump_df['Year'] == most_recent_year - 1].iloc[0]

    delta_pumps = current_data['Installed Heat Pump'] - previous_data['Installed Heat Pump']
    st.metric(
        label=f"Heat Pumps Installed ({int(most_recent_year)})",
        value=f"{int(current_data['Installed Heat Pump']):,}",
        delta=f"{int(delta_pumps):,} from {int(previous_data['Year'])}"
    )

    # Create chart for heat pump installations
    st.subheader("Heat Pump Installation Growth Over Time")

    fig_hp = go.Figure()

    # Add bar chart for total heat pumps installed
    fig_hp.add_trace(go.Bar(
        x=heat_pump_df['Year'],
        y=heat_pump_df['Installed Heat Pump'],
        name='Heat Pumps Installed',
        marker=dict(color='#06A77D')
    ))

    fig_hp.update_layout(
        xaxis_title="Year",
        yaxis_title="Number of Heat Pumps Installed",
        hovermode='x unified',
        height=400
    )

    st.plotly_chart(fig_hp, use_container_width=True)

    # Show data table (simplified - just year and heat pumps)
    st.subheader("Heat Pump Installation Data")
    display_hp_df = heat_pump_df[['Year', 'Installed Heat Pump']].copy()
    display_hp_df.columns = ['Year', 'Heat Pumps Installed']
    st.dataframe(display_hp_df.sort_values('Year', ascending=False), hide_index=True)

    # Growth analysis
    total_growth = current_data['Installed Heat Pump'] - heat_pump_df['Installed Heat Pump'].min()
    growth_rate = ((current_data['Installed Heat Pump'] / heat_pump_df.iloc[0]['Installed Heat Pump']) - 1) * 100

    st.success(f"🌱 Heat pump installations have grown by **{int(total_growth)}** units ({growth_rate:.1f}%) from {int(heat_pump_df['Year'].min())} to {int(most_recent_year)}.")
