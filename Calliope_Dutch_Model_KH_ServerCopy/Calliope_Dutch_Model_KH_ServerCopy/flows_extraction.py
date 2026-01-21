"""
Optimized Calliope V0.6 Flow Extraction
Extracts tidy flow data from .nc files and saves to CSV with aggregated summaries.
No visualization code—pure data extraction and processing.
"""

import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path


# -------- UTILITY FUNCTIONS -------- #
def extract_tidy(ds, var_name, index_dim, value_label):
    """Extract and tidy a single variable from the dataset."""
    df = ds[var_name].to_series().reset_index().rename(
        columns={index_dim: "item", "timesteps": "time", var_name: value_label}
    )
    # Split composite index into columns
    parts = df["item"].str.split("::", expand=True)
    if index_dim.startswith("loc_tech"):
        if parts.shape[1] == 3:
            parts.columns = ["location", "technology", "carrier"]
        else:
            parts.columns = ["location", "technology"]
    else:
        parts.columns = ["location", "carrier"]
    df = pd.concat([df, parts], axis=1)
    # Reorder
    cols = ["time", "location"]
    if "technology" in df.columns:
        cols.append("technology")
    if "carrier" in df.columns:
        cols.append("carrier")
    cols.append(value_label)
    return df[cols]


def extract_cost_om(ds):
    """Extract operational cost data."""
    df = ds["cost_om_con"].to_series().reset_index().rename(
        columns={
            "costs": "cost_category",
            "loc_techs_om_cost": "item",
            "timesteps": "time",
            "cost_om_con": "operational_cost"
        }
    )
    df[["location", "technology"]] = df["item"].str.split("::", expand=True)
    df = df.dropna(subset=["operational_cost"])
    df = df[df["cost_category"] == "monetary"]
    return df[["time", "location", "technology", "operational_cost"]]


def extract_flows(nc_file):
    """
    Extract all flow data from a Calliope V0.6 .nc file.
    Returns: (full_tidy_df, aggregate_summary_df)
    """
    ds = xr.open_dataset(nc_file)
    
    # Calculate timestep duration
    time_coords = ds.coords["timesteps"].values
    if len(time_coords) > 1:
        timestep_hours = (time_coords[1] - time_coords[0]) / np.timedelta64(1, 'h')
    else:
        timestep_hours = 1.0

    # Extract base flow data
    prod  = extract_tidy(ds, "carrier_prod", "loc_tech_carriers_prod", "production")
    con   = extract_tidy(ds, "carrier_con",  "loc_tech_carriers_con", "consumption")
    store = extract_tidy(ds, "storage",      "loc_techs_store",       "storage_level")
    req   = extract_tidy(ds, "required_resource", "loc_techs_balance_demand_constraint", "required_resource")
    
    # Handle unmet_demand (may not exist in all runs)
    try:
        unmet = extract_tidy(ds, "unmet_demand", "loc_carriers", "unmet_demand")
    except KeyError:
        print("Warning: 'unmet_demand' not found. Creating zero-filled placeholder.")
        unique_combos = prod[["time", "location", "carrier"]].drop_duplicates()
        unmet = unique_combos.copy()
        unmet["unmet_demand"] = 0.0

    # Extract cost data
    varc = ds["cost_var"].to_series().reset_index().rename(
        columns={
            "costs": "var_cost_category",
            "loc_techs_om_cost": "item",
            "timesteps": "time",
            "cost_var": "variable_cost"
        }
    )
    varc[["location", "technology"]] = varc["item"].str.split("::", expand=True)
    varc = varc[["time", "location", "technology", "var_cost_category", "variable_cost"]]
    omc = extract_cost_om(ds)

    # Extract capacity data
    df_cap = ds["energy_cap"].to_series().reset_index()
    df_cap.columns = ["item", "capacity"]
    df_cap[["location", "technology"]] = df_cap["item"].str.split("::", expand=True)
    capacity = df_cap[["location", "technology", "capacity"]]

    # Extract coordinate data
    coord_array = ds["loc_coordinates"].values
    coords_idx  = ds.coords["coordinates"].values.tolist()
    locs        = ds.coords["locs"].values.tolist()
    df_coords   = pd.DataFrame(coord_array.T, columns=coords_idx)
    df_coords["location"] = locs
    coords = df_coords[["location", "lon", "lat"]]
    
    ds.close()

    # Merge all data
    net = (prod
           .merge(con, on=["time","location","technology","carrier"], how="outer")
           .fillna({"production":0, "consumption":0}))
    net["net_flow"] = net["production"] + net["consumption"]

    net = (net
           .merge(store, on=["time","location","technology"], how="left")
           .merge(varc,  on=["time","location","technology"], how="left")
           .merge(omc,   on=["time","location","technology"], how="left")
           .merge(req,   on=["time","location","technology"], how="left")
           .merge(unmet, on=["time","location","carrier"],    how="left")
           .merge(capacity, on=["location","technology"],    how="left")
           .merge(coords, on="location", how="left")
          )

    # Calculate utilization metrics
    net["prod_utilization"] = (net["production"] / timestep_hours) / net["capacity"]
    net["con_utilization"]  = (net["consumption"].abs()  / timestep_hours) / net["capacity"]
    
    # Fill NaNs with 0 for numeric columns
    for col in [
        "storage_level", "variable_cost", "operational_cost",
        "required_resource", "unmet_demand", "capacity",
        "prod_utilization", "con_utilization"
    ]:
        if col in net:
            net[col] = net[col].fillna(0)

    # Generate aggregate summary
    agg_summary = generate_aggregate_summary(net)

    return net, agg_summary


