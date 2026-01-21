"""
SMR Demand Fulfillment Analysis - Flexible Multi-Scenario
- Extracts ONLY active SMR tech per run
- Deduplicates per (time, location, carrier) - takes first value
- Then sums across ALL locations (SMR can be at multiple locations)
- Units: GWh, weighted by K-means cluster weights
- Organized by: NBNL Scenario (EV/KM) × Sensitivity Scenario (C75/C150/H2/H5)
- Cost calculations SKIPPED
"""

import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
import json
from collections import defaultdict



# -------- CONFIG -------- #
# SMR Types, Configurations, NBNL Scenarios, and Sensitivity Scenarios
SMR_TYPES = ["TO", "HI", "RR"]
CONFIGURATIONS = {"CHP": "", "CHH2P": "X"}  # Empty string for CHP, "X" for CHH2P
NBNL_SCENARIOS = ["EV", "KM"]
SENSITIVITY_SCENARIOS = ["C75", "C150", "H2", "H5"]

DEMAND_TECHS = {
    "electricity": "demand_elc",
    "heat": "demand_pth",
    "hydrogen": "demand_hyd"
}

CARRIERS = ["electricity", "heat", "hydrogen"]


# -------- UTILITY FUNCTIONS -------- #
def parse_run_name(run_name):
    """
    Parse a run name like 'RRX_C75_EV' into components.
    Returns: (smr_type, config, sensitivity, nbnl_scenario) or None if invalid
    """
    parts = run_name.split("_")
    if len(parts) != 3:
        return None
    
    smr_config_str = parts[0]  # e.g., "TO", "TOX", "HI", "HIX", etc.
    sensitivity = parts[1]      # e.g., "C75", "C150", "H2", "H5"
    nbnl = parts[2]            # e.g., "EV", "KM"
    
    # Parse SMR config
    if smr_config_str.endswith("X"):
        smr_type = smr_config_str[:-1]  # "TOX" -> "TO", "HIX" -> "HI"
        config = "CHH2P"
    else:
        smr_type = smr_config_str       # "TO" -> "TO"
        config = "CHP"
    
    # Validate
    if smr_type not in SMR_TYPES or config not in CONFIGURATIONS:
        return None
    if sensitivity not in SENSITIVITY_SCENARIOS:
        return None
    if nbnl not in NBNL_SCENARIOS:
        return None
    
    return {
        "smr_type": smr_type,
        "config": config,
        "sensitivity": sensitivity,
        "nbnl_scenario": nbnl
    }


def discover_runs(nc_folder):
    """
    Discover all .nc files in the folder and parse their names.
    Returns: dict mapping run_name -> parsed metadata
    """
    nc_folder = Path(nc_folder)
    nc_files = sorted(nc_folder.glob("*.nc"))
    
    runs = {}
    for nc_file in nc_files:
        run_name = nc_file.stem  # e.g., "RRX_C75_EV" from "RRX_C75_EV.nc"
        parsed = parse_run_name(run_name)
        if parsed:
            runs[run_name] = parsed
        else:
            print(f"Warning: Could not parse run name '{run_name}'")
    
    return runs


def load_full_csv(csv_path):
    """Load the full tidy CSV from extraction."""
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    return df


def get_timestep_weights(nc_file):
    """Extract timestep weights from .nc file."""
    try:
        ds = xr.open_dataset(nc_file)
        if 'timestep_weights' in ds.data_vars:
            weights = ds['timestep_weights'].values
            ds.close()
            return weights
        else:
            ds.close()
            return None
    except Exception as e:
        print(f"Warning: Could not load weights from {nc_file}: {e}")
        return None


def find_active_smr_tech(df):
    """Find the active SMR technology in the dataset."""
    smr_df = df[df['technology'].str.contains('SMR', na=False, case=False)]
    active_smrs = smr_df[smr_df['production'] > 0]['technology'].unique()
    
    if len(active_smrs) > 0:
        return active_smrs[0]
    else:
        return None


