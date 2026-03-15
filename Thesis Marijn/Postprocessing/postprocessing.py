import xarray as xr
import pandas as pd
import yaml
import json
from pathlib import Path
from jinja2 import Template
import folium
from folium.plugins import BeautifyIcon
from folium.features import DivIcon
from branca.element import Template as BrancaTemplate, MacroElement

# Tech categories and colors copied from your script here
TECH_CATEGORIES_MAIN = {
    "Hydrogen": ["pp_ccgt_hyd","pp_ocgt_hyd"],
    "Gas":      ["pp_ccgt_gas","pp_ocgt_gas"],
    "Power":    ["pp_nuclear_conventional","pp_nuclear_smr", 
                 "pp_biomass_standalone","pp_waste_incinerator",
                 "wind_offshore","wind_onshore","pv_rooftop","pv_utility",
                 "hydro_RoR","curtailment_elc"],
    "SMR":      ["pp_SMR_Hitachi_CHP_1", "pp_SMR_RollsRoyce_CHP_1", "pp_SMR_Thorizon_CHP_1", 
                 "pp_SMR_Hitachi_CH2P_1", "pp_SMR_RollsRoyce_CH2P_1", "pp_SMR_Thorizon_CH2P_1",
                 "pp_SMR_Hitachi_CHH2P_1", "pp_SMR_RollsRoyce_CHH2P_1", "pp_SMR_Thorizon_CHH2P_1",
                 "pp_SMR_Hitachi_CHP_2", "pp_SMR_RollsRoyce_CHP_2", "pp_SMR_Thorizon_CHP_2", 
                 "pp_SMR_Hitachi_CH2P_2", "pp_SMR_RollsRoyce_CH2P_2", "pp_SMR_Thorizon_CH2P_2",
                 "pp_SMR_Hitachi_CHH2P_2", "pp_SMR_RollsRoyce_CHH2P_2", "pp_SMR_Thorizon_CHH2P_2",
                 "pp_SMR_Hitachi_CHP_3", "pp_SMR_RollsRoyce_CHP_3", "pp_SMR_Thorizon_CHP_3", 
                 "pp_SMR_Hitachi_CH2P_3", "pp_SMR_RollsRoyce_CH2P_3", "pp_SMR_Thorizon_CH2P_3",
                 "pp_SMR_Hitachi_CHH2P_3", "pp_SMR_RollsRoyce_CHH2P_3", "pp_SMR_Thorizon_CHH2P_3"],
    # "SMR":      ["pp_SMR_CHP_generic","pp_SMR_CHH2P_generic"],
    "Heat":     ["pth_electric_boiler"],
    "Conversion": ["pp_elektrolyser_onshore","pp_elektrolyser_offshore",
                   "reformer_smr_ccs","reformer_atr_ccs_96"],
    "Storage":  ["ES_BESS_IDES","ES_BESS_offshore","ES_BESS_MDES","ES_BESS_households","ES_pumped_hydro"],
    "Import":   ["import_DIE","import_SIE","import_DEN","import_NOR",
                "import_EYC","import_WSL","import_UK","import_GRO","import_ZAN"],
    "Export":   ["export_DIE","export_SIE","export_DEN","export_NOR",
                "export_EYC","export_WSL","export_UK","export_GRO","export_ZAN"],
}

TECH_CATEGORIES_MINI = {
    "Nuclear": ["pp_nuclear_conventional","pp_nuclear_smr", "pp_SMR_CHP_generic","pp_SMR_CHH2P_generic"],
    "SMR":      ["pp_SMR_Hitachi_CHP_1", "pp_SMR_RollsRoyce_CHP_1", "pp_SMR_Thorizon_CHP_1", 
                 "pp_SMR_Hitachi_CH2P_1", "pp_SMR_RollsRoyce_CH2P_1", "pp_SMR_Thorizon_CH2P_1",
                 "pp_SMR_Hitachi_CHH2P_1", "pp_SMR_RollsRoyce_CHH2P_1", "pp_SMR_Thorizon_CHH2P_1",
                 "pp_SMR_Hitachi_CHP_2", "pp_SMR_RollsRoyce_CHP_2", "pp_SMR_Thorizon_CHP_2", 
                 "pp_SMR_Hitachi_CH2P_2", "pp_SMR_RollsRoyce_CH2P_2", "pp_SMR_Thorizon_CH2P_2",
                 "pp_SMR_Hitachi_CHH2P_2", "pp_SMR_RollsRoyce_CHH2P_2", "pp_SMR_Thorizon_CHH2P_2",
                 "pp_SMR_Hitachi_CHP_3", "pp_SMR_RollsRoyce_CHP_3", "pp_SMR_Thorizon_CHP_3", 
                 "pp_SMR_Hitachi_CH2P_3", "pp_SMR_RollsRoyce_CH2P_3", "pp_SMR_Thorizon_CH2P_3",
                 "pp_SMR_Hitachi_CHH2P_3", "pp_SMR_RollsRoyce_CHH2P_3", "pp_SMR_Thorizon_CHH2P_3"],
    "VRE": ["wind_offshore","wind_onshore","pv_rooftop","pv_utility"],
    "Other_Renewable": ["hydro_RoR","pp_biomass_standalone","pp_waste_incinerator"],
    "Gas": ["pp_ccgt_gas","pp_ocgt_gas"],
    "Hydrogen": ["pp_ccgt_hyd","pp_ocgt_hyd"],
    "Electrolyser": ["pp_elektrolyser_onshore","pp_elektrolyser_offshore"],
    "Heat": ["pth_electric_boiler"],
    "Storage": ["ES_BESS_IDES","ES_BESS_offshore","ES_BESS_MDES","ES_BESS_households","ES_pumped_hydro"],
    "Import": ["import_DIE","import_SIE","import_DEN","import_NOR","import_EYC","import_WSL","import_UK","import_GRO","import_ZAN"],
    "Export": ["export_DIE","export_SIE","export_DEN","export_NOR","export_EYC","export_WSL","export_UK","export_GRO","export_ZAN"],
}

