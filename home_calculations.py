"""
Home page calculations module.

This module contains all calculation logic for the Home.py dashboard page.
Separating calculations from UI allows for thorough testing without Streamlit dependencies.
"""

import pandas as pd
from data_loader import load_vehicle_data, load_energy_data, load_mass_save_data, calculate_total_fossil_fuel_heating
import emission_factors


def process_vehicles_data(vehicles_df):
    """
    Process vehicle data to calculate yearly emissions.

    Adjusts for electric vehicles to avoid double-counting with residential electricity:
    - Battery Electric: 100% excluded (counted in residential electricity)
    - Plug-in Hybrid: 50% reduction (half from home charging, half from gasoline)
    - Hybrid Electric: 100% included (self-charging, no home electricity)

    Args:
        vehicles_df (pd.DataFrame): Raw vehicle data with Quarter and tCo2e columns

    Returns:
        pd.DataFrame: Yearly vehicle emissions with columns ['year', 'vehicles_tco2e']
    """
    # Convert Quarter to datetime
    vehicles_df = vehicles_df.copy()
    vehicles_df['Quarter_Date'] = pd.to_datetime(vehicles_df['Quarter'])

    # Filter to only January quarters (Q1 represents previous year's final number)
    vehicles_df['Month'] = vehicles_df['Quarter_Date'].dt.month
    vehicles_q1 = vehicles_df[vehicles_df['Month'] == 1].copy()

    # Extract year (use previous year as the calendar year)
    vehicles_q1['year'] = vehicles_q1['Quarter_Date'].dt.year - 1

    # Exclude Battery Electric vehicles (to avoid double counting)
    vehicles_q1_adjusted = vehicles_q1[vehicles_q1['Type'] != 'Battery Electric'].copy()

    # For Plug-in Hybrid, reduce emissions by 50%
    vehicles_q1_adjusted.loc[vehicles_q1_adjusted['Type'] == 'Plug-in Hybrid', 'tCo2e'] *= 0.5

    # Sum tCO2e by year
    vehicles_yearly = vehicles_q1_adjusted.groupby('year')['tCo2e'].sum().reset_index()
    vehicles_yearly.columns = ['year', 'vehicles_tco2e']

    return vehicles_yearly


def process_energy_data(energy_df):
    """
    Process municipal energy data to calculate yearly emissions.

    Separates electric from other fuels for detailed tracking.

    Args:
        energy_df (pd.DataFrame): Raw municipal energy data

    Returns:
        tuple: (energy_yearly, energy_electric, energy_other)
            - energy_yearly: Total municipal buildings emissions
            - energy_electric: Municipal electric emissions only
            - energy_other: Municipal other fuels emissions only
    """
    energy_df = energy_df.copy()

    # Separate electric from other fuels
    energy_electric = energy_df[energy_df['account_fuel'] == 'Electric'].groupby('fiscal_year')['mtco2e'].sum().reset_index()
    energy_electric.columns = ['year', 'electric_mtco2e']

    energy_other = energy_df[energy_df['account_fuel'] != 'Electric'].groupby('fiscal_year')['mtco2e'].sum().reset_index()
    energy_other.columns = ['year', 'other_fuels_mtco2e']

    # Total municipal buildings
    energy_yearly = energy_df.groupby('fiscal_year')['mtco2e'].sum().reset_index()
    energy_yearly.columns = ['year', 'municipal_buildings_mtco2e']

    return energy_yearly, energy_electric, energy_other


