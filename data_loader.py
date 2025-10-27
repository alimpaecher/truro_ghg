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


@st.cache_data(ttl=600)
def load_assessors_data():
    """Load Truro Assessors data from Excel file."""
    try:
        # Load the assessors data from the BT_Extract sheet
        assessors_df = pd.read_excel('data/TRURO_Assessors original_2020-12-17-2019.xls', sheet_name='BT_Extract')

        return assessors_df

    except Exception as e:
        st.error(f"Error loading assessors data: {str(e)}")
        return None


@st.cache_data(ttl=600)
def load_mass_save_data():
    """Load Mass Save Geographic Report data for Truro."""
    try:
        import glob

        # Find all Mass Save files
        files = glob.glob('data/masssaveenergyusage/*.xls')

        all_data = []
        for filename in files:
            # Extract year from filename
            year = int(filename.split('/')[-1].split(' ')[0])

            # Read the file
            df = pd.read_excel(filename, skiprows=1)

            # Filter for Truro
            truro_data = df[(df['Town'] == 'Truro') & (df['County'] == 'Barnstable')]

            # Add year column
            truro_data['Year'] = year

            all_data.append(truro_data)

        # Combine all years
        combined_df = pd.concat(all_data, ignore_index=True)

        # Clean the electric usage column (remove commas, convert to float)
        combined_df['Electric_MWh'] = combined_df['Annual  Electric  Usage (MWh)'].str.replace(',', '').astype(float)

        return combined_df

    except Exception as e:
        st.error(f"Error loading Mass Save data: {str(e)}")
        return None


def calculate_residential_emissions(df):
    """
    Calculate estimated mtCO2e emissions for residential and commercial properties.

    Methodology:
    - Excludes municipal properties (PropertyType = 'E')
    - Applies seasonal adjustment: 67.1% seasonal (30% heating), 32.9% year-round (100%)
    - Uses fuel consumption benchmarks from Mass.gov
    - Applies emission factors from emission_factors.csv

    WARNING: Electric heating benchmarks are estimates and need verification
    """

    # Filter to residential/commercial only (exclude municipal Type E)
    df_calc = df[(df['PropertyType'] == 'R') & (df['NetSF'].notna()) & (df['NetSF'] > 0)].copy()

    # Emission factors (from emission_factors.csv)
    EMISSION_FACTORS = {
        'OIL': 0.01030,      # tCO2e per gallon (Diesel oil row 8)
        'GAS': 0.00574,      # tCO2e per gallon (Propane row 5)
        'ELECTRIC': 0.000239  # tCO2e per kWh (Electricity row 9: 239 kg/MWh / 1000)
    }

    # Fuel consumption benchmarks (gal/sq ft or kWh/sq ft)
    FUEL_CONSUMPTION = {
        'OIL': 0.40,         # gal/sq ft/year (Mass.gov)
        'GAS': 0.39,         # gal/sq ft/year (Mass.gov for propane)
        'ELECTRIC_RESISTANCE': 12.0,  # kWh/sq ft/year (ESTIMATE - NEEDS SOURCE)
        'HEAT_PUMP': 4.0     # kWh/sq ft/year (ESTIMATE - NEEDS SOURCE, assumes COP of 3)
    }

    # Seasonal adjustment percentages (from CLC census)
    SEASONAL_PCT = 0.671
    SEASONAL_HEATING_FACTOR = 0.30
    YEARROUND_HEATING_FACTOR = 1.00

    # Identify property categories
    MOTELS_RESORTS = ['MOTELS', 'RESORT CONDO', 'INNS']
    COMMERCIAL_TYPES = ['RESTAURANTS', 'SMALL RETAIL', 'GEN OFFICE BLDG', 'WAREHOUSE',
                        'BANK BLDG', 'SERVICE STATION', 'FUEL SERVICE', 'MARINAS',
                        'CAMPING FAC', 'MULTI-USE COM']

    # Add classification columns
    df_calc['is_motel_resort'] = df_calc['StateClassDesc'].isin(MOTELS_RESORTS)
    df_calc['is_commercial'] = df_calc['StateClassDesc'].isin(COMMERCIAL_TYPES)
    df_calc['is_residential'] = ~(df_calc['is_motel_resort'] | df_calc['is_commercial'])

    # Calculate seasonal adjustment factor for each property
    def get_seasonal_factor(row):
        if row['is_motel_resort']:
            return SEASONAL_HEATING_FACTOR  # 100% seasonal
        elif row['is_commercial']:
            # For now, use average adjustment - could be refined per your commercial factors
            return 0.65  # Approximate average based on your commercial heating percentages
        else:
            # Residential: statistical split
            return (SEASONAL_PCT * SEASONAL_HEATING_FACTOR +
                   (1 - SEASONAL_PCT) * YEARROUND_HEATING_FACTOR)

    df_calc['seasonal_factor'] = df_calc.apply(get_seasonal_factor, axis=1)

    # Calculate fuel consumption and emissions
    def calculate_emissions(row):
        sqft = row['NetSF']
        fuel = row['FUEL']
        hvac = row['HVAC']
        seasonal_adj = row['seasonal_factor']

        # Determine fuel consumption
        if fuel == 'OIL':
            gallons = sqft * FUEL_CONSUMPTION['OIL'] * seasonal_adj
            emissions = gallons * EMISSION_FACTORS['OIL']
        elif fuel == 'GAS':  # Propane
            gallons = sqft * FUEL_CONSUMPTION['GAS'] * seasonal_adj
            emissions = gallons * EMISSION_FACTORS['GAS']
        elif fuel == 'ELECTRIC':
            # Check if heat pump or resistance
            if hvac == 'HEAT PUMP':
                kwh = sqft * FUEL_CONSUMPTION['HEAT_PUMP'] * seasonal_adj
            else:
                kwh = sqft * FUEL_CONSUMPTION['ELECTRIC_RESISTANCE'] * seasonal_adj
            emissions = kwh * EMISSION_FACTORS['ELECTRIC']
        else:
            emissions = 0

        return emissions

    df_calc['mtco2e'] = df_calc.apply(calculate_emissions, axis=1)

    return df_calc


# Keep backward compatibility
@st.cache_data(ttl=600)
def load_data():
    """Load data - alias for load_vehicle_data for backward compatibility."""
    return load_vehicle_data()