def calculate_demand_fulfillment_weighted(df, weights, carrier, smr_tech=None):
    """
    Calculate demand fulfillment for a carrier with K-means cluster weights.
    Deduplicates per (time, location, carrier) before summing.
    Returns: (total_demand_GWh, total_supply_GWh, fulfillment_%)
    """
    demand_tech = DEMAND_TECHS.get(carrier)
    if not demand_tech:
        return 0, 0, 0
    
    df_carrier = df[df['carrier'] == carrier].copy()
    
    # Apply weights
    if weights is not None:
        times = df['time'].unique()
        time_to_weight = {}
        for i, t in enumerate(sorted(times)):
            if i < len(weights):
                time_to_weight[t] = weights[i]
            else:
                time_to_weight[t] = 1.0
        df_carrier['weight'] = df_carrier['time'].map(time_to_weight)
    else:
        df_carrier['weight'] = 1.0
    
    # Total demand (negative consumption with weight)
    # Deduplicate per (time, location) - take first value
    demand_rows = df_carrier[
        (df_carrier['technology'] == demand_tech) & 
        (df_carrier['consumption'] < 0)
    ].copy()
    
    if len(demand_rows) == 0:
        return 0, 0, 0
    
    demand_dedup = demand_rows.drop_duplicates(subset=['time', 'location'], keep='first')
    total_demand_gwh = (demand_dedup['consumption'].abs() * demand_dedup['weight']).sum()
    
    if total_demand_gwh == 0:
        return 0, 0, 0
    
    # Total SMR supply (ONLY active tech)
    # Deduplicate per (time, location) - take first value, then sum across locations
    if smr_tech is not None:
        supply_rows = df_carrier[
            (df_carrier['technology'] == smr_tech) &
            (df_carrier['production'] > 0)
        ].copy()
        
        supply_dedup = supply_rows.drop_duplicates(subset=['time', 'location'], keep='first')
        total_supply_gwh = (supply_dedup['production'] * supply_dedup['weight']).sum()
    else:
        total_supply_gwh = 0
    
    fulfillment_pct = (total_supply_gwh / total_demand_gwh * 100) if total_demand_gwh > 0 else 0
    
    return total_demand_gwh, total_supply_gwh, fulfillment_pct


def calculate_smr_production_by_carrier_weighted(df, weights, smr_tech):
    """
    Calculate total SMR production by carrier.
    Deduplicates per (time, location, carrier) before summing.
    """
    if smr_tech is None:
        return {c: 0 for c in CARRIERS}
    
    df_smr = df[df['technology'] == smr_tech].copy()
    
    if weights is not None:
        times = df['time'].unique()
        time_to_weight = {}
        for i, t in enumerate(sorted(times)):
            if i < len(weights):
                time_to_weight[t] = weights[i]
            else:
                time_to_weight[t] = 1.0
        df_smr['weight'] = df_smr['time'].map(time_to_weight)
    else:
        df_smr['weight'] = 1.0
    
    # Deduplicate per (time, location, carrier) - take first
    df_smr_dedup = df_smr.drop_duplicates(subset=['time', 'location', 'carrier'], keep='first')
    
    # Apply weight and sum by carrier
    df_smr_dedup['weighted_prod'] = df_smr_dedup['production'] * df_smr_dedup['weight']
    prod_by_carrier = df_smr_dedup.groupby('carrier')['weighted_prod'].sum()
    
    result = {}
    for carrier in CARRIERS:
        result[carrier] = prod_by_carrier.get(carrier, 0)
    
    return result


# -------- ANALYSIS FUNCTIONS -------- #
def analyze_run(nc_file, csv_path, run_name):
    """Analyze a single run."""
    print(f"  Loading {run_name}...")
    
    weights = get_timestep_weights(nc_file)
    df = load_full_csv(csv_path)
    
    # Find active SMR tech
    smr_tech = find_active_smr_tech(df)
    
    results = {
        'run_name': run_name,
        'n_timesteps': len(df['time'].unique()),
        'n_locations': df['location'].nunique(),
        'total_weight': np.sum(weights) if weights is not None else None,
        'active_smr_tech': smr_tech
    }
    
    # Demand fulfillment by carrier (SMRs only) - DEDUPLICATED & WEIGHTED
    for carrier in CARRIERS:
        demand, supply, pct = calculate_demand_fulfillment_weighted(df, weights, carrier, smr_tech=smr_tech)
        results[f'{carrier}_demand_GWh'] = round(demand, 1)
        results[f'{carrier}_smr_supply_GWh'] = round(supply, 1)
        results[f'{carrier}_smr_fulfillment_pct'] = round(pct, 2)
    
    # SMR production by carrier - DEDUPLICATED
    smr_prod = calculate_smr_production_by_carrier_weighted(df, weights, smr_tech)
    for carrier in CARRIERS:
        prod = smr_prod.get(carrier, 0)
        results[f'smr_prod_{carrier}_GWh'] = round(prod, 1)
    
    # Total SMR production
    total_smr_prod = sum(smr_prod.values())
    results['smr_prod_total_GWh'] = round(total_smr_prod, 1)
    
    # Co-generation distribution
    if total_smr_prod > 0:
        for carrier in CARRIERS:
            share = (smr_prod.get(carrier, 0) / total_smr_prod * 100)
            results[f'smr_prod_share_{carrier}_pct'] = round(share, 1)
    else:
        for carrier in CARRIERS:
            results[f'smr_prod_share_{carrier}_pct'] = 0
    
    return results


