"""
Projections module for future GHG emissions scenarios.

This module calculates projected emissions from 2024-2050 based on:
1. EV adoption goals
2. Residential heat pump adoption goals
3. Municipal building electrification goals
4. Grid decarbonization (from emission_factors)

All projections use baseline data from home_calculations and apply
goal-based trajectories with linear interpolation between milestone years.
"""

import pandas as pd
import numpy as np
from home_calculations import prepare_home_dashboard_data
import emission_factors


def load_goals():
    """
    Load all goal CSV files and inject current state (2024) as baseline.

    Calculates current EV and heat pump adoption from 2023 baseline data
    and adds it as the first goal year (2024) to ensure smooth interpolation
    from current state to future goals.

    Returns:
        dict: Dictionary with keys:
            - 'ev_adoption': EV adoption goals by year
            - 'residential_heat_pumps': Residential heat pump adoption goals
            - 'municipal_electrification': Municipal building electrification goals
            - 'clean_energy': Grid clean energy goals (already in emission_factors)
    """
    # Load CSV files
    ev_goals = pd.read_csv('data/goals/ev_adoption.csv')
    ev_goals['EV Adoption'] = ev_goals['EV Adoption'].str.replace('%', '').astype(float) / 100.0

    residential_hp_goals = pd.read_csv('data/goals/residential_heat_pump_adoption.csv')
    residential_hp_goals['heat pump adoption'] = residential_hp_goals['heat pump adoption'].str.replace('%', '').astype(float) / 100.0

    municipal_elec_goals = pd.read_csv('data/goals/municipal_electrification.csv')
    municipal_elec_goals['munipal_heat_pump_adoption'] = municipal_elec_goals['munipal_heat_pump_adoption'].str.replace('%', '').astype(float) / 100.0

    # Calculate current adoption from 2023 baseline data
    from data_loader import load_vehicle_data

    try:
        # Get 2023 Q4 vehicle data to calculate current EV adoption
        vehicles_df = load_vehicle_data()
        q4_2023 = vehicles_df[vehicles_df['Quarter'] == '10/1/23']

        if len(q4_2023) > 0:
            total_emissions = q4_2023['tCo2e'].sum()
            ev_hybrid_emissions = q4_2023[q4_2023['Type'].str.contains('Electric|Hybrid', case=False, na=False)]['tCo2e'].sum()
            current_ev_pct = ev_hybrid_emissions / total_emissions if total_emissions > 0 else 0.03
        else:
            # Fallback if no 2023 data
            current_ev_pct = 0.03  # ~3% based on typical MA adoption
    except Exception:
        # Fallback if data loading fails
        current_ev_pct = 0.03

    # Estimate current heat pump adoption (harder to calculate, use conservative estimate)
    # Based on Mass Save data, roughly 5% of homes have heat pumps as of 2023
    current_hp_pct = 0.05

    # Municipal electrification is just starting, use 0%
    current_muni_pct = 0.0

    # Inject 2024 baseline into goals (only if not already present)
    if 2024 not in ev_goals['year'].values:
        baseline_ev = pd.DataFrame({'year': [2024], 'EV Adoption': [current_ev_pct]})
        ev_goals = pd.concat([baseline_ev, ev_goals], ignore_index=True).sort_values('year')

    if 2024 not in residential_hp_goals['year'].values:
        baseline_hp = pd.DataFrame({'year': [2024], 'heat pump adoption': [current_hp_pct]})
        residential_hp_goals = pd.concat([baseline_hp, residential_hp_goals], ignore_index=True).sort_values('year')

    if 2024 not in municipal_elec_goals['year'].values:
        baseline_muni = pd.DataFrame({'year': [2024], 'munipal_heat_pump_adoption': [current_muni_pct]})
        municipal_elec_goals = pd.concat([baseline_muni, municipal_elec_goals], ignore_index=True).sort_values('year')

    return {
        'ev_adoption': ev_goals,
        'residential_heat_pumps': residential_hp_goals,
        'municipal_electrification': municipal_elec_goals
    }


