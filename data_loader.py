"""Helper functions for loading vehicle data from local CSV files."""
import pandas as pd
import streamlit as st


@st.cache_data(ttl=600)
def load_vehicle_data():
    """Load vehicle data from local CSV files and calculate tCO2e emissions."""
    try:
        # Load the vehicle count data
        vehicles_df = pd.read_csv('data/TruroVehicles.csv')

        # Load vehicle factors (miles per year, MPG, MPkWh)
        vehicle_factors_df = pd.read_csv('data/vehicles_factors.csv')

        # Load emission factors
        emission_factors_df = pd.read_csv('data/emission_factors.csv')

        # Extract emission factors from the CSV
        # Gasoline: 0.00882 tCO2e per gallon (Motor gasoline row)
        # Diesel: 0.01030 tCO2e per gallon
        # Electricity: 0.000239 tCO2e per kWh (239.3333 kg/MWh / 1000)
        gal_emission_factor = 0.00882
        diesel_emission_factor = 0.01030
        kwh_emission_factor = 0.000239

        # Calculate tCO2e per vehicle for each type
        tco2e_per_vehicle = {}

        for idx, row in vehicle_factors_df.iterrows():
            vehicle_type = row.iloc[0]  # First column is vehicle type
            if vehicle_type == '' or pd.isna(vehicle_type):
                continue

            miles_per_year = row['Miles per Year']
            mpg = row['MPgal']
            mpkwh = row['MPkwh']

            gal_used = 0
            kwh_used = 0

            # Calculate fuel/energy consumption
            if not pd.isna(mpg) and mpg > 0:
                gal_used = miles_per_year / mpg

            if not pd.isna(mpkwh) and mpkwh > 0:
                kwh_used = miles_per_year / mpkwh

            # Determine emission factor based on vehicle type
            if vehicle_type == 'Diesel' or vehicle_type == 'Motorcycle Gasoline':
                gal_ef = diesel_emission_factor
            else:
                gal_ef = gal_emission_factor

            # Calculate total emissions per vehicle
            tco2e_from_gal = gal_used * gal_ef
            tco2e_from_kwh = kwh_used * kwh_emission_factor
            total_tco2e = tco2e_from_gal + tco2e_from_kwh

            tco2e_per_vehicle[vehicle_type] = round(total_tco2e, 2)

        # Add tCO2e column to vehicles dataframe
        vehicles_df['tCo2e'] = vehicles_df.apply(
            lambda row: row['Number'] * tco2e_per_vehicle.get(row['Type'], 0),
            axis=1
        )

        return vehicles_df

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None


@st.cache_data(ttl=600)
def load_energy_data():
    """Load municipal energy data from local CSV file."""
    try:
        # Load the municipal energy data
        energy_df = pd.read_csv('data/municipal_energy.csv')
        return energy_df

    except Exception as e:
        st.error(f"Error loading energy data: {str(e)}")
        return None


@st.cache_data(ttl=600)
def load_clc_participation_data():
    """Load CLC participation data from local CSV file."""
    try:
        # Load the CLC participation data
        clc_df = pd.read_csv('data/clc_participation.csv')

        # Clean the percentage column - remove % sign and convert to float
        clc_df['Cumulative Location Participation Rate %'] = clc_df['Cumulative Location Participation Rate %'].str.replace('%', '').astype(float)

        return clc_df

    except Exception as e:
        st.error(f"Error loading CLC participation data: {str(e)}")
        return None


@st.cache_data(ttl=600)
def load_clc_census_data():
    """Load CLC census data from local CSV file."""
    try:
        # Load the CLC census data, skip the empty rows at the end
        clc_census_df = pd.read_csv('data/clc_census.csv', nrows=2)

        # Clean numeric columns - remove commas and convert to integers
        numeric_cols = clc_census_df.columns[clc_census_df.columns != 'City/Block group']
        for col in numeric_cols:
            if clc_census_df[col].dtype == 'object':
                clc_census_df[col] = clc_census_df[col].str.replace(',', '').replace('', '0')
                # Convert to numeric, coerce errors to NaN
                clc_census_df[col] = pd.to_numeric(clc_census_df[col], errors='coerce')

        return clc_census_df

    except Exception as e:
        st.error(f"Error loading CLC census data: {str(e)}")
        return None


@st.cache_data(ttl=600)
def load_clc_heat_pump_data():
    """Load CLC heat pump installation data from local CSV file."""
    try:
        # Load the heat pump installation data
        heat_pump_df = pd.read_csv('data/clc_heat_pump_installation.csv')

        # Rename the first column to 'Year' (it appears to be unnamed)
        heat_pump_df.columns = ['Year', 'Installed Heat Pump', 'Installed Heat Pumps Location']

        return heat_pump_df

    except Exception as e:
        st.error(f"Error loading CLC heat pump data: {str(e)}")
        return None


# Keep backward compatibility
@st.cache_data(ttl=600)
def load_data():
    """Load data - alias for load_vehicle_data for backward compatibility."""
    return load_vehicle_data()
