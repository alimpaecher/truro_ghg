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


def calculate_propane_displacement():
    """
    Calculate propane displacement by heat pumps from 2021-2023.

    Uses:
    - Assessors data (2019) for baseline propane usage
    - CLC heat pump installation data for conversion tracking

    Assumptions:
    - Heat pumps replaced propane heating systems
    - CLC-funded installations are year-round homes (100% heating factor)
    - Uses median square footage of residential propane properties
    """

    # Load assessors and heat pump data
    assessors_df = load_assessors_data()
    heat_pump_df = load_clc_heat_pump_data()

    if assessors_df is None or heat_pump_df is None:
        return None

    # Filter to year-round residential propane properties
    # Exclude motels, resorts, commercial
    MOTELS_RESORTS = ['MOTELS', 'RESORT CONDO', 'INNS']
    COMMERCIAL_TYPES = ['RESTAURANTS', 'SMALL RETAIL', 'GEN OFFICE BLDG', 'WAREHOUSE',
                        'BANK BLDG', 'SERVICE STATION', 'FUEL SERVICE', 'MARINAS',
                        'CAMPING FAC', 'MULTI-USE COM']

    propane_residential = assessors_df[
        (assessors_df['PropertyType'] == 'R') &
        (assessors_df['FUEL'] == 'GAS') &
        (assessors_df['NetSF'].notna()) &
        (assessors_df['NetSF'] > 0) &
        (~assessors_df['StateClassDesc'].isin(MOTELS_RESORTS)) &
        (~assessors_df['StateClassDesc'].isin(COMMERCIAL_TYPES))
    ].copy()

    # Calculate median square footage
    median_sqft = propane_residential['NetSF'].median()
    total_propane_properties = len(propane_residential)

    # Baseline propane consumption per property (year-round, 100% heating)
    PROPANE_CONSUMPTION = 0.39  # gal/sq ft/year
    PROPANE_EMISSION_FACTOR = 0.00574  # tCO2e per gallon

    propane_per_property_gal = median_sqft * PROPANE_CONSUMPTION * 1.00  # year-round
    propane_per_property_mtco2e = propane_per_property_gal * PROPANE_EMISSION_FACTOR

    # Total baseline propane usage (2019)
    baseline_propane_gal = total_propane_properties * propane_per_property_gal
    baseline_propane_mtco2e = total_propane_properties * propane_per_property_mtco2e

    # Heat pump conversion tracking
    # Baseline from assessors database: 92 heat pump properties in 2019
    baseline_heat_pumps_2019 = len(assessors_df[assessors_df['HVAC'].str.contains('HEAT PUMP', case=False, na=False)])

    heat_pump_df_sorted = heat_pump_df.sort_values('Year')

    # Get first CLC data point (2021: 165 locations)
    first_clc_year = int(heat_pump_df_sorted.iloc[0]['Year'])
    first_clc_locations = int(heat_pump_df_sorted.iloc[0]['Installed Heat Pumps Location'])

    # Interpolate 2020 value assuming linear growth from 2019 to 2021
    # 2019: 92, 2021: 165 → 2020: (92 + 165) / 2 ≈ 128.5 → 129
    interpolated_2020_locations = int((baseline_heat_pumps_2019 + first_clc_locations) / 2)

    # Calculate year-by-year
    results = []

    # Add 2019 baseline (assessors data)
    results.append({
        'Year': 2019,
        'Heat_Pump_Locations': baseline_heat_pumps_2019,
        'Cumulative_Conversions': 0,
        'Remaining_Propane_Properties': total_propane_properties,
        'Remaining_Propane_Gal': baseline_propane_gal,
        'Remaining_Propane_mtCO2e': baseline_propane_mtco2e,
        'Propane_Saved_Gal': 0,
        'Propane_Saved_mtCO2e': 0,
        'Percent_Reduction': 0
    })

    # Add 2020 interpolated
    conversions_2020 = interpolated_2020_locations - baseline_heat_pumps_2019
    results.append({
        'Year': 2020,
        'Heat_Pump_Locations': interpolated_2020_locations,
        'Cumulative_Conversions': conversions_2020,
        'Remaining_Propane_Properties': total_propane_properties - conversions_2020,
        'Remaining_Propane_Gal': (total_propane_properties - conversions_2020) * propane_per_property_gal,
        'Remaining_Propane_mtCO2e': (total_propane_properties - conversions_2020) * propane_per_property_mtco2e,
        'Propane_Saved_Gal': conversions_2020 * propane_per_property_gal,
        'Propane_Saved_mtCO2e': conversions_2020 * propane_per_property_mtco2e,
        'Percent_Reduction': (conversions_2020 / total_propane_properties * 100)
    })

    # Add CLC data (2021-2023)
    for idx, row in heat_pump_df_sorted.iterrows():
        year = int(row['Year'])
        locations = int(row['Installed Heat Pumps Location'])

        # Calculate cumulative conversions from 2019 assessors baseline (92 heat pumps)
        conversions = locations - baseline_heat_pumps_2019

        # Calculate reduced propane usage
        remaining_propane_properties = total_propane_properties - conversions
        remaining_propane_gal = remaining_propane_properties * propane_per_property_gal
        remaining_propane_mtco2e = remaining_propane_properties * propane_per_property_mtco2e

        # Calculate savings
        propane_saved_gal = conversions * propane_per_property_gal
        propane_saved_mtco2e = conversions * propane_per_property_mtco2e

        results.append({
            'Year': year,
            'Heat_Pump_Locations': locations,
            'Cumulative_Conversions': conversions,
            'Remaining_Propane_Properties': remaining_propane_properties,
            'Remaining_Propane_Gal': remaining_propane_gal,
            'Remaining_Propane_mtCO2e': remaining_propane_mtco2e,
            'Propane_Saved_Gal': propane_saved_gal,
            'Propane_Saved_mtCO2e': propane_saved_mtco2e,
            'Percent_Reduction': (conversions / total_propane_properties * 100) if conversions > 0 else 0
        })

    results_df = pd.DataFrame(results)

    # Add metadata
    metadata = {
        'baseline_year': 2019,
        'baseline_heat_pumps': baseline_heat_pumps_2019,
        'baseline_propane_properties': total_propane_properties,
        'baseline_propane_gal': baseline_propane_gal,
        'baseline_propane_mtco2e': baseline_propane_mtco2e,
        'median_sqft': median_sqft,
        'propane_per_property_gal': propane_per_property_gal,
        'propane_per_property_mtco2e': propane_per_property_mtco2e,
        'interpolated_2020': interpolated_2020_locations
    }

    return results_df, metadata