def interpolate_goal(goals_df, year_col, value_col, target_year, baseline_year=2023, baseline_value=0.0):
    """
    Interpolate a goal value for a specific year.

    Linear interpolation between milestone years in the goals dataframe.
    For years before the first goal year, interpolates from baseline.
    For years after the last goal year, uses the last goal value.

    Args:
        goals_df (pd.DataFrame): Goals dataframe with year and value columns
        year_col (str): Name of the year column
        value_col (str): Name of the value column (as percentage 0.0-1.0)
        target_year (int): Year to get goal for
        baseline_year (int): Baseline year (default 2023)
        baseline_value (float): Baseline value at baseline year (default 0.0)

    Returns:
        float: Interpolated goal value (0.0 to 1.0)
    """
    # If target year is baseline or earlier, return baseline
    if target_year <= baseline_year:
        return baseline_value

    # Find surrounding goal years
    goals_df = goals_df.sort_values(year_col)
    years_before = goals_df[goals_df[year_col] <= target_year]
    years_after = goals_df[goals_df[year_col] >= target_year]

    if len(years_before) == 0:
        # Before first goal year - interpolate from baseline to first goal
        first_year = goals_df[year_col].min()
        first_value = goals_df[goals_df[year_col] == first_year][value_col].values[0]

        ratio = (target_year - baseline_year) / (first_year - baseline_year)
        return baseline_value + (first_value - baseline_value) * ratio

    elif len(years_after) == 0:
        # After last goal year - use last goal value
        return goals_df[value_col].iloc[-1]

    else:
        # Between two goal years - linear interpolation
        year_before = years_before[year_col].max()
        year_after = years_after[year_col].min()

        value_before = goals_df[goals_df[year_col] == year_before][value_col].values[0]
        value_after = goals_df[goals_df[year_col] == year_after][value_col].values[0]

        if year_before == year_after:
            return value_before

        ratio = (target_year - year_before) / (year_after - year_before)
        return value_before + (value_after - value_before) * ratio


def project_vehicle_emissions(baseline_vehicles_tco2e, target_year, ev_adoption_pct, population_growth_factor=1.0):
    """
    Project vehicle emissions for a future year based on EV adoption.

    Assumes:
    - Total vehicle fleet grows with population
    - EVs replace ICE vehicles at the specified adoption rate
    - EV emissions use future grid emission factor (grid decarbonization applied)
    - ICE vehicle efficiency remains constant

    Args:
        baseline_vehicles_tco2e (float): Baseline year vehicle emissions (2023)
        target_year (int): Target year for projection
        ev_adoption_pct (float): EV adoption percentage (0.0 to 1.0)
        population_growth_factor (float): Population growth multiplier (default 1.0)

    Returns:
        dict: Dictionary with:
            - 'total_vehicles_tco2e': Total vehicle emissions
            - 'ice_vehicles_tco2e': ICE vehicle emissions
            - 'ev_vehicles_tco2e': EV vehicle emissions
            - 'ev_adoption_pct': EV adoption percentage used
    """
    # Assume baseline is 100% ICE (close enough for 2023)
    baseline_ice_emissions = baseline_vehicles_tco2e

    # Apply population growth to total fleet
    total_fleet_emissions_if_all_ice = baseline_ice_emissions * population_growth_factor

    # Calculate ICE portion (what's left after EV adoption)
    ice_portion = 1.0 - ev_adoption_pct
    ice_emissions = total_fleet_emissions_if_all_ice * ice_portion

    # Calculate EV emissions
    # Assume EVs have similar mileage as ICE vehicles they replace
    # Emission factor from electricity grid (with decarbonization)
    elec_factor_future = emission_factors.get_emission_factor('ELECTRIC', target_year)
    elec_factor_baseline = emission_factors.get_emission_factor('ELECTRIC')  # Historical

    # Estimate EV efficiency: ~3.5 mi/kWh vs ICE ~25 MPG
    # If ICE vehicle uses 1 gallon for 25 miles (0.00882 tCO2e),
    # EV uses ~7.14 kWh for 25 miles
    # Baseline EV emissions per vehicle-equivalent: 7.14 kWh * 0.000239 = 0.00171 tCO2e per 25 miles
    # vs ICE: 0.00882 tCO2e per 25 miles
    # So EV is ~19% of ICE emissions at current grid
    ev_efficiency_ratio = 0.19  # EV emissions as fraction of ICE at baseline grid

    # Apply future grid decarbonization
    if elec_factor_baseline > 0:
        grid_improvement = elec_factor_future / elec_factor_baseline
    else:
        grid_improvement = 0

    ev_emissions_per_vehicle = baseline_ice_emissions * ev_efficiency_ratio * grid_improvement * population_growth_factor
    ev_emissions = ev_emissions_per_vehicle * ev_adoption_pct

    total_emissions = ice_emissions + ev_emissions

    return {
        'total_vehicles_tco2e': total_emissions,
        'ice_vehicles_tco2e': ice_emissions,
        'ev_vehicles_tco2e': ev_emissions,
        'ev_adoption_pct': ev_adoption_pct
    }