def generate_aggregate_summary(df):
    """
    Generate aggregate summary statistics for quick descriptive analysis.
    Returns summary tables organized by useful groupings.
    """
    summary = {}
    
    # 1. Production by technology & carrier (total, mean, max)
    summary['prod_by_tech_carrier'] = (
        df.groupby(['technology', 'carrier'])['production']
        .agg(['sum', 'mean', 'max', 'min', 'count'])
        .reset_index()
        .rename(columns={'sum': 'total_prod', 'count': 'n_records'})
    )
    
    # 2. Consumption by technology & carrier
    summary['con_by_tech_carrier'] = (
        df.groupby(['technology', 'carrier'])['consumption']
        .agg(['sum', 'mean', 'max', 'min', 'count'])
        .reset_index()
        .rename(columns={'sum': 'total_con', 'count': 'n_records'})
    )
    
    # 3. Net flow by technology & carrier
    summary['net_by_tech_carrier'] = (
        df.groupby(['technology', 'carrier'])['net_flow']
        .agg(['sum', 'mean', 'max', 'min', 'std'])
        .reset_index()
        .rename(columns={'sum': 'total_net', 'std': 'std_net'})
    )
    
    # 4. Demand fulfillment share by technology & carrier
    # (production / |consumption| where consumption < 0)
    df_demand = df[df['consumption'] < 0].copy()
    if len(df_demand) > 0:
        df_demand['fulfillment'] = df_demand['production'] / df_demand['consumption'].abs()
        summary['demand_fulfillment'] = (
            df_demand.groupby(['technology', 'carrier'])['fulfillment']
            .agg(['mean', 'min', 'max', 'std', 'count'])
            .reset_index()
            .rename(columns={'mean': 'avg_fulfillment', 'count': 'n_demand_records'})
        )
    
    # 5. By location & technology
    summary['by_location_tech'] = (
        df.groupby(['location', 'technology']).agg({
            'production': ['sum', 'mean'],
            'consumption': ['sum', 'mean'],
            'net_flow': ['sum', 'mean'],
            'capacity': 'first'
        })
        .reset_index()
    )
    summary['by_location_tech'].columns = ['location', 'technology', 
                                           'prod_total', 'prod_mean',
                                           'con_total', 'con_mean',
                                           'net_total', 'net_mean',
                                           'capacity']
    
    # 6. By location & carrier
    summary['by_location_carrier'] = (
        df.groupby(['location', 'carrier']).agg({
            'production': ['sum', 'mean'],
            'consumption': ['sum', 'mean'],
            'net_flow': ['sum', 'mean']
        })
        .reset_index()
    )
    summary['by_location_carrier'].columns = ['location', 'carrier',
                                              'prod_total', 'prod_mean',
                                              'con_total', 'con_mean',
                                              'net_total', 'net_mean']
    
    # 7. Costs by technology
    df_costs = df[df['variable_cost'] > 0].copy()
    if len(df_costs) > 0:
        summary['costs_by_tech'] = (
            df_costs.groupby('technology')['variable_cost']
            .agg(['sum', 'mean', 'max', 'count'])
            .reset_index()
            .rename(columns={'sum': 'total_cost', 'count': 'n_cost_records'})
        )
    
    # 8. Capacity by location & technology
    summary['capacity_by_location_tech'] = (
        df.groupby(['location', 'technology'])['capacity']
        .first()
        .reset_index()
    )
    
    return summary


