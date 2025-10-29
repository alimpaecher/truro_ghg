import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.title("Solar Installations in Truro")

# Load solar data
@st.cache_data
def load_solar_data():
    df = pd.read_csv('data/solar_data.csv')
    # Filter for Truro only
    df = df[df['City'] == 'Truro'].copy()
    return df

df = load_solar_data()

if df is not None and len(df) > 0:
    st.success(f"Successfully loaded {len(df)} years of solar data for Truro")

    # Filter to years with actual data (non-zero capacity)
    df_with_data = df[df['Capacity (kW DC) All Cumulative'] > 0].copy()

    if len(df_with_data) > 0:
        # Get latest year data
        latest_year = df_with_data['Year'].max()
        latest_data = df_with_data[df_with_data['Year'] == latest_year].iloc[0]

        # Display key metrics for latest year
        st.subheader(f"Solar Installation Status as of {int(latest_year)}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label="Total Capacity (kW DC)",
                value=f"{latest_data['Capacity (kW DC) All Cumulative']:.1f}"
            )
        with col2:
            st.metric(
                label="Total Projects",
                value=f"{int(latest_data['Project Count All Cumulative'])}"
            )
        with col3:
            avg_capacity = latest_data['Capacity (kW DC) All Cumulative'] / latest_data['Project Count All Cumulative']
            st.metric(
                label="Avg Capacity per Project",
                value=f"{avg_capacity:.1f} kW"
            )

        # Cumulative capacity growth over time
        st.subheader("Cumulative Solar Capacity Growth")

        fig_cumulative = go.Figure()
        fig_cumulative.add_trace(go.Scatter(
            x=df_with_data['Year'],
            y=df_with_data['Capacity (kW DC) All Cumulative'],
            mode='lines+markers',
            name='Total Capacity',
            line=dict(color='#FFA500', width=3),
            marker=dict(size=8)
        ))

        fig_cumulative.update_layout(
            xaxis_title="Year",
            yaxis_title="Cumulative Capacity (kW DC)",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_cumulative, use_container_width=True)

        # Annual new installations
        st.subheader("Annual New Solar Installations")

        # Calculate annual additions
        df_annual = df_with_data[['Year', 'Capacity (kW DC) All', 'Project Count All']].copy()
        df_annual = df_annual[df_annual['Capacity (kW DC) All'] > 0]

        fig_annual = go.Figure()
        fig_annual.add_trace(go.Bar(
            x=df_annual['Year'],
            y=df_annual['Capacity (kW DC) All'],
            name='Annual Capacity Added',
            marker_color='#228B22'
        ))

        fig_annual.update_layout(
            xaxis_title="Year",
            yaxis_title="Annual Capacity Added (kW DC)",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_annual, use_container_width=True)

        # Breakdown by installation type (Residential vs others)
        st.subheader("Cumulative Capacity by Installation Type")

        # Prepare data for stacked area chart
        type_columns = {
            'Residential': 'Capacity (kW DC) Residential Cumulative',
            'Commercial': 'Capacity (kW DC) Commercial Cumulative',
            'Municipal': 'Capacity (kW DC) Municipal Cumulative',
            'Other': 'Capacity (kW DC) Other Cumulative'
        }

        fig_types = go.Figure()

        for type_name, col_name in type_columns.items():
            if col_name in df_with_data.columns:
                # Only add trace if there's non-zero data
                if df_with_data[col_name].sum() > 0:
                    fig_types.add_trace(go.Scatter(
                        x=df_with_data['Year'],
                        y=df_with_data[col_name],
                        name=type_name,
                        mode='lines',
                        stackgroup='one',
                        line=dict(width=0.5)
                    ))

        fig_types.update_layout(
            xaxis_title="Year",
            yaxis_title="Cumulative Capacity (kW DC)",
            hovermode='x unified',
            height=500
        )
        st.plotly_chart(fig_types, use_container_width=True)

        # Project count growth
        st.subheader("Number of Solar Projects Over Time")

        col1, col2 = st.columns(2)

        with col1:
            fig_projects = go.Figure()
            fig_projects.add_trace(go.Scatter(
                x=df_with_data['Year'],
                y=df_with_data['Project Count All Cumulative'],
                mode='lines+markers',
                name='Total Projects',
                line=dict(color='#4169E1', width=3),
                marker=dict(size=8)
            ))

            fig_projects.update_layout(
                title="Cumulative Project Count",
                xaxis_title="Year",
                yaxis_title="Number of Projects",
                height=350
            )
            st.plotly_chart(fig_projects, use_container_width=True)

        with col2:
            # Annual new projects
            df_projects_annual = df_with_data[['Year', 'Project Count All']].copy()
            df_projects_annual = df_projects_annual[df_projects_annual['Project Count All'] > 0]

            fig_projects_annual = go.Figure()
            fig_projects_annual.add_trace(go.Bar(
                x=df_projects_annual['Year'],
                y=df_projects_annual['Project Count All'],
                marker_color='#DC143C'
            ))

            fig_projects_annual.update_layout(
                title="Annual New Projects",
                xaxis_title="Year",
                yaxis_title="Number of New Projects",
                height=350
            )
            st.plotly_chart(fig_projects_annual, use_container_width=True)

        # Summary statistics
        st.subheader("Summary Statistics")

        total_capacity = latest_data['Capacity (kW DC) All Cumulative']
        total_projects = int(latest_data['Project Count All Cumulative'])
        residential_capacity = latest_data['Capacity (kW DC) Residential Cumulative']
        residential_projects = int(latest_data['Project Count Residential Cumulative'])

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Overall")
            st.write(f"**Total Capacity:** {total_capacity:.1f} kW DC")
            st.write(f"**Total Projects:** {total_projects}")
            st.write(f"**Average Project Size:** {total_capacity/total_projects:.1f} kW")

            # Estimate annual energy production (kW DC * 1.2 MWh/kW for Massachusetts)
            estimated_annual_kwh = total_capacity * 1200
            st.write(f"**Estimated Annual Production:** {estimated_annual_kwh:,.0f} kWh")

        with col2:
            st.markdown("### Residential")
            st.write(f"**Residential Capacity:** {residential_capacity:.1f} kW DC ({residential_capacity/total_capacity*100:.1f}%)")
            st.write(f"**Residential Projects:** {residential_projects} ({residential_projects/total_projects*100:.1f}%)")
            if residential_projects > 0:
                st.write(f"**Avg Residential Size:** {residential_capacity/residential_projects:.1f} kW")

    else:
        st.info("No solar installation data available for Truro yet.")
else:
    st.error("Could not load solar data for Truro.")