def project_residential_heating_emissions(baseline_fossil_mtco2e, baseline_electric_mtco2e,
                                          target_year, heat_pump_adoption_pct):
    """
    Project residential heating emissions based on heat pump adoption.

    Assumes:
    - Heat pumps replace fossil fuel heating (oil + propane)
    - Heat pumps have COP ~3 (3x more efficient than resistance heating)
    - New electric heating uses future grid emission factor

    Args:
        baseline_fossil_mtco2e (float): Baseline residential fossil fuel heating
        baseline_electric_mtco2e (float): Baseline residential electricity
        target_year (int): Target year for projection
        heat_pump_adoption_pct (float): Heat pump adoption percentage (0.0 to 1.0)

    Returns:
        dict: Dictionary with:
            - 'total_residential_heating_mtco2e': Total residential heating emissions
            - 'fossil_fuel_mtco2e': Remaining fossil fuel heating
            - 'electric_mtco2e': Total electric (baseline + heat pumps)
            - 'heat_pump_adoption_pct': Adoption percentage used
    """
    # Fossil fuel heating that gets replaced
    fossil_replaced = baseline_fossil_mtco2e * heat_pump_adoption_pct
    fossil_remaining = baseline_fossil_mtco2e * (1.0 - heat_pump_adoption_pct)

    # Calculate heat pump electricity usage
    # Fossil fuel → heat pump conversion
    # Assume heat pumps have COP of 3, so 1/3 the energy input per unit heat
    # But emissions depend on grid carbon intensity

    # First, estimate the thermal energy that was being produced by fossil fuels
    # Using heating oil as proxy: 0.01030 tCO2e/gal, ~138 MJ/gal thermal
    # For simplicity, assume heat pumps need 1/3 the energy (COP=3)

    # Get emission factors
    elec_factor_future = emission_factors.get_emission_factor('ELECTRIC', target_year)
    oil_factor = emission_factors.get_emission_factor('OIL')

    # Rough conversion: fossil emissions → heat pump electric emissions
    # With current grid: heat pump is ~70% less emissions than oil
    # With clean grid: even better
    # Simplified: heat pump emissions = fossil_replaced * (elec_factor / oil_factor) * (1/3 for COP)
    if oil_factor > 0:
        heat_pump_electric_emissions = fossil_replaced * (elec_factor_future / oil_factor) * 0.33
    else:
        heat_pump_electric_emissions = 0

    # Total residential electric = baseline + heat pumps
    # Note: baseline electric also benefits from grid decarbonization
    elec_factor_baseline = emission_factors.get_emission_factor('ELECTRIC')
    if elec_factor_baseline > 0:
        baseline_electric_adjusted = baseline_electric_mtco2e * (elec_factor_future / elec_factor_baseline)
    else:
        baseline_electric_adjusted = baseline_electric_mtco2e

    total_electric = baseline_electric_adjusted + heat_pump_electric_emissions

    total_heating = fossil_remaining + total_electric

    return {
        'total_residential_heating_mtco2e': total_heating,
        'fossil_fuel_mtco2e': fossil_remaining,
        'electric_mtco2e': total_electric,
        'heat_pump_adoption_pct': heat_pump_adoption_pct,
        'heat_pump_electric_mtco2e': heat_pump_electric_emissions
    }