tech_colors = {
    "pp_nuclear_conventional": "#9ef01a",
    "pp_nuclear_smr": "#ffff3f",
    "pp_SMR_Hitachi_CHP_1": "#2d9e40",
    "pp_SMR_RollsRoyce_CHP_1": "#2ca83d",
    "pp_SMR_Thorizon_CHP_1": "#a0d468",
    "pp_SMR_RollsRoyce_CH2P_1": "#ddaf30",
    "pp_SMR_Thorizon_CH2P_1": "#ca9a21",
    "pp_SMR_Hitachi_CH2P_1": "#f8b712",
    "pp_SMR_RollsRoyce_CHH2P_1": "#30dda6",
    "pp_SMR_Thorizon_CHH2P_1": "#21ca86",
    "pp_SMR_Hitachi_CHH2P_1": "#12f891",
    "pp_SMR_Hitachi_CHP_2": "#2d9e40",
    "pp_SMR_RollsRoyce_CHP_2": "#2ca83d",
    "pp_SMR_Thorizon_CHP_2": "#a0d468",
    "pp_SMR_RollsRoyce_CH2P_2": "#ddaf30",
    "pp_SMR_Thorizon_CH2P_2": "#ca9a21",
    "pp_SMR_Hitachi_CH2P_2": "#f8b712",
    "pp_SMR_RollsRoyce_CHH2P_2": "#30dda6",
    "pp_SMR_Thorizon_CHH2P_2": "#21ca86",
    "pp_SMR_Hitachi_CHH2P_2": "#12f891",
    "pp_SMR_Hitachi_CHP_3": "#2d9e40",
    "pp_SMR_RollsRoyce_CHP_3": "#2ca83d",
    "pp_SMR_Thorizon_CHP_3": "#a0d468",
    "pp_SMR_RollsRoyce_CH2P_3": "#ddaf30",
    "pp_SMR_Thorizon_CH2P_3": "#ca9a21",
    "pp_SMR_Hitachi_CH2P_3": "#f8b712",
    "pp_SMR_RollsRoyce_CHH2P_3": "#30dda6",
    "pp_SMR_Thorizon_CHH2P_3": "#21ca86",
    "pp_SMR_Hitachi_CHH2P_3": "#12f891",
    "pp_SMR_CHP_generic": "#12f891",
    "pp_SMR_CHH2P_generic": "#12f891",
    "wind_offshore": "#34a0a4",
    "wind_onshore": "#52b69a",
    "pv_rooftop": "#b5e48c",
    "pv_utility": "#d9ed92",
    "hydro_RoR": "#168aad",
    "pp_biomass_standalone": "#f4a261",
    "pp_waste_incinerator": "#e76f51",
    "pp_ccgt_gas": "#577590",
    "pp_ocgt_gas": "#345678",
    "pp_ccgt_hyd": "#277da1",
    "pp_ocgt_hyd": "#1b4965",
    "pp_elektrolyser_onshore": "#f9c74f",
    "pp_elektrolyser_offshore": "#f4d35e",
    "pth_electric_boiler": "#f94144",
    "ES_BESS_IDES": "#8338ec",
    "ES_BESS_offshore": "#8338ec",
    "ES_BESS_MDES": "#9d4edd",
    "ES_BESS_households": "#b084cc",
    "ES_pumped_hydro": "#6a4c93",
    "import_DIE": "#ffe5d9",
    "import_SIE": "#ffd7ba",
    "import_DEN": "#ffbcaf",
    "import_NOR": "#ff8b72",
    "import_EYC": "#ffa600",
    "import_WSL": "#ff9933",
    "import_UK": "#ff7700",
    "import_GRO": "#ff4400",
    "import_ZAN": "#cc3300",
    "export_DIE": "#9d8189",
    "export_SIE": "#ab8fa9",
    "export_DEN": "#b48db6",
    "export_NOR": "#c299c9",
    "export_EYC": "#d1aadd",
    "export_WSL": "#dfb8f2",
    "export_UK": "#ebb8fc",
    "export_GRO": "#f5c5fc",
    "export_ZAN": "#f9d9fc",
}

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

def categorize_main(t):
    for cat, lst in TECH_CATEGORIES_MAIN.items():
        if any(t.startswith(p) for p in lst):
            return cat
    return "Other"

def categorize_mini(t):
    for cat, lst in TECH_CATEGORIES_MINI.items():
        if any(t.startswith(p) for p in lst):
            return cat
    return None

def load_and_process_data(netcdf_path, model_yaml_path):
    ds = xr.open_dataset(netcdf_path)
    cap_da = ds["energy_cap"]
    df = cap_da.to_series().reset_index()
    df.columns = ["loc_tech", "capacity"]
    df[["node", "tech"]] = df["loc_tech"].str.split("::", expand=True)
    df_simple = df[["node", "tech", "capacity"]]
    # Filter out unwanted tech prefixes
    mask = df_simple['tech'].apply(lambda x: not any(x.startswith(pref) for pref in exclude_prefixes))
    df_filtered = df_simple[mask].reset_index(drop=True)
    # Also load locations from YAML
    with open(model_yaml_path) as f:
        locations = yaml.safe_load(f)["locations"]
    return df_filtered, locations

