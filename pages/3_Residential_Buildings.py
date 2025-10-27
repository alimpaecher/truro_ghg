import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_assessors_data, calculate_residential_emissions, load_mass_save_data, calculate_propane_displacement

st.title("Residential & Commercial Buildings: Heating & Energy")

st.markdown("""
This page explains how we track energy use and emissions from residential and commercial buildings in Truro,
combining multiple data sources to tell the story of the town's energy transition from 2019 to 2023.
""")

# Load all data sources
mass_save_data = load_mass_save_data()
propane_data_tuple = calculate_propane_displacement()
df = load_assessors_data()

if mass_save_data is not None and propane_data_tuple is not None:
    propane_results, propane_metadata = propane_data_tuple

    # SECTION 1: OVERVIEW
    st.header("1. Energy Trends Overview (2019-2023)")

    st.markdown("""
    This chart shows the big picture: how Truro's building energy use has changed over five years.
    We track two types of energy:
    - **Fossil Fuel Heating (orange line)**: Propane emissions from home heating
    - **Electricity (green and blue lines)**: Power consumption in residential and commercial buildings
    """)

    # Prepare data for the combined chart
    residential_electric = mass_save_data[mass_save_data['Sector'] == 'Residential & Low-Income'].sort_values('Year')
    commercial_electric = mass_save_data[mass_save_data['Sector'] == 'Commercial & Industrial'].sort_values('Year')

    # Create figure with three lines
    fig_overview = go.Figure()

    # Fossil Fuel Heating (Propane emissions)
    fig_overview.add_trace(go.Scatter(
        x=propane_results['Year'],
        y=propane_results['Remaining_Propane_mtCO2e'],
        name='Fossil Fuel Heating (Propane)',
        mode='lines+markers',
        line=dict(width=3, color='#D45113'),
        marker=dict(size=8),
        yaxis='y1'
    ))

    # Residential Energy Use (Electricity MWh)
    fig_overview.add_trace(go.Scatter(
        x=residential_electric['Year'],
        y=residential_electric['Electric_MWh'],
        name='Residential Energy Use',
        mode='lines+markers',
        line=dict(width=3, color='#06A77D'),
        marker=dict(size=8),
        yaxis='y2'
    ))

    # Commercial Energy Use (Electricity MWh)
    fig_overview.add_trace(go.Scatter(
        x=commercial_electric['Year'],
        y=commercial_electric['Electric_MWh'],
        name='Commercial Energy Use',
        mode='lines+markers',
        line=dict(width=3, color='#1E88E5'),
        marker=dict(size=8),
        yaxis='y2'
    ))

    # Update layout with dual y-axes
    fig_overview.update_layout(
        xaxis=dict(title="Year"),
        yaxis=dict(
            title=dict(text="Propane Emissions (mtCO2e)", font=dict(color="#D45113")),
            tickfont=dict(color="#D45113"),
            rangemode='tozero',
            showgrid=True
        ),
        yaxis2=dict(
            title=dict(text="Electricity Usage (MWh)", font=dict(color="#06A77D")),
            tickfont=dict(color="#06A77D"),
            overlaying='y',
            side='right',
            rangemode='tozero',
            showgrid=False
        ),
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig_overview, use_container_width=True)

    st.markdown("""
    **What the chart tells us:**
    - Propane emissions are declining as homes convert to heat pumps
    - Residential electricity usage is increasing (heat pumps use electricity)
    - Commercial electricity usage remains relatively stable
    """)

    st.divider()

    # SECTION 2: ELECTRICITY DATA
    st.header("2. Electricity Usage: Direct Measurement")

    st.markdown("""
    ### How We Got This Data

    Electricity usage data comes from **Mass Save's Geographic Report**, which aggregates actual utility billing data
    by municipality and sector. This is direct measurement—no estimates or calculations needed.

    **Data Source**: [Mass Save Geographic Savings](https://www.masssavedata.com/Public/GeographicSavings)
    """)

    # Display electricity data table
    st.subheader("Electricity Consumption by Year")

    # Create table
    electricity_table = []
    for year in sorted(mass_save_data['Year'].unique()):
        year_data = mass_save_data[mass_save_data['Year'] == year]
        res_row = year_data[year_data['Sector'] == 'Residential & Low-Income'].iloc[0]
        com_row = year_data[year_data['Sector'] == 'Commercial & Industrial'].iloc[0]

        electricity_table.append({
            'Year': int(year),
            'Residential (MWh)': f"{res_row['Electric_MWh']:,.0f}",
            'Commercial (MWh)': f"{com_row['Electric_MWh']:,.0f}",
            'Total (MWh)': f"{res_row['Electric_MWh'] + com_row['Electric_MWh']:,.0f}"
        })

    st.dataframe(pd.DataFrame(electricity_table), hide_index=True, use_container_width=True)

    st.info("""
    💡 **Note**: This electricity data is already complete—we have actual measurements from utilities.
    The Mass Save data includes all electricity consumption, including from heat pumps.

    For reference, you can convert electricity to emissions using the grid's emission factor (0.000239 tCO2e/kWh),
    but this conversion isn't needed for the propane displacement analysis below.
    """)

    st.divider()

    # SECTION 3: FOSSIL FUEL HEATING
    st.header("3. Fossil Fuel Heating: Estimated from Property Data")

    st.markdown("""
    ### Why Estimation is Necessary

    Unlike electricity, there's no centralized reporting for oil and propane (fossil fuel) consumption in Truro.
    Homes buy heating fuel from various suppliers, and there's no municipal aggregation of this data.

    Instead, we **estimate** heating fuel usage based on building characteristics from the Assessors Database.
    """)

    st.subheader("Step 1: Property Inventory")

    st.markdown("""
    The **Truro Assessors Database (2019)** contains detailed information about every property in town, including:
    - Square footage
    - Heating fuel type (Oil, Propane, Electric, etc.)
    - HVAC system type
    - Property use (residential, commercial, seasonal)
    """)

    if df is not None:
        # Property counts
        df_with_sqft = df[df['NetSF'].notna() & (df['NetSF'] > 0)].copy()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Properties", f"{len(df):,}")
        with col2:
            st.metric("With Square Footage", f"{len(df_with_sqft):,}")
        with col3:
            propane_count = len(df_with_sqft[df_with_sqft['FUEL'] == 'GAS'])
            st.metric("Propane Heating", f"{propane_count:,}")

        # Show fuel type breakdown
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Heating Fuel Distribution:**")
            fuel_counts = df_with_sqft['FUEL'].value_counts().reset_index()
            fuel_counts.columns = ['Fuel Type', 'Number of Properties']
            st.dataframe(fuel_counts, hide_index=True, use_container_width=True)

        with col2:
            st.markdown("**Heating System (HVAC) Distribution:**")
            hvac_counts = df_with_sqft['HVAC'].value_counts().reset_index()
            hvac_counts.columns = ['HVAC Type', 'Number of Properties']
            st.dataframe(hvac_counts, hide_index=True, use_container_width=True)

        st.info("""
        💡 **Key Observation**: In 2019, the assessors database shows **92 properties with heat pumps**.
        This becomes our baseline for tracking heat pump growth through CLC data (2021-2023).
        """)

    st.subheader("Step 2: Establishing Baseline Fossil Fuel Emissions")

    st.markdown("""
    To track how fossil fuel heating changes over time, we establish a **2019 baseline** for propane heating specifically.

    Why focus on propane? Heat pump conversions in Truro have primarily targeted propane heating systems, so we track
    **year-round residential propane properties** as they convert to heat pumps (CLC-funded installations).
    """)

    st.markdown("""
    **Baseline Metrics (2019):**
    """)

    baseline_metrics = pd.DataFrame({
        'Metric': [
            'Year-Round Residential Propane Properties',
            'Median Property Size',
            'Total Baseline Propane Emissions'
        ],
        'Value': [
            f"{propane_metadata['baseline_propane_properties']:,} properties",
            f"{propane_metadata['median_sqft']:,.0f} sq ft",
            f"{propane_metadata['baseline_propane_mtco2e']:,.1f} mtCO2e/year"
        ],
        'Notes': [
            'From assessors database (excludes motels, commercial)',
            'Used for heat pump displacement calculations',
            'This is what we track reducing over time'
        ]
    })

    st.table(baseline_metrics)

    st.markdown("""
    The calculation uses:
    - **Propane consumption benchmark**: 0.39 gallons per sq ft per year ([Mass.gov](https://www.mass.gov/info-details/household-heating-costs))
    - **Propane emission factor**: 0.00574 tCO2e per gallon (from emission_factors.csv)
    - **Year-round heating factor**: 100% (these are occupied homes, not seasonal)

    **Note**: Oil heating (the other major fossil fuel in the data) is not included in the displacement tracking below,
    as heat pump conversions have primarily targeted propane systems.
    """)

    st.divider()

    # SECTION 4: TRACKING THE TRANSITION
    st.header("4. Tracking the Energy Transition: Heat Pump Adoption")

    st.markdown("""
    ### How Heat Pumps Change the Picture

    As properties convert from propane heating to heat pumps:
    - **Propane consumption decreases** (homes stop buying propane)
    - **Electricity consumption increases** (heat pumps use electricity)
    - **Net emissions usually decrease** (heat pumps are ~3x more efficient than resistance heating)

    We track this transition by combining two data sources:
    """)

    # Data sources for heat pump tracking
    st.subheader("Data Sources for Propane Displacement")

    heat_pump_sources = pd.DataFrame({
        'Year': ['2019', '2020', '2021-2023'],
        'Source': ['Assessors Database', 'Interpolated (Linear)', 'Cape Light Compact'],
        'Heat Pump Count': [
            f"{propane_metadata['baseline_heat_pumps']} properties",
            f"{propane_metadata['interpolated_2020']} properties (estimated)",
            'Actual CLC installation tracking'
        ],
        'Data Quality': ['Actual property records', 'Estimated', 'Actual installations']
    })

    st.table(heat_pump_sources)

    st.info("""
    📊 **Why interpolate 2020?** We have a 2019 snapshot from assessors and 2021-2023 tracking from CLC.
    We assume linear growth between these points to avoid a data gap.
    """)

    st.subheader("Heat Pump Growth Over Time")

    # Chart showing heat pump adoption
    fig_heat_pumps = go.Figure()

    fig_heat_pumps.add_trace(go.Scatter(
        x=propane_results['Year'],
        y=propane_results['Heat_Pump_Locations'],
        mode='lines+markers',
        line=dict(width=3, color='#06A77D'),
        marker=dict(size=10),
        name='Heat Pump Installations'
    ))

    fig_heat_pumps.update_layout(
        xaxis_title="Year",
        yaxis_title="Number of Heat Pump Installations",
        yaxis=dict(rangemode='tozero'),
        height=400
    )

    st.plotly_chart(fig_heat_pumps, use_container_width=True)

    st.subheader("Calculating Propane Displacement")

    st.markdown("""
    ### Key Assumptions

    We make several assumptions to estimate how much propane consumption has decreased.
    Each assumption has a rationale, but could be wrong:
    """)

    # Assumption 1
    st.markdown("**1. Heat Pumps Replace Propane Systems**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("✅ **Our Assumption:**")
        st.write("Heat pumps replaced propane heating (not oil or electric resistance)")
        st.caption("*Justification: Propane most common conversion target in coastal MA; CLC program priorities*")
    with col2:
        st.markdown("⚠️ **Why We Might Be Wrong:**")
        st.write("Some heat pumps may have replaced oil or electric resistance heating instead")
        st.caption("*Impact: Would overestimate propane reduction*")

    # Assumption 2
    st.markdown("**2. Installations Are in Year-Round Homes**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("✅ **Our Assumption:**")
        st.write("All CLC-funded installations are in year-round occupied homes")
        st.caption("*Justification: CLC incentives favor year-round homeowners; seasonal homes less likely to invest*")
    with col2:
        st.markdown("⚠️ **Why We Might Be Wrong:**")
        st.write("Some installations could be in seasonal homes that got upgraded")
        st.caption("*Impact: Would overestimate propane displacement per property (seasonal homes use less heating)*")

    # Assumption 3
    st.markdown(f"**3. Representative Property Size: {propane_metadata['median_sqft']:,.0f} sq ft**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("✅ **Our Assumption:**")
        st.write(f"Use median square footage ({propane_metadata['median_sqft']:,.0f} sq ft) for all conversions")
        st.caption("*Justification: Median is middle value; best proxy when actual property data unavailable*")
    with col2:
        st.markdown("⚠️ **Why We Might Be Wrong:**")
        st.write("Actual converted properties may be larger or smaller than median")
        st.caption("*Impact: Would under/overestimate fuel savings depending on actual sizes*")

    # Assumption 4
    st.markdown("**4. Assessors Data Aligns with CLC Data**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("✅ **Our Assumption:**")
        st.write("2019 assessors database accurately represents the baseline; heat pump count (92) matches with 2021 CLC data (165)")
        st.caption("*Justification: Assessors data is close in time to CLC baseline; linear interpolation for 2020 is reasonable*")
    with col2:
        st.markdown("⚠️ **Why We Might Be Wrong:**")
        st.write("Property characteristics may have changed between 2019-2021; assessors data may have capture issues; transition period could have anomalies")
        st.caption("*Impact: Baseline propane property count or characteristics could be off, affecting all subsequent calculations*")

    st.subheader("Propane Reduction Results")

    st.markdown("""
    By tracking heat pump installations and applying our assumptions, we can estimate how propane emissions have declined:
    """)

    # Chart showing propane decline
    fig_propane_decline = go.Figure()

    fig_propane_decline.add_trace(go.Scatter(
        x=propane_results['Year'],
        y=propane_results['Remaining_Propane_mtCO2e'],
        name='Remaining Propane Emissions',
        mode='lines+markers',
        line=dict(width=3, color='#D45113'),
        marker=dict(size=10),
        fill='tozeroy',
        fillcolor='rgba(212, 81, 19, 0.2)'
    ))

    fig_propane_decline.add_trace(go.Scatter(
        x=propane_results['Year'],
        y=propane_results['Propane_Saved_mtCO2e'],
        name='Propane Emissions Eliminated',
        mode='lines+markers',
        line=dict(width=3, color='#06A77D'),
        marker=dict(size=10)
    ))

    fig_propane_decline.update_layout(
        xaxis_title="Year",
        yaxis_title="Emissions (mtCO2e)",
        yaxis=dict(rangemode='tozero'),
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig_propane_decline, use_container_width=True)

    # Year-by-year table
    st.markdown("**Year-by-Year Breakdown:**")

    table_display = propane_results.copy()
    table_display = table_display[[
        'Year', 'Heat_Pump_Locations', 'Cumulative_Conversions',
        'Remaining_Propane_mtCO2e', 'Propane_Saved_mtCO2e', 'Percent_Reduction'
    ]]

    table_display['Year'] = table_display['Year'].astype(int)
    table_display['Heat_Pump_Locations'] = table_display['Heat_Pump_Locations'].astype(int)
    table_display['Cumulative_Conversions'] = table_display['Cumulative_Conversions'].astype(int)
    table_display['Remaining_Propane_mtCO2e'] = table_display['Remaining_Propane_mtCO2e'].apply(lambda x: f"{x:,.1f}")
    table_display['Propane_Saved_mtCO2e'] = table_display['Propane_Saved_mtCO2e'].apply(lambda x: f"{x:,.1f}")
    table_display['Percent_Reduction'] = table_display['Percent_Reduction'].apply(lambda x: f"{x:.1f}%")

    table_display.columns = [
        'Year',
        'Total Heat Pumps',
        'Conversions from 2019',
        'Remaining Emissions (mtCO2e)',
        'Emissions Eliminated (mtCO2e)',
        '% Reduction'
    ]

    st.dataframe(table_display, hide_index=True, use_container_width=True)

    # Summary
    latest_year_data = propane_results.iloc[-1]

    st.success(f"""
    📊 **Bottom Line ({int(latest_year_data['Year'])})**:
    - **{int(latest_year_data['Cumulative_Conversions'])} properties** have converted from propane to heat pumps since 2019
    - **{latest_year_data['Propane_Saved_mtCO2e']:.1f} mtCO2e** in propane emissions eliminated annually
    - This represents a **{latest_year_data['Percent_Reduction']:.1f}% reduction** from the 2019 baseline
    """)

    st.divider()

    # SECTION 5: LIMITATIONS
    st.header("5. Important Limitations & Uncertainties")

    st.markdown("""
    ### What We're Confident About
    - ✅ **Electricity consumption**: Direct measurements from utilities
    - ✅ **Heat pump installations**: Actual CLC tracking data (2021-2023)
    - ✅ **Property characteristics**: Real assessors data (2019)

    ### What Involves Assumptions & Estimates
    """)

    st.markdown("""
    **1. Propane Consumption Baseline**
    - **Limitation**: No direct measurement of propane usage available
    - **How we address it**: Use Mass.gov benchmark (0.39 gal/sq ft) for propane consumption estimates

    **2. Heat Pump Replacement Targets**
    - **Limitation**: Cannot verify each heat pump replaced propane specifically (vs oil or electric)
    - **How we address it**: Assume propane target based on MA coastal conversion patterns and CLC program priorities

    **3. 2020 Heat Pump Count**
    - **Limitation**: Interpolated value between 2019 assessors (92) and 2021 CLC (165)
    - **How we address it**: Linear interpolation is reasonable given close timeframe and steady growth pattern

    **4. Property Sizes**
    - **Limitation**: Using median square footage; actual converted properties vary
    - **How we address it**: Median is best available proxy when actual property-level conversion data unavailable
    """)

    st.info("""
    💡 **Future Improvements:**
    - Update with newer assessors data when available (though CLC tracking is reliable for actual heat pump installations)
    - Cross-reference CLC installations with assessors data to verify fuel types being replaced
    - Track oil heating displacement separately from propane
    - Obtain actual propane delivery data if suppliers are willing to share aggregated information
    """)

else:
    st.error("Unable to load required data. Please check that all data files are available.")