def project_municipal_building_emissions(baseline_other_fuels_mtco2e, baseline_electric_mtco2e,
                                         target_year, electrification_pct):
    """
    Project municipal building emissions based on electrification goals.

    Assumes:
    - Municipal buildings transition from oil/gas to electric heat pumps
    - Similar efficiency assumptions as residential heat pumps

    Args:
        baseline_other_fuels_mtco2e (float): Baseline municipal other fuels
        baseline_electric_mtco2e (float): Baseline municipal electricity
        target_year (int): Target year for projection
        electrification_pct (float): Electrification percentage (0.0 to 1.0)

    Returns:
        dict: Dictionary with:
            - 'total_municipal_mtco2e': Total municipal building emissions
            - 'other_fuels_mtco2e': Remaining other fuels
            - 'electric_mtco2e': Total electric (baseline + conversions)
            - 'electrification_pct': Percentage used
    """
    # Similar logic to residential heating
    fuels_replaced = baseline_other_fuels_mtco2e * electrification_pct
    fuels_remaining = baseline_other_fuels_mtco2e * (1.0 - electrification_pct)

    elec_factor_future = emission_factors.get_emission_factor('ELECTRIC', target_year)
    oil_factor = emission_factors.get_emission_factor('OIL')
    elec_factor_baseline = emission_factors.get_emission_factor('ELECTRIC')

    # Heat pump conversion (COP = 3)
    if oil_factor > 0:
        converted_electric_emissions = fuels_replaced * (elec_factor_future / oil_factor) * 0.33
    else:
        converted_electric_emissions = 0

    # Baseline electric with grid decarbonization
    if elec_factor_baseline > 0:
        baseline_electric_adjusted = baseline_electric_mtco2e * (elec_factor_future / elec_factor_baseline)
    else:
        baseline_electric_adjusted = baseline_electric_mtco2e

    total_electric = baseline_electric_adjusted + converted_electric_emissions
    total_municipal = fuels_remaining + total_electric

    return {
        'total_municipal_mtco2e': total_municipal,
        'other_fuels_mtco2e': fuels_remaining,
        'electric_mtco2e': total_electric,
        'electrification_pct': electrification_pct
    }


def project_commercial_electricity(baseline_commercial_electric_mtco2e, target_year):
    """
    Project commercial electricity emissions with grid decarbonization.

    Assumes constant electricity usage, but cleaner grid over time.

    Args:
        baseline_commercial_electric_mtco2e (float): Baseline commercial electricity
        target_year (int): Target year

    Returns:
        float: Projected commercial electricity emissions
    """
    elec_factor_future = emission_factors.get_emission_factor('ELECTRIC', target_year)
    elec_factor_baseline = emission_factors.get_emission_factor('ELECTRIC')

    if elec_factor_baseline > 0:
        return baseline_commercial_electric_mtco2e * (elec_factor_future / elec_factor_baseline)
    else:
        return baseline_commercial_electric_mtco2e


