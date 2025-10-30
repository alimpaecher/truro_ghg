"""
Regression tests for Home.py

These tests verify that the Home page's data processing and calculations
remain consistent after refactoring.
"""

import sys
import os
import pytest
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock streamlit
class MockStreamlit:
    @staticmethod
    def cache_data(ttl=None):
        def decorator(func):
            return func
        return decorator

    @staticmethod
    def error(msg):
        print(f"Error: {msg}")

    @staticmethod
    def set_page_config(**kwargs):
        pass

    @staticmethod
    def title(text):
        pass

    @staticmethod
    def success(text):
        pass

    @staticmethod
    def subheader(text):
        pass

    @staticmethod
    def columns(n):
        return [MockStreamlit() for _ in range(n)]

    @staticmethod
    def metric(label, value, delta=None):
        pass

sys.modules['streamlit'] = MockStreamlit()

from data_loader import load_vehicle_data, load_energy_data, load_mass_save_data, calculate_total_fossil_fuel_heating


class TestHomePageCalculations:
    """Test the key calculations performed in Home.py."""

    def test_2023_total_emissions(self):
        """Test that 2023 total emissions match expected value.

        This is a critical regression test for the main dashboard metric.
        """
        # Replicate Home.py logic for 2023
        vehicles_df = load_vehicle_data()
        energy_df = load_energy_data()
        mass_save_data = load_mass_save_data()
        fossil_fuel_data_tuple = calculate_total_fossil_fuel_heating()

        assert vehicles_df is not None
        assert energy_df is not None
        assert mass_save_data is not None
        assert fossil_fuel_data_tuple is not None

        fossil_fuel_results, fossil_fuel_metadata = fossil_fuel_data_tuple

        # Process vehicles data (same logic as Home.py)
        vehicles_df['Quarter_Date'] = pd.to_datetime(vehicles_df['Quarter'])
        vehicles_df['Month'] = vehicles_df['Quarter_Date'].dt.month
        vehicles_q1 = vehicles_df[vehicles_df['Month'] == 1].copy()
        vehicles_q1['year'] = vehicles_q1['Quarter_Date'].dt.year - 1

        # Adjust for EVs
        vehicles_q1_adjusted = vehicles_q1[vehicles_q1['Type'] != 'Battery Electric'].copy()
        vehicles_q1_adjusted.loc[vehicles_q1_adjusted['Type'] == 'Plug-in Hybrid', 'tCo2e'] *= 0.5

        vehicles_yearly = vehicles_q1_adjusted.groupby('year')['tCo2e'].sum().reset_index()
        vehicles_yearly.columns = ['year', 'vehicles_tco2e']

        # Process energy data
        energy_df = energy_df[energy_df['fiscal_year'] < 2025]
        energy_yearly = energy_df.groupby('fiscal_year')['mtco2e'].sum().reset_index()
        energy_yearly.columns = ['year', 'municipal_buildings_mtco2e']

        # Fossil fuel heating
        fossil_fuel_yearly = fossil_fuel_results[['year', 'total_fossil_fuel_mtco2e']].copy()
        fossil_fuel_yearly.columns = ['year', 'residential_fossil_fuel_mtco2e']
        fossil_fuel_yearly['year'] = fossil_fuel_yearly['year'].astype(int)

        # Residential electricity
        ELECTRIC_EMISSION_FACTOR = 0.000239
        residential_electric = mass_save_data[mass_save_data['Sector'] == 'Residential & Low-Income'].copy()
        residential_electric['residential_electric_mtco2e'] = residential_electric['Electric_MWh'] * 1000 * ELECTRIC_EMISSION_FACTOR
        residential_electric_yearly = residential_electric[['Year', 'residential_electric_mtco2e']].copy()
        residential_electric_yearly.columns = ['year', 'residential_electric_mtco2e']
        residential_electric_yearly['year'] = residential_electric_yearly['year'].astype(int)

        # Commercial electricity
        commercial_electric = mass_save_data[mass_save_data['Sector'] == 'Commercial & Industrial'].copy()
        commercial_electric['commercial_electric_mtco2e'] = commercial_electric['Electric_MWh'] * 1000 * ELECTRIC_EMISSION_FACTOR
        commercial_electric_yearly = commercial_electric[['Year', 'commercial_electric_mtco2e']].copy()
        commercial_electric_yearly.columns = ['year', 'commercial_electric_mtco2e']
        commercial_electric_yearly['year'] = commercial_electric_yearly['year'].astype(int)

        # Merge
        combined_df = pd.merge(vehicles_yearly, energy_yearly, on='year', how='outer')
        combined_df = pd.merge(combined_df, fossil_fuel_yearly, on='year', how='left')
        combined_df = pd.merge(combined_df, residential_electric_yearly, on='year', how='left')
        combined_df = pd.merge(combined_df, commercial_electric_yearly, on='year', how='left')
        combined_df = combined_df.fillna(0)
        combined_df = combined_df[combined_df['year'] >= 2019]

        # Calculate total
        combined_df['total_tco2e'] = (combined_df['vehicles_tco2e'] +
                                       combined_df['municipal_buildings_mtco2e'] +
                                       combined_df['residential_fossil_fuel_mtco2e'] +
                                       combined_df['residential_electric_mtco2e'] +
                                       combined_df['commercial_electric_mtco2e'])

        # Get 2023 total
        data_2023 = combined_df[combined_df['year'] == 2023]
        assert len(data_2023) > 0, "No 2023 data found"

        total_2023 = data_2023['total_tco2e'].values[0]

        # Expected value with 2% tolerance
        # Baseline: 26,019 mtCO2e for 2023
        expected = 26019.0
        tolerance = expected * 0.02

        assert abs(total_2023 - expected) < tolerance, \
            f"2023 total emissions changed: expected ~{expected}, got {total_2023}"

    def test_emissions_components_non_negative(self):
        """Test that all emission components are non-negative."""
        vehicles_df = load_vehicle_data()
        energy_df = load_energy_data()
        mass_save_data = load_mass_save_data()
        fossil_fuel_data_tuple = calculate_total_fossil_fuel_heating()

        fossil_fuel_results, _ = fossil_fuel_data_tuple

        # Check vehicles
        vehicles_df['Quarter_Date'] = pd.to_datetime(vehicles_df['Quarter'])
        vehicles_df['Month'] = vehicles_df['Quarter_Date'].dt.month
        vehicles_q1 = vehicles_df[vehicles_df['Month'] == 1].copy()
        assert (vehicles_q1['tCo2e'] >= 0).all(), "Negative vehicle emissions"

        # Check energy
        assert (energy_df['mtco2e'] >= 0).all(), "Negative energy emissions"

        # Check fossil fuel
        assert (fossil_fuel_results['total_fossil_fuel_mtco2e'] >= 0).all(), \
            "Negative fossil fuel emissions"

    def test_combined_dataframe_structure(self):
        """Test that the combined dataframe has the expected structure."""
        vehicles_df = load_vehicle_data()
        energy_df = load_energy_data()
        mass_save_data = load_mass_save_data()
        fossil_fuel_data_tuple = calculate_total_fossil_fuel_heating()

        assert vehicles_df is not None
        assert energy_df is not None
        assert mass_save_data is not None
        assert fossil_fuel_data_tuple is not None

        # This test verifies the data structure hasn't changed
        expected_vehicle_columns = ['Type', 'Number', 'Quarter', 'tCo2e']
        for col in expected_vehicle_columns:
            assert col in vehicles_df.columns, f"Missing vehicle column: {col}"

        assert 'fiscal_year' in energy_df.columns
        assert 'mtco2e' in energy_df.columns

        assert 'Sector' in mass_save_data.columns
        assert 'Electric_MWh' in mass_save_data.columns


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
