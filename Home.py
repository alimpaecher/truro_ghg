import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from home_calculations import prepare_home_dashboard_data
from data_loader import calculate_total_fossil_fuel_heating

# Page configuration
st.set_page_config(
    page_title="Town of Truro GHG Dashboard",
    page_icon="🌍",
    layout="wide"
)

st.title("Town of Truro GHG Emissions Dashboard")

# Load and prepare all data using the calculation module
try:
    combined_df, metadata = prepare_home_dashboard_data()

    # Also load fossil fuel results for the narrative section
    fossil_fuel_data_tuple = calculate_total_fossil_fuel_heating()
    fossil_fuel_results, fossil_fuel_metadata = fossil_fuel_data_tuple

    st.success("Successfully loaded data from all sources")

    # Display current year metrics
    most_recent_year = combined_df['year'].max()
    current_year = combined_df[combined_df['year'] == most_recent_year].iloc[0]
    previous_year = combined_df[combined_df['year'] == most_recent_year - 1].iloc[0]

    st.subheader(f"Year {int(most_recent_year)} Totals")
    col1, col2, col3 = st.columns(3)

    with col1:
        delta_vehicles = current_year['vehicles_tco2e'] - previous_year['vehicles_tco2e']
        st.metric(
            label="Vehicles tCO2e",
            value=f"{current_year['vehicles_tco2e']:.2f}",
            delta=f"{delta_vehicles:.2f}"
        )

    with col2:
        delta_buildings = current_year['municipal_buildings_mtco2e'] - previous_year['municipal_buildings_mtco2e']
        st.metric(
            label="Municipal Buildings mtCO2e",
            value=f"{current_year['municipal_buildings_mtco2e']:.2f}",
            delta=f"{delta_buildings:.2f}"
        )

    with col3:
        delta_total = current_year['total_tco2e'] - previous_year['total_tco2e']
        st.metric(
            label="Total tCO2e",
            value=f"{current_year['total_tco2e']:.2f}",
            delta=f"{delta_total:.2f}"
        )

    # Create combined emissions chart
    st.subheader("Total Emissions Over Time")

    # Add filters for the chart
    all_categories = [
        'Residential Fossil Fuel Heating',
        'Residential Electricity',
        'Commercial Electricity',
        'Municipal Buildings (Other Fuels)',
        'Municipal Buildings (Electric)',
        'Vehicles'
    ]
    selected_categories = st.multiselect(
        "Select categories to display:",
        options=all_categories,
        default=all_categories
    )

    if selected_categories:
        # Stacked Area Chart
        st.markdown("#### Stacked Area Chart")
        fig_stacked = go.Figure()

        # Residential Fossil Fuel Heating
        if 'Residential Fossil Fuel Heating' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['residential_fossil_fuel_mtco2e'],
                name='Residential Fossil Fuel Heating',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(212, 81, 19, 0.5)'
            ))

        # Residential Electricity
        if 'Residential Electricity' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['residential_electric_mtco2e'],
                name='Residential Electricity',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(6, 167, 125, 0.5)'
            ))

        # Commercial Electricity
        if 'Commercial Electricity' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['commercial_electric_mtco2e'],
                name='Commercial Electricity',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(30, 136, 229, 0.5)'
            ))

        # Municipal Buildings - Other Fuels
        if 'Municipal Buildings (Other Fuels)' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['other_fuels_mtco2e'],
                name='Municipal Buildings (Other Fuels)',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(255, 127, 80, 0.5)'
            ))

        # Municipal Buildings - Electric
        if 'Municipal Buildings (Electric)' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['electric_mtco2e'],
                name='Municipal Buildings (Electric)',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(106, 168, 79, 0.5)'
            ))

        # Vehicles
        if 'Vehicles' in selected_categories:
            fig_stacked.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['vehicles_tco2e'],
                name='Vehicles',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(70, 130, 180, 0.5)'
            ))

        fig_stacked.update_layout(
            xaxis_title="Year",
            yaxis_title="mtCO2e",
            hovermode='x unified',
            height=500
        )

        st.plotly_chart(fig_stacked, use_container_width=True)

        # Line Graph
        st.markdown("#### Line Graph")
        fig_line = go.Figure()

        # Residential Fossil Fuel Heating
        if 'Residential Fossil Fuel Heating' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['residential_fossil_fuel_mtco2e'],
                name='Residential Fossil Fuel Heating',
                mode='lines+markers',
                line=dict(width=3, color='rgb(212, 81, 19)'),
                marker=dict(size=8)
            ))

        # Residential Electricity
        if 'Residential Electricity' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['residential_electric_mtco2e'],
                name='Residential Electricity',
                mode='lines+markers',
                line=dict(width=3, color='rgb(6, 167, 125)'),
                marker=dict(size=8)
            ))

        # Commercial Electricity
        if 'Commercial Electricity' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['commercial_electric_mtco2e'],
                name='Commercial Electricity',
                mode='lines+markers',
                line=dict(width=3, color='rgb(30, 136, 229)'),
                marker=dict(size=8)
            ))

        # Municipal Buildings - Other Fuels
        if 'Municipal Buildings (Other Fuels)' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['other_fuels_mtco2e'],
                name='Municipal Buildings (Other Fuels)',
                mode='lines+markers',
                line=dict(width=3, color='rgb(255, 127, 80)'),
                marker=dict(size=8)
            ))

        # Municipal Buildings - Electric
        if 'Municipal Buildings (Electric)' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['electric_mtco2e'],
                name='Municipal Buildings (Electric)',
                mode='lines+markers',
                line=dict(width=3, color='rgb(106, 168, 79)'),
                marker=dict(size=8)
            ))

        # Vehicles
        if 'Vehicles' in selected_categories:
            fig_line.add_trace(go.Scatter(
                x=combined_df['year'],
                y=combined_df['vehicles_tco2e'],
                name='Vehicles',
                mode='lines+markers',
                line=dict(width=3, color='rgb(70, 130, 180)'),
                marker=dict(size=8)
            ))

        fig_line.update_layout(
            xaxis_title="Year",
            yaxis_title="mtCO2e",
            hovermode='x unified',
            height=500
        )

        st.plotly_chart(fig_line, use_container_width=True)

        # Add warning notes
        st.caption("⚠️ Note: 2024 data for residential fossil fuel heating and residential electricity are estimates based on 2023 values.")
        st.caption("ℹ️ Note: To avoid double counting, Battery Electric vehicle emissions are excluded (assumed charged at home), and Plug-in Hybrid emissions are reduced by 50%. This assumes most EV charging occurs in Truro; charging outside of town would not be captured in residential electricity data. Given current low EV adoption rates, this adjustment has minimal impact on totals.")
    else:
        st.warning("Please select at least one category to display the chart.")

    # Add summary of changes from 2019 to 2023
    st.subheader("2019-2023 Emissions Summary")

    # Get 2019 and 2023 data
    data_2019 = combined_df[combined_df['year'] == 2019].iloc[0]
    data_2023 = combined_df[combined_df['year'] == 2023].iloc[0]

    # Calculate changes
    residential_heating_change = data_2023['residential_fossil_fuel_mtco2e'] - data_2019['residential_fossil_fuel_mtco2e']
    residential_electric_change = data_2023['residential_electric_mtco2e'] - data_2019['residential_electric_mtco2e']
    vehicles_change = data_2023['vehicles_tco2e'] - data_2019['vehicles_tco2e']
    commercial_change = data_2023['commercial_electric_mtco2e'] - data_2019['commercial_electric_mtco2e']
    municipal_fuels_change = data_2023['other_fuels_mtco2e'] - data_2019['other_fuels_mtco2e']
    total_change = data_2023['total_tco2e'] - data_2019['total_tco2e']

    # Show key metrics in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🏠 Residential Heating",
            value=f"{data_2023['residential_fossil_fuel_mtco2e']:.0f} mtCO2e",
            delta=f"{residential_heating_change:.0f} mtCO2e",
            delta_color="inverse"
        )

    with col2:
        st.metric(
            label="⚡ Residential Electric",
            value=f"{data_2023['residential_electric_mtco2e']:.0f} mtCO2e",
            delta=f"{residential_electric_change:.0f} mtCO2e",
            delta_color="inverse"
        )

    with col3:
        st.metric(
            label="🚗 Vehicles",
            value=f"{data_2023['vehicles_tco2e']:.0f} tCO2e",
            delta=f"{vehicles_change:.0f} tCO2e",
            delta_color="inverse"
        )

    with col4:
        st.metric(
            label="📊 Total Emissions",
            value=f"{data_2023['total_tco2e']:.0f} mtCO2e",
            delta=f"{total_change:.0f} mtCO2e",
            delta_color="inverse"
        )

    st.markdown("---")

    # Population growth chart
    st.subheader("Truro Population Growth (2019-2023)")

    pop_2019 = data_2019['Population']
    pop_2023 = data_2023['Population']
    pop_change = pop_2023 - pop_2019
    pop_change_pct = (pop_change / pop_2019) * 100

    fig_population = go.Figure()
    fig_population.add_trace(go.Scatter(
        x=combined_df['year'],
        y=combined_df['Population'],
        mode='lines+markers',
        line=dict(width=3, color='rgb(99, 110, 250)'),
        marker=dict(size=10),
        name='Population'
    ))

    fig_population.update_layout(
        xaxis_title="Year",
        yaxis_title="Population",
        hovermode='x unified',
        height=400,
        showlegend=False
    )

    st.plotly_chart(fig_population, use_container_width=True)

    st.markdown(f"""
    Truro's population grew from **{int(pop_2019):,}** in 2019 to **{int(pop_2023):,}** in 2023,
    an increase of **{int(pop_change):,} residents ({pop_change_pct:.1f}%)**. This significant growth,
    largely driven by increased full-time occupancy during and after COVID, likely contributes to increased
    vehicle registrations and electricity usage.
    """)

    st.markdown("---")

    # Simplified narrative
    col_a, col_b = st.columns(2)

    # Calculate percentages for narrative
    heating_pct = abs((residential_heating_change / data_2019['residential_fossil_fuel_mtco2e']) * 100)
    electric_pct = (residential_electric_change / data_2019['residential_electric_mtco2e']) * 100
    net_residential = residential_heating_change + residential_electric_change

    # Get number of conversions from fossil fuel data
    conversions_2023 = fossil_fuel_results[fossil_fuel_results['year'] == 2023]['cumulative_conversions'].iloc[0]

    with col_a:
        st.markdown("### ✅ Progress: Heat Pump Adoption")
        st.markdown(f"""
        **Residential fossil fuel heating dropped {heating_pct:.1f}%** ({residential_heating_change:.0f} mtCO2e), reflecting the conversion of **{int(conversions_2023)} properties** to heat pumps through the Cape Light Compact program.

        **Residential electricity increased {electric_pct:.1f}%** ({residential_electric_change:+.0f} mtCO2e). The largest jump occurred in 2019-2020, which seems unlikely to be primarily from heat pump adoption given the gradual conversion timeline. This may reflect increased full-time occupancy during COVID.

        **Net residential benefit: {net_residential:.0f} mtCO2e**
        """)

    # Calculate vehicle and total percentages for narrative
    vehicle_pct = (vehicles_change / data_2019['vehicles_tco2e']) * 100
    total_pct = (total_change / data_2019['total_tco2e']) * 100

    with col_b:
        st.markdown("### ⚠️ Challenge: Vehicle Emissions")
        st.markdown(f"""
        **Vehicle emissions increased {vehicle_pct:.1f}%** ({vehicles_change:+.0f} tCO2e). This reflects more vehicles on the road as population grew {pop_change_pct:.1f}%, without sufficient adoption of electric vehicles.

        **Municipal buildings and commercial electricity remained relatively steady**, with minor reductions.

        **Overall: {total_change:.0f} mtCO2e ({total_pct:.1f}% reduction) from 2019 to 2023**
        """)

    # Show breakdown by sector
    st.subheader("Emissions by Sector")

    # Calculate sector totals
    sector_df = combined_df.copy()
    sector_df['Transportation'] = sector_df['vehicles_tco2e']
    sector_df['Buildings'] = (sector_df['residential_fossil_fuel_mtco2e'] +
                               sector_df['other_fuels_mtco2e'])
    sector_df['Energy (Electricity)'] = (sector_df['residential_electric_mtco2e'] +
                                          sector_df['commercial_electric_mtco2e'] +
                                          sector_df['electric_mtco2e'])

    # Create two columns for absolute and percentage charts
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("#### Absolute Emissions (mtCO2e)")
        # Create sector stacked area chart
        fig_sectors = go.Figure()

        fig_sectors.add_trace(go.Scatter(
            x=sector_df['year'],
            y=sector_df['Buildings'],
            name='Buildings',
            mode='lines',
            line=dict(width=0),
            stackgroup='one',
            fillcolor='rgba(212, 81, 19, 0.6)'
        ))

        fig_sectors.add_trace(go.Scatter(
            x=sector_df['year'],
            y=sector_df['Energy (Electricity)'],
            name='Energy (Electricity)',
            mode='lines',
            line=dict(width=0),
            stackgroup='one',
            fillcolor='rgba(6, 167, 125, 0.6)'
        ))

        fig_sectors.add_trace(go.Scatter(
            x=sector_df['year'],
            y=sector_df['Transportation'],
            name='Transportation',
            mode='lines',
            line=dict(width=0),
            stackgroup='one',
            fillcolor='rgba(70, 130, 180, 0.6)'
        ))

        fig_sectors.update_layout(
            xaxis_title="Year",
            yaxis_title="mtCO2e",
            hovermode='x unified',
            height=400,
            showlegend=True
        )

        st.plotly_chart(fig_sectors, use_container_width=True)

    with col_chart2:
        st.markdown("#### Percentage of Total Emissions (%)")
        # Calculate percentages
        sector_df['Buildings_pct'] = (sector_df['Buildings'] / sector_df['total_tco2e']) * 100
        sector_df['Energy_pct'] = (sector_df['Energy (Electricity)'] / sector_df['total_tco2e']) * 100
        sector_df['Transportation_pct'] = (sector_df['Transportation'] / sector_df['total_tco2e']) * 100

        # Create 100% stacked area chart
        fig_percent = go.Figure()

        fig_percent.add_trace(go.Scatter(
            x=sector_df['year'],
            y=sector_df['Buildings_pct'],
            name='Buildings',
            mode='lines',
            line=dict(width=0),
            stackgroup='one',
            groupnorm='percent',
            fillcolor='rgba(212, 81, 19, 0.6)'
        ))

        fig_percent.add_trace(go.Scatter(
            x=sector_df['year'],
            y=sector_df['Energy_pct'],
            name='Energy (Electricity)',
            mode='lines',
            line=dict(width=0),
            stackgroup='one',
            groupnorm='percent',
            fillcolor='rgba(6, 167, 125, 0.6)'
        ))

        fig_percent.add_trace(go.Scatter(
            x=sector_df['year'],
            y=sector_df['Transportation_pct'],
            name='Transportation',
            mode='lines',
            line=dict(width=0),
            stackgroup='one',
            groupnorm='percent',
            fillcolor='rgba(70, 130, 180, 0.6)'
        ))

        fig_percent.update_layout(
            xaxis_title="Year",
            yaxis_title="Percentage (%)",
            yaxis=dict(range=[0, 100]),
            hovermode='x unified',
            height=400,
            showlegend=True
        )

        st.plotly_chart(fig_percent, use_container_width=True)

    # Add animated pie chart showing composition over time
    st.markdown("#### Sector Composition Over Time (Animated)")

    # Prepare data for animated pie chart
    years = sorted(sector_df['year'].unique())

    # Create frames for animation
    frames = []
    for year in years:
        year_data = sector_df[sector_df['year'] == year].iloc[0]
        frame = go.Frame(
            data=[go.Pie(
                labels=['Buildings', 'Energy (Electricity)', 'Transportation'],
                values=[year_data['Buildings'], year_data['Energy (Electricity)'], year_data['Transportation']],
                marker=dict(colors=['rgba(212, 81, 19, 0.8)', 'rgba(6, 167, 125, 0.8)', 'rgba(70, 130, 180, 0.8)']),
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>%{value:.1f} mtCO2e<br>%{percent}<extra></extra>'
            )],
            name=str(int(year)),
            layout=go.Layout(title_text=f"Year {int(year)}")
        )
        frames.append(frame)

    # Create initial frame (first year)
    first_year_data = sector_df[sector_df['year'] == years[0]].iloc[0]
    fig_animated = go.Figure(
        data=[go.Pie(
            labels=['Buildings', 'Energy (Electricity)', 'Transportation'],
            values=[first_year_data['Buildings'], first_year_data['Energy (Electricity)'], first_year_data['Transportation']],
            marker=dict(colors=['rgba(212, 81, 19, 0.8)', 'rgba(6, 167, 125, 0.8)', 'rgba(70, 130, 180, 0.8)']),
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>%{value:.1f} mtCO2e<br>%{percent}<extra></extra>'
        )],
        frames=frames
    )

    # Add slider control (no play/pause buttons)
    fig_animated.update_layout(
        title=f"Year {int(years[0])}",
        height=500,
        sliders=[dict(
            active=0,
            steps=[dict(
                method="animate",
                args=[[f.name], {"frame": {"duration": 300, "redraw": True},
                                 "mode": "immediate",
                                 "transition": {"duration": 300}}],
                label=f.name
            ) for f in frames],
            x=0.1,
            y=0,
            len=0.9,
            xanchor="left",
            yanchor="top"
        )]
    )

    st.plotly_chart(fig_animated, use_container_width=True)

    # Display sector breakdown table
    sector_display = sector_df[['year', 'Transportation', 'Buildings', 'Energy (Electricity)', 'total_tco2e']].copy()
    sector_display.columns = ['Year', 'Transportation (mtCO2e)', 'Buildings (mtCO2e)', 'Energy (Electricity) (mtCO2e)', 'Total (mtCO2e)']
    st.dataframe(sector_display.sort_values('Year', ascending=False), hide_index=True)

    st.markdown("""
    **Sector Definitions:**
    - **Transportation**: All registered vehicles (gasoline, diesel, hybrid), excluding electric vehicle home charging
    - **Buildings**: Fossil fuel heating (residential propane, municipal buildings - oil/propane/gas)
    - **Energy (Electricity)**: All electricity consumption (residential, commercial, municipal buildings)
    """)

    # Per Capita Emissions
    st.markdown("---")
    st.subheader("Per Capita Emissions")

    # Calculate per capita emissions
    combined_df['per_capita_tco2e'] = combined_df['total_tco2e'] / combined_df['Population']

    col_per_capita1, col_per_capita2 = st.columns([2, 1])

    with col_per_capita1:
        fig_per_capita = go.Figure()

        fig_per_capita.add_trace(go.Scatter(
            x=combined_df['year'],
            y=combined_df['per_capita_tco2e'],
            mode='lines+markers',
            name='Per Capita Emissions',
            line=dict(color='rgb(231, 76, 60)', width=3),
            marker=dict(size=10)
        ))

        fig_per_capita.update_layout(
            title='Per Capita GHG Emissions',
            xaxis_title='Year',
            yaxis_title='tCO2e per Person',
            hovermode='x',
            height=400
        )

        st.plotly_chart(fig_per_capita, use_container_width=True)

    with col_per_capita2:
        # Get 2019 and most recent year data
        data_2019 = combined_df[combined_df['year'] == 2019].iloc[0]
        data_most_recent = combined_df[combined_df['year'] == combined_df['year'].max()].iloc[0]

        per_capita_2019 = data_2019['per_capita_tco2e']
        per_capita_recent = data_most_recent['per_capita_tco2e']
        per_capita_change = per_capita_recent - per_capita_2019
        per_capita_change_pct = (per_capita_change / per_capita_2019) * 100

        st.markdown("### Key Metrics")
        st.metric(
            label=f"Per Capita Emissions ({int(data_most_recent['year'])})",
            value=f"{per_capita_recent:.2f} tCO2e/person",
            delta=f"{per_capita_change:.2f} ({per_capita_change_pct:+.1f}%)",
            delta_color="inverse"
        )

        st.metric(
            label="Population",
            value=f"{int(data_most_recent['Population']):,}"
        )

        st.metric(
            label="Total Emissions",
            value=f"{data_most_recent['total_tco2e']:.0f} mtCO2e"
        )

        st.markdown(f"""
        Per capita emissions help normalize emissions data relative to population growth.
        From 2019 to {int(data_most_recent['year'])}, per capita emissions changed by
        **{per_capita_change_pct:+.1f}%**, while total population grew by
        **{((data_most_recent['Population'] - data_2019['Population']) / data_2019['Population'] * 100):.1f}%**.
        """)

    st.markdown("---")

    # Show detailed breakdown table
    st.subheader("Detailed Emissions Breakdown by Year")
    display_df = combined_df[[
        'year',
        'residential_fossil_fuel_mtco2e',
        'residential_electric_mtco2e',
        'commercial_electric_mtco2e',
        'other_fuels_mtco2e',
        'electric_mtco2e',
        'vehicles_tco2e',
        'total_tco2e'
    ]].copy()
    display_df.columns = [
        'Year',
        'Residential Fossil Fuel Heating (mtCO2e)',
        'Residential Electric (mtCO2e)',
        'Commercial Electric (mtCO2e)',
        'Municipal Buildings - Other Fuels (mtCO2e)',
        'Municipal Buildings - Electric (mtCO2e)',
        'Vehicles (mtCO2e)',
        'Total (mtCO2e)'
    ]
    st.dataframe(display_df.sort_values('Year', ascending=False), hide_index=True)

    # Download option
    st.subheader("Download Data")
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Combined Data as CSV",
        data=csv,
        file_name="combined_emissions_data.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.write("Please check that all required data files are present.")
