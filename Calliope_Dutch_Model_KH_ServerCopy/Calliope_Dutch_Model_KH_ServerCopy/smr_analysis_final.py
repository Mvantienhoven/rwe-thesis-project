"""
SMR Demand Fulfillment & Cost Analysis (TRULY FIXED)
- Extracts ONLY active SMR tech per run
- Deduplicates per (time, location, carrier) - takes first value
- Then sums across ALL locations (SMR can be at multiple locations)
- Units: GWh, weighted by K-means cluster weights
"""

import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
import json


# -------- CONFIG -------- #
RUNS = {
    "EV": {
        "baseline": "BL_EV",
        "smr_configs": {
            "CHP": ["TO_EV", "HI_EV", "RR_EV"],
            "CHH2P": ["TOX_EV", "HIX_EV", "RRX_EV"]
        }
    },
    "KM": {
        "baseline": "BL_KM",
        "smr_configs": {
            "CHP": ["TO_KM", "HI_KM", "RR_KM"],
            "CHH2P": ["TOX_KM", "HIX_KM", "RRX_KM"]
        }
    }
}

DEMAND_TECHS = {
    "electricity": "demand_elc",
    "heat": "demand_pth",
    "hydrogen": "demand_hyd"
}

CARRIERS = ["electricity", "heat", "hydrogen"]


# -------- ANALYSIS FUNCTIONS -------- #
def load_full_csv(csv_path):
    """Load the full tidy CSV from extraction."""
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    return df


def find_nc_file(nc_root_folder, bl2_folder, run_name):
    """Find .nc file for a run (baseline in BL2/, SMR in root)."""
    nc_root = Path(nc_root_folder)
    bl2 = Path(bl2_folder)
    
    if run_name in ["BL_EV", "BL_KM"]:
        nc_file = bl2 / f"{run_name}.nc"
    else:
        nc_file = nc_root / f"{run_name}.nc"
    
    return nc_file if nc_file.exists() else None


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


def calculate_carrier_costs_weighted(df, weights, carrier):
    """
    Calculate costs for a carrier (weighted).
    Deduplicates per (time, location, carrier) before summing.
    """
    df_carrier = df[df['carrier'] == carrier].copy()
    
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

    cost_rows = df_carrier[df_carrier['variable_cost'] > 0].copy()

    # FIX: Deduplicate per (time, location, carrier) BEFORE summing
    cost_dedup = cost_rows.drop_duplicates(subset=['time', 'location', 'carrier'], keep='first')

    total_cost = (cost_dedup['variable_cost'] * cost_dedup['weight']).sum()

    return total_cost



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
    
    # Total system costs
    total_var_cost = df[df['variable_cost'] > 0]['variable_cost'].sum()
    results['total_var_cost_M€'] = round(total_var_cost, 1)
    
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
    
    # Costs by carrier - DEDUPLICATED
    for carrier in CARRIERS:
        carrier_cost = calculate_carrier_costs_weighted(df, weights, carrier)
        results[f'var_cost_{carrier}_M€'] = round(carrier_cost, 1)
    
    return results


def build_comparison_table(data_dict, scenario):
    """Build comparison table for a scenario."""
    rows = []
    
    config = RUNS[scenario]
    baseline_name = config['baseline']
    
    baseline_data = data_dict.get(baseline_name)
    if baseline_data:
        rows.append({
            'Run': baseline_name,
            'Type': 'Baseline',
            'Config': 'N/A',
            'Capacity': 'N/A',
            **baseline_data
        })
    
    for config_type, smr_types in config['smr_configs'].items():
        for smr_run in smr_types:
            smr_data = data_dict.get(smr_run)
            if smr_data:
                capacity = smr_run.replace(f"_{scenario}", "").replace("X", "")
                rows.append({
                    'Run': smr_run,
                    'Type': 'SMR',
                    'Config': config_type,
                    'Capacity': capacity,
                    **smr_data
                })
    
    df_comparison = pd.DataFrame(rows)
    return df_comparison


