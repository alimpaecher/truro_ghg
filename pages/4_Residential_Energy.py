import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_assessors_data, calculate_residential_emissions, load_mass_save_data, calculate_propane_displacement

st.title("Truro Residential & Commercial Energy")

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

    Unlike electricity, there's no centralized reporting for propane (and oil) consumption in Truro.
    Homes buy propane from various suppliers, and there's no municipal aggregation of this data.

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
        st.markdown("**Heating Fuel Distribution:**")
        fuel_counts = df_with_sqft['FUEL'].value_counts().reset_index()
        fuel_counts.columns = ['Fuel Type', 'Number of Properties']
        st.dataframe(fuel_counts, hide_index=True, use_container_width=True)

    st.subheader("Step 2: Estimate Fuel Consumption")

    st.markdown("""
    For each property, we estimate annual fuel consumption based on:
    1. **Square footage** (larger homes use more fuel)
    2. **Fuel consumption benchmarks** (gallons per square foot per year)
    3. **Seasonal adjustment** (seasonal homes use less heating)
    """)

    # Consumption benchmarks
    consumption_benchmarks = pd.DataFrame({
        'Fuel Type': ['Heating Oil', 'Propane', 'Electric Resistance', 'Heat Pumps'],
        'Consumption Rate': ['0.40 gal/sq ft/year', '0.39 gal/sq ft/year', '~12 kWh/sq ft/year ⚠️', '~4 kWh/sq ft/year ⚠️'],
        'Source': ['Mass.gov', 'Mass.gov', 'Estimate', 'Estimate (COP ~3.0)']
    })

    st.table(consumption_benchmarks)

    st.warning("""
    ⚠️ **Important**: Oil and propane benchmarks come from [Mass.gov](https://www.mass.gov/info-details/household-heating-costs),
    but electric heating rates are rough estimates that should be validated with local energy assessors.
    """)

    st.subheader("Step 3: Seasonal Adjustment")

    st.markdown("""
    Truro has a high percentage of seasonal properties. These properties are either vacant or heated at minimal levels
    during winter, so they use much less fuel than year-round homes.

    Based on CLC census data:
    """)

    seasonal_breakdown = pd.DataFrame({
        'Property Type': ['Seasonal/Vacant', 'Year-Round Occupied'],
        '% of Residential': ['67.1%', '32.9%'],
        'Heating Usage': ['30% of full heating', '100% of full heating'],
        'Rationale': ['Heat at maintenance level or off', 'Full heating all winter']
    })

    st.table(seasonal_breakdown)

    st.markdown("""
    **Weighted Average for Residential Properties:**
    - (67.1% × 30%) + (32.9% × 100%) = **53% of theoretical full-year heating**

    This means our calculations assume the average residential property uses about half the fuel of a year-round occupied home.
    """)

    st.subheader("Step 4: Convert to Emissions")

    st.markdown("""
    Finally, we convert fuel consumption to emissions using emission factors from `emission_factors.csv`:
    """)

    fuel_emissions = pd.DataFrame({
        'Fuel Type': ['Heating Oil', 'Propane', 'Electricity'],
        'Emission Factor': ['0.01030 tCO2e/gal', '0.00574 tCO2e/gal', '0.000239 tCO2e/kWh'],
        'Source': ['Diesel oil factor', 'Propane factor', 'NPCC New England grid']
    })

    st.table(fuel_emissions)

    st.markdown("""
    **Complete Calculation Example (Year-Round Propane Home):**
    1. Property size: 2,000 sq ft
    2. Consumption: 2,000 × 0.39 gal/sq ft × 1.00 (year-round) = 780 gallons/year
    3. Emissions: 780 gal × 0.00574 tCO2e/gal = **4.5 mtCO2e/year**
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

    We make several assumptions to estimate how much propane consumption has decreased:
    """)

    assumptions = pd.DataFrame({
        'Assumption': [
            'Heat pumps replace propane',
            'CLC installations are year-round homes',
            'Representative property size',
            'Conversion timing'
        ],
        'What We Assume': [
            'Heat pumps replaced propane systems (not oil or electric)',
            'All CLC-funded installations are in year-round occupied homes',
            f"Use median square footage: {propane_metadata['median_sqft']:,.0f} sq ft",
            'Properties converted in the year they appear in CLC data'
        ],
        'Why This Matters': [
            'Propane most common target for conversions in coastal MA',
            'Year-round homes use 100% heating vs 30% for seasonal',
            'Cannot know actual size of each converted property',
            'Gives us year-by-year displacement estimates'
        ]
    })

    st.table(assumptions)

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

    limitations = pd.DataFrame({
        'Area': [
            'Propane Consumption',
            'Electric Heating Rates',
            'Seasonal Properties',
            'Heat Pump Targets',
            '2020 Heat Pump Count',
            'Property Sizes',
            'Net Emissions Impact'
        ],
        'Limitation': [
            'No direct measurement available',
            'kWh/sq ft estimates not validated locally',
            'Cannot identify which specific properties are seasonal',
            'Cannot verify each heat pump replaced propane specifically',
            'Interpolated value (linear assumption)',
            'Using median square footage, actual properties vary',
            'Need to calculate increased electricity vs decreased propane'
        ],
        'How We Address It': [
            'Use Mass.gov benchmarks (0.39 gal/sq ft)',
            'Clearly mark as estimates needing validation',
            'Apply statistical approach (67.1% seasonal × 30% factor)',
            'Assume propane target based on MA coastal patterns',
            'Reasonable given assessors (92) and 2021 CLC (165) data',
            'Best available proxy for typical conversion',
            'Could add in future with detailed heat pump usage analysis'
        ]
    })

    st.dataframe(limitations, hide_index=True, use_container_width=True)

    st.info("""
    💡 **Future Improvements:**
    - Validate electric heating benchmarks with Mass Save actual usage data
    - Refine seasonal property identification (tax records, utility connection data)
    - Calculate net emissions change (propane savings vs electricity increase)
    - Update with newer assessors data when available
    - Track oil heating displacement separately from propane
    """)

else:
    st.error("Unable to load required data. Please check that all data files are available.")