def build_comparison_tables(all_data, runs_metadata):
    """
    Build comparison tables organized by:
    - NBNL Scenario (EV/KM)
    - Sensitivity Scenario (C75/C150/H2/H5)
    
    Returns: nested dict {nbnl_scenario -> {sensitivity_scenario -> dataframe}}
    """
    comparisons = {}
    
    for nbnl in NBNL_SCENARIOS:
        comparisons[nbnl] = {}
        
        for sensitivity in SENSITIVITY_SCENARIOS:
            rows = []
            
            # Find all runs matching this NBNL + Sensitivity combination
            for run_name, parsed in runs_metadata.items():
                if parsed['nbnl_scenario'] == nbnl and parsed['sensitivity'] == sensitivity:
                    if run_name in all_data:
                        run_data = all_data[run_name]
                        rows.append({
                            'Run': run_name,
                            'SMR_Type': parsed['smr_type'],
                            'Config': parsed['config'],
                            **run_data
                        })
            
            if rows:
                df_comparison = pd.DataFrame(rows)
                comparisons[nbnl][sensitivity] = df_comparison
    
    return comparisons


def generate_reports(nc_folder, data_folder, output_folder):
    """Main function to discover and process all runs."""
    nc_folder = Path(nc_folder)
    data_folder = Path(data_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Discover all runs
    print("\n" + "="*70)
    print("DISCOVERING RUNS")
    print("="*70)
    
    runs_metadata = discover_runs(nc_folder)
    print(f"\nFound {len(runs_metadata)} valid runs:")
    
    # Group by NBNL and Sensitivity for display
    by_group = defaultdict(list)
    for run_name, parsed in runs_metadata.items():
        group_key = f"{parsed['nbnl_scenario']} / {parsed['sensitivity']}"
        by_group[group_key].append(run_name)
    
    for group_key in sorted(by_group.keys()):
        print(f"  {group_key}: {len(by_group[group_key])} runs")
    
    # Analyze all runs
    print("\n" + "="*70)
    print("PROCESSING RUNS")
    print("="*70)
    
    all_data = {}
    
    for nbnl in NBNL_SCENARIOS:
        print(f"\n{nbnl} Scenario:")
        
        for sensitivity in SENSITIVITY_SCENARIOS:
            print(f"  {sensitivity}:")
            
            for run_name, parsed in runs_metadata.items():
                if parsed['nbnl_scenario'] == nbnl and parsed['sensitivity'] == sensitivity:
                    nc_file = nc_folder / f"{run_name}.nc"
                    csv_file = data_folder / f"{run_name}_full.csv"
                    
                    if not nc_file.exists():
                        print(f"    ✗ {run_name}: .nc file not found")
                        continue
                    
                    if not csv_file.exists():
                        print(f"    ✗ {run_name}: CSV not found")
                        continue
                    
                    try:
                        results = analyze_run(nc_file, csv_file, run_name)
                        all_data[run_name] = results
                        smr_tech = results.get('active_smr_tech', 'None')
                        print(f"    ✓ {run_name} (SMR: {smr_tech})")
                    except Exception as e:
                        print(f"    ✗ {run_name}: {e}")
    
    # Build comparison tables
    print("\n" + "="*70)
    print("GENERATING COMPARISON TABLES")
    print("="*70)
    
    comparisons = build_comparison_tables(all_data, runs_metadata)
    
    # Save comparison tables
    for nbnl in NBNL_SCENARIOS:
        nbnl_folder = output_folder / nbnl
        nbnl_folder.mkdir(exist_ok=True)
        
        print(f"\n{nbnl} Scenario:")
        
        for sensitivity in SENSITIVITY_SCENARIOS:
            if sensitivity in comparisons.get(nbnl, {}):
                df_comparison = comparisons[nbnl][sensitivity]
                output_csv = nbnl_folder / f"comparison_{sensitivity}.csv"
                df_comparison.to_csv(output_csv, index=False)
                print(f"  ✓ {sensitivity}: {output_csv} ({len(df_comparison)} runs)")
                
                # Print preview
                print(f"    Preview (Demand Fulfillment %):")
                preview_cols = ['Run', 'SMR_Type', 'Config',
                               'electricity_smr_fulfillment_pct',
                               'heat_smr_fulfillment_pct', 
                               'hydrogen_smr_fulfillment_pct']
                if all(col in df_comparison.columns for col in preview_cols):
                    print(df_comparison[preview_cols].to_string(index=False))
    
    # Save raw data
    output_json = output_folder / "all_run_data.json"
    with open(output_json, 'w') as f:
        json.dump(all_data, f, indent=2, default=str)
    print(f"\n✓ Raw data saved: {output_json}")
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    
    return comparisons, all_data, runs_metadata


def prepare_visualization_data(comparisons, output_folder):
    """
    Prepare visualization data organized by NBNL and Sensitivity.
    Returns separate visualization CSVs for each NBNL × Sensitivity combination.
    """
    output_folder = Path(output_folder)
    
    print("\nPreparing visualization data...")
    
    viz_data = {}
    
    for nbnl in NBNL_SCENARIOS:
        nbnl_folder = output_folder / nbnl
        
        for sensitivity in SENSITIVITY_SCENARIOS:
            if sensitivity not in comparisons.get(nbnl, {}):
                continue
            
            df_comp = comparisons[nbnl][sensitivity]
            group_key = f"{nbnl}_{sensitivity}"
            viz_data[group_key] = {}
            
            # VIZ 1: Demand fulfillment
            viz1_rows = []
            for _, row in df_comp.iterrows():
                viz1_rows.append({
                    'Run': row['Run'],
                    'SMR_Type': row['SMR_Type'],
                    'Config': row['Config'],
                    'Electricity_Fulfillment_%': row['electricity_smr_fulfillment_pct'],
                    'Heat_Fulfillment_%': row['heat_smr_fulfillment_pct'],
                    'Hydrogen_Fulfillment_%': row['hydrogen_smr_fulfillment_pct']
                })
            
            df_viz1 = pd.DataFrame(viz1_rows)
            viz1_csv = nbnl_folder / f"viz1_demand_fulfillment_{sensitivity}.csv"
            df_viz1.to_csv(viz1_csv, index=False)
            viz_data[group_key]['demand_fulfillment'] = viz1_csv
            print(f"  ✓ VIZ1 ({nbnl}/{sensitivity}): {viz1_csv}")
            
            # VIZ 2: SMR production
            viz2_rows = []
            for _, row in df_comp.iterrows():
                viz2_rows.append({
                    'Run': row['Run'],
                    'SMR_Type': row['SMR_Type'],
                    'Config': row['Config'],
                    'Electricity_Production_GWh': row.get('smr_prod_electricity_GWh', 0),
                    'Heat_Production_GWh': row.get('smr_prod_heat_GWh', 0),
                    'Hydrogen_Production_GWh': row.get('smr_prod_hydrogen_GWh', 0)
                })
            
            df_viz2 = pd.DataFrame(viz2_rows)
            viz2_csv = nbnl_folder / f"viz2_smr_production_{sensitivity}.csv"
            df_viz2.to_csv(viz2_csv, index=False)
            viz_data[group_key]['smr_production'] = viz2_csv
            print(f"  ✓ VIZ2 ({nbnl}/{sensitivity}): {viz2_csv}")
            
            # VIZ 3: Co-generation distribution
            viz3_rows = []
            for _, row in df_comp.iterrows():
                viz3_rows.append({
                    'Run': row['Run'],
                    'SMR_Type': row['SMR_Type'],
                    'Config': row['Config'],
                    'Electricity_Share_%': row.get('smr_prod_share_electricity_pct', 0),
                    'Heat_Share_%': row.get('smr_prod_share_heat_pct', 0),
                    'Hydrogen_Share_%': row.get('smr_prod_share_hydrogen_pct', 0)
                })
            
            df_viz3 = pd.DataFrame(viz3_rows)
            viz3_csv = nbnl_folder / f"viz3_cogeneration_distribution_{sensitivity}.csv"
            df_viz3.to_csv(viz3_csv, index=False)
            viz_data[group_key]['cogeneration_distribution'] = viz3_csv
            print(f"  ✓ VIZ3 ({nbnl}/{sensitivity}): {viz3_csv}")
    
    print("\n✓ All visualization data ready!")
    
    return viz_data


# -------- MAIN -------- #
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SMR Demand Fulfillment Analysis - Multi-Scenario"
    )
    parser.add_argument("--nc_folder", type=str, required=True,
                        help="Folder containing .nc files")
    parser.add_argument("--data_folder", type=str, required=True,
                        help="Folder containing extracted _full.csv files")
    parser.add_argument("--output", type=str, required=True,
                        help="Output folder for results")
    
    args = parser.parse_args()
    
    comparisons, all_data, runs_metadata = generate_reports(
        args.nc_folder, args.data_folder, args.output
    )
    viz_data = prepare_visualization_data(comparisons, args.output)
    
    print("\n✓ COMPLETE!")
