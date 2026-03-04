
import xarray as xr
import pandas as pd
import yaml
import numpy as np
from pathlib import Path

def load_and_process_data(netcdf_path, model_yaml_path):
    """Load capacity and cost data from netcdf file"""
    exclude_prefixes = [
        "free_gas_transmission",
        "free_hyd_transmission", 
        "free_co2_stored_transmission",
        "free_solid_fuel_transmission",
        "free_ets_budget_transmission",
        "free_ets_penalty_transmission",
        "free_sink_transmission",
        "free_co2_transmission",
    ]

    ds = xr.open_dataset(netcdf_path)

    # Load capacity data
    cap_da = ds["energy_cap"]
    df_cap = cap_da.to_series().reset_index()
    df_cap.columns = ["loc_tech", "capacity"]
    df_cap[["node", "tech"]] = df_cap["loc_tech"].str.split("::", expand=True)
    df_cap = df_cap[["node", "tech", "capacity"]]

    # Filter out unwanted tech prefixes
    mask = df_cap['tech'].apply(lambda x: not any(x.startswith(pref) for pref in exclude_prefixes))
    df_cap = df_cap[mask].reset_index(drop=True)

    # Load cost data
    cost_matrix = ds["cost"].values
    loc_techs_cost = ds.coords["loc_techs_cost"].values
    cost_cats = list(ds.coords["costs"].values)
    df_cost = pd.DataFrame(cost_matrix.T, index=loc_techs_cost, columns=cost_cats).reset_index().rename(columns={"index":"loc_tech"})

    # Split loc_tech into node and tech
    df_cost[["node", "tech_full"]] = df_cost["loc_tech"].str.split("::", expand=True)
    df_cost["tech"] = df_cost["tech_full"].str.replace(
        r"^(interconnector_base|transmission_hvac).*$",
        lambda m: m.group(1), regex=True
    )

    # Filter costs
    pattern = "|".join(exclude_prefixes)
    df_cost = df_cost[~df_cost["tech_full"].str.contains(pattern)]
    df_cost = df_cost[["node", "tech", "tech_full", "monetary"]]

    # Load variable costs
    varc = ds["cost_var"].to_series().reset_index().rename(
        columns={
            "costs": "var_cost_category",
            "loc_techs_om_cost": "item",
            "timesteps": "time", 
            "cost_var": "variable_cost"
        }
    )
    varc[["location", "technology"]] = varc["item"].str.split("::", expand=True)
    varc = varc[varc["var_cost_category"] == "monetary"]

    # Filter transmission prefixes from variable costs
    transmission_prefixes = [
        "transmission_hvac", "free_co2_transmission", "free_co2_stored_transmission",
        "free_gas_transmission", "free_hyd_transmission", 
        "free_sink_transmission", "interconnector_"
    ]
    varc = varc[~varc["technology"].str.startswith(tuple(transmission_prefixes))]

    ds.close()
    return df_cap, df_cost, varc

def calculate_key_metrics(df_cap, df_cost, df_varc):
    """Calculate the key comparison metrics"""

    # 1. Total System Cost (TSC) = sum of all monetary costs
    total_node_costs = df_cost['monetary'].sum()
    total_link_costs = df_cost[df_cost['tech_full'].str.contains(":")]['monetary'].sum()
    total_system_cost = total_node_costs + total_link_costs

    # 2. Total Links Costs (interconnector + transmission)
    link_costs = df_cost[
        (df_cost['tech'].str.startswith('interconnector_base')) | 
        (df_cost['tech'].str.startswith('transmission_hvac'))
    ]['monetary'].sum()

    # 3. Total Variable Costs
    total_variable_costs = df_varc['variable_cost'].sum()

    # 4. Installed capacity of nuclear SMR
    smr_capacity = df_cap[df_cap['tech'] == 'pp_nuclear_smr']['capacity'].sum()

    # 5. Installed capacity of VRES (Variable Renewable Energy Sources)
    vres_techs = ['wind_offshore', 'wind_onshore', 'pv_rooftop', 'pv_utility']
    vres_capacity = df_cap[df_cap['tech'].isin(vres_techs)]['capacity'].sum()

    # 6. Installed capacity of transmission_hvac
    transmission_hvac_capacity = df_cap[
        df_cap['tech'].str.startswith('transmission_hvac')
    ]['capacity'].sum()

    # 7. Installed capacity of interconnector_base
    interconnector_base_capacity = df_cap[
        df_cap['tech'].str.startswith('interconnector_base')
    ]['capacity'].sum()

    return {
        'Total System Cost (M€)': total_system_cost,
        'Total Links Costs (M€)': link_costs,
        'Total Variable Costs (€)': total_variable_costs,
        'SMR Installed Capacity (GW)': smr_capacity,
        'VRES Installed Capacity (GW)': vres_capacity,
        'Transmission HVAC Capacity (GW)': transmission_hvac_capacity,
        'Interconnector Base Capacity (GW)': interconnector_base_capacity
    }

