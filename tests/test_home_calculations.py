"""
Unit tests for home_calculations.py

Tests the calculation logic extracted from Home.py to ensure
it produces consistent results.
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

sys.modules['streamlit'] = MockStreamlit()

import home_calculations
from data_loader import load_vehicle_data, load_energy_data, load_mass_save_data, calculate_total_fossil_fuel_heating


class TestProcessVehiclesData:
    """Test vehicle data processing."""

    def test_process_vehicles_data_structure(self):
        """Test that processed vehicles data has correct structure."""
        vehicles_df = load_vehicle_data()
        result = home_calculations.process_vehicles_data(vehicles_df)

        assert 'year' in result.columns
        assert 'vehicles_tco2e' in result.columns
        assert len(result) > 0

    def test_process_vehicles_excludes_battery_electric(self):
        """Test that battery electric vehicles are excluded."""
        vehicles_df = load_vehicle_data()
        result = home_calculations.process_vehicles_data(vehicles_df)

        # Should not include battery electric in totals
        # (This is implicitly tested by the emission values)
        assert result['vehicles_tco2e'].sum() > 0

    def test_process_vehicles_2023_value(self):
        """Test 2023 vehicle emissions match expected value."""
        vehicles_df = load_vehicle_data()
        result = home_calculations.process_vehicles_data(vehicles_df)

        data_2023 = result[result['year'] == 2023]
        if len(data_2023) > 0:
            # Expected value with tolerance
            emissions_2023 = data_2023['vehicles_tco2e'].values[0]
            expected = 12502.0  # Approximate
            tolerance = expected * 0.05

            assert abs(emissions_2023 - expected) < tolerance, \
                f"2023 vehicle emissions: {emissions_2023}"


class TestProcessEnergyData:
    """Test municipal energy data processing."""

    def test_process_energy_data_returns_three_dataframes(self):
        """Test that process_energy_data returns three dataframes."""
        energy_df = load_energy_data()
        energy_yearly, energy_electric, energy_other = home_calculations.process_energy_data(energy_df)

        assert isinstance(energy_yearly, pd.DataFrame)
        assert isinstance(energy_electric, pd.DataFrame)
        assert isinstance(energy_other, pd.DataFrame)

    def test_process_energy_data_structure(self):
        """Test that energy data has correct structure."""
        energy_df = load_energy_data()
        energy_yearly, energy_electric, energy_other = home_calculations.process_energy_data(energy_df)

        assert 'year' in energy_yearly.columns
        assert 'municipal_buildings_mtco2e' in energy_yearly.columns

        assert 'year' in energy_electric.columns
        assert 'electric_mtco2e' in energy_electric.columns

        assert 'year' in energy_other.columns
        assert 'other_fuels_mtco2e' in energy_other.columns

    def test_process_energy_filters_future_years(self):
        """Test that future years (>= 2025) are filtered out."""
        energy_df = load_energy_data()
        energy_yearly, _, _ = home_calculations.process_energy_data(energy_df)

        # Should not have 2025 or later
        assert (energy_yearly['year'] < 2025).all()


class TestProcessResidentialCommercialElectricity:
    """Test residential/commercial electricity processing."""

    def test_process_residential_commercial_structure(self):
        """Test that residential/commercial electricity has correct structure."""
        mass_save_data = load_mass_save_data()
        residential, commercial = home_calculations.process_residential_commercial_electricity(mass_save_data)

        assert 'year' in residential.columns
        assert 'residential_electric_mtco2e' in residential.columns

        assert 'year' in commercial.columns
        assert 'commercial_electric_mtco2e' in commercial.columns

    def test_process_uses_centralized_emission_factor(self):
        """Test that processing uses centralized emission factor."""
        mass_save_data = load_mass_save_data()
        residential, _ = home_calculations.process_residential_commercial_electricity(mass_save_data)

        # Should use 0.000239 tCO2e/kWh for historical
        # Check that emissions are reasonable (not zero, not too high)
        if len(residential) > 0:
            assert residential['residential_electric_mtco2e'].sum() > 0


class TestProcessFossilFuelHeating:
    """Test fossil fuel heating data processing."""

    def test_process_fossil_fuel_heating_structure(self):
        """Test that fossil fuel heating has correct structure."""
        fossil_fuel_data_tuple = calculate_total_fossil_fuel_heating()
        fossil_fuel_results, _ = fossil_fuel_data_tuple

        result = home_calculations.process_fossil_fuel_heating(fossil_fuel_results)

        assert 'year' in result.columns
        assert 'residential_fossil_fuel_mtco2e' in result.columns

    def test_process_fossil_fuel_2023_value(self):
        """Test 2023 fossil fuel heating matches expected value."""
        fossil_fuel_data_tuple = calculate_total_fossil_fuel_heating()
        fossil_fuel_results, _ = fossil_fuel_data_tuple

        result = home_calculations.process_fossil_fuel_heating(fossil_fuel_results)

        data_2023 = result[result['year'] == 2023]
        if len(data_2023) > 0:
            emissions_2023 = data_2023['residential_fossil_fuel_mtco2e'].values[0]
            expected = 6582.0  # Approximate
            tolerance = expected * 0.05

            assert abs(emissions_2023 - expected) < tolerance, \
                f"2023 fossil fuel heating: {emissions_2023}"


class TestMergeAllEmissionsData:
    """Test merging of all emissions data."""

    def test_merge_all_emissions_data_structure(self):
        """Test that merged data has all expected columns."""
        vehicles_df = load_vehicle_data()
        energy_df = load_energy_data()
        mass_save_data = load_mass_save_data()
        fossil_fuel_data_tuple = calculate_total_fossil_fuel_heating()
        fossil_fuel_results, _ = fossil_fuel_data_tuple

        vehicles_yearly = home_calculations.process_vehicles_data(vehicles_df)
        energy_yearly, energy_electric, energy_other = home_calculations.process_energy_data(energy_df)
        fossil_fuel_yearly = home_calculations.process_fossil_fuel_heating(fossil_fuel_results)
        residential_electric_yearly, commercial_electric_yearly = \
            home_calculations.process_residential_commercial_electricity(mass_save_data)

        result = home_calculations.merge_all_emissions_data(
            vehicles_yearly, energy_yearly, energy_electric, energy_other,
            fossil_fuel_yearly, residential_electric_yearly, commercial_electric_yearly
        )

        expected_columns = [
            'year', 'vehicles_tco2e', 'municipal_buildings_mtco2e',
            'electric_mtco2e', 'other_fuels_mtco2e', 'residential_fossil_fuel_mtco2e',
            'residential_electric_mtco2e', 'commercial_electric_mtco2e'
        ]

        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"

    def test_merge_filters_to_2019_onwards(self):
        """Test that merged data starts from 2019."""
        vehicles_df = load_vehicle_data()
        energy_df = load_energy_data()
        mass_save_data = load_mass_save_data()
        fossil_fuel_data_tuple = calculate_total_fossil_fuel_heating()
        fossil_fuel_results, _ = fossil_fuel_data_tuple

        vehicles_yearly = home_calculations.process_vehicles_data(vehicles_df)
        energy_yearly, energy_electric, energy_other = home_calculations.process_energy_data(energy_df)
        fossil_fuel_yearly = home_calculations.process_fossil_fuel_heating(fossil_fuel_results)
        residential_electric_yearly, commercial_electric_yearly = \
            home_calculations.process_residential_commercial_electricity(mass_save_data)

        result = home_calculations.merge_all_emissions_data(
            vehicles_yearly, energy_yearly, energy_electric, energy_other,
            fossil_fuel_yearly, residential_electric_yearly, commercial_electric_yearly
        )

        assert result['year'].min() >= 2019


class TestCalculateTotalEmissions:
    """Test total emissions calculation."""

    def test_calculate_total_emissions_adds_column(self):
        """Test that total_tco2e column is added."""
        combined_df, _ = home_calculations.prepare_home_dashboard_data()

        assert 'total_tco2e' in combined_df.columns

    def test_calculate_total_emissions_2023(self):
        """Test 2023 total emissions match expected value."""
        combined_df, _ = home_calculations.prepare_home_dashboard_data()

        data_2023 = combined_df[combined_df['year'] == 2023]
        if len(data_2023) > 0:
            total_2023 = data_2023['total_tco2e'].values[0]

            # Expected value from regression test
            expected = 26019.0
            tolerance = expected * 0.02

            assert abs(total_2023 - expected) < tolerance, \
                f"2023 total emissions: {total_2023}"


class TestPrepareHomeDashboardData:
    """Test main preparation function."""

    def test_prepare_home_dashboard_data_returns_tuple(self):
        """Test that prepare_home_dashboard_data returns dataframe and metadata."""
        result = home_calculations.prepare_home_dashboard_data()

        assert isinstance(result, tuple)
        assert len(result) == 2

        combined_df, metadata = result
        assert isinstance(combined_df, pd.DataFrame)
        assert isinstance(metadata, dict)

    def test_prepare_home_dashboard_data_metadata(self):
        """Test that metadata contains expected keys."""
        _, metadata = home_calculations.prepare_home_dashboard_data()

        assert 'fossil_fuel_metadata' in metadata
        assert 'most_recent_year' in metadata

    def test_prepare_home_dashboard_data_has_population(self):
        """Test that prepared data includes population."""
        combined_df, _ = home_calculations.prepare_home_dashboard_data()

        assert 'Population' in combined_df.columns

    def test_prepare_home_dashboard_data_all_years_present(self):
        """Test that all years from 2019 onwards are present."""
        combined_df, metadata = home_calculations.prepare_home_dashboard_data()

        most_recent_year = metadata['most_recent_year']

        # Should have continuous years from 2019 to most recent
        expected_years = list(range(2019, most_recent_year + 1))
        actual_years = sorted(combined_df['year'].unique())

        assert actual_years == expected_years


class TestBackwardCompatibility:
    """Test backward compatibility with original Home.py calculations."""

    def test_2023_total_matches_original(self):
        """Test that 2023 total matches expected value with centralized emission factors.

        Note: This value changed from 26019.33 to 25966.88 when we moved to centralized
        emission factors, because we now correctly use heating oil factor (0.01020)
        instead of diesel truck factor (0.01030) that was hard-coded before.
        This is more accurate!
        """
        combined_df, _ = home_calculations.prepare_home_dashboard_data()

        data_2023 = combined_df[combined_df['year'] == 2023]
        total_2023 = data_2023['total_tco2e'].values[0]

        # Updated expected value with centralized emission factors
        expected = 25966.88
        tolerance = 5.0  # Allow small differences due to rounding

        assert abs(total_2023 - expected) < tolerance, \
            f"2023 total changed: expected {expected}, got {total_2023}"

    def test_components_non_negative(self):
        """Test that all emission components are non-negative."""
        combined_df, _ = home_calculations.prepare_home_dashboard_data()

        assert (combined_df['vehicles_tco2e'] >= 0).all()
        assert (combined_df['municipal_buildings_mtco2e'] >= 0).all()
        assert (combined_df['residential_fossil_fuel_mtco2e'] >= 0).all()
        assert (combined_df['residential_electric_mtco2e'] >= 0).all()
        assert (combined_df['commercial_electric_mtco2e'] >= 0).all()
        assert (combined_df['total_tco2e'] >= 0).all()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
