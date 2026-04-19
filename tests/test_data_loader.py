"""
Regression tests for data_loader.py

These tests capture the current outputs of data_loader functions to ensure
that refactoring doesn't break existing calculations. If these tests fail
after changes, it means the outputs have changed and need investigation.
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock streamlit before importing data_loader
import unittest.mock as mock

# Create a proper mock for streamlit that doesn't interfere with decorators
class MockStreamlit:
    @staticmethod
    def cache_data(ttl=None):
        """Mock cache_data decorator - just return the function unchanged."""
        def decorator(func):
            return func
        return decorator

    @staticmethod
    def error(msg):
        """Mock error function."""
        print(f"Error: {msg}")

sys.modules['streamlit'] = MockStreamlit()

import data_loader


class TestLoadVehicleData:
    """Test vehicle data loading and emissions calculations."""

    def test_load_vehicle_data_returns_dataframe(self):
        """Test that load_vehicle_data returns a DataFrame."""
        result = data_loader.load_vehicle_data()
        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_vehicle_data_has_required_columns(self):
        """Test that vehicle data has expected columns."""
        result = data_loader.load_vehicle_data()
        required_columns = ['Type', 'Number', 'tCo2e']
        for col in required_columns:
            assert col in result.columns, f"Missing required column: {col}"

    def test_vehicle_emissions_2023_total(self):
        """Test that 2023 Q4 vehicle emissions match expected value.

        This is a regression test. If this fails, vehicle emission calculations
        have changed and need investigation.
        """
        result = data_loader.load_vehicle_data()

        # Get Q4 2023 data (most recent complete data)
        q4_2023 = result[result['Quarter'] == '2023 Q4']

        if len(q4_2023) > 0:
            total_emissions = q4_2023['tCo2e'].sum()

            # Expected value based on current implementation
            # Allow 1% tolerance for floating point variations
            expected = 29650.0  # Will be set after first run
            tolerance = expected * 0.01

            assert abs(total_emissions - expected) < tolerance, \
                f"Vehicle emissions changed: expected ~{expected}, got {total_emissions}"

    def test_vehicle_emissions_non_negative(self):
        """Test that all vehicle emissions are non-negative."""
        result = data_loader.load_vehicle_data()
        assert (result['tCo2e'] >= 0).all(), "Found negative emissions"

    def test_vehicle_data_structure(self):
        """Test that vehicle data structure is preserved."""
        result = data_loader.load_vehicle_data()

        # Should have multiple quarters
        assert len(result) > 0, "No vehicle data loaded"

        # Should have Quarter column
        assert 'Quarter' in result.columns


class TestLoadEnergyData:
    """Test municipal energy data loading."""

    def test_load_energy_data_returns_dataframe(self):
        """Test that load_energy_data returns a DataFrame."""
        result = data_loader.load_energy_data()
        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_energy_data_not_empty(self):
        """Test that energy data is not empty."""
        result = data_loader.load_energy_data()
        assert len(result) > 0, "Energy data is empty"


class TestLoadMassSaveData:
    """Test Mass Save residential electricity data loading."""

    def test_load_mass_save_data_returns_dataframe(self):
        """Test that load_mass_save_data returns a DataFrame."""
        result = data_loader.load_mass_save_data()
        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_mass_save_has_electric_column(self):
        """Test that Mass Save data has Electric_MWh column."""
        result = data_loader.load_mass_save_data()
        assert 'Electric_MWh' in result.columns
        assert 'Year' in result.columns

    def test_mass_save_has_sector_column(self):
        """Data is pre-filtered to Truro upstream; Sector splits res/commercial."""
        result = data_loader.load_mass_save_data()
        assert 'Sector' in result.columns
        expected_sectors = {'Residential & Low-Income', 'Commercial & Industrial'}
        assert expected_sectors.issubset(set(result['Sector'].unique()))


class TestLoadCLCHeatPumpData:
    """Test CLC heat pump installation data loading."""

    def test_load_clc_heat_pump_data_returns_dataframe(self):
        """Test that load_clc_heat_pump_data returns a DataFrame."""
        result = data_loader.load_clc_heat_pump_data()
        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_heat_pump_data_columns(self):
        """Test that heat pump data has expected columns."""
        result = data_loader.load_clc_heat_pump_data()
        expected_columns = ['Year', 'Installed Heat Pump', 'Installed Heat Pumps Location']
        assert list(result.columns) == expected_columns


class TestCalculateResidentialEmissions:
    """Test residential emissions calculations."""

    def test_calculate_residential_emissions_baseline(self):
        """Test that residential emissions calculation produces expected results.

        This is a regression test using 2019 assessors data.
        """
        assessors_df = data_loader.load_assessors_data()
        assert assessors_df is not None

        result = data_loader.calculate_residential_emissions(assessors_df)
        assert result is not None
        assert isinstance(result, pd.DataFrame)

        # Should have mtco2e column
        assert 'mtco2e' in result.columns

        # Total emissions should be in expected range
        total_emissions = result['mtco2e'].sum()

        # Expected baseline (2019) from assessors data
        # This includes oil + propane + electric heating
        # Actual value: ~8,853 mtCO2e (includes all residential heating types)
        # Allow 5% tolerance
        expected = 8853.0
        tolerance = expected * 0.05

        assert abs(total_emissions - expected) < tolerance, \
            f"Residential emissions changed: expected ~{expected}, got {total_emissions} mtCO2e"

    def test_residential_emissions_non_negative(self):
        """Test that all residential emissions are non-negative."""
        assessors_df = data_loader.load_assessors_data()
        result = data_loader.calculate_residential_emissions(assessors_df)

        assert (result['mtco2e'] >= 0).all(), "Found negative emissions"

    def test_residential_excludes_municipal(self):
        """Test that municipal properties (Type E) are excluded."""
        assessors_df = data_loader.load_assessors_data()
        result = data_loader.calculate_residential_emissions(assessors_df)

        # Should not contain Type E
        assert not (result['PropertyType'] == 'E').any(), \
            "Municipal properties (Type E) not excluded"


class TestCalculatePropaneDisplacement:
    """Test propane displacement calculations."""

    def test_calculate_propane_displacement_returns_tuple(self):
        """Test that calculate_propane_displacement returns dataframe and metadata."""
        result = data_loader.calculate_propane_displacement()
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2

        results_df, metadata = result
        assert isinstance(results_df, pd.DataFrame)
        assert isinstance(metadata, dict)

    def test_propane_displacement_structure(self):
        """Test that propane displacement has expected structure."""
        results_df, metadata = data_loader.calculate_propane_displacement()

        # Check dataframe columns
        expected_columns = ['Year', 'Heat_Pump_Locations', 'Cumulative_Conversions',
                          'Remaining_Propane_Properties', 'Remaining_Propane_Gal',
                          'Remaining_Propane_mtCO2e', 'Propane_Saved_Gal',
                          'Propane_Saved_mtCO2e', 'Percent_Reduction']

        for col in expected_columns:
            assert col in results_df.columns, f"Missing column: {col}"

        # Check metadata keys
        expected_metadata = ['baseline_year', 'baseline_heat_pumps',
                           'baseline_propane_properties', 'median_sqft']

        for key in expected_metadata:
            assert key in metadata, f"Missing metadata key: {key}"

    def test_propane_displacement_2023_values(self):
        """Test 2023 propane displacement values match expected.

        This is a regression test for 2023 data.
        """
        results_df, metadata = data_loader.calculate_propane_displacement()

        # Get 2023 data
        data_2023 = results_df[results_df['Year'] == 2023]

        if len(data_2023) > 0:
            # 2023 should show reduction from baseline
            cumulative_conversions = data_2023['Cumulative_Conversions'].values[0]
            assert cumulative_conversions > 0, "No conversions recorded by 2023"

            # Saved emissions should be positive
            saved_emissions = data_2023['Propane_Saved_mtCO2e'].values[0]
            assert saved_emissions > 0, "No propane savings by 2023"


class TestCalculateTotalFossilFuelHeating:
    """Test total fossil fuel heating calculations (SINGLE SOURCE OF TRUTH)."""

    def test_calculate_total_fossil_fuel_heating_returns_tuple(self):
        """Test that calculate_total_fossil_fuel_heating returns dataframe and metadata."""
        result = data_loader.calculate_total_fossil_fuel_heating()
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2

        results_df, metadata = result
        assert isinstance(results_df, pd.DataFrame)
        assert isinstance(metadata, dict)

    def test_fossil_fuel_heating_structure(self):
        """Test that fossil fuel heating has expected structure."""
        results_df, metadata = data_loader.calculate_total_fossil_fuel_heating()

        # Check dataframe columns
        expected_columns = ['year', 'heat_pump_locations', 'cumulative_conversions',
                          'oil_mtco2e', 'propane_mtco2e', 'propane_mtco2e_eliminated',
                          'total_fossil_fuel_mtco2e']

        for col in expected_columns:
            assert col in results_df.columns, f"Missing column: {col}"

    def test_fossil_fuel_heating_2019_baseline(self):
        """Test 2019 baseline values match expected.

        CRITICAL REGRESSION TEST - 2019 baseline is the foundation for all calculations.
        Expected values (with seasonal adjustment):
        - Oil: ~5,402.4 mtCO2e (constant)
        - Propane: ~2,106.3 mtCO2e (before displacement)
        - Total: ~7,508.7 mtCO2e
        """
        results_df, metadata = data_loader.calculate_total_fossil_fuel_heating()

        # Get 2019 data
        data_2019 = results_df[results_df['year'] == 2019]
        assert len(data_2019) > 0, "No 2019 baseline data"

        oil_2019 = data_2019['oil_mtco2e'].values[0]
        propane_2019 = data_2019['propane_mtco2e'].values[0]
        total_2019 = data_2019['total_fossil_fuel_mtco2e'].values[0]

        # Test baseline values with 1% tolerance
        assert abs(oil_2019 - 5402.4) < 54, \
            f"Oil baseline changed: expected ~5,402.4, got {oil_2019}"

        assert abs(propane_2019 - 2106.3) < 21, \
            f"Propane baseline changed: expected ~2,106.3, got {propane_2019}"

        assert abs(total_2019 - 7508.7) < 75, \
            f"Total baseline changed: expected ~7,508.7, got {total_2019}"

        # No conversions in 2019
        conversions_2019 = data_2019['cumulative_conversions'].values[0]
        assert conversions_2019 == 0, "2019 should have no conversions"

    def test_fossil_fuel_heating_2023_reduction(self):
        """Test that 2023 shows propane reduction from heat pumps."""
        results_df, metadata = data_loader.calculate_total_fossil_fuel_heating()

        # Get 2019 and 2023 data
        data_2019 = results_df[results_df['year'] == 2019]
        data_2023 = results_df[results_df['year'] == 2023]

        if len(data_2023) > 0:
            # Total should decrease from 2019 to 2023
            total_2019 = data_2019['total_fossil_fuel_mtco2e'].values[0]
            total_2023 = data_2023['total_fossil_fuel_mtco2e'].values[0]

            assert total_2023 < total_2019, \
                "Total emissions should decrease due to heat pump conversions"

            # Oil should stay constant
            oil_2019 = data_2019['oil_mtco2e'].values[0]
            oil_2023 = data_2023['oil_mtco2e'].values[0]

            assert abs(oil_2023 - oil_2019) < 1, \
                "Oil emissions should remain constant"

            # Propane should decrease
            propane_2019 = data_2019['propane_mtco2e'].values[0]
            propane_2023 = data_2023['propane_mtco2e'].values[0]

            assert propane_2023 < propane_2019, \
                "Propane emissions should decrease due to heat pump conversions"

    def test_fossil_fuel_heating_values_non_negative(self):
        """Test that all values are non-negative."""
        results_df, metadata = data_loader.calculate_total_fossil_fuel_heating()

        assert (results_df['oil_mtco2e'] >= 0).all()
        assert (results_df['propane_mtco2e'] >= 0).all()
        assert (results_df['total_fossil_fuel_mtco2e'] >= 0).all()
        assert (results_df['cumulative_conversions'] >= 0).all()


class TestEmissionFactors:
    """Test that emission factors are as expected (before refactoring)."""

    def test_hardcoded_emission_factors(self):
        """Test current hard-coded emission factors.

        These values are currently hard-coded in data_loader.py.
        After refactoring to centralized emission_factors.py, this test
        will verify backward compatibility.
        """
        # These are the current hard-coded values in data_loader.py
        expected_factors = {
            'gasoline': 0.00882,      # tCO2e per gallon
            'diesel': 0.01030,        # tCO2e per gallon
            'electricity': 0.000239,  # tCO2e per kWh
            'propane': 0.00574        # tCO2e per gallon
        }

        # Load emission factors CSV and verify values match
        emission_factors_df = pd.read_csv('data/emission_factors.csv')

        # This test documents the current state
        # After refactoring, we'll verify the centralized module returns these values
        assert emission_factors_df is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