def save_extraction(net_df, agg_summary, output_folder, base_filename):
    """
    Save full tidy data and aggregate summaries to CSVs.
    
    Parameters:
    -----------
    net_df : pd.DataFrame
        Full tidy dataframe with all records
    agg_summary : dict
        Dictionary of aggregate summary dataframes
    output_folder : str or Path
        Output folder path
    base_filename : str
        Base filename (without extension)
    """
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Save full tidy data
    full_csv = output_folder / f"{base_filename}_full.csv"
    net_df.to_csv(full_csv, index=False)
    print(f"✓ Full tidy data saved: {full_csv}")
    print(f"  Records: {len(net_df)}, Columns: {len(net_df.columns)}")
    
    # Save aggregate summaries
    agg_folder = output_folder / f"{base_filename}_aggregates"
    agg_folder.mkdir(exist_ok=True)
    
    for summary_name, summary_df in agg_summary.items():
        agg_csv = agg_folder / f"{summary_name}.csv"
        summary_df.to_csv(agg_csv, index=False)
        print(f"✓ Aggregate summary saved: {agg_csv}")


def process_single_file(nc_file_path, output_folder):
    """
    Main function to process a single .nc file.
    
    Parameters:
    -----------
    nc_file_path : str or Path
        Path to the .nc file
    output_folder : str or Path
        Output folder where CSV files will be saved
    """
    nc_file_path = Path(nc_file_path)
    
    if not nc_file_path.exists():
        raise FileNotFoundError(f"NC file not found: {nc_file_path}")
    
    print(f"\n{'='*60}")
    print(f"Processing: {nc_file_path.name}")
    print(f"{'='*60}")
    
    # Extract data
    print("Extracting flows...")
    net_df, agg_summary = extract_flows(nc_file_path)
    
    # Save
    base_filename = nc_file_path.stem  # filename without extension
    save_extraction(net_df, agg_summary, output_folder, base_filename)
    
    print(f"✓ Processing complete!\n")
    
    return net_df, agg_summary

def process_single_file_fast(nc_file_path, output_folder):
    """
    Simplified processing to extract only the full tidy dataframe and save its CSV,
    skipping the aggregate summaries for faster performance.
    """
    nc_file_path = Path(nc_file_path)
    if not nc_file_path.exists():
        raise FileNotFoundError(f"NC file not found: {nc_file_path}")
    
    print(f"\n{'='*60}")
    print(f"Processing (fast): {nc_file_path.name}")
    print(f"{'='*60}")
    
    print("Extracting flows...")
    net_df, _ = extract_flows(nc_file_path)  # Only get full dataframe; ignore summaries
    
    # Save only full tidy data
    base_filename = nc_file_path.stem
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    full_csv = output_folder / f"{base_filename}_full.csv"
    net_df.to_csv(full_csv, index=False)
    
    print(f"✓ Full tidy data saved: {full_csv}")
    print(f"  Records: {len(net_df)}, Columns: {len(net_df.columns)}")
    print(f"✓ Processing complete (fast)!\n")
    
    return net_df