def process_residential_commercial_electricity(mass_save_data, year=None):
    """
    Process Mass Save data to calculate residential and commercial electricity emissions.

    Args:
        mass_save_data (pd.DataFrame): Mass Save energy usage data
        year (int, optional): Year for emission factor (for future projections).
                             If None, uses current/historical factor.

    Returns:
        tuple: (residential_electric_yearly, commercial_electric_yearly)
    """
    # Get emission factor (uses centralized module)
    electric_emission_factor = emission_factors.get_emission_factor('ELECTRIC', year)

    # Residential electricity
    residential_electric = mass_save_data[mass_save_data['Sector'] == 'Residential & Low-Income'].copy()
    residential_electric['residential_electric_mtco2e'] = (
        residential_electric['Electric_MWh'] * 1000 * electric_emission_factor
    )
    residential_electric_yearly = residential_electric[['Year', 'residential_electric_mtco2e']].copy()
    residential_electric_yearly.columns = ['year', 'residential_electric_mtco2e']
    residential_electric_yearly['year'] = residential_electric_yearly['year'].astype(int)

    # Commercial electricity
    commercial_electric = mass_save_data[mass_save_data['Sector'] == 'Commercial & Industrial'].copy()
    commercial_electric['commercial_electric_mtco2e'] = (
        commercial_electric['Electric_MWh'] * 1000 * electric_emission_factor
    )
    commercial_electric_yearly = commercial_electric[['Year', 'commercial_electric_mtco2e']].copy()
    commercial_electric_yearly.columns = ['year', 'commercial_electric_mtco2e']
    commercial_electric_yearly['year'] = commercial_electric_yearly['year'].astype(int)

    return residential_electric_yearly, commercial_electric_yearly


def process_fossil_fuel_heating(fossil_fuel_results):
    """
    Process fossil fuel heating data from calculate_total_fossil_fuel_heating.

    Args:
        fossil_fuel_results (pd.DataFrame): Results from calculate_total_fossil_fuel_heating()

    Returns:
        pd.DataFrame: Yearly fossil fuel heating emissions
    """
    fossil_fuel_yearly = fossil_fuel_results[['year', 'total_fossil_fuel_mtco2e']].copy()
    fossil_fuel_yearly.columns = ['year', 'residential_fossil_fuel_mtco2e']
    fossil_fuel_yearly['year'] = fossil_fuel_yearly['year'].astype(int)

    return fossil_fuel_yearly


def merge_all_emissions_data(vehicles_yearly, energy_yearly, energy_electric, energy_other,
                              fossil_fuel_yearly, residential_electric_yearly, commercial_electric_yearly):
    """
    Merge all emission data sources into a single dataframe.

    Args:
        vehicles_yearly: Vehicle emissions by year
        energy_yearly: Municipal building emissions by year
        energy_electric: Municipal electric emissions by year
        energy_other: Municipal other fuels emissions by year
        fossil_fuel_yearly: Residential fossil fuel heating by year
        residential_electric_yearly: Residential electricity by year
        commercial_electric_yearly: Commercial electricity by year

    Returns:
        pd.DataFrame: Combined emissions data with all categories
    """
    combined_df = pd.merge(vehicles_yearly, energy_yearly, on='year', how='outer')
    combined_df = pd.merge(combined_df, energy_electric, on='year', how='left')
    combined_df = pd.merge(combined_df, energy_other, on='year', how='left')
    combined_df = pd.merge(combined_df, fossil_fuel_yearly, on='year', how='left')
    combined_df = pd.merge(combined_df, residential_electric_yearly, on='year', how='left')
    combined_df = pd.merge(combined_df, commercial_electric_yearly, on='year', how='left')
    combined_df = combined_df.sort_values('year')
    combined_df = combined_df.fillna(0)

    # Filter to start from 2019 (when vehicle data begins)
    combined_df = combined_df[combined_df['year'] >= 2019]

    return combined_df


def get_baseline_year(combined_df):
    """
    Return the most recent year in combined_df where all key emission categories
    have non-zero values — i.e. the latest fully-populated historical year.

    Projections and chart "historical vs projected" cutoffs should key off this
    rather than a hardcoded constant.
    """
    key_cols = [
        'vehicles_tco2e',
        'municipal_buildings_mtco2e',
        'residential_fossil_fuel_mtco2e',
        'residential_electric_mtco2e',
        'commercial_electric_mtco2e',
    ]
    has_all = (combined_df[key_cols] > 0).all(axis=1)
    years_with_data = combined_df[has_all]['year']
    if len(years_with_data) > 0:
        return int(years_with_data.max())
    return int(combined_df['year'].max())


