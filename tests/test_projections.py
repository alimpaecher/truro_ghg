"""
Unit tests for projections.py

Tests the projection calculation logic for future emissions scenarios.
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

import projections


class TestLoadGoals:
    """Test goal loading functionality."""

    def test_load_goals_returns_dict(self):
        """Test that load_goals returns a dictionary."""
        goals = projections.load_goals()
        assert isinstance(goals, dict)

    def test_load_goals_has_all_keys(self):
        """Test that all expected goal types are present."""
        goals = projections.load_goals()

        expected_keys = ['ev_adoption', 'residential_heat_pumps', 'municipal_electrification']
        for key in expected_keys:
            assert key in goals, f"Missing key: {key}"

    def test_ev_adoption_goals_structure(self):
        """Test EV adoption goals have correct structure."""
        goals = projections.load_goals()
        ev_goals = goals['ev_adoption']

        assert 'year' in ev_goals.columns
        assert 'EV Adoption' in ev_goals.columns

        # Check that percentages are converted to decimals (0-1)
        assert (ev_goals['EV Adoption'] >= 0).all()
        assert (ev_goals['EV Adoption'] <= 1).all()

    def test_ev_adoption_2050_goal(self):
        """Test that 2050 EV adoption goal is 100%."""
        goals = projections.load_goals()
        ev_goals = goals['ev_adoption']

        ev_2050 = ev_goals[ev_goals['year'] == 2050]['EV Adoption'].values[0]
        assert abs(ev_2050 - 1.0) < 0.01, "2050 should be 100% EV"


class TestInterpolateGoal:
    """Test goal interpolation logic."""

    def test_interpolate_before_baseline(self):
        """Test that years before baseline return baseline value."""
        goals = projections.load_goals()
        ev_goals = goals['ev_adoption']

        result = projections.interpolate_goal(ev_goals, 'Year', 'EV Adoption', 2020, 2023, 0.0)
        assert result == 0.0

    def test_interpolate_at_goal_year(self):
        """Test that interpolation at a goal year returns exact value."""
        goals = projections.load_goals()
        ev_goals = goals['ev_adoption']

        # 2030 goal is 17%
        result = projections.interpolate_goal(ev_goals, 'year', 'EV Adoption', 2030, 2023, 0.0)
        assert abs(result - 0.17) < 0.01

    def test_interpolate_between_goals(self):
        """Test linear interpolation between goal years."""
        goals = projections.load_goals()
        ev_goals = goals['ev_adoption']

        # 2030: 17%, 2040: 40%
        # 2035 should be halfway: (17 + 40) / 2 = 28.5%
        result = projections.interpolate_goal(ev_goals, 'year', 'EV Adoption', 2035, 2023, 0.0)
        expected = (0.17 + 0.40) / 2
        assert abs(result - expected) < 0.01

    def test_interpolate_after_last_goal(self):
        """Test that years after last goal use last goal value."""
        goals = projections.load_goals()
        ev_goals = goals['ev_adoption']

        # After 2050 (100%) should still be 100%
        result = projections.interpolate_goal(ev_goals, 'year', 'EV Adoption', 2060, 2023, 0.0)
        assert abs(result - 1.0) < 0.01


class TestProjectVehicleEmissions:
    """Test vehicle emissions projections."""

    def test_project_vehicles_no_ev_adoption(self):
        """Test projection with 0% EV adoption (baseline scenario)."""
        baseline = 12500.0  # Example baseline
        result = projections.project_vehicle_emissions(baseline, 2030, 0.0, 1.0)

        # With no EV adoption and no population growth, should equal baseline
        assert abs(result['total_vehicles_tco2e'] - baseline) < 1.0
        assert result['ev_adoption_pct'] == 0.0

    def test_project_vehicles_100_percent_ev(self):
        """Test projection with 100% EV adoption."""
        baseline = 12500.0
        result = projections.project_vehicle_emissions(baseline, 2050, 1.0, 1.0)

        # With 100% EV and clean grid (2050), emissions should be near zero
        assert result['total_vehicles_tco2e'] < 1000  # Much lower than baseline
        assert result['ev_adoption_pct'] == 1.0

    def test_project_vehicles_population_growth(self):
        """Test that population growth increases vehicle emissions."""
        baseline = 12500.0

        result_no_growth = projections.project_vehicle_emissions(baseline, 2030, 0.0, 1.0)
        result_with_growth = projections.project_vehicle_emissions(baseline, 2030, 0.0, 1.1)

        # 10% population growth should increase emissions
        assert result_with_growth['total_vehicles_tco2e'] > result_no_growth['total_vehicles_tco2e']

    def test_project_vehicles_returns_dict(self):
        """Test that vehicle projection returns expected structure."""
        result = projections.project_vehicle_emissions(12500.0, 2030, 0.17, 1.0)

        expected_keys = ['total_vehicles_tco2e', 'ice_vehicles_tco2e',
                        'ev_vehicles_tco2e', 'ev_adoption_pct']
        for key in expected_keys:
            assert key in result


class TestProjectResidentialHeating:
    """Test residential heating projections."""

    def test_project_residential_no_heat_pumps(self):
        """Test projection with 0% heat pump adoption."""
        baseline_fossil = 6500.0
        baseline_electric = 3500.0

        result = projections.project_residential_heating_emissions(
            baseline_fossil, baseline_electric, 2030, 0.0
        )

        # With no heat pumps, fossil fuel should remain (adjusted for grid decarbonization)
        assert result['fossil_fuel_mtco2e'] > 6000
        assert result['heat_pump_adoption_pct'] == 0.0

    def test_project_residential_full_heat_pumps(self):
        """Test projection with 100% heat pump adoption."""
        baseline_fossil = 6500.0
        baseline_electric = 3500.0

        result = projections.project_residential_heating_emissions(
            baseline_fossil, baseline_electric, 2050, 1.0
        )

        # With 100% heat pumps, fossil fuel should be zero
        assert result['fossil_fuel_mtco2e'] < 100  # Near zero (rounding)
        assert result['heat_pump_adoption_pct'] == 1.0

    def test_project_residential_structure(self):
        """Test that residential projection returns expected structure."""
        result = projections.project_residential_heating_emissions(
            6500.0, 3500.0, 2030, 0.3
        )

        expected_keys = ['total_residential_heating_mtco2e', 'fossil_fuel_mtco2e',
                        'electric_mtco2e', 'heat_pump_adoption_pct', 'heat_pump_electric_mtco2e']
        for key in expected_keys:
            assert key in result


class TestProjectMunicipalBuildings:
    """Test municipal building projections."""

    def test_project_municipal_no_electrification(self):
        """Test projection with 0% electrification."""
        baseline_fuels = 150.0
        baseline_electric = 100.0

        result = projections.project_municipal_building_emissions(
            baseline_fuels, baseline_electric, 2030, 0.0
        )

        assert result['electrification_pct'] == 0.0

    def test_project_municipal_full_electrification(self):
        """Test projection with 100% electrification."""
        baseline_fuels = 150.0
        baseline_electric = 100.0

        result = projections.project_municipal_building_emissions(
            baseline_fuels, baseline_electric, 2040, 1.0
        )

        # With 100% electrification, other fuels should be zero
        assert result['other_fuels_mtco2e'] < 10
        assert result['electrification_pct'] == 1.0


class TestProjectCommercialElectricity:
    """Test commercial electricity projections."""

    def test_project_commercial_with_grid_decarbonization(self):
        """Test that commercial electricity benefits from grid decarbonization."""
        baseline = 2500.0

        result_2030 = projections.project_commercial_electricity(baseline, 2030)
        result_2050 = projections.project_commercial_electricity(baseline, 2050)

        # 2050 should have lower emissions due to cleaner grid
        assert result_2050 < result_2030
        assert result_2050 < baseline


class TestProjectEmissionsForYear:
    """Test complete year projection."""

    def test_project_emissions_for_year_structure(self):
        """Test that projection for a year returns complete structure."""
        goals = projections.load_goals()
        baseline_data = {
            'vehicles_tco2e': 12500.0,
            'residential_fossil_fuel_mtco2e': 6500.0,
            'residential_electric_mtco2e': 3500.0,
            'commercial_electric_mtco2e': 2500.0,
            'other_fuels_mtco2e': 150.0,
            'electric_mtco2e': 100.0
        }

        result = projections.project_emissions_for_year(baseline_data, 2030, goals, 1.0)

        # Check all expected keys
        expected_keys = ['year', 'vehicles_tco2e', 'residential_fossil_fuel_mtco2e',
                        'total_tco2e', 'ev_adoption_pct', 'heat_pump_adoption_pct',
                        'grid_clean_energy_pct']
        for key in expected_keys:
            assert key in result

    def test_project_emissions_decreases_over_time(self):
        """Test that emissions decrease from 2030 to 2050."""
        goals = projections.load_goals()
        baseline_data = {
            'vehicles_tco2e': 12500.0,
            'residential_fossil_fuel_mtco2e': 6500.0,
            'residential_electric_mtco2e': 3500.0,
            'commercial_electric_mtco2e': 2500.0,
            'other_fuels_mtco2e': 150.0,
            'electric_mtco2e': 100.0
        }

        result_2030 = projections.project_emissions_for_year(baseline_data, 2030, goals, 1.0)
        result_2050 = projections.project_emissions_for_year(baseline_data, 2050, goals, 1.0)

        # 2050 should have much lower total emissions than 2030
        assert result_2050['total_tco2e'] < result_2030['total_tco2e']


class TestCreateFullProjection:
    """Test full projection creation."""

    def test_create_full_projection_returns_tuple(self):
        """Test that create_full_projection returns expected tuple."""
        result = projections.create_full_projection(2024, 2050)

        assert isinstance(result, tuple)
        assert len(result) == 3

        projection_df, baseline_data, goals = result
        assert isinstance(projection_df, pd.DataFrame)
        assert isinstance(baseline_data, dict)
        assert isinstance(goals, dict)

    def test_2024_matches_2023_baseline(self):
        """Test that 2024 projection matches 2023 baseline (continuity test)."""
        from home_calculations import prepare_home_dashboard_data

        # Get 2023 baseline
        combined_df, metadata = prepare_home_dashboard_data()
        baseline_2023 = combined_df[combined_df['year'] == 2023].iloc[0]

        # Get 2024 projection
        projection_df, baseline_data, goals = projections.create_full_projection(2024, 2024)
        projection_2024 = projection_df[projection_df['year'] == 2024].iloc[0]

        # Total should match within 1% (allowing for minor grid changes)
        assert abs(projection_2024['total_tco2e'] - baseline_2023['total_tco2e']) / baseline_2023['total_tco2e'] < 0.01, \
            f"2024 projection ({projection_2024['total_tco2e']:.0f}) should match 2023 baseline ({baseline_2023['total_tco2e']:.0f})"

        # Vehicles should match exactly (no EV adoption before first goal in 2030)
        assert abs(projection_2024['vehicles_tco2e'] - baseline_2023['vehicles_tco2e']) < 1.0, \
            f"2024 vehicles ({projection_2024['vehicles_tco2e']:.0f}) should match 2023 ({baseline_2023['vehicles_tco2e']:.0f})"

        # Residential fossil should match exactly (no heat pump adoption before first goal in 2030)
        assert abs(projection_2024['residential_fossil_fuel_mtco2e'] - baseline_2023['residential_fossil_fuel_mtco2e']) < 1.0, \
            f"2024 res fossil ({projection_2024['residential_fossil_fuel_mtco2e']:.1f}) should match 2023 ({baseline_2023['residential_fossil_fuel_mtco2e']:.1f})"

    def test_create_full_projection_year_range(self):
        """Test that projection includes all years in range."""
        projection_df, _, _ = projections.create_full_projection(2024, 2050)

        assert projection_df['year'].min() == 2024
        assert projection_df['year'].max() == 2050
        assert len(projection_df) == 27  # 2024-2050 inclusive

    def test_create_full_projection_has_all_columns(self):
        """Test that projection has all expected columns."""
        projection_df, _, _ = projections.create_full_projection(2024, 2030)

        expected_columns = ['year', 'total_tco2e', 'vehicles_tco2e',
                          'residential_fossil_fuel_mtco2e', 'ev_adoption_pct',
                          'heat_pump_adoption_pct', 'grid_clean_energy_pct']

        for col in expected_columns:
            assert col in projection_df.columns, f"Missing column: {col}"

    def test_create_full_projection_2050_reduction(self):
        """Test that 2050 shows significant emission reduction."""
        projection_df, baseline_data, _ = projections.create_full_projection(2024, 2050)

        baseline_total = baseline_data['total_tco2e']
        projected_2050 = projection_df[projection_df['year'] == 2050]['total_tco2e'].values[0]

        reduction_pct = (baseline_total - projected_2050) / baseline_total * 100

        # Should achieve at least 90% reduction by 2050
        assert reduction_pct > 90, f"2050 reduction is only {reduction_pct:.1f}%"

    def test_create_full_projection_emissions_decrease(self):
        """Test that emissions consistently decrease over time."""
        projection_df, _, _ = projections.create_full_projection(2024, 2050)

        # Check that 2030 < 2024, 2040 < 2030, 2050 < 2040
        total_2024 = projection_df[projection_df['year'] == 2024]['total_tco2e'].values[0]
        total_2030 = projection_df[projection_df['year'] == 2030]['total_tco2e'].values[0]
        total_2040 = projection_df[projection_df['year'] == 2040]['total_tco2e'].values[0]
        total_2050 = projection_df[projection_df['year'] == 2050]['total_tco2e'].values[0]

        assert total_2030 < total_2024
        assert total_2040 < total_2030
        assert total_2050 < total_2040

    def test_create_full_projection_all_positive(self):
        """Test that all projected values are non-negative."""
        projection_df, _, _ = projections.create_full_projection(2024, 2050)

        # All emissions should be >= 0
        assert (projection_df['total_tco2e'] >= 0).all()
        assert (projection_df['vehicles_tco2e'] >= 0).all()
        assert (projection_df['residential_fossil_fuel_mtco2e'] >= 0).all()

    def test_create_full_projection_adoption_rates_valid(self):
        """Test that all adoption rates are between 0 and 1."""
        projection_df, _, _ = projections.create_full_projection(2024, 2050)

        assert (projection_df['ev_adoption_pct'] >= 0).all()
        assert (projection_df['ev_adoption_pct'] <= 1).all()

        assert (projection_df['heat_pump_adoption_pct'] >= 0).all()
        assert (projection_df['heat_pump_adoption_pct'] <= 1).all()

        assert (projection_df['grid_clean_energy_pct'] >= 0).all()
        assert (projection_df['grid_clean_energy_pct'] <= 1).all()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
