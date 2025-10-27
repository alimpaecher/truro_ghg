import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_assessors_data, calculate_residential_emissions

st.title("Truro Residential & Commercial Energy")

# Load the data
df = load_assessors_data()

if df is not None:
    st.success(f"Successfully loaded {len(df)} property records")

    # Filter out records with no NetSF data
    df_with_sqft = df[df['NetSF'].notna() & (df['NetSF'] > 0)].copy()

    st.write(f"Properties with square footage data: {len(df_with_sqft):,}")

    # Total Square Footage by HVAC Type
    st.subheader("Total Square Footage by HVAC Type")

    hvac_sqft = df_with_sqft.groupby('HVAC')['NetSF'].sum().sort_values(ascending=False).reset_index()
    hvac_sqft.columns = ['HVAC', 'Total Square Feet']

    fig_hvac = go.Figure(data=[go.Bar(
        x=hvac_sqft['HVAC'],
        y=hvac_sqft['Total Square Feet'],
        marker=dict(color='#06A77D')
    )])

    fig_hvac.update_layout(
        xaxis_title="HVAC Type",
        yaxis_title="Total Square Feet",
        height=500,
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig_hvac, use_container_width=True)

    # Total Square Footage by FUEL Type
    st.subheader("Total Square Footage by Fuel Type")

    fuel_sqft = df_with_sqft.groupby('FUEL')['NetSF'].sum().sort_values(ascending=False).reset_index()
    fuel_sqft.columns = ['FUEL', 'Total Square Feet']

    fig_fuel = go.Figure(data=[go.Bar(
        x=fuel_sqft['FUEL'],
        y=fuel_sqft['Total Square Feet'],
        marker=dict(color='#D45113')
    )])

    fig_fuel.update_layout(
        xaxis_title="Fuel Type",
        yaxis_title="Total Square Feet",
        height=500,
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig_fuel, use_container_width=True)

    # Combined HVAC and FUEL matrix
    st.subheader("Square Footage by HVAC and Fuel Type (Heatmap)")

    # Create pivot table
    pivot = df_with_sqft.pivot_table(
        values='NetSF',
        index='HVAC',
        columns='FUEL',
        aggfunc='sum',
        fill_value=0
    )

    # Sort by total square footage
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale='YlOrRd',
        text=pivot.values.astype(int),
        texttemplate='%{text:,}',
        textfont={"size": 10},
        hoverongaps=False
    ))

    fig_heatmap.update_layout(
        xaxis_title="Fuel Type",
        yaxis_title="HVAC Type",
        height=700
    )

    st.plotly_chart(fig_heatmap, use_container_width=True)

    # Summary statistics
    st.subheader("Summary Statistics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Properties", f"{len(df):,}")
        st.metric("Properties with Sq Ft Data", f"{len(df_with_sqft):,}")

    with col2:
        st.metric("Total Square Footage", f"{df_with_sqft['NetSF'].sum():,.0f}")
        st.metric("Average Property Size", f"{df_with_sqft['NetSF'].mean():,.0f} sq ft")

    with col3:
        most_common_hvac = df_with_sqft['HVAC'].mode()[0] if len(df_with_sqft['HVAC'].mode()) > 0 else "N/A"
        most_common_fuel = df_with_sqft['FUEL'].mode()[0] if len(df_with_sqft['FUEL'].mode()) > 0 else "N/A"
        st.metric("Most Common HVAC", most_common_hvac)
        st.metric("Most Common Fuel", most_common_fuel)

    # Data tables
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("HVAC Breakdown")
        hvac_counts = df_with_sqft['HVAC'].value_counts().reset_index()
        hvac_counts.columns = ['HVAC Type', 'Count']
        st.dataframe(hvac_counts, hide_index=True)

    with col2:
        st.subheader("Fuel Breakdown")
        fuel_counts = df_with_sqft['FUEL'].value_counts().reset_index()
        fuel_counts.columns = ['Fuel Type', 'Count']
        st.dataframe(fuel_counts, hide_index=True)

    # Divider before emissions section
    st.divider()

    # ESTIMATED EMISSIONS SECTION
    st.header("Estimated Community-Wide Emissions")

    # Methodology and Assumptions (prominently displayed)
    with st.expander("📋 **Methodology & Assumptions** (Click to expand)", expanded=False):
        st.markdown("""
        ### Data Source
        - **Source**: Truro Assessors Database (2019 tax year data)
        - **Properties Analyzed**: Residential and commercial properties (PropertyType = 'R')
        - **Exclusions**: Municipal/exempt properties (PropertyType = 'E') are excluded as they are tracked separately in the Municipal Energy page

        ### Seasonal Adjustment Methodology
        Based on CLC census data showing Truro's seasonal nature:

        - **67.1%** of properties are classified as seasonal/vacant
        - **32.9%** of properties are year-round occupied

        **Heating Usage Assumptions:**
        - **Seasonal properties**: Use 30% of year-round heating (heat kept at maintenance level ~50-55°F or turned off)
        - **Year-round properties**: Use 100% heating
        - **Motels/Resorts**: Assumed 100% seasonal (closed in winter)
        - **Commercial properties**: Average adjustment of 65% (rough estimate - needs refinement)

        **Calculation Example for Residential:**
        - Seasonal adjustment factor = (0.671 × 0.30) + (0.329 × 1.00) = **0.530** or 53% of theoretical full-year heating

        ### Fuel Consumption Benchmarks

        **Heating Oil:**
        - **0.40 gallons per square foot per year**
        - Source: [Mass.gov Household Heating Costs](https://www.mass.gov/info-details/household-heating-costs)
        - Based on average MA household consumption

        **Propane (reported as "GAS" in data):**
        - **0.39 gallons per square foot per year**
        - Source: [Mass.gov Household Heating Costs](https://www.mass.gov/info-details/household-heating-costs)
        - Note: Truro has no natural gas service; "GAS" refers to propane

        **Electric Resistance Heating:**
        - **~12 kWh per square foot per year** ⚠️ **ESTIMATED - AUTHORITATIVE SOURCE NEEDED**
        - This is a rough estimate based on typical MA electric resistance heating
        - Actual usage varies significantly based on insulation, thermostat settings, and climate

        **Heat Pumps:**
        - **~4 kWh per square foot per year** ⚠️ **ESTIMATED - AUTHORITATIVE SOURCE NEEDED**
        - Assumes heat pump COP (Coefficient of Performance) of ~3.0
        - Estimated as 1/3 of electric resistance consumption
        - Actual performance varies with outdoor temperature

        ### Emission Factors
        All emission factors sourced from `emission_factors.csv`:

        - **Heating Oil**: 0.01030 tCO2e per gallon (Diesel oil, row 8)
        - **Propane**: 0.00574 tCO2e per gallon (Propane, row 5)
        - **Electricity**: 0.000239 tCO2e per kWh (NPCC New England grid, row 9: 239 kg CO2e/MWh)

        ### Key Limitations & Uncertainties

        ⚠️ **Important Caveats:**

        1. **Statistical Approach**: We don't know which specific properties are seasonal, so we apply statistical averages
        2. **Electric Heating Benchmarks**: The kWh/sq ft estimates for electric resistance and heat pumps are rough approximations and should be validated with local data
        3. **2019 Data**: Property characteristics are from 2019 and may not reflect recent changes (renovations, fuel switching, etc.)
        4. **Actual Usage Varies**: Individual heating consumption depends on:
           - Building insulation quality
           - Thermostat settings
           - Occupant behavior
           - Weather patterns
           - Building orientation and solar gain
        5. **Commercial Factors**: Commercial property adjustments are simplified and could be refined with business-specific data

        ### Calculation Formula
        For each property:
        ```
        Fuel Consumption = Square Footage × Fuel Rate (gal or kWh per sq ft) × Seasonal Adjustment Factor
        Emissions (mtCO2e) = Fuel Consumption × Emission Factor
        ```

        ### Recommendations for Improvement
        - Obtain actual utility billing data if possible
        - Validate electric heating benchmarks with local energy assessors
        - Refine commercial property heating factors with business-specific data
        - Consider updating with more recent assessors data
        """)

    # Calculate emissions
    df_emissions = calculate_residential_emissions(df)

    # Display totals
    st.subheader("Total Estimated Emissions")

    total_emissions = df_emissions['mtco2e'].sum()
    residential_emissions = df_emissions[df_emissions['is_residential']]['mtco2e'].sum()
    commercial_emissions = df_emissions[df_emissions['is_commercial']]['mtco2e'].sum()
    motel_emissions = df_emissions[df_emissions['is_motel_resort']]['mtco2e'].sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Emissions", f"{total_emissions:,.0f} mtCO2e")
    with col2:
        st.metric("Residential", f"{residential_emissions:,.0f} mtCO2e")
    with col3:
        st.metric("Commercial", f"{commercial_emissions:,.0f} mtCO2e")
    with col4:
        st.metric("Motels/Resorts", f"{motel_emissions:,.0f} mtCO2e")

    # Emissions by fuel type
    st.subheader("Emissions by Fuel Type")

    fuel_emissions = df_emissions.groupby('FUEL')['mtco2e'].sum().sort_values(ascending=False).reset_index()
    fuel_emissions.columns = ['Fuel Type', 'mtCO2e']

    fig_fuel_emissions = go.Figure(data=[go.Bar(
        x=fuel_emissions['Fuel Type'],
        y=fuel_emissions['mtCO2e'],
        marker=dict(color='#D45113')
    )])

    fig_fuel_emissions.update_layout(
        xaxis_title="Fuel Type",
        yaxis_title="mtCO2e",
        height=400
    )

    st.plotly_chart(fig_fuel_emissions, use_container_width=True)

    # Breakdown table
    st.subheader("Emissions Breakdown")

    breakdown_data = {
        'Category': ['Residential', 'Commercial', 'Motels/Resorts', '**Total**'],
        'Properties': [
            int(df_emissions['is_residential'].sum()),
            int(df_emissions['is_commercial'].sum()),
            int(df_emissions['is_motel_resort'].sum()),
            int(len(df_emissions))
        ],
        'Square Footage': [
            f"{df_emissions[df_emissions['is_residential']]['NetSF'].sum():,.0f}",
            f"{df_emissions[df_emissions['is_commercial']]['NetSF'].sum():,.0f}",
            f"{df_emissions[df_emissions['is_motel_resort']]['NetSF'].sum():,.0f}",
            f"**{df_emissions['NetSF'].sum():,.0f}**"
        ],
        'Emissions (mtCO2e)': [
            f"{residential_emissions:,.0f}",
            f"{commercial_emissions:,.0f}",
            f"{motel_emissions:,.0f}",
            f"**{total_emissions:,.0f}**"
        ]
    }

    st.dataframe(pd.DataFrame(breakdown_data), hide_index=True)

    # Comparison note
    st.info("""
    💡 **Context**: These are *estimated* residential and commercial heating emissions for all of Truro,
    based on assessors data and statistical modeling. Compare this to:
    - **Municipal Buildings** emissions shown on the Municipal Energy page (~600-700 mtCO2e)
    - **Municipal Vehicles** emissions shown on the Vehicles page (~300-400 tCO2e)

    This residential/commercial estimate represents heating for ~3,000 properties vs. the handful of municipal buildings and vehicles.
    """)