def project_emissions_for_year(baseline_data, target_year, goals, population_growth_factor=1.0):
    """
    Project all emissions for a specific target year.

    Args:
        baseline_data (dict): Baseline emissions data (from 2023)
        target_year (int): Target year for projection
        goals (dict): Goals dictionary from load_goals()
        population_growth_factor (float): Population growth multiplier

    Returns:
        dict: Complete emissions projection for the year
    """
    # Interpolate all goals for this year
    ev_adoption = interpolate_goal(
        goals['ev_adoption'], 'year', 'EV Adoption', target_year,
        baseline_year=2023, baseline_value=0.0
    )

    hp_adoption = interpolate_goal(
        goals['residential_heat_pumps'], 'year', 'heat pump adoption', target_year,
        baseline_year=2023, baseline_value=0.0
    )

    muni_elec = interpolate_goal(
        goals['municipal_electrification'], 'year', 'munipal_heat_pump_adoption', target_year,
        baseline_year=2023, baseline_value=0.0
    )

    # Project each sector
    vehicles = project_vehicle_emissions(
        baseline_data['vehicles_tco2e'], target_year, ev_adoption, population_growth_factor
    )

    residential_heating = project_residential_heating_emissions(
        baseline_data['residential_fossil_fuel_mtco2e'],
        baseline_data['residential_electric_mtco2e'],
        target_year, hp_adoption
    )

    municipal = project_municipal_building_emissions(
        baseline_data['other_fuels_mtco2e'],
        baseline_data['electric_mtco2e'],
        target_year, muni_elec
    )

    commercial_electric = project_commercial_electricity(
        baseline_data['commercial_electric_mtco2e'], target_year
    )

    # Calculate total
    total_emissions = (
        vehicles['total_vehicles_tco2e'] +
        residential_heating['total_residential_heating_mtco2e'] +
        commercial_electric +
        municipal['total_municipal_mtco2e']
    )

    return {
        'year': target_year,
        'vehicles_tco2e': vehicles['total_vehicles_tco2e'],
        'vehicles_ice_tco2e': vehicles['ice_vehicles_tco2e'],
        'vehicles_ev_tco2e': vehicles['ev_vehicles_tco2e'],
        'ev_adoption_pct': ev_adoption,
        'residential_fossil_fuel_mtco2e': residential_heating['fossil_fuel_mtco2e'],
        'residential_electric_mtco2e': residential_heating['electric_mtco2e'],
        'residential_heat_pump_electric_mtco2e': residential_heating['heat_pump_electric_mtco2e'],
        'heat_pump_adoption_pct': hp_adoption,
        'commercial_electric_mtco2e': commercial_electric,
        'municipal_other_fuels_mtco2e': municipal['other_fuels_mtco2e'],
        'municipal_electric_mtco2e': municipal['electric_mtco2e'],
        'municipal_electrification_pct': muni_elec,
        'total_tco2e': total_emissions,
        'grid_clean_energy_pct': emission_factors.get_grid_clean_energy_percent(target_year)
    }


