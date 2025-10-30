import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from projections import create_full_projection
from home_calculations import prepare_home_dashboard_data

# Page configuration
st.set_page_config(
    page_title="Emissions Projections - Town of Truro",
    page_icon="🔮",
    layout="wide"
)

st.title("Emissions Projections to 2050")

st.markdown("""
This page shows projected greenhouse gas emissions from 2024 to 2050 based on
the Town of Truro's climate action goals:
- **EV Adoption**: Transitioning to electric vehicles (17% by 2030, 100% by 2050)
- **Residential Heat Pumps**: Converting heating systems (30% by 2030, 92% by 2050)
- **Municipal Electrification**: Electrifying municipal buildings (62% by 2030, 100% by 2040)
- **Grid Decarbonization**: Massachusetts grid becoming cleaner (70% clean by 2030, 100% by 2050)
""")

# Load historical and projected data
try:
    with st.spinner("Loading projection data..."):
        # Get historical data
        historical_df, metadata = prepare_home_dashboard_data()

        # Get projections
        projection_df, baseline_data, goals = create_full_projection(2024, 2050)

        # Combine historical and projected data
        # Filter historical to only include years before 2024 (projections start at 2024)
        historical_for_chart = historical_df[historical_df['year'] < 2024][['year', 'vehicles_tco2e', 'residential_fossil_fuel_mtco2e',
                                               'residential_electric_mtco2e', 'commercial_electric_mtco2e',
                                               'other_fuels_mtco2e', 'electric_mtco2e', 'total_tco2e']]

        # Rename projection columns to match historical
        projection_for_chart = projection_df[['year', 'vehicles_tco2e', 'residential_fossil_fuel_mtco2e',
                                                'residential_electric_mtco2e', 'commercial_electric_mtco2e',
                                                'municipal_other_fuels_mtco2e', 'municipal_electric_mtco2e', 'total_tco2e']].copy()

        # Rename municipal columns to match historical naming
        projection_for_chart = projection_for_chart.rename(columns={
            'municipal_other_fuels_mtco2e': 'other_fuels_mtco2e',
            'municipal_electric_mtco2e': 'electric_mtco2e'
        })

        # Combine
        combined_chart_df = pd.concat([historical_for_chart, projection_for_chart], ignore_index=True)
        combined_chart_df = combined_chart_df.sort_values('year')

    st.success("Successfully loaded projection data")

    # Key Metrics
    st.subheader("Projected 2050 Impact")

    baseline_2023 = historical_df[historical_df['year'] == 2023]['total_tco2e'].values[0]
    projected_2050 = projection_df[projection_df['year'] == 2050]['total_tco2e'].values[0]
    reduction = baseline_2023 - projected_2050
    reduction_pct = (reduction / baseline_2023) * 100

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="2023 Baseline",
            value=f"{baseline_2023:,.0f} tCO2e"
        )

    with col2:
        st.metric(
            label="2050 Projected",
            value=f"{projected_2050:,.0f} tCO2e",
            delta=f"-{reduction:,.0f} tCO2e",
            delta_color="normal"
        )

    with col3:
        st.metric(
            label="Reduction",
            value=f"{reduction_pct:.1f}%",
            delta=f"{reduction:,.0f} tCO2e reduced",
            delta_color="normal"
        )

    with col4:
        # 2030 interim target
        projected_2030 = projection_df[projection_df['year'] == 2030]['total_tco2e'].values[0]
        reduction_2030 = baseline_2023 - projected_2030
        reduction_2030_pct = (reduction_2030 / baseline_2023) * 100
        st.metric(
            label="2030 Interim",
            value=f"{projected_2030:,.0f} tCO2e",
            delta=f"-{reduction_2030_pct:.1f}%",
            delta_color="normal"
        )

    # Extended Emissions Chart (Historical + Projected)
    st.subheader("Total Emissions: Historical and Projected (2019-2050)")

    # Add category filter
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
        default=all_categories,
        key="categories_filter"
    )

    if selected_categories:
        fig_combined = go.Figure()

        # Add a vertical line at 2024 to separate historical from projected
        fig_combined.add_vline(
            x=2024,
            line_dash="dash",
            line_color="gray",
            annotation_text="Projected →",
            annotation_position="top right"
        )

        # Residential Fossil Fuel Heating
        if 'Residential Fossil Fuel Heating' in selected_categories:
            fig_combined.add_trace(go.Scatter(
                x=combined_chart_df['year'],
                y=combined_chart_df['residential_fossil_fuel_mtco2e'],
                name='Residential Fossil Fuel Heating',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(212, 81, 19, 0.5)'
            ))

        # Residential Electricity
        if 'Residential Electricity' in selected_categories:
            fig_combined.add_trace(go.Scatter(
                x=combined_chart_df['year'],
                y=combined_chart_df['residential_electric_mtco2e'],
                name='Residential Electricity',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(6, 167, 125, 0.5)'
            ))

        # Commercial Electricity
        if 'Commercial Electricity' in selected_categories:
            fig_combined.add_trace(go.Scatter(
                x=combined_chart_df['year'],
                y=combined_chart_df['commercial_electric_mtco2e'],
                name='Commercial Electricity',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(30, 136, 229, 0.5)'
            ))

        # Municipal Buildings - Other Fuels
        if 'Municipal Buildings (Other Fuels)' in selected_categories:
            fig_combined.add_trace(go.Scatter(
                x=combined_chart_df['year'],
                y=combined_chart_df['other_fuels_mtco2e'],
                name='Municipal Buildings (Other Fuels)',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(255, 127, 80, 0.5)'
            ))

        # Municipal Buildings - Electric
        if 'Municipal Buildings (Electric)' in selected_categories:
            fig_combined.add_trace(go.Scatter(
                x=combined_chart_df['year'],
                y=combined_chart_df['electric_mtco2e'],
                name='Municipal Buildings (Electric)',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(41, 128, 185, 0.5)'
            ))

        # Vehicles
        if 'Vehicles' in selected_categories:
            fig_combined.add_trace(go.Scatter(
                x=combined_chart_df['year'],
                y=combined_chart_df['vehicles_tco2e'],
                name='Vehicles',
                mode='lines',
                line=dict(width=0),
                stackgroup='one',
                fillcolor='rgba(142, 68, 173, 0.5)'
            ))

        fig_combined.update_layout(
            title='Total GHG Emissions by Category (Historical and Projected)',
            xaxis_title='Year',
            yaxis_title='tCO2e',
            hovermode='x unified',
            height=600
        )

        st.plotly_chart(fig_combined, use_container_width=True)

    # Climate Action Progress
    st.subheader("Climate Action Progress")

    # Create tabs for each projection component
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚗 EV Adoption",
        "🏠 Heat Pumps",
        "🏛️ Municipal Buildings",
        "⚡ Grid Decarbonization"
    ])

    with tab1:
        st.markdown("### Electric Vehicle Adoption")
        st.markdown("""
        Transitioning from internal combustion engine (ICE) vehicles to electric vehicles (EVs).
        - **2030 Goal**: 17% EV adoption
        - **2040 Goal**: 40% EV adoption
        - **2050 Goal**: 100% EV adoption
        """)

        # EV adoption chart
        fig_ev = go.Figure()

        fig_ev.add_trace(go.Scatter(
            x=projection_df['year'],
            y=projection_df['ev_adoption_pct'] * 100,
            name='EV Adoption',
            mode='lines+markers',
            line=dict(color='rgb(142, 68, 173)', width=3),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(142, 68, 173, 0.2)'
        ))

        # Add goal markers
        ev_goals = goals['ev_adoption']
        fig_ev.add_trace(go.Scatter(
            x=ev_goals['year'],
            y=ev_goals['EV Adoption'] * 100,
            name='Goals',
            mode='markers',
            marker=dict(size=12, color='red', symbol='star')
        ))

        fig_ev.update_layout(
            title='EV Adoption Rate Over Time',
            xaxis_title='Year',
            yaxis_title='EV Adoption (%)',
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_ev, use_container_width=True)

        # Vehicle emissions chart
        fig_vehicles = go.Figure()

        fig_vehicles.add_trace(go.Scatter(
            x=combined_chart_df['year'],
            y=combined_chart_df['vehicles_tco2e'],
            name='Vehicle Emissions',
            mode='lines+markers',
            line=dict(color='rgb(142, 68, 173)', width=3),
            marker=dict(size=6)
        ))

        fig_vehicles.add_vline(x=2024, line_dash="dash", line_color="gray")

        fig_vehicles.update_layout(
            title='Vehicle Emissions Over Time',
            xaxis_title='Year',
            yaxis_title='tCO2e',
            hovermode='x',
            height=400
        )

        st.plotly_chart(fig_vehicles, use_container_width=True)

    with tab2:
        st.markdown("### Residential Heat Pump Adoption")
        st.markdown("""
        Replacing fossil fuel heating systems with efficient electric heat pumps.
        - **2030 Goal**: 30% heat pump adoption
        - **2040 Goal**: 61% heat pump adoption
        - **2050 Goal**: 92% heat pump adoption

        Heat pumps are ~3x more efficient than traditional electric resistance heating.
        """)

        # Heat pump adoption chart
        fig_hp = go.Figure()

        fig_hp.add_trace(go.Scatter(
            x=projection_df['year'],
            y=projection_df['heat_pump_adoption_pct'] * 100,
            name='Heat Pump Adoption',
            mode='lines+markers',
            line=dict(color='rgb(212, 81, 19)', width=3),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(212, 81, 19, 0.2)'
        ))

        # Add goal markers
        hp_goals = goals['residential_heat_pumps']
        fig_hp.add_trace(go.Scatter(
            x=hp_goals['year'],
            y=hp_goals['heat pump adoption'] * 100,
            name='Goals',
            mode='markers',
            marker=dict(size=12, color='red', symbol='star')
        ))

        fig_hp.update_layout(
            title='Heat Pump Adoption Rate Over Time',
            xaxis_title='Year',
            yaxis_title='Heat Pump Adoption (%)',
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_hp, use_container_width=True)

        # Residential heating emissions chart
        fig_heating = go.Figure()

        # Fossil fuel heating
        fig_heating.add_trace(go.Scatter(
            x=projection_df['year'],
            y=projection_df['residential_fossil_fuel_mtco2e'],
            name='Fossil Fuel Heating',
            mode='lines+markers',
            line=dict(color='rgb(212, 81, 19)', width=3),
            marker=dict(size=6)
        ))

        # Electric heating (existing + heat pumps)
        fig_heating.add_trace(go.Scatter(
            x=projection_df['year'],
            y=projection_df['residential_electric_mtco2e'],
            name='Electric Heating',
            mode='lines+markers',
            line=dict(color='rgb(6, 167, 125)', width=3),
            marker=dict(size=6)
        ))

        fig_heating.update_layout(
            title='Residential Heating Emissions Over Time',
            xaxis_title='Year',
            yaxis_title='mtCO2e',
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_heating, use_container_width=True)

    with tab3:
        st.markdown("### Municipal Building Electrification")
        st.markdown("""
        Converting municipal buildings from fossil fuels to electricity.
        - **2027 Goal**: 11% electrification
        - **2030 Goal**: 62% electrification
        - **2040 Goal**: 100% electrification
        """)

        # Municipal electrification chart
        fig_muni = go.Figure()

        fig_muni.add_trace(go.Scatter(
            x=projection_df['year'],
            y=projection_df['municipal_electrification_pct'] * 100,
            name='Electrification',
            mode='lines+markers',
            line=dict(color='rgb(255, 127, 80)', width=3),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(255, 127, 80, 0.2)'
        ))

        # Add goal markers
        muni_goals = goals['municipal_electrification']
        fig_muni.add_trace(go.Scatter(
            x=muni_goals['year'],
            y=muni_goals['munipal_heat_pump_adoption'] * 100,
            name='Goals',
            mode='markers',
            marker=dict(size=12, color='red', symbol='star')
        ))

        fig_muni.update_layout(
            title='Municipal Building Electrification Rate Over Time',
            xaxis_title='Year',
            yaxis_title='Electrification (%)',
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_muni, use_container_width=True)

        # Municipal emissions chart
        fig_muni_emissions = go.Figure()

        # Other fuels
        fig_muni_emissions.add_trace(go.Scatter(
            x=projection_df['year'],
            y=projection_df['municipal_other_fuels_mtco2e'],
            name='Other Fuels',
            mode='lines+markers',
            line=dict(color='rgb(255, 127, 80)', width=3),
            marker=dict(size=6)
        ))

        # Electric
        fig_muni_emissions.add_trace(go.Scatter(
            x=projection_df['year'],
            y=projection_df['municipal_electric_mtco2e'],
            name='Electric',
            mode='lines+markers',
            line=dict(color='rgb(41, 128, 185)', width=3),
            marker=dict(size=6)
        ))

        fig_muni_emissions.update_layout(
            title='Municipal Building Emissions Over Time',
            xaxis_title='Year',
            yaxis_title='mtCO2e',
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_muni_emissions, use_container_width=True)

    with tab4:
        st.markdown("### Massachusetts Grid Decarbonization")
        st.markdown("""
        As the Massachusetts electricity grid incorporates more renewable energy,
        the emissions from electricity consumption decrease over time.
        - **2025**: 53% clean energy
        - **2030**: 70% clean energy
        - **2050**: 100% clean energy (net zero)

        This benefits all electric consumption: residential, commercial, municipal, and EVs.
        """)

        # Grid clean energy chart
        fig_grid = go.Figure()

        fig_grid.add_trace(go.Scatter(
            x=projection_df['year'],
            y=projection_df['grid_clean_energy_pct'] * 100,
            name='Clean Energy',
            mode='lines+markers',
            line=dict(color='rgb(6, 167, 125)', width=3),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(6, 167, 125, 0.2)'
        ))

        fig_grid.update_layout(
            title='Grid Clean Energy Percentage Over Time',
            xaxis_title='Year',
            yaxis_title='Clean Energy (%)',
            hovermode='x',
            height=400
        )

        st.plotly_chart(fig_grid, use_container_width=True)

        # Total electricity emissions chart
        fig_elec_total = go.Figure()

        total_elec_emissions = (
            projection_df['residential_electric_mtco2e'] +
            projection_df['commercial_electric_mtco2e'] +
            projection_df['municipal_electric_mtco2e']
        )

        fig_elec_total.add_trace(go.Scatter(
            x=projection_df['year'],
            y=total_elec_emissions,
            name='Total Electricity Emissions',
            mode='lines+markers',
            line=dict(color='rgb(30, 136, 229)', width=3),
            marker=dict(size=6)
        ))

        fig_elec_total.update_layout(
            title='Total Electricity-Related Emissions Over Time',
            xaxis_title='Year',
            yaxis_title='mtCO2e',
            hovermode='x',
            height=400
        )

        st.plotly_chart(fig_elec_total, use_container_width=True)

    # Milestone Table
    st.subheader("Key Milestone Years")

    milestone_years = [2024, 2030, 2040, 2050]
    milestone_data = []

    for year in milestone_years:
        row = projection_df[projection_df['year'] == year].iloc[0]
        milestone_data.append({
            'Year': int(year),
            'Total Emissions (tCO2e)': f"{row['total_tco2e']:,.0f}",
            'EV Adoption': f"{row['ev_adoption_pct']*100:.1f}%",
            'Heat Pumps': f"{row['heat_pump_adoption_pct']*100:.1f}%",
            'Municipal Electrification': f"{row['municipal_electrification_pct']*100:.1f}%",
            'Grid Clean Energy': f"{row['grid_clean_energy_pct']*100:.1f}%",
            'Reduction from 2023': f"{((baseline_2023 - row['total_tco2e']) / baseline_2023 * 100):.1f}%"
        })

    milestone_df = pd.DataFrame(milestone_data)
    st.dataframe(milestone_df, use_container_width=True, hide_index=True)

    # Detailed Projection Data
    with st.expander("📊 View Detailed Projection Data"):
        display_projection_df = projection_df[[
            'year', 'total_tco2e', 'vehicles_tco2e',
            'residential_fossil_fuel_mtco2e', 'residential_electric_mtco2e',
            'commercial_electric_mtco2e', 'municipal_other_fuels_mtco2e', 'municipal_electric_mtco2e',
            'ev_adoption_pct', 'heat_pump_adoption_pct',
            'municipal_electrification_pct', 'grid_clean_energy_pct'
        ]].copy()

        # Format for display
        display_projection_df['year'] = display_projection_df['year'].astype(int)
        display_projection_df['ev_adoption_pct'] = (display_projection_df['ev_adoption_pct'] * 100).round(1)
        display_projection_df['heat_pump_adoption_pct'] = (display_projection_df['heat_pump_adoption_pct'] * 100).round(1)
        display_projection_df['municipal_electrification_pct'] = (display_projection_df['municipal_electrification_pct'] * 100).round(1)
        display_projection_df['grid_clean_energy_pct'] = (display_projection_df['grid_clean_energy_pct'] * 100).round(1)

        display_projection_df.columns = [
            'Year', 'Total Emissions', 'Vehicles',
            'Residential Fossil', 'Residential Electric',
            'Commercial Electric', 'Municipal Other', 'Municipal Electric',
            'EV Adoption (%)', 'Heat Pumps (%)',
            'Municipal Elec (%)', 'Grid Clean (%)'
        ]

        st.dataframe(display_projection_df, use_container_width=True, hide_index=True)

    # Notes
    st.markdown("---")
    st.markdown("""
    **Notes:**
    - All projections assume goals are achieved through linear interpolation between milestone years
    - Population growth is assumed to be zero for conservative estimates
    - Heat pump efficiency assumes COP (Coefficient of Performance) of 3.0
    - EV efficiency improves as the grid becomes cleaner
    - Grid decarbonization goals based on Massachusetts state targets
    """)

except Exception as e:
    st.error(f"Error loading projection data: {str(e)}")
    st.write("Please check that all required data files and goal files are present.")
    import traceback
    st.code(traceback.format_exc())
