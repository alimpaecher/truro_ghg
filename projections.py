"""
Projections module for future GHG emissions scenarios.

This module calculates projected emissions through 2050 based on:
1. EV adoption goals
2. Residential heat pump adoption goals
3. Municipal building electrification goals
4. Grid decarbonization (from emission_factors)

All projections use baseline data from home_calculations and apply
goal-based trajectories with linear interpolation between milestone years.
The baseline year is derived dynamically from the most recent year of
complete historical data.
"""

import pandas as pd
import numpy as np
from home_calculations import prepare_home_dashboard_data, get_baseline_year
import emission_factors


def load_goals(baseline_year):
    """
    Load all goal CSV files and inject current state as the first projection year.

    Calculates current EV and heat pump adoption from baseline-year data and adds
    it as the first goal year (baseline_year + 1) to ensure smooth interpolation
    from current state to future goals.

    Args:
        baseline_year (int): Most recent year of historical data.

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

    from data_loader import load_vehicle_data, calculate_total_fossil_fuel_heating, load_assessors_data

    inject_year = baseline_year + 1

    try:
        vehicles_df = load_vehicle_data()
        vehicles_df = vehicles_df.copy()
        vehicles_df['Quarter_Date'] = pd.to_datetime(vehicles_df['Quarter'])
        # Use Q4 of baseline year for current EV share (October = Q4 registrations)
        baseline_q4 = vehicles_df[(vehicles_df['Quarter_Date'].dt.year == baseline_year) &
                                  (vehicles_df['Quarter_Date'].dt.month == 10)]

        if len(baseline_q4) > 0:
            total_emissions = baseline_q4['tCo2e'].sum()
            ev_hybrid_emissions = baseline_q4[baseline_q4['Type'].str.contains('Electric|Hybrid', case=False, na=False)]['tCo2e'].sum()
            current_ev_pct = ev_hybrid_emissions / total_emissions if total_emissions > 0 else 0.03
        else:
            current_ev_pct = 0.03
    except Exception:
        current_ev_pct = 0.03

    try:
        fossil_fuel_tuple = calculate_total_fossil_fuel_heating()
        fossil_fuel_results, _ = fossil_fuel_tuple
        hp_series = fossil_fuel_results[fossil_fuel_results['year'] == baseline_year]['heat_pump_locations']
        if len(hp_series) == 0:
            # Fall back to the most recent heat-pump data if baseline year isn't covered
            hp_count = fossil_fuel_results.sort_values('year').iloc[-1]['heat_pump_locations']
        else:
            hp_count = hp_series.values[0]

        assessors_df = load_assessors_data()
        residential_properties = len(assessors_df[(assessors_df['PropertyType'] == 'R') &
                                                    (assessors_df['NetSF'].notna()) &
                                                    (assessors_df['NetSF'] > 0)])

        current_hp_pct = hp_count / residential_properties if residential_properties > 0 else 0.10
    except Exception:
        current_hp_pct = 0.10

    current_muni_pct = 0.0

    if inject_year not in ev_goals['year'].values:
        baseline_ev = pd.DataFrame({'year': [inject_year], 'EV Adoption': [current_ev_pct]})
        ev_goals = pd.concat([baseline_ev, ev_goals], ignore_index=True).sort_values('year')

    if inject_year not in residential_hp_goals['year'].values:
        baseline_hp = pd.DataFrame({'year': [inject_year], 'heat pump adoption': [current_hp_pct]})
        residential_hp_goals = pd.concat([baseline_hp, residential_hp_goals], ignore_index=True).sort_values('year')

    if inject_year not in municipal_elec_goals['year'].values:
        baseline_muni = pd.DataFrame({'year': [inject_year], 'munipal_heat_pump_adoption': [current_muni_pct]})
        municipal_elec_goals = pd.concat([baseline_muni, municipal_elec_goals], ignore_index=True).sort_values('year')

    return {
        'ev_adoption': ev_goals,
        'residential_heat_pumps': residential_hp_goals,
        'municipal_electrification': municipal_elec_goals
    }


def interpolate_goal(goals_df, year_col, value_col, target_year, baseline_year, baseline_value=0.0):
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
        baseline_year (int): Baseline year (most recent historical year)
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


def project_emissions_for_year(baseline_data, target_year, goals, baseline_year, population_growth_factor=1.0):
    """
    Project all emissions for a specific target year.

    Args:
        baseline_data (dict): Baseline emissions data (from baseline_year)
        target_year (int): Target year for projection
        goals (dict): Goals dictionary from load_goals()
        baseline_year (int): Most recent historical year used as baseline
        population_growth_factor (float): Population growth multiplier

    Returns:
        dict: Complete emissions projection for the year
    """
    # Interpolate all goals for this year
    ev_adoption = interpolate_goal(
        goals['ev_adoption'], 'year', 'EV Adoption', target_year,
        baseline_year=baseline_year, baseline_value=0.0
    )

    hp_adoption = interpolate_goal(
        goals['residential_heat_pumps'], 'year', 'heat pump adoption', target_year,
        baseline_year=baseline_year, baseline_value=0.0
    )

    muni_elec = interpolate_goal(
        goals['municipal_electrification'], 'year', 'munipal_heat_pump_adoption', target_year,
        baseline_year=baseline_year, baseline_value=0.0
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


def create_full_projection(start_year=None, end_year=2050, population_growth_rate=0.0):
    """
    Create full emissions projection from start_year to end_year.

    Args:
        start_year (int, optional): First projection year. Defaults to baseline_year + 1
            where baseline_year is the most recent complete year of historical data.
        end_year (int): Last projection year (default 2050)
        population_growth_rate (float): Annual population growth rate (default 0.0)

    Returns:
        tuple: (projection_df, baseline_data, goals)
            - projection_df: DataFrame with projections for each year
            - baseline_data: Baseline data used (from the most recent historical year)
            - goals: Goals dictionary
    """
    combined_df, metadata = prepare_home_dashboard_data()
    baseline_year = get_baseline_year(combined_df)
    baseline_year_data = combined_df[combined_df['year'] == baseline_year].iloc[0]

    if start_year is None:
        start_year = baseline_year + 1

    baseline_data = {
        'vehicles_tco2e': baseline_year_data['vehicles_tco2e'],
        'residential_fossil_fuel_mtco2e': baseline_year_data['residential_fossil_fuel_mtco2e'],
        'residential_electric_mtco2e': baseline_year_data['residential_electric_mtco2e'],
        'commercial_electric_mtco2e': baseline_year_data['commercial_electric_mtco2e'],
        'other_fuels_mtco2e': baseline_year_data['other_fuels_mtco2e'],
        'electric_mtco2e': baseline_year_data['electric_mtco2e'],
        'total_tco2e': baseline_year_data['total_tco2e'],
        'baseline_year': baseline_year,
    }

    goals = load_goals(baseline_year)

    projections = []
    first_projection_year = baseline_year + 1
    for year in range(start_year, end_year + 1):
        years_from_baseline = year - baseline_year
        pop_growth_factor = (1 + population_growth_rate) ** years_from_baseline

        # The first projection year should match baseline emissions exactly (continuity),
        # but display the injected current-state adoption rates for charting.
        if year == first_projection_year:
            ev_pct = goals['ev_adoption'][goals['ev_adoption']['year'] == year]['EV Adoption'].values[0] if year in goals['ev_adoption']['year'].values else 0.03
            hp_pct = goals['residential_heat_pumps'][goals['residential_heat_pumps']['year'] == year]['heat pump adoption'].values[0] if year in goals['residential_heat_pumps']['year'].values else 0.05
            muni_pct = goals['municipal_electrification'][goals['municipal_electrification']['year'] == year]['munipal_heat_pump_adoption'].values[0] if year in goals['municipal_electrification']['year'].values else 0.0

            projection = {
                'year': year,
                'vehicles_tco2e': baseline_data['vehicles_tco2e'],
                'vehicles_ice_tco2e': baseline_data['vehicles_tco2e'] * (1 - ev_pct),
                'vehicles_ev_tco2e': baseline_data['vehicles_tco2e'] * ev_pct,
                'ev_adoption_pct': ev_pct,
                'residential_fossil_fuel_mtco2e': baseline_data['residential_fossil_fuel_mtco2e'],
                'residential_electric_mtco2e': baseline_data['residential_electric_mtco2e'],
                'residential_heat_pump_electric_mtco2e': 0.0,  # Already in baseline
                'heat_pump_adoption_pct': hp_pct,
                'commercial_electric_mtco2e': baseline_data['commercial_electric_mtco2e'],
                'municipal_other_fuels_mtco2e': baseline_data['other_fuels_mtco2e'],
                'municipal_electric_mtco2e': baseline_data['electric_mtco2e'],
                'municipal_electrification_pct': muni_pct,
                'total_tco2e': baseline_data['total_tco2e'],
                'grid_clean_energy_pct': emission_factors.get_grid_clean_energy_percent(year)
            }
        else:
            projection = project_emissions_for_year(baseline_data, year, goals, baseline_year, pop_growth_factor)
        projections.append(projection)

    projection_df = pd.DataFrame(projections)

    return projection_df, baseline_data, goals


if __name__ == '__main__':
    print("Creating emissions projections...")
    projection_df, baseline, goals = create_full_projection()

    baseline_year = baseline['baseline_year']
    print(f"\nProjections created for {len(projection_df)} years: {projection_df['year'].min()}-{projection_df['year'].max()}")
    print(f"Baseline year (most recent complete historical data): {baseline_year}")

    print("\nKey milestones:")
    for year in [baseline_year + 1, 2030, 2040, 2050]:
        row = projection_df[projection_df['year'] == year]
        if len(row) == 0:
            continue
        data = row.iloc[0]
        print(f"\n{year}:")
        print(f"  Total emissions: {data['total_tco2e']:.0f} mtCO2e")
        print(f"  EV adoption: {data['ev_adoption_pct']*100:.1f}%")
        print(f"  Heat pump adoption: {data['heat_pump_adoption_pct']*100:.1f}%")
        print(f"  Grid clean energy: {data['grid_clean_energy_pct']*100:.1f}%")

    print(f"\nReduction from {baseline_year} baseline ({baseline['total_tco2e']:.0f} mtCO2e) to 2050:")
    reduction = baseline['total_tco2e'] - projection_df[projection_df['year'] == 2050]['total_tco2e'].values[0]
    reduction_pct = (reduction / baseline['total_tco2e']) * 100
    print(f"  {reduction:.0f} mtCO2e ({reduction_pct:.1f}% reduction)")