def generate_reports(nc_root_folder, bl2_folder, data_folder, output_folder):
    """Main function."""
    nc_root_folder = Path(nc_root_folder)
    bl2_folder = Path(bl2_folder)
    data_folder = Path(data_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    all_data = {}
    
    print("\n" + "="*70)
    print("PROCESSING 14 RUNS (DEDUPLICATED + K-MEANS WEIGHTS)")
    print("="*70)
    
    for scenario in ['EV', 'KM']:
        print(f"\n{scenario} Scenario:")
        
        config = RUNS[scenario]
        all_runs = [config['baseline']]
        for smr_configs in config['smr_configs'].values():
            all_runs.extend(smr_configs)
        
        for run_name in all_runs:
            nc_file = find_nc_file(nc_root_folder, bl2_folder, run_name)
            csv_file = data_folder / f"{run_name}_full.csv"
            
            if nc_file is None:
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
    
    comparisons = {}
    for scenario in ['EV', 'KM']:
        print(f"\nBuilding {scenario} comparison table...")
        df_comparison = build_comparison_table(all_data, scenario)
        comparisons[scenario] = df_comparison
        
        output_csv = output_folder / f"comparison_{scenario}.csv"
        df_comparison.to_csv(output_csv, index=False)
        print(f"  ✓ Saved: {output_csv}")
        
        print(f"\n{scenario} Preview (Demand Fulfillment %):")
        preview_cols = ['Run', 'Type', 'Config', 'Capacity', 
                       'electricity_smr_fulfillment_pct',
                       'heat_smr_fulfillment_pct', 
                       'hydrogen_smr_fulfillment_pct']
        print(df_comparison[preview_cols].to_string(index=False))
    
    output_json = output_folder / "all_run_data.json"
    with open(output_json, 'w') as f:
        json.dump(all_data, f, indent=2, default=str)
    print(f"\n✓ Raw data saved: {output_json}")
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    
    return comparisons, all_data


def prepare_visualization_data(comparisons, output_folder):
    """Prepare data for visualizations."""
    output_folder = Path(output_folder)
    
    print("\nPreparing visualization data...")
    
    # VIZ 1: Demand fulfillment
    viz1_rows = []
    for scenario, df_comp in comparisons.items():
        df_smr = df_comp[df_comp['Type'] == 'SMR']
        for _, row in df_smr.iterrows():
            viz1_rows.append({
                'Scenario': scenario,
                'Run': row['Run'],
                'Config': row['Config'],
                'Capacity': row['Capacity'],
                'Electricity_Fulfillment_%': row['electricity_smr_fulfillment_pct'],
                'Heat_Fulfillment_%': row['heat_smr_fulfillment_pct'],
                'Hydrogen_Fulfillment_%': row['hydrogen_smr_fulfillment_pct']
            })
    
    df_viz1 = pd.DataFrame(viz1_rows)
    viz1_csv = output_folder / "viz1_demand_fulfillment.csv"
    df_viz1.to_csv(viz1_csv, index=False)
    print(f"  ✓ VIZ1: {viz1_csv}")
    
    # VIZ 2: Cost comparison
    viz2_rows = []
    for scenario, df_comp in comparisons.items():
        for _, row in df_comp.iterrows():
            viz2_rows.append({
                'Scenario': scenario,
                'Run': row['Run'],
                'Type': row['Type'],
                'Config': row['Config'],
                'Total_Var_Cost_M€': row['total_var_cost_M€'],
                'Electricity_Cost_M€': row['var_cost_electricity_M€'],
                'Heat_Cost_M€': row['var_cost_heat_M€'],
                'Hydrogen_Cost_M€': row['var_cost_hydrogen_M€']
            })
    
    df_viz2 = pd.DataFrame(viz2_rows)
    viz2_csv = output_folder / "viz2_cost_comparison.csv"
    df_viz2.to_csv(viz2_csv, index=False)
    print(f"  ✓ VIZ2: {viz2_csv}")
    
    # VIZ 3: SMR production
    viz3_rows = []
    for scenario, df_comp in comparisons.items():
        df_smr = df_comp[df_comp['Type'] == 'SMR']
        for _, row in df_smr.iterrows():
            viz3_rows.append({
                'Scenario': scenario,
                'Run': row['Run'],
                'Config': row['Config'],
                'Capacity': row['Capacity'],
                'Electricity_Production_GWh': row.get('smr_prod_electricity_GWh', 0),
                'Heat_Production_GWh': row.get('smr_prod_heat_GWh', 0),
                'Hydrogen_Production_GWh': row.get('smr_prod_hydrogen_GWh', 0)
            })
    
    df_viz3 = pd.DataFrame(viz3_rows)
    viz3_csv = output_folder / "viz3_smr_production.csv"
    df_viz3.to_csv(viz3_csv, index=False)
    print(f"  ✓ VIZ3: {viz3_csv}")
    
    # VIZ 4: Co-generation distribution
    viz4_rows = []
    for scenario, df_comp in comparisons.items():
        df_smr = df_comp[df_comp['Type'] == 'SMR']
        for _, row in df_smr.iterrows():
            viz4_rows.append({
                'Scenario': scenario,
                'Run': row['Run'],
                'Config': row['Config'],
                'Capacity': row['Capacity'],
                'Electricity_Share_%': row.get('smr_prod_share_electricity_pct', 0),
                'Heat_Share_%': row.get('smr_prod_share_heat_pct', 0),
                'Hydrogen_Share_%': row.get('smr_prod_share_hydrogen_pct', 0)
            })
    
    df_viz4 = pd.DataFrame(viz4_rows)
    viz4_csv = output_folder / "viz4_cogeneration_distribution.csv"
    df_viz4.to_csv(viz4_csv, index=False)
    print(f"  ✓ VIZ4: {viz4_csv}")
    
    print("\n✓ All visualization data ready!")
    
    return df_viz1, df_viz2, df_viz3, df_viz4


# -------- MAIN -------- #
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--nc_root", type=str, required=True)
    parser.add_argument("--bl2", type=str, required=True)
    parser.add_argument("--data_folder", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    
    args = parser.parse_args()
    
    comparisons, all_data = generate_reports(args.nc_root, args.bl2, args.data_folder, args.output)
    df_viz1, df_viz2, df_viz3, df_viz4 = prepare_visualization_data(comparisons, args.output)
    
    print("\n✓ COMPLETE!")