def calculate_total_emissions(combined_df):
    """
    Calculate total emissions by summing all categories.

    Args:
        combined_df (pd.DataFrame): Combined emissions data

    Returns:
        pd.DataFrame: Combined data with 'total_tco2e' column added
    """
    combined_df = combined_df.copy()

    combined_df['total_tco2e'] = (
        combined_df['vehicles_tco2e'] +
        combined_df['municipal_buildings_mtco2e'] +
        combined_df['residential_fossil_fuel_mtco2e'] +
        combined_df['residential_electric_mtco2e'] +
        combined_df['commercial_electric_mtco2e']
    )

    return combined_df


def add_population_data(combined_df, population_df):
    """
    Add population data to combined emissions dataframe.

    Args:
        combined_df (pd.DataFrame): Combined emissions data
        population_df (pd.DataFrame): Population data by year

    Returns:
        pd.DataFrame: Combined data with population column
    """
    combined_df = pd.merge(
        combined_df,
        population_df[['Year', 'Population']],
        left_on='year',
        right_on='Year',
        how='left'
    )
    combined_df = combined_df.drop('Year', axis=1)

    return combined_df


def prepare_home_dashboard_data():
    """
    Main function to prepare all data for the Home dashboard.

    This is the primary entry point that orchestrates all calculations.
    Loads data from all sources and processes it into a combined dataframe.

    Returns:
        tuple: (combined_df, metadata_dict) where:
            - combined_df: DataFrame with all emissions data by year
            - metadata_dict: Dictionary with metadata about the calculations
                - 'fossil_fuel_metadata': Metadata from fossil fuel calculations
                - 'most_recent_year': Most recent year in the data
    """
    # Load all datasets
    vehicles_df = load_vehicle_data()
    energy_df = load_energy_data()
    mass_save_data = load_mass_save_data()
    fossil_fuel_data_tuple = calculate_total_fossil_fuel_heating()

    if vehicles_df is None or energy_df is None or mass_save_data is None or fossil_fuel_data_tuple is None:
        raise ValueError("Failed to load one or more required datasets")

    fossil_fuel_results, fossil_fuel_metadata = fossil_fuel_data_tuple

    # Load and process population data
    population_df = pd.read_csv('data/truro-population.csv')
    population_df['Population'] = population_df['Population'].str.replace(',', '').astype(int)

    # Process all data sources
    vehicles_yearly = process_vehicles_data(vehicles_df)
    energy_yearly, energy_electric, energy_other = process_energy_data(energy_df)
    fossil_fuel_yearly = process_fossil_fuel_heating(fossil_fuel_results)
    residential_electric_yearly, commercial_electric_yearly = process_residential_commercial_electricity(mass_save_data)

    # Merge all data
    combined_df = merge_all_emissions_data(
        vehicles_yearly, energy_yearly, energy_electric, energy_other,
        fossil_fuel_yearly, residential_electric_yearly, commercial_electric_yearly
    )

    # Calculate totals
    combined_df = calculate_total_emissions(combined_df)

    # Add population
    combined_df = add_population_data(combined_df, population_df)

    # Prepare metadata
    metadata = {
        'fossil_fuel_metadata': fossil_fuel_metadata,
        'most_recent_year': int(combined_df['year'].max())
    }

    return combined_df, metadata


if __name__ == '__main__':
    # Test the module
    print("Preparing home dashboard data...")
    combined_df, metadata = prepare_home_dashboard_data()

    print(f"\nData prepared for years: {combined_df['year'].min():.0f} - {combined_df['year'].max():.0f}")
    print(f"Most recent year: {metadata['most_recent_year']}")

    print("\nRecent emissions (mtCO2e):")
    recent = combined_df[combined_df['year'] >= 2021][['year', 'vehicles_tco2e', 'municipal_buildings_mtco2e',
                                                         'residential_fossil_fuel_mtco2e', 'total_tco2e']]
    print(recent.to_string(index=False))

    baseline_year = get_baseline_year(combined_df)
    print(f"\nBaseline year (most recent complete data): {baseline_year}")
    print(f"{baseline_year} Total Emissions: {combined_df[combined_df['year']==baseline_year]['total_tco2e'].values[0]:.2f} mtCO2e")
