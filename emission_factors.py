"""
Centralized emission factors module.

This module provides a single source of truth for all emission factors
used in the GHG emissions calculations. It handles:
- Loading emission factors from CSV
- Grid decarbonization adjustments based on clean energy goals
- Backward compatibility with existing hard-coded values

All emission factors should be accessed through this module to ensure consistency.
"""

import pandas as pd
import numpy as np


# Cache the loaded data at module level
_emission_factors_df = None
_clean_energy_goals_df = None


def _load_emission_factors():
    """Load emission factors from CSV (cached)."""
    global _emission_factors_df
    if _emission_factors_df is None:
        df = pd.read_csv('data/emission_factors.csv')
        # Skip the first row (example row) and reset index
        df = df.iloc[1:].reset_index(drop=True)
        # Rename the tCO2e column for easier access
        df = df.rename(columns={'Unnamed: 17': 'tCO2e'})
        # Convert tCO2e to float
        df['tCO2e'] = pd.to_numeric(df['tCO2e'], errors='coerce')
        _emission_factors_df = df
    return _emission_factors_df


def _load_clean_energy_goals():
    """Load clean energy goals from CSV (cached)."""
    global _clean_energy_goals_df
    if _clean_energy_goals_df is None:
        _clean_energy_goals_df = pd.read_csv('data/goals/clean_energy_goals.csv')
        # Clean percentage column
        _clean_energy_goals_df['green energy'] = (
            _clean_energy_goals_df['green energy']
            .str.replace('%', '')
            .astype(float) / 100.0
        )
    return _clean_energy_goals_df


def get_grid_clean_energy_percent(year):
    """
    Get the percentage of clean energy in the grid for a given year.

    Uses clean_energy_goals.csv with linear interpolation between data points.

    Args:
        year (int): The year to get clean energy percentage for

    Returns:
        float: Clean energy percentage (0.0 to 1.0)
    """
    goals_df = _load_clean_energy_goals()

    # If year is in the data, return it directly
    if year in goals_df['year'].values:
        return goals_df[goals_df['year'] == year]['green energy'].values[0]

    # Otherwise, interpolate
    # Find the two closest years
    years_before = goals_df[goals_df['year'] <= year]
    years_after = goals_df[goals_df['year'] >= year]

    if len(years_before) == 0:
        # Before first data point, use first value
        return goals_df['green energy'].iloc[0]
    elif len(years_after) == 0:
        # After last data point, use last value
        return goals_df['green energy'].iloc[-1]
    else:
        # Interpolate between closest points
        year_before = years_before['year'].max()
        year_after = years_after['year'].min()

        pct_before = goals_df[goals_df['year'] == year_before]['green energy'].values[0]
        pct_after = goals_df[goals_df['year'] == year_after]['green energy'].values[0]

        # Linear interpolation
        ratio = (year - year_before) / (year_after - year_before)
        return pct_before + (pct_after - pct_before) * ratio