@st.cache_data(ttl=600)
def calculate_total_fossil_fuel_heating():
    """
    SINGLE SOURCE OF TRUTH for all fossil fuel heating calculations.

    Calculates total fossil fuel heating emissions (oil + propane) with heat pump displacement.

    BASELINE (2019) - with seasonal adjustment (67.1% seasonal, 32.9% year-round):
    - Oil: ~5,402.4 mtCO2e (constant, not being displaced)
    - All Propane: ~2,106.3 mtCO2e (821 properties, seasonal-adjusted)
    - TOTAL: ~7,508.7 mtCO2e

    DISPLACEMENT: As heat pumps installed, propane decreases (assumes year-round equivalent for conversions)
    """

    assessors_df = load_assessors_data()
    heat_pump_df = load_clc_heat_pump_data()

    if assessors_df is None or heat_pump_df is None:
        return None

    # Filter to residential/commercial only (exclude municipal Type E)
    df_calc = assessors_df[(assessors_df['PropertyType'] == 'R') &
                           (assessors_df['NetSF'].notna()) &
                           (assessors_df['NetSF'] > 0)].copy()

    # Constants
    OIL_CONSUMPTION = 0.40  # gal/sq ft/year
    PROPANE_CONSUMPTION = 0.39  # gal/sq ft/year
    OIL_EMISSION_FACTOR = 0.01030  # tCO2e per gallon
    PROPANE_EMISSION_FACTOR = 0.00574  # tCO2e per gallon

    # Seasonal adjustment
    SEASONAL_PCT = 0.671
    SEASONAL_HEATING_FACTOR = 0.30
    YEARROUND_HEATING_FACTOR = 1.00
    avg_seasonal_factor = (SEASONAL_PCT * SEASONAL_HEATING_FACTOR +
                          (1 - SEASONAL_PCT) * YEARROUND_HEATING_FACTOR)

    # Oil (constant)
    oil_properties = df_calc[df_calc['FUEL'] == 'OIL'].copy()
    oil_sqft_total = oil_properties['NetSF'].sum()
    # Expected baseline (2019): ~5,402.4 mtCO2e
    oil_emissions_mtco2e = oil_sqft_total * OIL_CONSUMPTION * avg_seasonal_factor * OIL_EMISSION_FACTOR

    # All propane with seasonal adjustment
    all_propane_properties = df_calc[df_calc['FUEL'] == 'GAS'].copy()
    total_propane_count = len(all_propane_properties)
    propane_total_sqft = all_propane_properties['NetSF'].sum()
    # Expected baseline (2019): ~2,106.3 mtCO2e
    baseline_propane_mtco2e_seasonal = propane_total_sqft * PROPANE_CONSUMPTION * avg_seasonal_factor * PROPANE_EMISSION_FACTOR

    # Tracked propane for heat pump displacement (year-round subset)
    MOTELS_RESORTS = ['MOTELS', 'RESORT CONDO', 'INNS']
    COMMERCIAL_TYPES = ['RESTAURANTS', 'SMALL RETAIL', 'GEN OFFICE BLDG', 'WAREHOUSE',
                        'BANK BLDG', 'SERVICE STATION', 'FUEL SERVICE', 'MARINAS',
                        'CAMPING FAC', 'MULTI-USE COM']

    tracked_propane_properties = all_propane_properties[
        (~all_propane_properties['StateClassDesc'].isin(MOTELS_RESORTS)) &
        (~all_propane_properties['StateClassDesc'].isin(COMMERCIAL_TYPES))
    ].copy()

    tracked_propane_count = len(tracked_propane_properties)
    tracked_propane_median_sqft = tracked_propane_properties['NetSF'].median()

    # For displacement: assume tracked properties are 100% year-round
    propane_per_property_gal_yearround = tracked_propane_median_sqft * PROPANE_CONSUMPTION * 1.00
    propane_per_property_mtco2e_yearround = propane_per_property_gal_yearround * PROPANE_EMISSION_FACTOR

    # Heat pump tracking
    baseline_heat_pumps_2019 = len(assessors_df[assessors_df['HVAC'].str.contains('HEAT PUMP', case=False, na=False)])
    heat_pump_df_sorted = heat_pump_df.sort_values('Year')
    first_clc_year = int(heat_pump_df_sorted.iloc[0]['Year'])
    first_clc_locations = int(heat_pump_df_sorted.iloc[0]['Installed Heat Pumps Location'])
    interpolated_2020_locations = int((baseline_heat_pumps_2019 + first_clc_locations) / 2)

    # Build time series
    results = []

    # 2019
    results.append({
        'year': 2019,
        'heat_pump_locations': baseline_heat_pumps_2019,
        'cumulative_conversions': 0,
        'oil_mtco2e': oil_emissions_mtco2e,
        'propane_mtco2e': baseline_propane_mtco2e_seasonal,
        'propane_mtco2e_eliminated': 0,
        'total_fossil_fuel_mtco2e': oil_emissions_mtco2e + baseline_propane_mtco2e_seasonal
    })

    # 2020
    conversions_2020 = interpolated_2020_locations - baseline_heat_pumps_2019
    propane_eliminated_2020 = conversions_2020 * propane_per_property_mtco2e_yearround
    results.append({
        'year': 2020,
        'heat_pump_locations': interpolated_2020_locations,
        'cumulative_conversions': conversions_2020,
        'oil_mtco2e': oil_emissions_mtco2e,
        'propane_mtco2e': baseline_propane_mtco2e_seasonal - propane_eliminated_2020,
        'propane_mtco2e_eliminated': propane_eliminated_2020,
        'total_fossil_fuel_mtco2e': oil_emissions_mtco2e + (baseline_propane_mtco2e_seasonal - propane_eliminated_2020)
    })

    # 2021-2023
    for idx, row in heat_pump_df_sorted.iterrows():
        year = int(row['Year'])
        locations = int(row['Installed Heat Pumps Location'])
        conversions = locations - baseline_heat_pumps_2019
        propane_eliminated = conversions * propane_per_property_mtco2e_yearround
        propane_remaining = baseline_propane_mtco2e_seasonal - propane_eliminated

        results.append({
            'year': year,
            'heat_pump_locations': locations,
            'cumulative_conversions': conversions,
            'oil_mtco2e': oil_emissions_mtco2e,
            'propane_mtco2e': propane_remaining,
            'propane_mtco2e_eliminated': propane_eliminated,
            'total_fossil_fuel_mtco2e': oil_emissions_mtco2e + propane_remaining
        })

    results_df = pd.DataFrame(results)

    # Metadata
    metadata = {
        'oil_properties': len(oil_properties),
        'oil_emissions_baseline': oil_emissions_mtco2e,
        'total_propane_properties': total_propane_count,
        'baseline_propane_mtco2e_seasonal': baseline_propane_mtco2e_seasonal,
        'tracked_propane_properties': tracked_propane_count,
        'tracked_propane_median_sqft': tracked_propane_median_sqft,
        'propane_per_property_mtco2e_yearround': propane_per_property_mtco2e_yearround,
        'avg_seasonal_factor': avg_seasonal_factor
    }

    return results_df, metadata


# Keep backward compatibility
@st.cache_data(ttl=600)
def load_data():
    """Load data - alias for load_vehicle_data for backward compatibility."""
    return load_vehicle_data()
