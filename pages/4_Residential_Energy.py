import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_assessors_data, calculate_residential_emissions, load_mass_save_data, calculate_propane_displacement

st.title("Truro Residential & Commercial Energy")

# OVERVIEW CHART: Energy Trends 2019-2023
st.header("Energy Trends Overview (2019-2023)")

# Load all data sources
mass_save_data = load_mass_save_data()
propane_data_tuple = calculate_propane_displacement()

if mass_save_data is not None and propane_data_tuple is not None:
    propane_results, propane_metadata = propane_data_tuple

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

    st.info("""
    📊 **Reading this chart:**
    - **Fossil Fuel Heating (Propane)**: Shows declining propane emissions as properties convert to heat pumps (left y-axis, mtCO2e)
    - **Residential Energy Use**: Electricity consumption in residential properties, includes heat pumps (right y-axis, MWh)
    - **Commercial Energy Use**: Electricity consumption in commercial properties (right y-axis, MWh)

    Note: The 2020 propane value is interpolated. Electricity data from Mass Save; propane from assessors + CLC heat pump tracking.
    """)

    st.divider()

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

    # ACTUAL ENERGY USAGE DATA FROM MASS SAVE
    st.divider()
    st.header("Actual Energy Usage Data (Mass Save)")

    mass_save_df = load_mass_save_data()

    if mass_save_df is not None:
        st.markdown("""
        This section shows **actual electricity consumption data** from Mass Save's Geographic Report,
        which provides real utility billing data aggregated by municipality and sector.

        **Key Advantage**: Unlike the estimates above based on square footage and assumptions,
        this data represents actual measured electricity consumption in Truro.
        """)

        # Filter to get residential and commercial sectors
        residential_data = mass_save_df[mass_save_df['Sector'] == 'Residential & Low-Income']
        commercial_data = mass_save_df[mass_save_df['Sector'] == 'Commercial & Industrial']

        # Display latest year metrics
        latest_year = mass_save_df['Year'].max()
        latest_res = residential_data[residential_data['Year'] == latest_year].iloc[0]
        latest_com = commercial_data[commercial_data['Year'] == latest_year].iloc[0]

        st.subheader(f"Year {latest_year} Actual Electricity Usage")

        col1, col2, col3 = st.columns(3)
        with col1:
            res_mwh = latest_res['Electric_MWh']
            st.metric("Residential & Low-Income", f"{res_mwh:,.0f} MWh")
        with col2:
            com_mwh = latest_com['Electric_MWh']
            st.metric("Commercial & Industrial", f"{com_mwh:,.0f} MWh")
        with col3:
            total_mwh = res_mwh + com_mwh
            st.metric("Total", f"{total_mwh:,.0f} MWh")

        # Calculate emissions from electricity
        ELECTRIC_EMISSION_FACTOR = 0.000239  # tCO2e per kWh
        res_emissions = res_mwh * 1000 * ELECTRIC_EMISSION_FACTOR
        com_emissions = com_mwh * 1000 * ELECTRIC_EMISSION_FACTOR
        total_electric_emissions = res_emissions + com_emissions

        st.subheader(f"Estimated Emissions from Electricity ({latest_year})")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Residential", f"{res_emissions:,.1f} mtCO2e")
        with col2:
            st.metric("Commercial", f"{com_emissions:,.1f} mtCO2e")
        with col3:
            st.metric("Total", f"{total_electric_emissions:,.1f} mtCO2e")

        # Trend over time
        st.subheader("Electricity Usage Trend Over Time")

        # Sort by year for proper line chart
        residential_data_sorted = residential_data.sort_values('Year')
        commercial_data_sorted = commercial_data.sort_values('Year')

        fig_mass_save = go.Figure()

        fig_mass_save.add_trace(go.Scatter(
            x=residential_data_sorted['Year'],
            y=residential_data_sorted['Electric_MWh'],
            name='Residential & Low-Income',
            mode='lines+markers',
            line=dict(width=3),
            marker=dict(size=8)
        ))

        fig_mass_save.add_trace(go.Scatter(
            x=commercial_data_sorted['Year'],
            y=commercial_data_sorted['Electric_MWh'],
            name='Commercial & Industrial',
            mode='lines+markers',
            line=dict(width=3),
            marker=dict(size=8)
        ))

        fig_mass_save.update_layout(
            xaxis_title="Year",
            yaxis_title="Electricity Usage (MWh)",
            hovermode='x unified',
            height=500
        )

        st.plotly_chart(fig_mass_save, use_container_width=True)

        # Data table
        st.subheader("Electricity Usage by Year")

        # Pivot data for table display
        table_data = []
        for year in sorted(mass_save_df['Year'].unique()):
            year_data = mass_save_df[mass_save_df['Year'] == year]
            res_row = year_data[year_data['Sector'] == 'Residential & Low-Income'].iloc[0]
            com_row = year_data[year_data['Sector'] == 'Commercial & Industrial'].iloc[0]

            table_data.append({
                'Year': int(year),
                'Residential (MWh)': f"{res_row['Electric_MWh']:,.0f}",
                'Commercial (MWh)': f"{com_row['Electric_MWh']:,.0f}",
                'Total (MWh)': f"{res_row['Electric_MWh'] + com_row['Electric_MWh']:,.0f}",
                'Total Emissions (mtCO2e)': f"{(res_row['Electric_MWh'] + com_row['Electric_MWh']) * 1000 * ELECTRIC_EMISSION_FACTOR:,.1f}"
            })

        st.dataframe(pd.DataFrame(table_data), hide_index=True)

        st.warning("""
        ⚠️ **Important Notes:**
        - This data shows **electricity usage only** (not oil, propane, or other fuels)
        - Includes all electricity uses: heating, cooling, lighting, appliances, etc.
        - Does not distinguish between electric resistance heating and heat pumps
        - Mass Save data aggregates all residential/commercial properties, so we cannot break down by seasonal vs. year-round
        - Use this data to validate or refine the electric heating estimates in the assessor-based calculations above
        """)

        # Comparison insight
        st.info("""
        💡 **Validation Opportunity**: Compare the actual electricity usage here with the electric heating
        estimates in the assessor-based calculations above. Large discrepancies suggest the electric heating
        benchmarks (~12 kWh/sq ft for resistance, ~4 kWh/sq ft for heat pumps) may need adjustment.
        """)

    # PROPANE DISPLACEMENT BY HEAT PUMPS
    st.divider()
    st.header("Propane Displacement by Heat Pumps (2019-2023)")

    propane_results = calculate_propane_displacement()

    if propane_results is not None:
        results_df, metadata = propane_results

        st.markdown("""
        This section estimates the reduction in propane consumption as residential properties
        convert from propane heating to heat pumps. The baseline comes from the 2019 Assessors Database
        showing 92 heat pump installations, with subsequent growth tracked through Cape Light Compact data.
        """)

        # Methodology expander
        with st.expander("📋 **Methodology & Assumptions** (Click to expand)", expanded=False):
            st.markdown("""
            ### Key Assumptions
            """)

            # Assumptions table
            assumptions_data = pd.DataFrame({
                'Assumption': [
                    'Heat Pump Target',
                    'Property Type',
                    'Heating Factor',
                    'Square Footage',
                    'Baseline Year'
                ],
                'Value': [
                    'Propane heating systems',
                    'Year-round residential only',
                    '100% (full heating)',
                    f"{metadata['median_sqft']:,.0f} sq ft (median)",
                    f"{metadata['baseline_year']} (Assessors data)"
                ],
                'Rationale': [
                    'Propane most likely to be replaced; oil/electric less common for CLC conversions',
                    'CLC-funded conversions assumed to be year-round homes',
                    'Year-round properties heat at 100% vs. seasonal at 30%',
                    'Median chosen as representative of typical property',
                    'Most recent assessors data available'
                ]
            })
            st.table(assumptions_data)

            st.markdown("""
            ### Data Sources & Timeline
            """)

            # Data sources table
            data_sources = pd.DataFrame({
                'Year': ['2019', '2020', '2021-2023'],
                'Source': [
                    'Assessors Database',
                    'Interpolated (linear)',
                    'Cape Light Compact'
                ],
                'Heat Pump Count': [
                    f"{metadata['baseline_heat_pumps']} (actual)",
                    f"{metadata['interpolated_2020']} (estimated)",
                    'Actual CLC data'
                ],
                'Notes': [
                    'Baseline from property records',
                    'Assumed linear growth 2019→2021',
                    'Tracked installations'
                ]
            })
            st.table(data_sources)

            st.markdown("""
            ### Baseline Data
            """)

            # Baseline metrics table
            baseline_data = pd.DataFrame({
                'Metric': [
                    'Total Year-Round Residential Propane Properties',
                    'Median Property Size',
                    'Propane Consumption per Property',
                    'Baseline Total Propane Consumption',
                    'Baseline Total Emissions'
                ],
                'Value': [
                    f"{metadata['baseline_propane_properties']:,} properties",
                    f"{metadata['median_sqft']:,.0f} sq ft",
                    f"{metadata['propane_per_property_gal']:,.0f} gallons/year",
                    f"{metadata['baseline_propane_gal']:,.0f} gallons/year",
                    f"{metadata['baseline_propane_mtco2e']:,.1f} mtCO2e/year"
                ]
            })
            st.table(baseline_data)

            st.markdown("""
            ### Calculation Method

            **For each year (2019-2023):**
            1. Track cumulative heat pump installations (assessors 2019 baseline, interpolated 2020, CLC 2021-2023)
            2. Calculate conversions from 2019 baseline: `Conversions = Current_Locations - 92`
            3. Calculate remaining propane properties: `Remaining = Total_Propane_Properties - Conversions`
            4. Calculate remaining propane usage: `Remaining_Usage = Remaining_Properties × Propane_per_Property`
            5. Calculate propane saved: `Saved = Conversions × Propane_per_Property`

            **Exclusions from baseline propane properties:**
            - Motels, resorts, inns (100% seasonal, not typical CLC conversion targets)
            - Commercial properties (restaurants, retail, etc.)
            """)

            st.markdown("""
            ### Key Limitations
            """)

            # Limitations table
            limitations_data = pd.DataFrame({
                'Limitation': [
                    '2020 Interpolation',
                    'Direct Attribution',
                    'Median Square Footage',
                    'Electric Increase Not Tracked',
                    'Other Fuel Switching'
                ],
                'Description': [
                    '2020 value is linearly interpolated between 2019 assessors (92) and 2021 CLC (165) data',
                    'Cannot verify that all CLC heat pumps replaced propane specifically',
                    'Individual properties vary; some larger/smaller than median',
                    'Heat pumps increase electricity usage, but Mass Save data already captures this',
                    'Some propane properties may have switched to other fuels not related to heat pumps'
                ]
            })
            st.table(limitations_data)

        # Display baseline metrics at top
        st.subheader(f"Baseline Propane Usage ({metadata['baseline_year']})")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Propane Properties", f"{metadata['baseline_propane_properties']:,}")
        with col2:
            st.metric("Median Size", f"{metadata['median_sqft']:,.0f} sq ft")
        with col3:
            st.metric("Total Usage", f"{metadata['baseline_propane_gal']:,.0f} gal/year")
        with col4:
            st.metric("Total Emissions", f"{metadata['baseline_propane_mtco2e']:,.1f} mtCO2e")

        # Year-by-year results
        st.subheader("Propane Reduction Over Time")

        # Chart showing propane emissions decline
        fig_propane = go.Figure()

        fig_propane.add_trace(go.Scatter(
            x=results_df['Year'],
            y=results_df['Remaining_Propane_mtCO2e'],
            name='Remaining Propane Emissions',
            mode='lines+markers',
            line=dict(width=3, color='#D45113'),
            marker=dict(size=10),
            fill='tozeroy',
            fillcolor='rgba(212, 81, 19, 0.2)'
        ))

        fig_propane.add_trace(go.Scatter(
            x=results_df['Year'],
            y=results_df['Propane_Saved_mtCO2e'],
            name='Propane Emissions Saved',
            mode='lines+markers',
            line=dict(width=3, color='#06A77D'),
            marker=dict(size=10)
        ))

        fig_propane.update_layout(
            xaxis_title="Year",
            yaxis_title="Emissions (mtCO2e)",
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

        st.plotly_chart(fig_propane, use_container_width=True)

        # Display detailed year-by-year table
        st.subheader("Year-by-Year Conversion Details")

        # Format table data
        table_display = results_df.copy()
        table_display['Heat_Pump_Locations'] = table_display['Heat_Pump_Locations'].astype(int)
        table_display['Cumulative_Conversions'] = table_display['Cumulative_Conversions'].astype(int)
        table_display['Remaining_Propane_Properties'] = table_display['Remaining_Propane_Properties'].astype(int)
        table_display['Remaining_Propane_Gal'] = table_display['Remaining_Propane_Gal'].apply(lambda x: f"{x:,.0f}")
        table_display['Remaining_Propane_mtCO2e'] = table_display['Remaining_Propane_mtCO2e'].apply(lambda x: f"{x:,.1f}")
        table_display['Propane_Saved_Gal'] = table_display['Propane_Saved_Gal'].apply(lambda x: f"{x:,.0f}")
        table_display['Propane_Saved_mtCO2e'] = table_display['Propane_Saved_mtCO2e'].apply(lambda x: f"{x:,.1f}")
        table_display['Percent_Reduction'] = table_display['Percent_Reduction'].apply(lambda x: f"{x:.1f}%")

        # Rename columns for display
        table_display.columns = [
            'Year',
            'Heat Pump Locations',
            'Cumulative Conversions',
            'Remaining Propane Properties',
            'Remaining Propane (gal/yr)',
            'Remaining Emissions (mtCO2e)',
            'Propane Saved (gal/yr)',
            'Emissions Saved (mtCO2e)',
            '% Reduction from Baseline'
        ]

        st.dataframe(table_display, hide_index=True)

        # Key insights
        latest_year = results_df.iloc[-1]

        st.success(f"""
        📊 **Summary for {int(latest_year['Year'])}**:
        - **{int(latest_year['Cumulative_Conversions'])} properties** have converted from propane to heat pumps
        - **{latest_year['Propane_Saved_mtCO2e']:.1f} mtCO2e** in propane emissions eliminated annually
        - This represents a **{latest_year['Percent_Reduction']:.1f}% reduction** from the {metadata['baseline_year']} baseline
        """)

        st.info("""
        💡 **Context**: While propane emissions have decreased, the Mass Save data above shows that
        electricity consumption has increased over this period. Heat pumps use electricity but are
        approximately 3x more efficient than electric resistance heating, so the net emissions impact
        depends on the electricity grid's carbon intensity (0.000239 tCO2e/kWh in our calculations).

        To calculate the net emissions change, you would need to:
        1. Estimate heat pump electricity consumption: ~4 kWh/sq ft × median sq ft × conversions
        2. Multiply by electricity emission factor: 0.000239 tCO2e/kWh
        3. Compare to propane emissions saved

        This analysis could be added in future iterations with more detailed heat pump usage data.
        """)

    else:
        st.error("Unable to load propane displacement data. Please check that assessors and heat pump data files are available.")