def load_costs(netcdf_path):
    ds = xr.open_dataset(netcdf_path)
    cost_matrix = ds["cost"].values
    loc_techs_cost = ds.coords["loc_techs_cost"].values
    cost_cats = list(ds.coords["costs"].values)
    df_cost = pd.DataFrame(cost_matrix.T, index=loc_techs_cost, columns=cost_cats).reset_index().rename(columns={"index":"loc_tech"})
    
    # Split loc_tech into node and full tech string (including target for links)
    df_cost[["node", "tech_full"]] = df_cost["loc_tech"].str.split("::", expand=True)
    
    # Extract base tech (without target suffix) for merging
    df_cost["tech"] = df_cost["tech_full"].str.replace(
        r"^(interconnector_base|transmission_hvac).*$",
        lambda m: m.group(1), regex=True
    )
    
    pattern = "|".join(exclude_prefixes)
    df_cost = df_cost[~df_cost["tech_full"].str.contains(pattern)]



    return df_cost[["node", "tech", "tech_full", "monetary"]]

def cost_totals(netcdf_path):
    # 1. Load dataset and select monetary slices
    ds = xr.open_dataset(netcdf_path)
    var_da = ds["cost_var"].sel(costs="monetary")          # dims: loc_techs_om_cost, timesteps
    inv_da = ds["cost_investment"].sel(costs="monetary")   # dims: loc_techs_investment_cost

    # 2. Extract loc::tech identifiers and derive tech names
    loc_var = ds.coords["loc_techs_om_cost"].values
    tech_var = [lt.split("::",1)[1] for lt in loc_var]
    loc_inv = ds.coords["loc_techs_investment_cost"].values
    tech_inv = [lt.split("::",1)[1] for lt in loc_inv]

    # 3. Aggregate per-tech variable and fixed costs
    df_var = pd.DataFrame({
        "tech": tech_var,
        "var_cost": var_da.sum(dim="timesteps").values
    }).groupby("tech", as_index=True)["var_cost"].sum()

    df_inv = pd.DataFrame({
        "tech": tech_inv,
        "fixed_cost": inv_da.values
    }).groupby("tech", as_index=True)["fixed_cost"].sum()

    # 4. Combine into single DataFrame, filling missing with 0
    df = pd.concat([df_var, df_inv], axis=1).fillna(0)

    # 5. Define masks
    mask_tech    = ~df.index.str.contains("transmission|interconnector|^ES_")
    mask_infra   = df.index.str.contains("transmission|interconnector")
    mask_storage = df.index.str.startswith("ES_")

    # 6. Compute summaries
    total_tech_cost_fixed    = df.loc[mask_tech, "fixed_cost"].sum()
    total_tech_cost_var      = df.loc[mask_tech, "var_cost"].sum()
    total_infra_cost_fixed   = df.loc[mask_infra, "fixed_cost"].sum()
    total_infra_cost_var     = df.loc[mask_infra, "var_cost"].sum()
    total_storage_cost_fixed = df.loc[mask_storage, "fixed_cost"].sum()
    total_storage_cost_var   = df.loc[mask_storage, "var_cost"].sum()
    total_var_cost           = df["var_cost"].sum()
    total_fixed_cost         = df["fixed_cost"].sum()
    total_system_cost        = total_var_cost + total_fixed_cost

    # 7. Return all results in a dict
    return {
        "total_tech_cost_fixed":    total_tech_cost_fixed,
        "total_tech_cost_var":      total_tech_cost_var,
        "total_infra_cost_fixed":   total_infra_cost_fixed,
        "total_infra_cost_var":     total_infra_cost_var,
        "total_storage_cost_fixed": total_storage_cost_fixed,
        "total_storage_cost_var":   total_storage_cost_var,
        "total_var_cost":           total_var_cost,
        "total_fixed_cost":         total_fixed_cost,
        "total_system_cost":        total_system_cost,
    }

def create_main_map(df, locations, geojson_path, cost_df_full):
    m = folium.Map(location=[52.2,5.3], zoom_start=7, tiles="cartodbpositron")
    nuts2 = json.load(open(geojson_path))
    folium.GeoJson(nuts2, style_function=lambda feat: {
        "fillColor":"#ffffff00","color":"#444444","weight":1
    }).add_to(m)



    # Build cost lookup for nodes (base tech only)
    cost_dict_nodes = df.set_index(["node", "tech"])["monetary"].to_dict()
    
    # Build cost lookup for links (node + tech_full with target)
    cost_dict_links = cost_df_full.set_index(["node", "tech_full"])["monetary"].to_dict()



    link_caps = {(r.node, r.tech): r.capacity for r in df.itertuples(index=False)}
    max_cap = max(link_caps.values()) if link_caps else 1



    for node, attrs in locations.items():
        coords = attrs["coordinates"]
        subset = df[df.node == node]
        if subset.empty:
            continue
        html = ""
        total_cost_node = subset.monetary.sum()



        for cat in list(TECH_CATEGORIES_MAIN.keys()) + ["Other"]:
            cat_df = subset[subset.tech.map(categorize_main) == cat]
            cat_df = cat_df[cat_df.capacity.round(4) >= 0.0001]
            if cat_df.empty:
                continue
            table = cat_df.assign(
                capacity=lambda d: d.capacity.map("{:.4f} GW".format),
                cost=lambda d: d.monetary.map(lambda x: "" if x == 0 else f"{x:.3f} M€")
            )[['tech', 'capacity', 'cost']]
            html += f"<h4 style='margin:4px 0'>{cat}</h4>"
            html += table.to_html(index=False, header=False, classes="table table-sm")



        total_row_html = (
            "<h4 style='margin:4px 0'>Total costs:</h4>"
            f"<table class='table table-sm'><tbody><tr><td></td><td></td><td><b>{total_cost_node:.3f} M€</b></td></tr></tbody></table>"
        )
        html += total_row_html



        folium.CircleMarker(
            [coords["lat"], coords["lon"]],
            radius=6, color="#023047", fill=True, fill_color="#023047",
            popup=folium.Popup(folium.IFrame(html, 400, 300), max_width=450),
            tooltip=node
        ).add_to(m)



    # Links with cost using full tech string for exact link cost
    for node, attrs in locations.items():
        src = attrs["coordinates"]
        for tgt, link in attrs.get("links", {}).items():
            for tech, props in link.get("techs", {}).items():
                cap = link_caps.get((node, tech+":"+tgt), 0)
                if not cap:
                    continue
                dest = locations[tgt]["coordinates"]
                cost = cost_dict_links.get((node, tech+":"+tgt), 0.0)
                weight = 1 + 25 * (cap / max_cap)
                color = "#ffb703" if tech == "interconnector_base" else "#8ecae6"
                popup = (
                    f"<b>Link:</b> {tech}<br>"
                    f"{node} ↔ {tgt}<br>"
                    f"{cap:.3f} GW<br>"
                    f"<b>Cost:</b> {cost:.3f} M€"
                )
                folium.PolyLine(
                    [(src["lat"], src["lon"]), (dest["lat"], dest["lon"])],
                    color=color, weight=weight, popup=popup, tooltip=tech
                ).add_to(m)



    return m