def get_base_emission_factor(fuel_type):
    """
    Get the base emission factor for a fuel type from the CSV.

    This returns the current (2019-2024) emission factor without any
    grid decarbonization adjustments.

    Args:
        fuel_type (str): One of:
            - 'GASOLINE' or 'GAL': Motor gasoline
            - 'DIESEL': Diesel oil
            - 'OIL' or 'HEATING_OIL': Heating oil (diesel)
            - 'PROPANE' or 'GAS': Propane
            - 'ELECTRIC' or 'ELECTRICITY': Electricity

    Returns:
        float: Emission factor in tCO2e per unit
            - Gasoline/Diesel/Oil/Propane: tCO2e per gallon
            - Electric: tCO2e per kWh
    """
    factors_df = _load_emission_factors()

    # Map fuel types to CSV rows
    fuel_mapping = {
        'GASOLINE': ('Motor gasoline (petrol)', 1.0),  # (fuel_name, conversion_factor)
        'GAL': ('Motor gasoline (petrol)', 1.0),
        'DIESEL': ('Diesel oil', 1.0),  # Row 8 - Trucks
        'OIL': ('Diesel oil', 1.0),     # Row 6 - Heating oil
        'HEATING_OIL': ('Diesel oil', 1.0),
        'PROPANE': ('Propane', 1.0),
        'GAS': ('Propane', 1.0),
        'ELECTRIC': ('Electricity', 0.001),  # CSV is in tCO2e/MWh, convert to tCO2e/kWh
        'ELECTRICITY': ('Electricity', 0.001)
    }

    fuel_info = fuel_mapping.get(fuel_type.upper())
    if fuel_info is None:
        raise ValueError(f"Unknown fuel type: {fuel_type}")

    fuel_name, conversion_factor = fuel_info

    # Find the row(s) for this fuel (escape regex special characters)
    matching_rows = factors_df[factors_df['Fuel type or activity'].str.contains(fuel_name, na=False, regex=False)]

    if len(matching_rows) == 0:
        raise ValueError(f"No emission factor found for {fuel_type}")

    # Special handling for different diesel types
    # After skipping example row, indices are: 0-based from actual data rows
    if fuel_type.upper() in ['OIL', 'HEATING_OIL']:
        # Use heating oil row (originally row 6, now row 3 after skipping example)
        # This has tCO2e = 0.010200
        heating_oil_rows = matching_rows[matching_rows['tCO2e'] == 0.010200]
        if len(heating_oil_rows) > 0:
            return heating_oil_rows['tCO2e'].values[0] * conversion_factor
        # Fallback to first diesel row
        return matching_rows['tCO2e'].values[0] * conversion_factor
    elif fuel_type.upper() == 'DIESEL':
        # Use diesel for trucks (tCO2e = 0.010300)
        diesel_truck_rows = matching_rows[matching_rows['tCO2e'] == 0.010300]
        if len(diesel_truck_rows) > 0:
            return diesel_truck_rows['tCO2e'].values[0] * conversion_factor
        # Fallback to first diesel row
        return matching_rows['tCO2e'].values[0] * conversion_factor

    # For all other fuels, use first matching row
    base_factor = matching_rows['tCO2e'].values[0]

    # Apply conversion factor (e.g., MWh to kWh for electricity)
    return base_factor * conversion_factor


def get_emission_factor(fuel_type, year=None):
    """
    Get the emission factor for a fuel type in a given year.

    For electricity in future years, applies grid decarbonization based on clean energy goals.
    For fossil fuels and historical electricity, returns the constant base emission factor.

    IMPORTANT: The base electricity emission factor (0.000239 tCO2e/kWh) reflects the grid mix
    as of ~2020 (54% clean). We only apply additional decarbonization for improvements beyond
    this baseline to avoid double-counting.

    Args:
        fuel_type (str): Fuel type (see get_base_emission_factor for options)
        year (int, optional): Year for the emission factor. Defaults to None (current/historical).
            For None or year ≤2024: returns base emission factors (no grid decarbonization)
            For future years (>2024): applies grid decarbonization to electricity only

    Returns:
        float: Emission factor in tCO2e per unit

    Examples:
        >>> get_emission_factor('GASOLINE')  # Returns 0.00882
        >>> get_emission_factor('ELECTRIC')  # Returns 0.000239 (no year = historical)
        >>> get_emission_factor('ELECTRIC', 2024)  # Returns 0.000239 (historical)
        >>> get_emission_factor('ELECTRIC', 2030)  # Returns ~0.000102 (70% clean vs 54% baseline)
        >>> get_emission_factor('ELECTRIC', 2050)  # Returns ~0 (100% clean grid)
    """
    base_factor = get_base_emission_factor(fuel_type)

    # Only apply grid decarbonization to electricity for FUTURE years (> 2024)
    if fuel_type.upper() in ['ELECTRIC', 'ELECTRICITY'] and year is not None and year > 2024:
        # Get clean energy percentage for this year
        clean_pct_future = get_grid_clean_energy_percent(year)

        # Baseline clean energy percentage (when base factor was measured, ~2020)
        clean_pct_baseline = get_grid_clean_energy_percent(2020)

        # Calculate the ratio of fossil fuel percentage
        # If baseline was 54% clean (46% fossil), and future is 70% clean (30% fossil),
        # then emissions should be 30/46 = 65% of baseline
        fossil_pct_baseline = 1.0 - clean_pct_baseline
        fossil_pct_future = 1.0 - clean_pct_future

        if fossil_pct_baseline > 0:
            decarbonization_ratio = fossil_pct_future / fossil_pct_baseline
        else:
            decarbonization_ratio = 0.0  # Grid was already 100% clean at baseline

        # Adjusted emission factor based on grid improvement
        return base_factor * decarbonization_ratio

    # For all other fuels and historical electricity, return base factor unchanged
    return base_factor