def process_multiple_files(nc_folder, output_folder, pattern="*.nc"):
    """
    Process multiple .nc files from a folder.
    
    Parameters:
    -----------
    nc_folder : str or Path
        Folder containing .nc files
    output_folder : str or Path
        Output folder where CSV files will be saved
    pattern : str
        Glob pattern for file matching (default: "*.nc")
    """
    nc_folder = Path(nc_folder)
    output_folder = Path(output_folder)
    
    nc_files = sorted(nc_folder.glob(pattern))
    
    if not nc_files:
        print(f"No .nc files matching '{pattern}' found in {nc_folder}")
        return
    
    print(f"\nFound {len(nc_files)} .nc file(s) to process")
    
    results = {}
    for nc_file in nc_files:
        try:
            net_df, agg_summary = process_single_file(nc_file, output_folder)
            results[nc_file.name] = {"success": True, "rows": len(net_df)}
        except Exception as e:
            print(f"✗ Error processing {nc_file.name}: {e}")
            results[nc_file.name] = {"success": False, "error": str(e)}
    
    # Summary
    print(f"\n{'='*60}")
    print("PROCESSING SUMMARY")
    print(f"{'='*60}")
    successful = sum(1 for r in results.values() if r["success"])
    print(f"Successful: {successful}/{len(nc_files)}")
    for filename, result in results.items():
        status = "✓" if result["success"] else "✗"
        if result["success"]:
            print(f"  {status} {filename}: {result['rows']} records")
        else:
            print(f"  {status} {filename}: {result['error']}")
    
    return results

def process_multiple_files_fast(nc_folder, output_folder, pattern="*.nc"):
    nc_folder = Path(nc_folder)
    output_folder = Path(output_folder)
    nc_files = sorted(nc_folder.glob(pattern))
    if not nc_files:
        print(f"No .nc files matching '{pattern}' found in {nc_folder}")
        return
    print(f"\nFound {len(nc_files)} .nc file(s) to process (fast)")
    results = {}
    for nc_file in nc_files:
        try:
            net_df = process_single_file_fast(nc_file, output_folder)
            results[nc_file.name] = {"success": True, "rows": len(net_df)}
        except Exception as e:
            print(f"✗ Error processing {nc_file.name}: {e}")
            results[nc_file.name] = {"success": False, "error": str(e)}
    print(f"\n{'='*60}")
    print("PROCESSING SUMMARY (fast)")
    print(f"{'='*60}")
    successful = sum(1 for r in results.values() if r["success"])
    print(f"Successful: {successful}/{len(nc_files)}")
    for filename, result in results.items():
        status = "✓" if result["success"] else "✗"
        if result["success"]:
            print(f"  {status} {filename}: {result['rows']} records")
        else:
            print(f"  {status} {filename}: {result['error']}")
    return results

# ---------- CLI ENTRYPOINT ---------- #
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Extract flow data from Calliope V0.6 .nc files to CSV"
    )
    parser.add_argument(
        "--nc_file", 
        type=str, 
        help="Path to single .nc file"
    )
    parser.add_argument(
        "--nc_folder", 
        type=str, 
        help="Path to folder containing .nc files (processes all)"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        required=True,
        help="Output folder for CSV files"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.nc",
        help="Glob pattern for file matching (default: '*.nc')"
    )
    
    args = parser.parse_args()
    
    if args.nc_file:
        process_single_file(args.nc_file, args.output)
    elif args.nc_folder:
        process_multiple_files(args.nc_folder, args.output, args.pattern)
    else:
        parser.print_help()