def build_plotly_traces_and_layout(df):
    import plotly.graph_objs as go

    df_sub = df.copy()
    df_sub["category_main"] = df_sub.tech.map(categorize_main)
    df_sub["category_mini"] = df_sub.tech.map(categorize_mini)
    df_sub = df_sub[df_sub.category_main != "Other"]

    nodes = sorted(df_sub.node.unique())
    mini_cats = list(TECH_CATEGORIES_MINI.keys())

    data_traces = []

    # 1. Installed capacities per technology per node (default All view)
    for tech, grp in df_sub.groupby("tech"):
        y = [grp[grp.node == n].capacity.sum() for n in nodes]
        if sum(y) == 0:
            continue  # Skip techs with zero total capacity
        cat = grp.category_main.iloc[0]
        color = tech_colors.get(tech, None)
        marker = {"color": color} if color else {}
        data_traces.append({
            "type": "bar",
            "name": tech,
            "legendgroup": cat,
            "legendgrouptitle": {"text": cat},  # Add group title for better legend grouping
            "x": nodes,
            "y": y,
            "marker": marker,
            "visible": True
        })

    # 2. Category dummy traces (main categories) for legend visuals
    main_cats = list(TECH_CATEGORIES_MAIN.keys()) + ["Other"]
    for cat in main_cats:
        data_traces.append({
            "type": "bar",
            "name": cat,
            "legendgroup": cat,
            "x": nodes,
            "y": [0] * len(nodes),
            "opacity": 0.4,
            "visible": True,
            "hoverinfo": "none"
        })

    # 3. Mini category traces (hidden initially), just for potential use (unchanged)
    tech_capacity_sums = df_sub.groupby('tech')['capacity'].sum()
    for cat in mini_cats:
        techs = TECH_CATEGORIES_MINI.get(cat, [])
        for tech in techs:
            cap = tech_capacity_sums.get(tech, 0.0)
            y_vals = [cap if c == cat else 0 for c in mini_cats]
            color = tech_colors.get(tech, None)
            trace = {
                "type": "bar",
                "name": tech,
                "legendgroup": cat,
                "x": mini_cats,
                "y": y_vals,
                "marker": {},
                "visible": False,
                "hoverinfo": "name+y",
                "hoverlabel": {"namelength": -1}
            }
            if color:
                trace["marker"]["color"] = color
            data_traces.append(trace)

    # 4. Total costs per node trace (hidden initially)
    total_costs_per_node = df.groupby("node")["monetary"].sum()
    total_cost_trace = {
        "type": "bar",
        "name": "Total costs [M€]",
        "x": nodes,
        "y": [total_costs_per_node.get(node, 0) for node in nodes],
        "marker": {"color": "crimson"},
        "visible": False
    }
    data_traces.append(total_cost_trace)

    # 5. Total installed capacities grouped by mini category (for "Total Installed Capacities" button)
    total_capacity_per_tech = df_sub.groupby("tech")["capacity"].sum()
    totals_start_idx = len(data_traces)
    for cat in mini_cats:
        cat_techs = [t for t in total_capacity_per_tech.index if t in TECH_CATEGORIES_MINI.get(cat, [])]
        for tech in cat_techs:
            y_val = total_capacity_per_tech.get(tech, 0)
            trace = {
                "type": "bar",
                "name": tech,
                "legendgroup": cat,
                "x": [cat],
                "y": [y_val],
                "marker": {"color": tech_colors.get(tech, "#777")},
                "visible": False,
                "hoverinfo": "name+y"
            }
            data_traces.append(trace)

    # 6. Total cost per technology grouped by mini category (for "Total cost per Technology" button)
    total_cost_per_tech = df.groupby("tech")["monetary"].sum()
    total_cost_tech_start_idx = len(data_traces)
    for cat in mini_cats:
        cat_techs = [t for t in total_cost_per_tech.index if t in TECH_CATEGORIES_MINI.get(cat, [])]
        for tech in cat_techs:
            cost_val = total_cost_per_tech.get(tech, 0)
            trace = {
                "type": "bar",
                "name": tech,
                "legendgroup": cat,
                "x": [cat],
                "y": [cost_val],
                "marker": {"color": tech_colors.get(tech, "#777")},
                "visible": False,
                "hoverinfo": "name+y"
            }
            data_traces.append(trace)

    # Determine counts of traces
    n_node_tech_traces = len([t for t in data_traces if t["visible"] and "x" in t and t["x"] == nodes])  # working count of initial visible tech traces
    n_node_cat_traces = len(main_cats)  # category dummy traces
    n_node_traces = n_node_tech_traces + n_node_cat_traces

    n_total_capacity_traces = len(data_traces) - totals_start_idx - (len(data_traces) - total_cost_tech_start_idx)
    n_total_cost_tech_traces = len(data_traces) - total_cost_tech_start_idx

    n_traces = len(data_traces)

    # Define visibility arrays
    buttons = []

    # Button: All installed capacities per node (default)
    all_vis = [True] * n_node_traces + [False] * (n_traces - n_node_traces)
    buttons.append({
        "method": "restyle",
        "label": "All",
        "args": [
            {"visible": all_vis},
            {"yaxis": {"title": "Capacity (GW)"},
             "xaxis": {"title": "", "type": "category", "categoryarray": nodes}}
        ]
    })

    # Buttons per main category (still available)
    unique_main_cats = sorted(set(df_sub.category_main))
    for cat in unique_main_cats:
        vis = []
        for i, t in enumerate(data_traces):
            if i < n_node_traces:
                vis.append(t.get("legendgroup") == cat)
            else:
                vis.append(False)
        buttons.append({
            "method": "restyle",
            "label": cat,
            "args": [
                {"visible": vis},
                {"yaxis": {"title": "Capacity (GW)"},
                 "xaxis": {"title": "", "type": "category", "categoryarray": nodes}}
            ]
        })

    # Button: Total Installed Capacities (stacked bars by mini category)
    totals_vis = [False] * totals_start_idx + [True] * n_total_capacity_traces + [False] * n_total_cost_tech_traces
    buttons.append({
        "method": "restyle",
        "label": "Total Installed Capacities",
        "args": [
            {"visible": totals_vis},
            {"yaxis": {"title": "Capacity (GW)"},
             "xaxis": {"title": "Technology Group", "type": "category", "categoryarray": mini_cats}}
        ]
    })

    # Button: Total costs per node
    total_cost_node_idx = totals_start_idx - 1
    total_cost_vis = [False] * n_traces
    total_cost_vis[total_cost_node_idx] = True
    buttons.append({
        "method": "restyle",
        "label": "Total costs per node",
        "args": [
            {"visible": total_cost_vis},
            {"yaxis": {"title": "Total Cost (M€)"},
             "xaxis": {"title": "", "type": "category", "categoryarray": nodes}}
        ]
    })

    # Button: Total cost per Technology (stacked bars by mini category)
    total_cost_tech_vis = (
        [False] * totals_start_idx +  # hide previous traces (installed capacity totals)
        [False] * n_total_capacity_traces +
        [True] * n_total_cost_tech_traces  # show only cost per tech traces
    )
    buttons.append({
        "method": "restyle",
        "label": "Total cost per Technology",
        "args": [
            {"visible": total_cost_tech_vis},
            {
                "yaxis.title.text": "Total Cost (M€)",
                "xaxis.title.text": "Technology Group",
                "xaxis.type": "category",
                "xaxis.categoryarray": mini_cats
            }
        ]
    })

    layout = {
        "barmode": "stack",
        "title": "",
        "xaxis": {"title": "", "tickangle": -45, "type": "category", "categoryarray": nodes},
        "yaxis": {"title": "Capacity (GW)"},
        "margin": {"l": 0, "r": 40, "t": 80, "b": 40},
        "legend": {"x": -0.06, "y": 1, "xanchor": "right", "yanchor": "top", "orientation": "v"},
        "updatemenus": [{
            "buttons": buttons,
            "direction": "down",
            "showactive": True,
            "x": 0.80,
            "y": 1.15,
            "xanchor": "left",
            "bgcolor": "white"
        }]
    }

    return data_traces, layout