# Convenience constants for backward compatibility
# These match the hard-coded values in the original code
GASOLINE_EMISSION_FACTOR = 0.00882   # tCO2e per gallon
DIESEL_EMISSION_FACTOR = 0.01030     # tCO2e per gallon
HEATING_OIL_EMISSION_FACTOR = 0.01030  # tCO2e per gallon
PROPANE_EMISSION_FACTOR = 0.00574    # tCO2e per gallon (actually 0.00574)
ELECTRIC_EMISSION_FACTOR_2024 = 0.000239  # tCO2e per kWh (current grid)


def get_all_factors(year=None):
    """
    Get all emission factors for a given year as a dictionary.

    Useful for passing to calculation functions that need multiple factors.

    Args:
        year (int, optional): Year for emission factors. Defaults to None (current/historical).

    Returns:
        dict: Dictionary with keys:
            - 'GASOLINE': Gasoline factor (tCO2e/gal)
            - 'DIESEL': Diesel factor (tCO2e/gal)
            - 'OIL': Heating oil factor (tCO2e/gal)
            - 'PROPANE': Propane factor (tCO2e/gal)
            - 'ELECTRIC': Electricity factor (tCO2e/kWh)
    """
    return {
        'GASOLINE': get_emission_factor('GASOLINE', year),
        'DIESEL': get_emission_factor('DIESEL', year),
        'OIL': get_emission_factor('OIL', year),
        'PROPANE': get_emission_factor('PROPANE', year),
        'ELECTRIC': get_emission_factor('ELECTRIC', year)
    }


if __name__ == '__main__':
    # Test the module
    print("Emission Factors (Current/Historical - no year specified):")
    print(f"  Gasoline: {get_emission_factor('GASOLINE'):.6f} tCO2e/gal")
    print(f"  Diesel: {get_emission_factor('DIESEL'):.6f} tCO2e/gal")
    print(f"  Heating Oil: {get_emission_factor('OIL'):.6f} tCO2e/gal")
    print(f"  Propane: {get_emission_factor('PROPANE'):.6f} tCO2e/gal")
    print(f"  Electricity: {get_emission_factor('ELECTRIC'):.6f} tCO2e/kWh")

    print("\nBackward Compatibility Check:")
    print(f"  Matches hard-coded gasoline (0.00882): {abs(get_emission_factor('GASOLINE') - 0.00882) < 0.00001}")
    print(f"  Matches hard-coded diesel (0.01030): {abs(get_emission_factor('DIESEL') - 0.01030) < 0.00001}")
    print(f"  Matches hard-coded propane (0.00574): {abs(get_emission_factor('PROPANE') - 0.00574) < 0.00001}")
    print(f"  Matches hard-coded electric (0.000239): {abs(get_emission_factor('ELECTRIC') - 0.000239) < 0.000001}")

    print("\nGrid Decarbonization (Future Projections):")
    for year in [2025, 2030, 2040, 2050]:
        clean_pct = get_grid_clean_energy_percent(year)
        elec_factor = get_emission_factor('ELECTRIC', year)
        reduction_pct = (1 - elec_factor / 0.000239) * 100
        print(f"  {year}: {clean_pct*100:.1f}% clean grid, {elec_factor:.6f} tCO2e/kWh ({reduction_pct:.1f}% reduction)")
