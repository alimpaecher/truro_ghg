import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_clc_participation_data

st.title("CLC Participation Data")

# Load the data
df = load_clc_participation_data()

if df is not None:
    st.success(f"Successfully loaded {len(df)} years of CLC participation data")

    # Display current year metrics
    most_recent_year = df['Year'].max()
    current_data = df[df['Year'] == most_recent_year].iloc[0]
    previous_data = df[df['Year'] == most_recent_year - 1].iloc[0]

    st.subheader(f"Year {int(most_recent_year)} Status")
    col1, col2 = st.columns(2)

    with col1:
        delta_rate = current_data['Cumulative Location Participation Rate %'] - previous_data['Cumulative Location Participation Rate %']
        st.metric(
            label="Cumulative Participation Rate",
            value=f"{current_data['Cumulative Location Participation Rate %']:.2f}%",
            delta=f"{delta_rate:.2f}%"
        )

    with col2:
        delta_locations = current_data['Active Locations'] - previous_data['Active Locations']
        st.metric(
            label="Active Locations",
            value=f"{int(current_data['Active Locations']):,}",
            delta=f"{int(delta_locations):,}"
        )

    # Create line chart for participation rate over time
    st.subheader("Cumulative Location Participation Rate Over Time")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['Year'],
        y=df['Cumulative Location Participation Rate %'],
        mode='lines+markers',
        name='Participation Rate',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8)
    ))

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Participation Rate (%)",
        hovermode='x unified',
        height=500,
        yaxis=dict(range=[0, max(df['Cumulative Location Participation Rate %']) * 1.1])
    )

    st.plotly_chart(fig, use_container_width=True)

    # Calculate year-over-year change
    df_sorted = df.sort_values('Year')
    df_sorted['YoY Change'] = df_sorted['Cumulative Location Participation Rate %'].diff()

    # Create year-over-year change chart
    st.subheader("Year-over-Year Change in Participation Rate")

    fig_yoy = go.Figure()

    fig_yoy.add_trace(go.Bar(
        x=df_sorted['Year'][1:],  # Skip first year since it has no previous year
        y=df_sorted['YoY Change'][1:],
        name='YoY Change',
        marker=dict(
            color=df_sorted['YoY Change'][1:],
            colorscale='RdYlGn',
            showscale=False
        )
    ))

    fig_yoy.update_layout(
        xaxis_title="Year",
        yaxis_title="Change in Participation Rate (percentage points)",
        hovermode='x unified',
        height=400
    )

    st.plotly_chart(fig_yoy, use_container_width=True)

    # Show data table
    st.subheader("Participation Data by Year")
    display_df = df.copy()
    display_df['Cumulative Location Participation Rate %'] = display_df['Cumulative Location Participation Rate %'].apply(lambda x: f"{x:.2f}%")
    st.dataframe(display_df.sort_values('Year', ascending=False), hide_index=True)