def create_full_projection(start_year=2024, end_year=2050, population_growth_rate=0.0):
    """
    Create full emissions projection from start_year to end_year.

    Args:
        start_year (int): First projection year (default 2024)
        end_year (int): Last projection year (default 2050)
        population_growth_rate (float): Annual population growth rate (default 0.0)

    Returns:
        tuple: (projection_df, baseline_data, goals)
            - projection_df: DataFrame with projections for each year
            - baseline_data: Baseline (2023) data used
            - goals: Goals dictionary
    """
    # Load baseline data
    combined_df, metadata = prepare_home_dashboard_data()
    baseline_year_data = combined_df[combined_df['year'] == 2023].iloc[0]

    baseline_data = {
        'vehicles_tco2e': baseline_year_data['vehicles_tco2e'],
        'residential_fossil_fuel_mtco2e': baseline_year_data['residential_fossil_fuel_mtco2e'],
        'residential_electric_mtco2e': baseline_year_data['residential_electric_mtco2e'],
        'commercial_electric_mtco2e': baseline_year_data['commercial_electric_mtco2e'],
        'other_fuels_mtco2e': baseline_year_data['other_fuels_mtco2e'],
        'electric_mtco2e': baseline_year_data['electric_mtco2e'],
        'total_tco2e': baseline_year_data['total_tco2e']
    }

    # Load goals
    goals = load_goals()

    # Project for each year
    projections = []
    for year in range(start_year, end_year + 1):
        years_from_baseline = year - 2023
        pop_growth_factor = (1 + population_growth_rate) ** years_from_baseline

        # For 2024, use baseline emissions but show actual current adoption percentages
        # The baseline already includes current EVs/heat pumps, so emissions = 2023
        # But we want to show the actual adoption rates for charting
        if year == 2024:
            # Get the injected 2024 adoption rates from goals
            ev_2024 = goals['ev_adoption'][goals['ev_adoption']['year'] == 2024]['EV Adoption'].values[0] if 2024 in goals['ev_adoption']['year'].values else 0.03
            hp_2024 = goals['residential_heat_pumps'][goals['residential_heat_pumps']['year'] == 2024]['heat pump adoption'].values[0] if 2024 in goals['residential_heat_pumps']['year'].values else 0.05
            muni_2024 = goals['municipal_electrification'][goals['municipal_electrification']['year'] == 2024]['munipal_heat_pump_adoption'].values[0] if 2024 in goals['municipal_electrification']['year'].values else 0.0

            projection = {
                'year': 2024,
                'vehicles_tco2e': baseline_data['vehicles_tco2e'],
                'vehicles_ice_tco2e': baseline_data['vehicles_tco2e'] * (1 - ev_2024),
                'vehicles_ev_tco2e': baseline_data['vehicles_tco2e'] * ev_2024,
                'ev_adoption_pct': ev_2024,
                'residential_fossil_fuel_mtco2e': baseline_data['residential_fossil_fuel_mtco2e'],
                'residential_electric_mtco2e': baseline_data['residential_electric_mtco2e'],
                'residential_heat_pump_electric_mtco2e': 0.0,  # Already included in baseline
                'heat_pump_adoption_pct': hp_2024,
                'commercial_electric_mtco2e': baseline_data['commercial_electric_mtco2e'],
                'municipal_other_fuels_mtco2e': baseline_data['other_fuels_mtco2e'],
                'municipal_electric_mtco2e': baseline_data['electric_mtco2e'],
                'municipal_electrification_pct': muni_2024,
                'total_tco2e': baseline_data['total_tco2e'],
                'grid_clean_energy_pct': emission_factors.get_grid_clean_energy_percent(2024)
            }
        else:
            projection = project_emissions_for_year(baseline_data, year, goals, pop_growth_factor)
        projections.append(projection)

    projection_df = pd.DataFrame(projections)

    return projection_df, baseline_data, goals


if __name__ == '__main__':
    # Test the module
    print("Creating emissions projections...")
    projection_df, baseline, goals = create_full_projection()

    print(f"\nProjections created for {len(projection_df)} years: {projection_df['year'].min()}-{projection_df['year'].max()}")

    print("\nKey milestones:")
    for year in [2024, 2030, 2040, 2050]:
        data = projection_df[projection_df['year'] == year].iloc[0]
        print(f"\n{year}:")
        print(f"  Total emissions: {data['total_tco2e']:.0f} mtCO2e")
        print(f"  EV adoption: {data['ev_adoption_pct']*100:.1f}%")
        print(f"  Heat pump adoption: {data['heat_pump_adoption_pct']*100:.1f}%")
        print(f"  Grid clean energy: {data['grid_clean_energy_pct']*100:.1f}%")

    print(f"\nReduction from 2023 baseline ({baseline['total_tco2e']:.0f} mtCO2e) to 2050:")
    reduction = baseline['total_tco2e'] - projection_df[projection_df['year'] == 2050]['total_tco2e'].values[0]
    reduction_pct = (reduction / baseline['total_tco2e']) * 100
    print(f"  {reduction:.0f} mtCO2e ({reduction_pct:.1f}% reduction)")
