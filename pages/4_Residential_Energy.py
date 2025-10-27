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
        """)

        st.markdown("### Seasonal Adjustment Methodology")
        st.markdown("Based on CLC census data showing Truro's seasonal nature:")

        # Seasonal breakdown table
        seasonal_data = pd.DataFrame({
            'Property Type': ['Seasonal/Vacant', 'Year-Round Occupied'],
            '% of Properties': ['67.1%', '32.9%'],
            'Heating Usage Factor': ['30%', '100%'],
            'Notes': ['Heat at maintenance level or off', 'Full heating']
        })
        st.table(seasonal_data)

        st.markdown("""
        **Property Category Adjustments:**
        """)

        # Property category table
        category_data = pd.DataFrame({
            'Category': ['Residential', 'Motels/Resorts', 'Commercial'],
            'Heating Factor': ['53% (weighted avg)', '30% (100% seasonal)', '65% (estimated)'],
            'Notes': ['Statistical split', 'Closed in winter', 'Needs refinement']
        })
        st.table(category_data)

        st.markdown("""
        **Calculation Example for Residential:**
        - Seasonal adjustment factor = (0.671 × 0.30) + (0.329 × 1.00) = **0.530** or 53% of theoretical full-year heating
        """)

        st.markdown("### Fuel Consumption Benchmarks")

        # Fuel consumption table
        fuel_consumption_data = pd.DataFrame({
            'Fuel Type': ['Heating Oil', 'Propane (GAS)', 'Electric Resistance', 'Heat Pumps'],
            'Consumption Rate': ['0.40 gal/sq ft/year', '0.39 gal/sq ft/year', '~12 kWh/sq ft/year', '~4 kWh/sq ft/year'],
            'Source': ['Mass.gov', 'Mass.gov', '⚠️ ESTIMATE', '⚠️ ESTIMATE'],
            'Notes': [
                'Based on MA average',
                'Truro has no natural gas',
                'Needs validation',
                'Assumes COP ~3.0'
            ]
        })
        st.table(fuel_consumption_data)

        st.markdown("""
        Source: [Mass.gov Household Heating Costs](https://www.mass.gov/info-details/household-heating-costs)

        ⚠️ **Electric heating benchmarks are rough estimates and need verification with local data**
        """)

        st.markdown("### Emission Factors")
        st.markdown("All emission factors sourced from `emission_factors.csv`:")

        # Emission factors table
        emission_factors_data = pd.DataFrame({
            'Fuel Type': ['Heating Oil', 'Propane', 'Electricity'],
            'Emission Factor': ['0.01030 tCO2e/gal', '0.00574 tCO2e/gal', '0.000239 tCO2e/kWh'],
            'Source Row': ['Row 8 (Diesel oil)', 'Row 5 (Propane)', 'Row 9 (NPCC New England)'],
            'Original Units': ['kg CO2e/gal', 'kg CO2e/gal', '239 kg CO2e/MWh']
        })
        st.table(emission_factors_data)

        st.markdown("""
        ### Calculation Formula
        For each property:
        ```
        Fuel Consumption = Square Footage × Fuel Rate (gal or kWh per sq ft) × Seasonal Adjustment Factor
        Emissions (mtCO2e) = Fuel Consumption × Emission Factor
        ```
        """)

        st.markdown("### Key Limitations & Uncertainties")
        st.markdown("⚠️ **Important Caveats:**")

        # Limitations table
        limitations_data = pd.DataFrame({
            'Limitation': [
                'Statistical Approach',
                'Electric Heating Benchmarks',
                '2019 Data',
                'Actual Usage Varies',
                'Commercial Factors'
            ],
            'Description': [
                'Don\'t know which specific properties are seasonal',
                'kWh/sq ft estimates need validation with local data',
                'May not reflect recent renovations or fuel switching',
                'Depends on insulation, thermostats, behavior, weather, etc.',
                'Simplified adjustments - could be refined with business data'
            ]
        })
        st.table(limitations_data)

        st.markdown("""
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
