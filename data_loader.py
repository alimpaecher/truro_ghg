"""Helper functions for loading data from Google Sheets."""
import pandas as pd
import streamlit as st


# Configuration
SPREADSHEET_ID = "1sVrJGf34KkzQJ4jv2yrqNMp7j4ghZRlX7wt2Bxk-vz8"
SHEET_GID = "1586854144"  # The gid for the Vehicles sheet


@st.cache_data(ttl=600)
def load_data():
    """Load data from publicly accessible Google Sheet."""
    try:
        # Construct the export URL for CSV format
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={SHEET_GID}"

        # Read the CSV directly into a DataFrame
        df = pd.read_csv(url)
        return df

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None