def create_mini_bar_map(df, locations, geojson_path):
    m = folium.Map(location=[52.2,5.3], zoom_start=7, tiles="cartodbpositron")
    m.get_root().html.add_child(folium.Element("<style>.map { position: relative; }</style>"))
    nuts2 = json.load(open(geojson_path))
    folium.GeoJson(nuts2, style_function=lambda feat: {
        "fillColor":"#ffffff00","color":"#444444","weight":1
    }).add_to(m)



    df_sub = df.copy()
    df_sub["category"] = df_sub.tech.map(categorize_mini)
    df_sub = df_sub[df_sub.category.notna()]
    cat_caps = df_sub.groupby(['node','category'])['capacity'].sum().unstack(fill_value=0)
    categories = list(TECH_CATEGORIES_MINI.keys())
    BAR_WIDTH, BAR_HEIGHT = 60, 14



    def make_mini_bar(cat_values):
        total = cat_values.sum()
        scale = BAR_WIDTH/total if total>0 else 0
        colors = {
            'Nuclear':'#43aa8b','VRE':'#90be6d','Other_Renewable':'#f3722c','SMR':"#006105",
            'Gas':'#577590','Hydrogen':'#277da1','Electrolyser':'#f9c74f',
            'Heat':'#f94144','Storage':'#8338ec','Import':'#ffe5d9','Export':'#9d8189'
        }
        spans=[]
        for cat in categories:
            w = int(cat_values.get(cat,0)*scale)
            if w>0:
                spans.append(f"<span style='display:inline-block;width:{w}px;height:{BAR_HEIGHT}px;background:{colors[cat]};margin:0;'></span>")
        return f"<div style='width:{BAR_WIDTH}px;height:{BAR_HEIGHT}px;display:flex;align-items:center;background:transparent;border:1px solid #444;border-radius:2px;'>"+ "".join(spans)+"</div>"



    for node, attrs in locations.items():
        lat, lon = attrs["coordinates"]["lat"], attrs["coordinates"]["lon"]
        if node not in cat_caps.index: continue
        subset = df_sub[df_sub.node==node]
        html=""
        for cat in categories:
            dfc = subset[subset.category==cat]
            if dfc.empty: continue
            html += f"<h4 style='margin:4px 0'>{cat}</h4>"
            html += dfc[["tech","capacity"]].assign(
                capacity=lambda d: d.capacity.map("{:.3f} GW".format)
            ).to_html(index=False,header=False,classes="table table-sm")
        popup = folium.Popup(folium.IFrame(html,400,300),max_width=450)
        folium.CircleMarker([lat,lon],radius=6,color="#023047",
                            fill=True,fill_color="#023047",popup=popup,tooltip=node).add_to(m)
        bar_html = make_mini_bar(cat_caps.loc[node])
        tooltip = ", ".join(f"{cat} {cat_caps.loc[node].get(cat,0):.2f} GW"
                            for cat in categories if cat_caps.loc[node].get(cat,0)>0)
        folium.map.Marker(
            [lat,lon],
            icon=DivIcon(icon_size=(BAR_WIDTH,BAR_HEIGHT),
                         icon_anchor=(10,-BAR_HEIGHT//2),
                         html=bar_html),
            tooltip=tooltip
        ).add_to(m)



    legend_html = """
    {% macro html(this, kwargs) %}
    <div style="
        position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%);
        background: white; padding:4px 8px; border:1px solid #444;
        font-size:10px; display:flex; flex-wrap:wrap; gap:6px; z-index:1000;">
        """ + "".join([
        f"<div style='display:flex;align-items:center;'><span style='background:{color};width:10px;height:10px;display:inline-block;margin-right:4px;'></span>{cat}</div>"
        for cat, color in [
            ("Nuclear","#70e000"),("VRE","#90be6d"),("Other Renewable","#f3722c"),
            ("Gas","#577590"),("Hydrogen","#277da1"),("Electrolyser","#f9c74f"),
            ("Heat","#f94144"),("Storage","#8338ec"),("Import","#ffe5d9"),("Export","#9d8189")
        ]
    ]) + """
    </div>
    {% endmacro %}
    """
    macro = MacroElement()
    macro._template = BrancaTemplate(legend_html)
    m.get_root().add_child(macro)



    return m

def add_smr_icons(m, df, locations):
    # Define all SMR tech IDs you want icons for
    smr_techs = {
        "pp_nuclear_smr": {"icon": "radiation", "color": "#70e000", "offset": (0.015, 0.015)},
        "pp_SMR_Hitachi_CHP_1": {"icon": "radiation", "color": "#B1A623", "offset": (0.015, 0.015)},
        "pp_SMR_RollsRoyce_CHP_1": {"icon": "radiation", "color": "#C3A433", "offset": (0.015, -0.015)},
        "pp_SMR_Thorizon_CHP_1": {"icon": "radiation", "color": "#B5A637", "offset": (-0.015, 0.015)},
        "pp_SMR_RollsRoyce_CH2P_1": {"icon": "industry",  "color": "#5BF8B4", "offset": (-0.015, -0.015)},
        "pp_SMR_Thorizon_CH2P_1": {"icon": "industry",    "color": "#22FFA3", "offset": (0.015, -0.03)},
        "pp_SMR_Hitachi_CH2P_1": {"icon": "industry",     "color": "#1ADB8E", "offset": (-0.03, 0.015)},
        "pp_SMR_RollsRoyce_CHH2P_1": {"icon": "industry",  "color": "#53BE3D", "offset": (-0.015, -0.015)},
        "pp_SMR_Thorizon_CHH2P_1": {"icon": "industry",    "color": "#3CBE2B", "offset": (0.015, -0.03)},
        "pp_SMR_Hitachi_CHH2P_1": {"icon": "industry",     "color": "#5FE868", "offset": (-0.03, 0.015)},
        "pp_SMR_Hitachi_CHP_2": {"icon": "radiation", "color": "#B1A623", "offset": (0.015, 0.015)},
        "pp_SMR_RollsRoyce_CHP_2": {"icon": "radiation", "color": "#C3A433", "offset": (0.015, -0.015)},
        "pp_SMR_Thorizon_CHP_2": {"icon": "radiation", "color": "#B5A637", "offset": (-0.015, 0.015)},
        "pp_SMR_RollsRoyce_CH2P_2": {"icon": "industry",  "color": "#5BF8B4", "offset": (-0.015, -0.015)},
        "pp_SMR_Thorizon_CH2P_2": {"icon": "industry",    "color": "#22FFA3", "offset": (0.015, -0.03)},
        "pp_SMR_Hitachi_CH2P_2": {"icon": "industry",     "color": "#1ADB8E", "offset": (-0.03, 0.015)},
        "pp_SMR_RollsRoyce_CHH2P_2": {"icon": "industry",  "color": "#53BE3D", "offset": (-0.015, -0.015)},
        "pp_SMR_Thorizon_CHH2P_2": {"icon": "industry",    "color": "#3CBE2B", "offset": (0.015, -0.03)},
        "pp_SMR_Hitachi_CHH2P_2": {"icon": "industry",     "color": "#5FE868", "offset": (-0.03, 0.015)},
        "pp_SMR_Hitachi_CHP_3": {"icon": "radiation", "color": "#B1A623", "offset": (0.015, 0.015)},
        "pp_SMR_RollsRoyce_CHP_3": {"icon": "radiation", "color": "#C3A433", "offset": (0.015, -0.015)},
        "pp_SMR_Thorizon_CHP_3": {"icon": "radiation", "color": "#B5A637", "offset": (-0.015, 0.015)},
        "pp_SMR_RollsRoyce_CH2P_3": {"icon": "industry",  "color": "#5BF8B4", "offset": (-0.015, -0.015)},
        "pp_SMR_Thorizon_CH2P_3": {"icon": "industry",    "color": "#22FFA3", "offset": (0.015, -0.03)},
        "pp_SMR_Hitachi_CH2P_3": {"icon": "industry",     "color": "#1ADB8E", "offset": (-0.03, 0.015)},
        "pp_SMR_RollsRoyce_CHH2P_3": {"icon": "industry",  "color": "#53BE3D", "offset": (-0.015, -0.015)},
        "pp_SMR_Thorizon_CHH2P_3": {"icon": "industry",    "color": "#3CBE2B", "offset": (0.015, -0.03)},
        "pp_SMR_Hitachi_CHH2P_3": {"icon": "industry",     "color": "#5FE868", "offset": (-0.03, 0.015)},
        "pp_SMR_CHP_generic":{"icon": "industry",     "color": "#5FE868", "offset": (-0.03, 0.015)},
        "pp_SMR_CHH2P_generic":{"icon": "industry",     "color": "#5FE868", "offset": (-0.03, 0.015)},

    }

    # Loop through each tech type
    for tech, props in smr_techs.items():
        # Find nodes where this tech is installed (capacity > 0)
        installed = df.loc[(df.tech == tech) & (df.capacity > 0), "node"].unique()
        for node in installed:
            coords = locations[node]["coordinates"]
            lat_off, lon_off = props["offset"]
            folium.Marker(
                [coords["lat"] + lat_off, coords["lon"] + lon_off],
                icon=BeautifyIcon(
                    icon=props["icon"],
                    icon_shape="marker",
                    border_color=props["color"],
                    text_color=props["color"],
                    background_color="transparent",
                ),
                tooltip=f"{node}: {tech} installed"
            ).add_to(m)

    return m

def run_IC(
    netcdf_path: str,
    model_yaml_path: str,
    output_html_path: str,
    html_title: str = "Energy System Overview"
):
    # Prefer legacy DelftBlue location, but fall back to local Postprocessing folder.
    geojson_path = Path.cwd() / "Research_Runs" / "Postprocessing" / "NUTS2.geojson"
    if not geojson_path.exists():
        geojson_path = Path.cwd() / "Postprocessing" / "NUTS2.geojson"
    #output_html_path = Path.cwd() / "analysis_results" / "Installed_Capacities.html"

    # Load and process data
    df_cap, locations = load_and_process_data(netcdf_path, model_yaml_path)
    df_cost = load_costs(netcdf_path)
    # merge on node and base tech to get costs for node popups
    df = pd.merge(df_cap, df_cost[["node", "tech", "monetary"]], how="left", on=["node", "tech"]).fillna({"monetary": 0.0})
    # keep cost_dict with tech_full for link cost lookup later
    cost_df_full = df_cost
    detailed_costs = cost_totals(netcdf_path)
 
    # -- Added: Calculate total supply installed power --
    supply_techs = [
        "pp_ccgt_hyd", "pp_ocgt_hyd",
        "pp_ccgt_gas", "pp_ocgt_gas",
        "pp_nuclear_conventional", "pp_nuclear_smr", "pp_SMR_CHP_generic", "pp_SMR_CHH2P_generic",
        "pp_SMR_Hitachi_CHP_1", "pp_SMR_RollsRoyce_CHP_1", "pp_SMR_Thorizon_CHP_1", 
        "pp_SMR_Hitachi_CH2P_1", "pp_SMR_RollsRoyce_CH2P_1", "pp_SMR_Thorizon_CH2P_1",
        "pp_SMR_Hitachi_CHH2P_1", "pp_SMR_RollsRoyce_CHH2P_1", "pp_SMR_Thorizon_CHH2P_1",
        "pp_SMR_Hitachi_CHP_2", "pp_SMR_RollsRoyce_CHP_2", "pp_SMR_Thorizon_CHP_2", 
        "pp_SMR_Hitachi_CH2P_2", "pp_SMR_RollsRoyce_CH2P_2", "pp_SMR_Thorizon_CH2P_2",
        "pp_SMR_Hitachi_CHH2P_2", "pp_SMR_RollsRoyce_CHH2P_2", "pp_SMR_Thorizon_CHH2P_2",
        "pp_SMR_Hitachi_CHP_3", "pp_SMR_RollsRoyce_CHP_3", "pp_SMR_Thorizon_CHP_3", 
        "pp_SMR_Hitachi_CH2P_3", "pp_SMR_RollsRoyce_CH2P_3", "pp_SMR_Thorizon_CH2P_3",
        "pp_SMR_Hitachi_CHH2P_3", "pp_SMR_RollsRoyce_CHH2P_3", "pp_SMR_Thorizon_CHH2P_3",
        "pp_biomass_standalone", "pp_waste_incinerator",
        "wind_offshore", "wind_onshore", "pv_rooftop", "pv_utility",
        "hydro_RoR", "curtailment_elc",
        "pth_electric_boiler",
        "pp_elektrolyser_onshore", "pp_elektrolyser_offshore",
        "reformer_smr_ccs", "reformer_atr_ccs_96"
    ]
    total_supply_installed = df[df.tech.isin(supply_techs)]["capacity"].sum()

    # -- Added: Calculate total transmission installed capacity --
    # Build a single regex for the exclude prefixes
    exclude_pattern = r'^(?:' + '|'.join(exclude_prefixes) + r')'

    # Mask for techs we want to include
    include_mask = df['tech'].str.contains(r'transmission|interconnector')

    # Mask for those we want to exclude
    exclude_mask = df['tech'].str.contains(exclude_pattern)

    # Final mask
    mask = include_mask & ~exclude_mask

    # Compute total installed transmission capacity
    pre_compute = df.loc[mask, 'capacity'].sum()
    total_transmission_installed = pre_compute/2
    storage_techs = TECH_CATEGORIES_MAIN.get("Storage",[])
    total_storage_installed = df[df.tech.isin(storage_techs)]["capacity"].sum()

    # Create maps
    map_a = create_main_map(df, locations, geojson_path, cost_df_full)
    map_b = create_mini_bar_map(df, locations, geojson_path)
    map_b = add_smr_icons(map_b, df, locations)

    map_a_html = map_a.get_root().render()
    map_b_html = map_b.get_root().render()

    # Build Plotly chart
    data_traces, layout = build_plotly_traces_and_layout(df)
    layout["title"] = html_title
    chart_json = json.dumps(data_traces)
    layout_json = json.dumps(layout)

    # Render HTML
    page_template = Template("""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"/>
    <title>{{ title }}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { margin:0; padding:20px; font-family:Arial }
        .maps { display:flex; gap:10px; height:55vh; }
        .map { flex:1; position: relative; }
        #chart { height:35vh; }
        .cost-summary {
            position: absolute; bottom: 10px; left: 10px;
            background: rgba(255,255,255,0.9); padding:10px;
            border:1px solid #444; font-size:11px;
            border-radius:4px; box-shadow:1px 1px 5px rgba(0,0,0,0.2);
            display: flex; gap: 20px; z-index:1001; user-select:none;
        }
        .cost-summary table { border-collapse: collapse; }
        .cost-summary th, .cost-summary td {
        border: 1px solid #ccc; padding: 4px 6px; text-align: right;
        }
        .cost-summary th:first-child,
        .cost-summary td:first-child {
        text-align: left;
        }
        .cost-summary .cap-table th,
        .cost-summary .cap-table td {
        border: none; padding: 2px 6px;
        }
        .cost-summary .cap-table td:first-child {
        text-align: left;
        font-weight: bold;
        }
    </style>
    </head><body>
    <h1 style="text-align:center">{{ title }}</h1>
    <div class="maps" style="position:relative;">
        <div class="map">{{ map_a|safe }}</div>
        <div class="map">{{ map_b|safe }}</div>
        <div class="cost-summary">
        <table>
            <thead>
            <tr>
                <th></th>
                <th>Var. cost [M€]</th>
                <th>Fixed cost [M€]</th>
            </tr>
            </thead>
            <tbody>
            <tr>
                <td>Total cost plants</td>
                <td>{{ total_tech_cost_var|round(3) }}</td>
                <td>{{ total_tech_cost_fixed|round(3) }}</td>
            </tr>
            <tr>
                <td>Total cost Transmission</td>
                <td>{{ total_infra_cost_var|round(3) }}</td>
                <td>{{ total_infra_cost_fixed|round(3) }}</td>
            </tr>
            <tr>
                <td>Total cost Storage</td>
                <td>{{ total_storage_cost_var|round(3) }}</td>
                <td>{{ total_storage_cost_fixed|round(3) }}</td>
            </tr>
            <tr>
                <td>Total Cost Breakdown</td>
                <td>{{ total_var_cost|round(3) }}</td>
                <td>{{ total_fixed_cost|round(3) }}</td>     
            </tr>
            <tr>       
                <td>Total System Cost</td>                        
                <td colspan="2">{{ total_system_cost|round(3) }}</td>
            </tr>
            </tbody>
        <table class="cap-table">
            <thead>
            <tr><th colspan="2">Installed capacity [GW]</th></tr>
            </thead>
            <tbody>
            <tr><td>Plants:</td>        <td>{{ total_supply_installed|round(3) }}</td></tr>
            <tr><td>Transmission:</td>  <td>{{ total_transmission_installed|round(3) }}</td></tr>
            <tr><td>Storage:</td>       <td>{{ total_storage_installed|round(3) }}</td></tr>
            </tbody>
        </table>
        </div>
    </div>
    <div id="chart"></div>
    <script>
        Plotly.newPlot('chart', {{ chart_json|safe }}, {{ layout_json|safe }}, {displayModeBar:false});
    </script>
    </body></html>
    """)


    rendered = page_template.render(
        title=html_title,
        map_a=map_a_html,
        map_b=map_b_html,
        chart_json=chart_json,
        layout_json=layout_json,
        total_tech_cost_fixed    = detailed_costs["total_tech_cost_fixed"],
        total_tech_cost_var      = detailed_costs["total_tech_cost_var"],
        total_infra_cost_fixed   = detailed_costs["total_infra_cost_fixed"],
        total_infra_cost_var     = detailed_costs["total_infra_cost_var"],
        total_storage_cost_fixed = detailed_costs["total_storage_cost_fixed"],
        total_storage_cost_var   = detailed_costs["total_storage_cost_var"],
        total_var_cost           = detailed_costs["total_var_cost"],
        total_fixed_cost         = detailed_costs["total_fixed_cost"],
        total_system_cost        = detailed_costs["total_system_cost"],
        total_supply_installed=total_supply_installed,
        total_transmission_installed=total_transmission_installed,
        total_storage_installed=total_storage_installed
    )

    # Ensure output directory exists
    output_html_path = Path(output_html_path)
    output_html_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"Combined page saved to {output_html_path}")