def compare_two_runs(netcdf_path_1, yaml_path_1, netcdf_path_2, yaml_path_2, 
                     run_1_name="Run 1", run_2_name="Run 2"):
    """
    Compare two Calliope model runs and return comparison tables

    Parameters:
    -----------
    netcdf_path_1 : str
        Path to first run's NetCDF file
    yaml_path_1 : str  
        Path to first run's YAML file
    netcdf_path_2 : str
        Path to second run's NetCDF file
    yaml_path_2 : str
        Path to second run's YAML file
    run_1_name : str
        Name for first run (default: "Run 1")
    run_2_name : str
        Name for second run (default: "Run 2")

    Returns:
    --------
    comparison_df : pd.DataFrame
        DataFrame with comparison of key metrics
    """

    print(f"Loading and processing {run_1_name}...")
    df_cap_1, df_cost_1, df_varc_1 = load_and_process_data(netcdf_path_1, yaml_path_1)
    metrics_1 = calculate_key_metrics(df_cap_1, df_cost_1, df_varc_1)

    print(f"Loading and processing {run_2_name}...")
    df_cap_2, df_cost_2, df_varc_2 = load_and_process_data(netcdf_path_2, yaml_path_2)
    metrics_2 = calculate_key_metrics(df_cap_2, df_cost_2, df_varc_2)

    # Create comparison DataFrame
    comparison_data = []
    for metric in metrics_1.keys():
        value_1 = metrics_1[metric]
        value_2 = metrics_2[metric]
        absolute_diff = value_2 - value_1

        # Calculate percentage change (handle division by zero)
        if value_1 != 0:
            percent_change = (absolute_diff / abs(value_1)) * 100
        elif value_2 != 0:
            percent_change = float('inf') if value_2 > 0 else float('-inf')
        else:
            percent_change = 0

        comparison_data.append({
            'Metric': metric,
            run_1_name: value_1,
            run_2_name: value_2,
            'Absolute Difference': absolute_diff,
            'Percentage Change (%)': percent_change
        })

    comparison_df = pd.DataFrame(comparison_data)

    # Format the DataFrame for better readability
    for col in [run_1_name, run_2_name, 'Absolute Difference']:
        if col in comparison_df.columns:
            comparison_df[col] = comparison_df[col].apply(lambda x: f"{x:.3f}")

    comparison_df['Percentage Change (%)'] = comparison_df['Percentage Change (%)'].apply(
        lambda x: f"{x:.2f}" if abs(x) != float('inf') else "N/A"
    )

    print("\n" + "="*80)
    print(f"COMPARISON: {run_1_name} vs {run_2_name}")
    print("="*80)
    print(comparison_df.to_string(index=False))
    print("="*80)

    return comparison_df

def detailed_capacity_comparison(netcdf_path_1, yaml_path_1, netcdf_path_2, yaml_path_2,
                               run_1_name="Run 1", run_2_name="Run 2"):
    """
    Create detailed capacity comparison by technology
    """

    print(f"\nCreating detailed capacity comparison...")
    df_cap_1, _, _ = load_and_process_data(netcdf_path_1, yaml_path_1)
    df_cap_2, _, _ = load_and_process_data(netcdf_path_2, yaml_path_2)

    # Aggregate capacity by technology
    cap_1 = df_cap_1.groupby('tech')['capacity'].sum()
    cap_2 = df_cap_2.groupby('tech')['capacity'].sum()

    # Combine into comparison DataFrame
    all_techs = set(cap_1.index) | set(cap_2.index)

    detailed_data = []
    for tech in sorted(all_techs):
        val_1 = cap_1.get(tech, 0)
        val_2 = cap_2.get(tech, 0)
        diff = val_2 - val_1

        if val_1 != 0:
            pct_change = (diff / val_1) * 100
        elif val_2 != 0:
            pct_change = float('inf') if val_2 > 0 else float('-inf')
        else:
            pct_change = 0

        # Only include technologies with non-zero capacity in at least one run
        if val_1 > 0.001 or val_2 > 0.001:  # threshold to avoid tiny values
            detailed_data.append({
                'Technology': tech,
                f'{run_1_name} (GW)': f"{val_1:.3f}",
                f'{run_2_name} (GW)': f"{val_2:.3f}",
                'Difference (GW)': f"{diff:.3f}",
                'Change (%)': f"{pct_change:.2f}" if abs(pct_change) != float('inf') else "N/A"
            })

    detailed_df = pd.DataFrame(detailed_data)

    print("\n" + "="*100)
    print(f"DETAILED CAPACITY COMPARISON: {run_1_name} vs {run_2_name}")
    print("="*100)
    print(detailed_df.to_string(index=False))
    print("="*100)

    return detailed_df

# Example usage function
def run_comparison_analysis():
    """
    Example function showing how to use the comparison tools
    Replace the file paths with your actual model run files
    """

    # Example file paths - REPLACE WITH YOUR ACTUAL PATHS
    netcdf_1 = "path/to/run1.nc"
    yaml_1 = "path/to/run1_model.yaml"
    netcdf_2 = "path/to/run2.nc"  
    yaml_2 = "path/to/run2_model.yaml"

    # Run the comparison
    comparison_df = compare_two_runs(
        netcdf_1, yaml_1, netcdf_2, yaml_2,
        run_1_name="Baseline", run_2_name="SMR Scenario"
    )

    # Get detailed capacity comparison
    detailed_df = detailed_capacity_comparison(
        netcdf_1, yaml_1, netcdf_2, yaml_2, 
        run_1_name="Baseline", run_2_name="SMR Scenario"
    )

    # Save results to CSV
    comparison_df.to_csv("comparison_summary.csv", index=False)
    detailed_df.to_csv("detailed_capacity_comparison.csv", index=False)

    print("\nComparison results saved to CSV files!")

    return comparison_df, detailed_df

# If running as script
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 5:
        print("Usage: python comparison_script.py <netcdf_1> <yaml_1> <netcdf_2> <yaml_2>")
        sys.exit(1)

    netcdf_1, yaml_1, netcdf_2, yaml_2 = sys.argv[1:5]

    comparison_df = compare_two_runs(netcdf_1, yaml_1, netcdf_2, yaml_2)
    detailed_df = detailed_capacity_comparison(netcdf_1, yaml_1, netcdf_2, yaml_2)
