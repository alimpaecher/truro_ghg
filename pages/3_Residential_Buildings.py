import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_assessors_data, calculate_residential_emissions, load_mass_save_data, calculate_propane_displacement, calculate_total_fossil_fuel_heating

st.title("Residential & Commercial Buildings: Heating & Energy")

st.markdown("""
This page explains how we track energy use and emissions from residential and commercial buildings in Truro,
combining multiple data sources to tell the story of the town's energy transition from 2019 to 2023.
""")

# Load all data sources
mass_save_data = load_mass_save_data()
fossil_fuel_tuple = calculate_total_fossil_fuel_heating()
propane_data_tuple = calculate_propane_displacement()
df = load_assessors_data()

if mass_save_data is not None and fossil_fuel_tuple is not None and propane_data_tuple is not None:
    fossil_fuel_results, fossil_fuel_metadata = fossil_fuel_tuple
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

    # Fossil Fuel Heating (Oil + Propane emissions)
    fig_overview.add_trace(go.Scatter(
        x=fossil_fuel_results['year'],
        y=fossil_fuel_results['total_fossil_fuel_mtco2e'],
        name='Fossil Fuel Heating (Oil + Propane)',
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
    - Fossil fuel heating emissions (oil + propane) are declining as homes convert to heat pumps
    - Oil heating (~5,402 mtCO2e) stays constant; propane heating decreases as properties convert
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
            'Total Fossil Fuel Heating Emissions',
            '  - Oil Heating',
            '  - Propane Heating (seasonal-adjusted)',
            'Oil Properties',
            'Propane Properties',
            'Tracked Propane Properties (for displacement)'
        ],
        'Value': [
            f"{fossil_fuel_metadata['oil_emissions_baseline'] + fossil_fuel_metadata['baseline_propane_mtco2e_seasonal']:,.1f} mtCO2e/year",
            f"{fossil_fuel_metadata['oil_emissions_baseline']:,.1f} mtCO2e/year",
            f"{fossil_fuel_metadata['baseline_propane_mtco2e_seasonal']:,.1f} mtCO2e/year",
            f"{fossil_fuel_metadata['oil_properties']:,} properties",
            f"{fossil_fuel_metadata['total_propane_properties']:,} properties",
            f"{fossil_fuel_metadata['tracked_propane_properties']:,} properties"
        ],
        'Notes': [
            'Total baseline (2019)',
            'Stays constant (not being displaced)',
            'All 821 properties with seasonal adjustment',
            'From assessors database',
            'From assessors database',
            'Year-round subset being tracked'
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

    st.subheader("Fossil Fuel Heating Reduction Results")

    st.markdown("""
    By tracking heat pump installations, we can see how total fossil fuel heating emissions have declined:
    """)

    # Chart showing fossil fuel decline (oil stays constant, tracked propane decreases)
    fig_fossil_fuel_decline = go.Figure()

    # Total fossil fuel heating (oil + all propane, with tracked propane declining)
    fig_fossil_fuel_decline.add_trace(go.Scatter(
        x=fossil_fuel_results['year'],
        y=fossil_fuel_results['total_fossil_fuel_mtco2e'],
        name='Total Fossil Fuel Heating',
        mode='lines+markers',
        line=dict(width=3, color='#D45113'),
        marker=dict(size=10),
        fill='tozeroy',
        fillcolor='rgba(212, 81, 19, 0.2)'
    ))

    # Oil (constant baseline)
    fig_fossil_fuel_decline.add_trace(go.Scatter(
        x=fossil_fuel_results['year'],
        y=fossil_fuel_results['oil_mtco2e'],
        name='Oil Heating (constant)',
        mode='lines',
        line=dict(width=2, color='#8B4513', dash='dash'),
        marker=dict(size=8)
    ))

    # Tracked propane emissions saved
    fig_fossil_fuel_decline.add_trace(go.Scatter(
        x=propane_results['Year'],
        y=propane_results['Propane_Saved_mtCO2e'],
        name='Propane Emissions Eliminated',
        mode='lines+markers',
        line=dict(width=3, color='#06A77D'),
        marker=dict(size=10)
    ))

    fig_fossil_fuel_decline.update_layout(
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

    st.plotly_chart(fig_fossil_fuel_decline, use_container_width=True)

    # Year-by-year table
    st.markdown("**Year-by-Year Breakdown:**")

    # Use data from the consolidated fossil fuel function
    table_display = fossil_fuel_results.copy()

    # Calculate percent reduction from 2019 baseline
    baseline_2019 = fossil_fuel_results[fossil_fuel_results['year'] == 2019]['total_fossil_fuel_mtco2e'].iloc[0]
    table_display['Percent_Reduction'] = ((baseline_2019 - table_display['total_fossil_fuel_mtco2e']) / baseline_2019 * 100)

    # Select and format display columns
    table_display_formatted = pd.DataFrame({
        'Year': table_display['year'].astype(int),
        'Total Heat Pumps': table_display['heat_pump_locations'].astype(int),
        'Conversions from 2019': table_display['cumulative_conversions'].astype(int),
        'Oil (constant)': table_display['oil_mtco2e'].apply(lambda x: f"{x:,.1f}"),
        'Propane (remaining)': table_display['propane_mtco2e'].apply(lambda x: f"{x:,.1f}"),
        'Total Fossil Fuel': table_display['total_fossil_fuel_mtco2e'].apply(lambda x: f"{x:,.1f}"),
        'Emissions Eliminated': table_display['propane_mtco2e_eliminated'].apply(lambda x: f"{x:,.1f}"),
        '% Reduction': table_display['Percent_Reduction'].apply(lambda x: f"{x:.1f}%")
    })

    st.dataframe(table_display_formatted, hide_index=True, use_container_width=True)

    # Summary
    latest_year_data = fossil_fuel_results.iloc[-1]

    st.success(f"""
    📊 **Bottom Line (2023)**:
    - **{int(latest_year_data['cumulative_conversions'])} properties** have converted from propane to heat pumps since 2019
    - **{latest_year_data['propane_mtco2e_eliminated']:.1f} mtCO2e** in propane emissions eliminated annually
    - **Total fossil fuel heating: {latest_year_data['total_fossil_fuel_mtco2e']:,.1f} mtCO2e** (down from {baseline_2019:,.1f} mtCO2e in 2019)
    - This represents a **{((baseline_2019 - latest_year_data['total_fossil_fuel_mtco2e']) / baseline_2019 * 100):.1f}% reduction** in total fossil fuel heating emissions
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

    # DETAILED CALCULATION BREAKDOWN
    st.divider()
    st.header("Detailed Calculation Breakdown")

    st.markdown("""
    This section shows exactly how we calculated the fossil fuel heating emissions by fuel type.
    The calculation includes **full-time vs seasonal occupancy** adjustments.
    """)

    # Load the total fossil fuel data
    fossil_fuel_tuple = calculate_total_fossil_fuel_heating()
    if fossil_fuel_tuple is not None:
        fossil_fuel_results, fossil_fuel_metadata = fossil_fuel_tuple

        # Seasonal adjustment factors
        SEASONAL_PCT = 0.671  # 67.1% of residential properties are seasonal
        SEASONAL_HEATING_FACTOR = 0.30  # Seasonal homes use 30% of year-round heating
        YEARROUND_HEATING_FACTOR = 1.00  # Year-round homes use 100%

        # Calculate weighted average seasonal adjustment
        avg_seasonal_factor = (SEASONAL_PCT * SEASONAL_HEATING_FACTOR +
                              (1 - SEASONAL_PCT) * YEARROUND_HEATING_FACTOR)

        st.markdown(f"""
        **Occupancy Assumptions (from CLC Census data):**
        - **{SEASONAL_PCT*100:.1f}%** of residential properties are **seasonal** (use {SEASONAL_HEATING_FACTOR*100:.0f}% heating)
        - **{(1-SEASONAL_PCT)*100:.1f}%** of residential properties are **year-round** (use {YEARROUND_HEATING_FACTOR*100:.0f}% heating)
        - **Weighted average heating factor: {avg_seasonal_factor*100:.1f}%**
        """)

        # Get detailed fuel data from assessors
        if df is not None:
            df_residential = df[(df['PropertyType'] == 'R') &
                               (df['NetSF'].notna()) &
                               (df['NetSF'] > 0)].copy()

            # Oil properties
            oil_properties = df_residential[df_residential['FUEL'] == 'OIL']
            oil_count = len(oil_properties)
            oil_median_sqft = oil_properties['NetSF'].median()
            oil_total_sqft = oil_properties['NetSF'].sum()

            # Propane properties
            gas_properties = df_residential[df_residential['FUEL'] == 'GAS']
            gas_count = len(gas_properties)
            gas_median_sqft = gas_properties['NetSF'].median()

            # All propane properties
            propane_total_sqft = gas_properties['NetSF'].sum()

            # Consumption rates
            OIL_CONSUMPTION = 0.40  # gal/sq ft/year
            PROPANE_CONSUMPTION = 0.39  # gal/sq ft/year

            # Emission factors
            OIL_EMISSION_FACTOR = 0.01030  # tCO2e/gal
            PROPANE_EMISSION_FACTOR = 0.00574  # tCO2e/gal

            # Calculate gallons and emissions for each fuel type

            # Oil (uses seasonal adjustment: 67.1% seasonal, 32.9% year-round)
            # Expected baseline (2019): ~5,402.4 mtCO2e
            oil_gallons_total = oil_total_sqft * OIL_CONSUMPTION * avg_seasonal_factor
            oil_mtco2e = oil_gallons_total * OIL_EMISSION_FACTOR

            # Propane (uses seasonal adjustment: 67.1% seasonal, 32.9% year-round)
            # Expected baseline (2019): ~2,106.3 mtCO2e
            propane_gallons_total = propane_total_sqft * PROPANE_CONSUMPTION * avg_seasonal_factor
            propane_mtco2e = propane_gallons_total * PROPANE_EMISSION_FACTOR

            st.markdown("### Fuel Type Breakdown (2019 Baseline)")

            # Create detailed fuel breakdown table
            fuel_breakdown = pd.DataFrame({
                'Fuel Type': [
                    'Oil',
                    'Propane (GAS)',
                    'TOTAL'
                ],
                'Number of Properties': [
                    f"{oil_count:,}",
                    f"{gas_count:,}",
                    f"{oil_count + gas_count:,}"
                ],
                'Median Sq Ft': [
                    f"{oil_median_sqft:,.0f}",
                    f"{gas_median_sqft:,.0f}",
                    '—'
                ],
                '% Year-Round / % Seasonal': [
                    f"{(1-SEASONAL_PCT)*100:.1f}% / {SEASONAL_PCT*100:.1f}%",
                    f"{(1-SEASONAL_PCT)*100:.1f}% / {SEASONAL_PCT*100:.1f}%",
                    '—'
                ],
                'Heating Factor': [
                    f"{avg_seasonal_factor*100:.1f}%",
                    f"{avg_seasonal_factor*100:.1f}%",
                    '—'
                ],
                'Consumption Rate': [
                    f"{OIL_CONSUMPTION} gal/sq ft/year",
                    f"{PROPANE_CONSUMPTION} gal/sq ft/year",
                    '—'
                ],
                'Total Gallons Used': [
                    f"{oil_gallons_total:,.0f}",
                    f"{propane_gallons_total:,.0f}",
                    f"{oil_gallons_total + propane_gallons_total:,.0f}"
                ],
                'Emission Factor': [
                    f"{OIL_EMISSION_FACTOR} tCO2e/gal",
                    f"{PROPANE_EMISSION_FACTOR} tCO2e/gal",
                    '—'
                ],
                'Total mtCO2e (2019)': [
                    f"{oil_mtco2e:,.1f}",
                    f"{propane_mtco2e:,.1f}",
                    f"{oil_mtco2e + propane_mtco2e:,.1f}"
                ]
            })

            st.dataframe(fuel_breakdown, hide_index=True, use_container_width=True)

            # Add verification note
            st.success(f"""
            ✓ **Verification - 2019 Baseline Totals:**
            - Oil: {oil_mtco2e:,.1f} mtCO2e (expected: ~5,402.4 mtCO2e)
            - Propane: {propane_mtco2e:,.1f} mtCO2e (expected: ~2,106.3 mtCO2e)
            - **Total: {oil_mtco2e + propane_mtco2e:,.1f} mtCO2e (expected: ~7,508.7 mtCO2e)**
            """)

            st.markdown("""
            **Note about Heat Pump Displacement:**
            - The propane displacement tracking (shown in the charts above) assumes that the 801 properties converting to heat pumps are **year-round homes** (100% heating factor)
            - This is a subset of the total 821 propane properties shown in this table
            - The remaining 20 propane properties are assumed to be seasonal or commercial and not part of the heat pump conversion program
            """)

    st.warning("""
    **Important Notes:**
    - Occupancy percentages (67.1% seasonal, 32.9% year-round) come from CLC census data
    - Tracked propane assumes 100% year-round occupancy because CLC-funded heat pump installations are primarily in year-round homes
    - Uses median square footage rather than actual building sizes for each property
    - Does not account for varying insulation levels, thermostat settings, or other efficiency factors
    """)

    st.info("""
    💡 **Future Improvements:**
    - Cross-reference CLC installations with assessors data to verify actual occupancy patterns
    - Track oil heating displacement separately if oil-to-heat-pump conversions increase
    - Obtain actual fuel delivery data if suppliers are willing to share aggregated information
    - Use actual square footage for each converted property instead of median
    - Update seasonal/year-round percentages with newer occupancy data
    """)

else:
    st.error("Unable to load required data. Please check that all data files are available.")
