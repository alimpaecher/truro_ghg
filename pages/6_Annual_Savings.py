import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_vehicle_data, calculate_total_fossil_fuel_heating

# Page configuration
st.set_page_config(
    page_title="Annual Savings - Truro GHG",
    page_icon="🌱",
    layout="wide"
)

st.title("Annual Emissions Savings")
st.markdown("### Impact of Heat Pumps, Electric Vehicles, and Solar on Truro's Carbon Footprint")

# Load solar data
@st.cache_data
def load_solar_data():
    """Load Truro solar installation data"""
    df = pd.read_csv('data/solar_data.csv')
    df = df[df['City'] == 'Truro'].copy()
    # Filter to years with data
    df = df[df['Capacity (kW DC) All Cumulative'] > 0].copy()
    return df

# Load data
vehicles_df = load_vehicle_data()
fossil_fuel_data_tuple = calculate_total_fossil_fuel_heating()
solar_df = load_solar_data()

if vehicles_df is not None and fossil_fuel_data_tuple is not None and solar_df is not None:
    fossil_fuel_results, fossil_fuel_metadata = fossil_fuel_data_tuple

    # ============================================================================
    # SOLAR SAVINGS CALCULATIONS
    # ============================================================================

    # Constants for solar calculations
    SOLAR_CAPACITY_FACTOR = 1.2  # MWh per kW DC per year (Massachusetts average)
    ELECTRICITY_EMISSION_FACTOR = 0.239  # tCO2e per MWh (from emission_factors.csv)

    # Filter solar data to 2019 onwards
    solar_savings = solar_df[solar_df['Year'] >= 2019][['Year', 'Capacity (kW DC) All Cumulative']].copy()
    solar_savings.columns = ['year', 'capacity_kw_dc_cumulative']

    # Get 2019 baseline capacity
    baseline_2019_capacity = solar_savings[solar_savings['year'] == 2019]['capacity_kw_dc_cumulative'].values[0] if len(solar_savings) > 0 else 0

    # Calculate capacity added since 2019
    solar_savings['capacity_kw_dc'] = solar_savings['capacity_kw_dc_cumulative'] - baseline_2019_capacity

    # Calculate energy generation and emissions avoided (only for NEW capacity since 2019)
    solar_savings['annual_mwh'] = solar_savings['capacity_kw_dc'] * SOLAR_CAPACITY_FACTOR
    solar_savings['solar_savings_mtco2e'] = solar_savings['annual_mwh'] * ELECTRICITY_EMISSION_FACTOR

    # ============================================================================
    # HEAT PUMP SAVINGS CALCULATIONS
    # ============================================================================

    # Extract heat pump savings from fossil fuel data
    heat_pump_savings = fossil_fuel_results[['year', 'propane_mtco2e_eliminated', 'cumulative_conversions']].copy()
    heat_pump_savings = heat_pump_savings[heat_pump_savings['year'] >= 2019].reset_index(drop=True)

    # Calculate incremental savings (new savings added each year)
    heat_pump_savings['incremental_savings'] = heat_pump_savings['propane_mtco2e_eliminated'].diff().fillna(heat_pump_savings['propane_mtco2e_eliminated'].iloc[0])

    # ============================================================================
    # ELECTRIC VEHICLE SAVINGS CALCULATIONS
    # ============================================================================

    # Process vehicles data
    vehicles_df['Quarter_Date'] = pd.to_datetime(vehicles_df['Quarter'])
    vehicles_df['Month'] = vehicles_df['Quarter_Date'].dt.month
    vehicles_q1 = vehicles_df[vehicles_df['Month'] == 1].copy()
    vehicles_q1['year'] = vehicles_q1['Quarter_Date'].dt.year - 1

    # Filter for 2019 onwards and EVs only
    ev_data = vehicles_q1[vehicles_q1['year'] >= 2019].copy()

    # Separate BEV and PHEV
    bev_yearly = ev_data[ev_data['Type'] == 'Battery Electric'].groupby('year')['Number'].sum().reset_index()
    bev_yearly.columns = ['year', 'bev_count']

    phev_yearly = ev_data[ev_data['Type'] == 'Plug-in Hybrid'].groupby('year')['Number'].sum().reset_index()
    phev_yearly.columns = ['year', 'phev_count']

    # Merge EV data
    ev_savings = pd.merge(bev_yearly, phev_yearly, on='year', how='outer').fillna(0)

    # Emission savings per vehicle per year
    # BEV: Gasoline vehicle (4.18 tCO2e/year) - BEV (0.74 tCO2e/year) = 3.44 tCO2e/year saved
    # PHEV: Assume 50% electric, so ~1.72 tCO2e/year saved (50% of BEV savings)
    BEV_SAVINGS_PER_VEHICLE = 3.44  # tCO2e per year
    PHEV_SAVINGS_PER_VEHICLE = 1.72  # tCO2e per year (50% of BEV)

    ev_savings['bev_savings_mtco2e'] = ev_savings['bev_count'] * BEV_SAVINGS_PER_VEHICLE
    ev_savings['phev_savings_mtco2e'] = ev_savings['phev_count'] * PHEV_SAVINGS_PER_VEHICLE
    ev_savings['total_ev_savings_mtco2e'] = ev_savings['bev_savings_mtco2e'] + ev_savings['phev_savings_mtco2e']

    # ============================================================================
    # COMBINED SAVINGS
    # ============================================================================

    # Merge all savings data
    combined_savings = pd.merge(heat_pump_savings, ev_savings, on='year', how='outer').fillna(0)
    combined_savings = pd.merge(combined_savings, solar_savings[['year', 'solar_savings_mtco2e', 'annual_mwh', 'capacity_kw_dc']], on='year', how='outer').fillna(0)
    combined_savings = combined_savings.sort_values('year')

    # Calculate total savings
    combined_savings['total_annual_savings'] = (combined_savings['propane_mtco2e_eliminated'] +
                                                  combined_savings['total_ev_savings_mtco2e'] +
                                                  combined_savings['solar_savings_mtco2e'])

    # ============================================================================
    # TOP METRICS SECTION
    # ============================================================================

    st.subheader("2023 Impact Summary")

    # Get 2023 data
    data_2023 = combined_savings[combined_savings['year'] == 2023].iloc[0]
    data_2019 = combined_savings[combined_savings['year'] == 2019].iloc[0]

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_savings = data_2023['total_annual_savings']
        st.metric(
            label="Total Annual Savings (2023)",
            value=f"{total_savings:.0f} mtCO2e/year",
            help="Ongoing annual emissions reductions from heat pumps, EVs, and solar"
        )

    with col2:
        heat_pump_conversions = int(data_2023['cumulative_conversions'])
        st.metric(
            label="Properties with Heat Pumps",
            value=f"{heat_pump_conversions}",
            delta=f"+{heat_pump_conversions - int(data_2019['cumulative_conversions'])} since 2019"
        )

    with col3:
        total_bevs = int(data_2023['bev_count'])
        st.metric(
            label="Battery Electric Vehicles",
            value=f"{total_bevs}",
            delta=f"+{total_bevs - int(data_2019['bev_count'])} since 2019"
        )

    with col4:
        total_phevs = int(data_2023['phev_count'])
        st.metric(
            label="Plug-in Hybrid Vehicles",
            value=f"{total_phevs}",
            delta=f"+{total_phevs - int(data_2019['phev_count'])} since 2019"
        )

    with col5:
        solar_capacity_added = data_2023['capacity_kw_dc']  # This is already the difference from 2019
        st.metric(
            label="Solar Added Since 2019",
            value=f"{solar_capacity_added:.0f} kW DC",
            help="New solar capacity installed since 2019 baseline"
        )

    st.markdown("---")

    # ============================================================================
    # COMBINED IMPACT SECTION
    # ============================================================================

    st.subheader("Combined Climate Action Impact")

    st.markdown("""
    This chart shows the total ongoing annual emissions savings from all climate actions combined.
    These are **ongoing annual reductions** - each year these heat pumps, EVs, and solar installations continue to avoid these emissions.
    """)

    # Stacked area chart
    fig_combined = go.Figure()

    fig_combined.add_trace(go.Scatter(
        x=combined_savings['year'],
        y=combined_savings['propane_mtco2e_eliminated'],
        name='Heat Pumps',
        mode='lines',
        line=dict(width=0),
        stackgroup='one',
        fillcolor='rgba(212, 81, 19, 0.7)'
    ))

    fig_combined.add_trace(go.Scatter(
        x=combined_savings['year'],
        y=combined_savings['bev_savings_mtco2e'],
        name='Battery Electric Vehicles',
        mode='lines',
        line=dict(width=0),
        stackgroup='one',
        fillcolor='rgba(6, 167, 125, 0.7)'
    ))

    fig_combined.add_trace(go.Scatter(
        x=combined_savings['year'],
        y=combined_savings['phev_savings_mtco2e'],
        name='Plug-in Hybrid Vehicles',
        mode='lines',
        line=dict(width=0),
        stackgroup='one',
        fillcolor='rgba(30, 136, 229, 0.7)'
    ))

    fig_combined.add_trace(go.Scatter(
        x=combined_savings['year'],
        y=combined_savings['solar_savings_mtco2e'],
        name='Solar Energy',
        mode='lines',
        line=dict(width=0),
        stackgroup='one',
        fillcolor='rgba(255, 193, 7, 0.7)'
    ))

    fig_combined.update_layout(
        xaxis_title="Year",
        yaxis_title="Total Annual Emissions Savings (mtCO2e/year)",
        hovermode='x unified',
        height=500
    )

    st.plotly_chart(fig_combined, use_container_width=True)

    # Summary table
    st.markdown("#### Year-by-Year Breakdown")

    display_df = combined_savings[['year', 'propane_mtco2e_eliminated', 'bev_savings_mtco2e',
                                     'phev_savings_mtco2e', 'solar_savings_mtco2e', 'total_annual_savings']].copy()
    display_df.columns = ['Year', 'Heat Pumps (mtCO2e/year)', 'BEVs (mtCO2e/year)',
                          'PHEVs (mtCO2e/year)', 'Solar (mtCO2e/year)', 'Total Savings (mtCO2e/year)']
    display_df = display_df.sort_values('Year', ascending=False)

    st.dataframe(display_df, hide_index=True)

    # Key insights
    st.markdown("---")
    st.markdown("### Key Insights")

    total_reduction_2023 = data_2023['total_annual_savings']
    hp_percentage = (data_2023['propane_mtco2e_eliminated'] / total_reduction_2023) * 100
    ev_percentage = (data_2023['total_ev_savings_mtco2e'] / total_reduction_2023) * 100
    solar_percentage = (data_2023['solar_savings_mtco2e'] / total_reduction_2023) * 100

    growth_2019_2023 = data_2023['total_annual_savings'] - data_2019['total_annual_savings']

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        **Heat Pumps Lead the Way**
        - Heat pumps account for **{hp_percentage:.1f}%** of total annual savings in 2023
        - {int(data_2023['cumulative_conversions'])} properties converted, saving {data_2023['propane_mtco2e_eliminated']:.0f} mtCO2e annually
        - Average savings: ~{data_2023['propane_mtco2e_eliminated'] / data_2023['cumulative_conversions']:.1f} mtCO2e per property per year
        """)

    with col2:
        st.markdown(f"""
        **EV Adoption Growing**
        - EVs account for **{ev_percentage:.1f}%** of total annual savings in 2023
        - {int(data_2023['bev_count'])} BEVs + {int(data_2023['phev_count'])} PHEVs on the road
        - Total EV savings: {data_2023['total_ev_savings_mtco2e']:.0f} mtCO2e annually
        """)

    with col3:
        st.markdown(f"""
        **Solar Energy Rising**
        - Solar accounts for **{solar_percentage:.1f}%** of total annual savings in 2023
        - {data_2023['capacity_kw_dc']:.0f} kW DC added since 2019
        - Generating ~{data_2023['annual_mwh']:.0f} MWh/year, saving {data_2023['solar_savings_mtco2e']:.0f} mtCO2e annually
        """)

    st.markdown(f"""
    **Overall Progress**
    - Total ongoing annual savings increased from {data_2019['total_annual_savings']:.0f} to {data_2023['total_annual_savings']:.0f} mtCO2e/year (2019-2023)
    - Growth of **{growth_2019_2023:.0f} mtCO2e/year** in new annual savings
    - These reductions compound each year - all heat pumps, EVs, and solar installations continue to avoid emissions as long as they operate
    """)

    st.caption("""
    ⚠️ **Notes**:
    - Baseline year is 2019 when comprehensive tracking began
    - 2024 data may be incomplete and is excluded from summary metrics
    - Heat pump savings based on propane displacement (oil displacement tracked separately)
    - EV savings assume replacement of average gasoline vehicle (4.18 tCO2e/year)
    - Solar savings based on 1.2 MWh/kW DC generation rate and 0.239 tCO2e/MWh grid emission factor
    - These are ongoing annual savings - the actual cumulative impact over multiple years is much larger
    """)

    st.markdown("---")

    # ============================================================================
    # HEAT PUMP SAVINGS SECTION
    # ============================================================================

    st.subheader("Heat Pump Emissions Savings")

    st.markdown("""
    Heat pumps save emissions by replacing propane heating systems. The chart below shows the cumulative annual savings - the total ongoing emissions avoided each year from all heat pumps in operation.
    """)

    fig_hp = go.Figure()

    # Cumulative savings only
    fig_hp.add_trace(go.Scatter(
        x=heat_pump_savings['year'],
        y=heat_pump_savings['propane_mtco2e_eliminated'],
        name='Heat Pump Savings',
        mode='lines+markers',
        line=dict(width=3, color='rgb(212, 81, 19)'),
        marker=dict(size=10),
        hovertemplate='<b>Year %{x}</b><br>%{y:.1f} mtCO2e/year<extra></extra>'
    ))

    fig_hp.update_layout(
        xaxis_title="Year",
        yaxis_title="Emissions Savings (mtCO2e/year)",
        hovermode='x unified',
        height=500,
        showlegend=False
    )

    st.plotly_chart(fig_hp, use_container_width=True)

    # Heat pump summary
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(
            label="Total Properties Converted (2019-2023)",
            value=f"{int(data_2023['cumulative_conversions']) - int(data_2019['cumulative_conversions'])}"
        )
    with col_b:
        st.metric(
            label="Cumulative Annual Savings (2023)",
            value=f"{data_2023['propane_mtco2e_eliminated']:.0f} mtCO2e/year"
        )

    st.caption("📊 Based on Cape Light Compact heat pump installation tracking and propane displacement calculations")

    st.markdown("---")

    # ============================================================================
    # ELECTRIC VEHICLE SAVINGS SECTION
    # ============================================================================

    st.subheader("Electric Vehicle Emissions Savings")

    st.markdown("""
    Electric vehicles (both Battery Electric and Plug-in Hybrid) save emissions by replacing gasoline vehicles.
    Savings are calculated compared to an average gasoline vehicle (4.18 tCO2e/year).
    """)

    # EV savings line chart
    fig_ev_savings = go.Figure()

    fig_ev_savings.add_trace(go.Scatter(
        x=ev_savings['year'],
        y=ev_savings['bev_savings_mtco2e'],
        name='Battery Electric (BEV)',
        mode='lines+markers',
        line=dict(width=3, color='rgb(6, 167, 125)'),
        marker=dict(size=10),
        stackgroup='one'
    ))

    fig_ev_savings.add_trace(go.Scatter(
        x=ev_savings['year'],
        y=ev_savings['phev_savings_mtco2e'],
        name='Plug-in Hybrid (PHEV)',
        mode='lines+markers',
        line=dict(width=3, color='rgb(30, 136, 229)'),
        marker=dict(size=10),
        stackgroup='one'
    ))

    fig_ev_savings.update_layout(
        xaxis_title="Year",
        yaxis_title="Emissions Savings (mtCO2e/year)",
        hovermode='x unified',
        height=500
    )

    st.plotly_chart(fig_ev_savings, use_container_width=True)

    # EV count chart
    st.markdown("#### Electric Vehicle Adoption")

    fig_ev_count = go.Figure()

    fig_ev_count.add_trace(go.Bar(
        x=ev_savings['year'],
        y=ev_savings['bev_count'],
        name='Battery Electric (BEV)',
        marker_color='rgb(6, 167, 125)'
    ))

    fig_ev_count.add_trace(go.Bar(
        x=ev_savings['year'],
        y=ev_savings['phev_count'],
        name='Plug-in Hybrid (PHEV)',
        marker_color='rgb(30, 136, 229)'
    ))

    fig_ev_count.update_layout(
        xaxis_title="Year",
        yaxis_title="Number of Vehicles",
        barmode='group',
        hovermode='x unified',
        height=400
    )

    st.plotly_chart(fig_ev_count, use_container_width=True)

    # EV summary
    col_c, col_d = st.columns(2)
    with col_c:
        total_evs = int(data_2023['bev_count'] + data_2023['phev_count'])
        baseline_evs = int(data_2019['bev_count'] + data_2019['phev_count'])
        st.metric(
            label="Total EVs Added (2019-2023)",
            value=f"{total_evs - baseline_evs}"
        )
    with col_d:
        st.metric(
            label="Annual Savings from EVs (2023)",
            value=f"{data_2023['total_ev_savings_mtco2e']:.0f} mtCO2e/year"
        )

    st.caption(f"📊 BEVs save ~{BEV_SAVINGS_PER_VEHICLE} mtCO2e/year each vs gasoline. PHEVs save ~{PHEV_SAVINGS_PER_VEHICLE} mtCO2e/year each (50% electric operation assumed)")

    st.markdown("---")

    # ============================================================================
    # SOLAR SAVINGS SECTION
    # ============================================================================

    st.subheader("Solar Energy Emissions Savings")

    st.markdown("""
    Solar installations save emissions by generating clean electricity, reducing the need for grid power.
    Charts show **new solar capacity installed since 2019** (baseline year), consistent with heat pump and EV tracking.
    """)

    # Solar capacity chart at the top
    st.markdown("#### Cumulative Solar Capacity Added Since 2019")

    fig_capacity_main = go.Figure()
    fig_capacity_main.add_trace(go.Scatter(
        x=solar_savings['year'],
        y=solar_savings['capacity_kw_dc'],
        mode='lines+markers',
        line=dict(width=3, color='rgb(255, 152, 0)'),
        marker=dict(size=10),
        fill='tozeroy',
        fillcolor='rgba(255, 152, 0, 0.3)'
    ))
    fig_capacity_main.update_layout(
        xaxis_title="Year",
        yaxis_title="Capacity Added (kW DC)",
        hovermode='x unified',
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_capacity_main, use_container_width=True)

    # Solar savings and generation side by side
    st.markdown("#### Emissions Savings and Energy Generation")

    col_solar1, col_solar2 = st.columns(2)

    with col_solar1:
        fig_savings = go.Figure()
        fig_savings.add_trace(go.Scatter(
            x=solar_savings['year'],
            y=solar_savings['solar_savings_mtco2e'],
            mode='lines+markers',
            line=dict(width=3, color='rgb(255, 193, 7)'),
            marker=dict(size=10)
        ))
        fig_savings.update_layout(
            title="Annual Emissions Savings",
            xaxis_title="Year",
            yaxis_title="Savings (mtCO2e/year)",
            height=350
        )
        st.plotly_chart(fig_savings, use_container_width=True)

    with col_solar2:
        fig_generation = go.Figure()
        fig_generation.add_trace(go.Scatter(
            x=solar_savings['year'],
            y=solar_savings['annual_mwh'],
            mode='lines+markers',
            line=dict(width=3, color='rgb(255, 235, 59)'),
            marker=dict(size=10)
        ))
        fig_generation.update_layout(
            title="Estimated Annual Generation",
            xaxis_title="Year",
            yaxis_title="Energy (MWh/year)",
            height=350
        )
        st.plotly_chart(fig_generation, use_container_width=True)

    # Solar summary
    col_e, col_f = st.columns(2)
    with col_e:
        capacity_added = data_2023['capacity_kw_dc']  # Already relative to 2019 baseline
        st.metric(
            label="Solar Capacity Added (2019-2023)",
            value=f"{capacity_added:.0f} kW DC"
        )
    with col_f:
        st.metric(
            label="Annual Savings from New Solar (2023)",
            value=f"{data_2023['solar_savings_mtco2e']:.0f} mtCO2e/year",
            help="Savings from solar capacity added since 2019"
        )

    st.caption(f"📊 Savings calculated only for NEW solar capacity installed since 2019. Generation estimate: {SOLAR_CAPACITY_FACTOR} MWh per kW DC per year. Emission factor: {ELECTRICITY_EMISSION_FACTOR} tCO2e per MWh (NPCC New England grid)")

else:
    st.error("Unable to load data. Please check the data sources.")
