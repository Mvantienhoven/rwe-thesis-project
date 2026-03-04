import xarray as xr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path

# -------- UTILITY FUNCTIONS -------- #
def extract_tidy(ds, var_name, index_dim, value_label):
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
    if "cost_om_con" not in ds:
        return None
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

def postprocess(nc_file, output_csv):
    ds = xr.open_dataset(nc_file)
    time_coords = ds.coords["timesteps"].values
    if len(time_coords) > 1:
        timestep_hours = (time_coords[1] - time_coords[0]) / np.timedelta64(1, 'h')
    else:
        timestep_hours = 1.0

    prod  = extract_tidy(ds, "carrier_prod", "loc_tech_carriers_prod", "production")
    con   = extract_tidy(ds, "carrier_con",  "loc_tech_carriers_con", "consumption")
    store = extract_tidy(ds, "storage",      "loc_techs_store",       "storage_level")
    req   = extract_tidy(ds, "required_resource", "loc_techs_balance_demand_constraint", "required_resource")
    try:
        unmet = extract_tidy(ds, "unmet_demand", "loc_carriers", "unmet_demand")
    except KeyError:
        print("Warning: 'unmet_demand' not found. Creating zero-filled placeholder.")
        unique_combos = prod[["time", "location", "carrier"]].drop_duplicates()
        unmet = unique_combos.copy()
        unmet["unmet_demand"] = 0.0


    base_cost_index = (
        pd.concat(
            [
                prod[["time", "location", "technology"]],
                con[["time", "location", "technology"]],
            ],
            ignore_index=True,
        )
        .drop_duplicates()
        .reset_index(drop=True)
    )

    if "cost_var" in ds:
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
    else:
        print("Warning: 'cost_var' not found. Using zero-filled variable_cost.")
        varc = base_cost_index.copy()
        varc["var_cost_category"] = "monetary"
        varc["variable_cost"] = 0.0

    omc = extract_cost_om(ds)
    if omc is None:
        print("Warning: 'cost_om_con' not found. Using zero-filled operational_cost.")
        omc = base_cost_index.copy()
        omc["operational_cost"] = 0.0

    df_cap = ds["energy_cap"].to_series().reset_index()
    df_cap.columns = ["item", "capacity"]
    df_cap[["location", "technology"]] = df_cap["item"].str.split("::", expand=True)
    capacity = df_cap[["location", "technology", "capacity"]]

    if "loc_coordinates" in ds:
        coord_array = ds["loc_coordinates"].values
        coords_idx  = ds.coords["coordinates"].values.tolist()
        locs        = ds.coords["locs"].values.tolist()
        df_coords   = pd.DataFrame(coord_array.T, columns=coords_idx)
        df_coords["location"] = locs
        coords = df_coords[["location", "lon", "lat"]]
    else:
        print("Warning: 'loc_coordinates' not found. Using NaN coordinates.")
        locs = ds.coords["locs"].values.tolist() if "locs" in ds.coords else []
        coords = pd.DataFrame({"location": locs, "lon": np.nan, "lat": np.nan})
    ds.close()

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

    net["prod_utilization"] = (net["production"] / timestep_hours) / net["capacity"]
    net["con_utilization"]  = (net["consumption"].abs()  / timestep_hours) / net["capacity"]
    for col in [
        "storage_level", "variable_cost", "operational_cost",
        "required_resource", "unmet_demand", "capacity",
        "prod_utilization", "con_utilization"
    ]:
        if col in net:
            net[col] = net[col].fillna(0)
    net.to_csv(output_csv, index=False)
    return net

# --------- PLOT 1: Carrier Flows --------- #
def plot_carrier_flows(df):
    TECH_LABELS = {
        "curtailment_elc": "Curtailment",
        "demand_elc": "Demand",
        "ES_BESS_households": "BESS Households",
        "ES_BESS_IDES": "BESS IDES",
        "ES_BESS_MDES": "BESS MDES",
        "ES_pumped_hydro": "Pumped Hydro",
        "pp_biomass_standalone": "Biomass",
        "pp_ccgt_gas": "CCGT Gas",
        "pp_ccgt_hyd": "CCGT Hydrogen",
        "pp_ocgt_gas": "OCGT Gas",
        "pp_ocgt_hyd": "OCGT Hydrogen",
        "pp_elektrolyser_onshore": "Elektrolyser - Onshore",
        "pp_elektrolyser_offshore": "Elektrolyser - Offshore",
        "pp_nuclear_conventional": "Nuclear Conventional",
        "pp_nuclear_smr": "Nuclear SMR",
        "pp_SMR_CHP_generic": "Nuclear CHP SMR",
        "pp_SMR_CHH2P_generic": "Nuclear CHH2P SMR",
        "pp_SMR_RollsRoyce_CHP_1": "CHP RollsRoyce SMR unit 1",
        "pp_SMR_RollsRoyce_CHP_2": "CHP RollsRoyce SMR unit 2",
        "pp_SMR_RollsRoyce_CHP_3": "CHP RollsRoyce SMR unit 3",
        "pp_SMR_Thorizon_CHP_1": "CHP Thorizon SMR unit 1",
        "pp_SMR_Thorizon_CHP_2": "CHP Thorizon SMR unit 2",
        "pp_SMR_Thorizon_CHP_3": "CHP Thorizon SMR unit 3",
        "pp_SMR_Hitachi_CHP_1": "CHP Hitachi SMR unit 1",
        "pp_SMR_Hitachi_CHP_2": "CHP Hitachi SMR unit 2",
        "pp_SMR_Hitachi_CHP_3": "CHP Hitachi SMR unit 3",
        "pp_SMR_RollsRoyce_CH2P_1": "CH2P RollsRoyce SMR unit 1",
        "pp_SMR_RollsRoyce_CH2P_2": "CH2P RollsRoyce SMR unit 2",
        "pp_SMR_RollsRoyce_CH2P_3": "CH2P RollsRoyce SMR unit 3",
        "pp_SMR_Thorizon_CH2P_1": "CH2P Thorizon SMR unit 1",
        "pp_SMR_Thorizon_CH2P_2": "CH2P Thorizon SMR unit 2",
        "pp_SMR_Thorizon_CH2P_3": "CH2P Thorizon SMR unit 3",
        "pp_SMR_Hitachi_CH2P_1": "CH2P Hitachi SMR unit 1",
        "pp_SMR_Hitachi_CH2P_2": "CH2P Hitachi SMR unit 2",
        "pp_SMR_Hitachi_CH2P_3": "CH2P Hitachi SMR unit 3",
        "pp_SMR_RollsRoyce_CHH2P_1": "CHH2P RollsRoyce SMR unit 1",
        "pp_SMR_Thorizon_CHH2P_1": "CHH2P Thorizon SMR unit 1",
        "pp_SMR_Hitachi_CHH2P_1": "CHH2P Hitachi SMR unit 1",
        "pp_SMR_RollsRoyce_CHH2P_2": "CHH2P RollsRoyce SMR unit 2",
        "pp_SMR_Thorizon_CHH2P_2": "CHH2P Thorizon SMR unit 2",
        "pp_SMR_Hitachi_CHH2P_2": "CHH2P Hitachi SMR unit 2",
        "pp_SMR_RollsRoyce_CHH2P_3": "CHH2P RollsRoyce SMR unit 3",
        "pp_SMR_Thorizon_CHH2P_3": "CHH2P Thorizon SMR unit 3",
        "pp_SMR_Hitachi_CHH2P_3": "CHH2P Hitachi SMR unit 3",
        "pp_waste_incinerator": "Waste Incinerator",
        "pth_electric_boiler": "Electric Boiler",
        "pv_rooftop": "PV Rooftop",
        "pv_utility": "PV Utility",
        "wind_offshore": "Wind Offshore",
        "wind_onshore": "Wind Onshore"
    }
    TECH_COLORS = {
        "Curtailment": "#000000",
        "Demand": "#444444",
        "Biomass": "#76c893",
        "CCGT Gas": "#34a0a4",
        "CCGT Hydrogen": "#168aad",
        "Electric Boiler": "#ffb4a2",
        "Hydro RoR": "#1a759f",
        "Nuclear Conventional": "#006d77",
        "Nuclear SMR": "#83c5be",
        "Nuclear CHP SMR": "#83c5be",
        "Nuclear CHH2P SMR":"#83c5be",
        "CHP RollsRoyce SMR unit 1": "#2d9e40",
        "CHP Thorizon SMR unit 1": "#2ca83d",
        "CHP Hitachi SMR unit 1": "#a0d468",
        "CH2P RollsRoyce SMR unit 1": "#ddaf30",
        "CH2P Thorizon SMR unit 1": "#ca9a21",
        "CH2P Hitachi SMR unit 1": "#f8b712",
        "CHH2P RollsRoyce SMR unit 1": "#30dda6",
        "CHH2P Thorizon SMR unit 1": "#21ca86",
        "CHH2P Hitachi SMR unit 1": "#12f891",
        "CHP RollsRoyce SMR unit 2": "#2d9e40",
        "CHP Thorizon SMR unit 2": "#2ca83d",
        "CHP Hitachi SMR unit 2": "#a0d468",
        "CH2P RollsRoyce SMR unit 2": "#ddaf30",
        "CH2P Thorizon SMR unit 2": "#ca9a21",
        "CH2P Hitachi SMR unit 2": "#f8b712",
        "CHH2P RollsRoyce SMR unit 2": "#30dda6",
        "CHH2P Thorizon SMR unit 2": "#21ca86",
        "CHH2P Hitachi SMR unit 2": "#12f891",
        "CHP RollsRoyce SMR unit 3": "#2d9e40",
        "CHP Thorizon SMR unit 3": "#2ca83d",
        "CHP Hitachi SMR unit 3": "#a0d468",
        "CH2P RollsRoyce SMR unit 3": "#ddaf30",
        "CH2P Thorizon SMR unit 3": "#ca9a21",
        "CH2P Hitachi SMR unit 3": "#f8b712",
        "CHH2P RollsRoyce SMR unit 3": "#30dda6",
        "CHH2P Thorizon SMR unit 3": "#21ca86",
        "CHH2P Hitachi SMR unit 3": "#12f891",
        "OCGT Gas": "#34a0a4",
        "OCGT Hydrogen": "#168aad",
        "Pumped Hydro": "#c19ee0",
        "PV Rooftop": "#ffd000",
        "PV Utility": "#ffc300",
        "Waste Incinerator": "#76c893",
        "Wind Offshore": "#b5e48c",
        "Wind Onshore": "#d9ed92",
        "BESS Households": "#d2b7e5",
        "BESS IDES": "#d2b7e5",
        "BESS MDES": "#c19ee0",
        "Elektrolyser - Onshore": "#02cecb",
        "Elektrolyser - Offshore": "#02cecb"
    }
    DEFAULT_COLOR = "lightgrey"
    STACK_ORDER = [
        "Nuclear Conventional", "Nuclear SMR", "Nuclear CHP SMR","Nuclear CHH2P SMR",
        "CHP RollsRoyce SMR unit 1","CHP Thorizon SMR unit 1", "CHP Hitachi SMR unit 1",
        "CH2P RollsRoyce SMR unit 1","CH2P Thorizon SMR unit 1", "CH2P Hitachi SMR unit 1",
        "CHH2P RollsRoyce SMR unit 1","CHH2P Thorizon SMR unit 1", "CHH2P Hitachi SMR unit 1", 
        "CHP RollsRoyce SMR unit 2","CHP Thorizon SMR unit 2", "CHP Hitachi SMR unit 2",
        "CH2P RollsRoyce SMR unit 2","CH2P Thorizon SMR unit 2", "CH2P Hitachi SMR unit 2",
        "CHH2P RollsRoyce SMR unit 2","CHH2P Thorizon SMR unit 2", "CHH2P Hitachi SMR unit 2", 
        "CHP RollsRoyce SMR unit 3","CHP Thorizon SMR unit 3", "CHP Hitachi SMR unit 3",
        "CH2P RollsRoyce SMR unit 3","CH2P Thorizon SMR unit 3", "CH2P Hitachi SMR unit 3",
        "CHH2P RollsRoyce SMR unit 3","CHH2P Thorizon SMR unit 3", "CHH2P Hitachi SMR unit 3", 
        "CCGT Gas", "CCGT Hydrogen",
        "Biomass", "Waste Incinerator", "Hydro RoR", "OCGT Gas", "OCGT Hydrogen",
        "Wind Offshore", "Wind Onshore", "PV Utility", "PV Rooftop",
        "Pumped Hydro", "BESS IDES", "BESS MDES", "BESS Households",
        "Elektrolyser - Onshore", "Elektrolyser - Offshore",
        "Electric Boiler", "Curtailment"
    ]
    OMIT_CARRIERS = {"ets_budget", "ets_penalty", "solid_fuel","sink"}
    OMIT_TECH_PREFIXES = [
        "free_co2_transmission", "free_co2_stored_transmission",
        "transmission_hvac", "free_gas_transmission",
        "free_hyd_transmission", "free_sink_transmission",
        "interconnector_", "co2_emissions_sink", "co2_storage",
    ]
    def should_drop_tech(tech: str) -> bool:
        return any(tech.startswith(p) for p in OMIT_TECH_PREFIXES)

    DEMAND_MAP = {
        "co2_emitted": ("co2_emissions_sink", "CO2 Emitted"),
        "co2_stored":  ("co2_storage",        "CO2 Stored"),
        "electricity": ("demand_elc",         "Demand"),
        "gas":         ("demand_gas",         "Demand"),
        "heat":        ("demand_pth",         "Demand"),
        "hydrogen":    ("demand_hyd",         "Demand")
    }

    df = df[~df["carrier"].isin(OMIT_CARRIERS)]
    df = df[~df["technology"].apply(should_drop_tech)]

    demand_codes = {code for code,_ in DEMAND_MAP.values()}
    df_d = df[df["technology"].isin(demand_codes)]
    df_f = df[~df["technology"].isin(demand_codes)]
    df_f["tech_label"] = df_f["technology"].map(TECH_LABELS).fillna(df_f["technology"])

    agg_f = df_f.groupby(["carrier","time","tech_label"])["net_flow"].sum().reset_index()
    agg_d = df_d.groupby(["carrier","time","technology"])["net_flow"].sum().reset_index()
    agg_u = df.groupby(["carrier","time"])["unmet_demand"].sum().reset_index()

    carriers = sorted(agg_f["carrier"].unique())
    fig = go.Figure()
    for carrier in carriers:
        vis = (carrier == "electricity")
        sub_f = agg_f[agg_f["carrier"] == carrier]
        for tech in STACK_ORDER:
            d = sub_f[sub_f["tech_label"] == tech]
            if d.empty: continue
            fig.add_trace(go.Bar(
                x=d["time"], y=d["net_flow"], name=tech,
                legendgroup=tech,
                marker_color=TECH_COLORS.get(tech, DEFAULT_COLOR),
                visible=vis,
                customdata=[carrier]*len(d),
            ))
        extras = [t for t in sub_f["tech_label"].unique() if t not in STACK_ORDER]
        for tech in extras:
            d = sub_f[sub_f["tech_label"] == tech]
            fig.add_trace(go.Bar(
                x=d["time"], y=d["net_flow"], name=tech,
                legendgroup=tech,
                marker_color=TECH_COLORS.get(tech, DEFAULT_COLOR),
                visible=vis,
                customdata=[carrier]*len(d),
            ))
        code, lbl = DEMAND_MAP.get(carrier, (None,None))
        if code:
            d = agg_d[(agg_d["carrier"]==carrier)&(agg_d["technology"]==code)]
            fig.add_trace(go.Scatter(
                x=d["time"], y=-d["net_flow"], mode="lines",
                line=dict(dash="dash", color="black", width=2),
                name=lbl, legendgroup="Demand",
                visible=vis,
                customdata=[carrier]*len(d),
            ))
        u = agg_u[agg_u["carrier"] == carrier]
        fig.add_trace(go.Scatter(
            x=u["time"], y=-u["unmet_demand"], mode="lines",
            line=dict(dash="dot", color="red", width=2),
            name="Unmet Demand", legendgroup="Unmet",
            visible=vis,
            customdata=[carrier]*len(u),
        ))
    # Dropdown
    buttons = []
    for carrier in carriers:
        vis = [bool(getattr(tr, "customdata", None) and tr.customdata[0] == carrier)
              for tr in fig.data]
        buttons.append(dict(
            method="update", label=carrier.capitalize(),
            args=[{"visible": vis},
                  {"title": f"{carrier.capitalize()} Net Flows by Technology"}]
        ))
    fig.update_layout(
        updatemenus=[dict(active=carriers.index("electricity"),
                          buttons=buttons, x=0, y=1.15,
                          xanchor="left", yanchor="top")],
        barmode="relative",
        title="Electricity Net Flows by Technology",
        xaxis=dict(title="Time", tickformat="%Y-%m-%d\n%H:%M"),
        yaxis=dict(title="Flow (GW)"),
        legend_title="Technology",
        height=600, margin=dict(t=100, l=60, r=20, b=40)
    )
    return fig

# --------- PLOT 2: Variable Costs --------- #
def plot_variable_costs(df):
    TRANSMISSION_PREFIXES = [
        "transmission_hvac", "free_co2_transmission", "free_co2_stored_transmission",
        "free_gas_transmission", "free_hyd_transmission",
        "free_sink_transmission", "interconnector_"
    ]
    TECH_LABELS = {
        "curtailment_elc": "Curtailment",
        "demand_elc": "Demand",
        "ES_BESS_households": "BESS Households",
        "ES_BESS_IDES": "BESS IDES",
        "ES_BESS_MDES": "BESS MDES",
        "ES_pumped_hydro": "Pumped Hydro",
        "pp_biomass_standalone": "Biomass",
        "pp_ccgt_gas": "CCGT Gas",
        "pp_ccgt_hyd": "CCGT Hydrogen",
        "pp_ocgt_gas": "OCGT Gas",
        "pp_ocgt_hyd": "OCGT Hydrogen",
        "pp_elektrolyser_onshore": "Elektrolyser - Onshore",
        "pp_elektrolyser_offshore": "Elektrolyser - Offshore",
        "pp_nuclear_conventional": "Nuclear Conventional",
        "pp_nuclear_smr": "Nuclear SMR",
        "pp_SMR_CHP_generic": "Nuclear CHP SMR",
        "pp_SMR_CHH2P_generic": "Nuclear CHH2P SMR",        
        "pp_SMR_Hitachi_CHP_1": "SMR Hitachi CHP unit 1",
        "pp_SMR_RollsRoyce_CHP_1": "SMR RollsRoyce CHP unit 1",
        "pp_SMR_Thorizon_CHP_1": "SMR Thorizon CHP unit 1",
        "pp_SMR_RollsRoyce_CH2P_1": "SMR RollsRoyce CH2P unit 1",
        "pp_SMR_Thorizon_CH2P_1": "SMR Thorizon CH2P unit 1",
        "pp_SMR_Hitachi_CH2P_1": "SMR Hitachi CH2P unit 1",
        "pp_SMR_RollsRoyce_CHH2P_1": "SMR RollsRoyce CHH2P unit 1",
        "pp_SMR_Thorizon_CHH2P_1": "SMR Thorizon CHH2P unit 1",
        "pp_SMR_Hitachi_CHH2P_1": "SMR Hitachi CHH2P unit 1",
        "pp_SMR_Hitachi_CHP_2": "SMR Hitachi CHP unit 2",
        "pp_SMR_RollsRoyce_CHP_2": "SMR RollsRoyce CHP unit 2",
        "pp_SMR_Thorizon_CHP_2": "SMR Thorizon CHP unit 2",
        "pp_SMR_RollsRoyce_CH2P_2": "SMR RollsRoyce CH2P unit 2",
        "pp_SMR_Thorizon_CH2P_2": "SMR Thorizon CH2P unit 2",
        "pp_SMR_Hitachi_CH2P_2": "SMR Hitachi CH2P unit 2",
        "pp_SMR_RollsRoyce_CHH2P_2": "SMR RollsRoyce CHH2P unit 2",
        "pp_SMR_Thorizon_CHH2P_2": "SMR Thorizon CHH2P unit 2",
        "pp_SMR_Hitachi_CHH2P_2": "SMR Hitachi CHH2P unit 2",
        "pp_SMR_Hitachi_CHP_3": "SMR Hitachi CHP unit 3",
        "pp_SMR_RollsRoyce_CHP_3": "SMR RollsRoyce CHP unit 3",
        "pp_SMR_Thorizon_CHP_3": "SMR Thorizon CHP unit 3",
        "pp_SMR_RollsRoyce_CH2P_3": "SMR RollsRoyce CH2P unit 3",
        "pp_SMR_Thorizon_CH2P_3": "SMR Thorizon CH2P unit 3",
        "pp_SMR_Hitachi_CH2P_3": "SMR Hitachi CH2P unit 3",
        "pp_SMR_RollsRoyce_CHH2P_3": "SMR RollsRoyce CHH2P unit 3",
        "pp_SMR_Thorizon_CHH2P_3": "SMR Thorizon CHH2P unit 3",
        "pp_SMR_Hitachi_CHH2P_3": "SMR Hitachi CHH2P unit 3",
        "pp_waste_incinerator": "Waste Incinerator",
        "pth_electric_boiler": "Electric Boiler",
        "pv_rooftop": "PV Rooftop",
        "pv_utility": "PV Utility",
        "wind_offshore": "Wind Offshore",
        "wind_onshore": "Wind Onshore"
    }
    STACK_ORDER = [
        "Nuclear Conventional", "Nuclear SMR","Nuclear CHP SMR","Nuclear CHH2P SMR", 
        "CHP RollsRoyce SMR unit 1","CHP Thorizon SMR unit 1", "CHP Hitachi SMR unit 1",
        "CH2P RollsRoyce SMR unit 1","CH2P Thorizon SMR unit 1", "CH2P Hitachi SMR unit 1",
        "CHH2P RollsRoyce SMR unit 1","CHH2P Thorizon SMR unit 1", "CHH2P Hitachi SMR unit 1", 
        "CHP RollsRoyce SMR unit 2","CHP Thorizon SMR unit 2", "CHP Hitachi SMR unit 2",
        "CH2P RollsRoyce SMR unit 2","CH2P Thorizon SMR unit 2", "CH2P Hitachi SMR unit 2",
        "CHH2P RollsRoyce SMR unit 2","CHH2P Thorizon SMR unit 2", "CHH2P Hitachi SMR unit 2", 
        "CHP RollsRoyce SMR unit 3","CHP Thorizon SMR unit 3", "CHP Hitachi SMR unit 3",
        "CH2P RollsRoyce SMR unit 3","CH2P Thorizon SMR unit 3", "CH2P Hitachi SMR unit 3",
        "CHH2P RollsRoyce SMR unit 3","CHH2P Thorizon SMR unit 3", "CHH2P Hitachi SMR unit 3", 
        "CCGT Gas", "CCGT Hydrogen",
        "Biomass", "Waste Incinerator", "Hydro RoR", "OCGT Gas", "OCGT Hydrogen",
        "Wind Offshore", "Wind Onshore", "PV Utility", "PV Rooftop",
        "Pumped Hydro", "BESS IDES", "BESS MDES", "BESS Households",
        "Elektrolyser - Onshore", "Elektrolyser - Offshore",
        "Electric Boiler", "Curtailment"
    ]
    TECH_COLORS = {
        "Curtailment": "#000000",
        "Demand": "#444444",
        "Biomass": "#76c893",
        "CCGT Gas": "#34a0a4",
        "CCGT Hydrogen": "#168aad",
        "Electric Boiler": "#ffb4a2",
        "Hydro RoR": "#1a759f",
        "Nuclear Conventional": "#006d77",
        "Nuclear SMR": "#83c5be",
        "Nuclear CHP SMR": "#83c5be",
        "Nuclear CHH2P SMR":"#83c5be",
        "CHP RollsRoyce SMR unit 1": "#2d9e40",
        "CHP Thorizon SMR unit 1": "#2ca83d",
        "CHP Hitachi SMR unit 1": "#a0d468",
        "CH2P RollsRoyce SMR unit 1": "#ddaf30",
        "CH2P Thorizon SMR unit 1": "#ca9a21",
        "CH2P Hitachi SMR unit 1": "#f8b712",
        "CHH2P RollsRoyce SMR unit 1": "#30dda6",
        "CHH2P Thorizon SMR unit 1": "#21ca86",
        "CHH2P Hitachi SMR unit 1": "#12f891",
        "CHP RollsRoyce SMR unit 2": "#2d9e40",
        "CHP Thorizon SMR unit 2": "#2ca83d",
        "CHP Hitachi SMR unit 2": "#a0d468",
        "CH2P RollsRoyce SMR unit 2": "#ddaf30",
        "CH2P Thorizon SMR unit 2": "#ca9a21",
        "CH2P Hitachi SMR unit 2": "#f8b712",
        "CHH2P RollsRoyce SMR unit 2": "#30dda6",
        "CHH2P Thorizon SMR unit 2": "#21ca86",
        "CHH2P Hitachi SMR unit 2": "#12f891",
        "CHP RollsRoyce SMR unit 3": "#2d9e40",
        "CHP Thorizon SMR unit 3": "#2ca83d",
        "CHP Hitachi SMR unit 3": "#a0d468",
        "CH2P RollsRoyce SMR unit 3": "#ddaf30",
        "CH2P Thorizon SMR unit 3": "#ca9a21",
        "CH2P Hitachi SMR unit 3": "#f8b712",
        "CHH2P RollsRoyce SMR unit 3": "#30dda6",
        "CHH2P Thorizon SMR unit 3": "#21ca86",
        "CHH2P Hitachi SMR unit 3": "#12f891",
        "OCGT Gas": "#34a0a4",
        "OCGT Hydrogen": "#168aad",
        "Pumped Hydro": "#c19ee0",
        "PV Rooftop": "#ffd000",
        "PV Utility": "#ffc300",
        "Waste Incinerator": "#76c893",
        "Wind Offshore": "#b5e48c",
        "Wind Onshore": "#d9ed92",
        "BESS Households": "#d2b7e5",
        "BESS IDES": "#d2b7e5",
        "BESS MDES": "#c19ee0",
        "Elektrolyser - Onshore": "#02cecb",
        "Elektrolyser - Offshore": "#02cecb"
    }
    df_var = df[df["var_cost_category"] == "monetary"].copy()
    df_var = df_var[~df_var["technology"].str.startswith(tuple(TRANSMISSION_PREFIXES))]
    df_var["tech_label"] = df_var["technology"].map(TECH_LABELS).fillna(df_var["technology"])
    agg_var = (
        df_var
        .groupby(["time", "tech_label"])["variable_cost"]
        .sum()
        .reset_index()
    )
    fig = go.Figure()
    for tech in STACK_ORDER + [t for t in agg_var["tech_label"].unique() if t not in STACK_ORDER]:
        df_tech = agg_var[agg_var["tech_label"] == tech]
        if df_tech.empty:
            continue
        fig.add_trace(go.Bar(
            x=df_tech["time"],
            y=df_tech["variable_cost"],
            name=tech,
            marker_color=TECH_COLORS.get(tech, None)
        ))
    fig.update_layout(
        barmode="relative",
        title="Monetary Variable Costs by Technology and Timestep (No Transmission)",
        xaxis=dict(title="Time", tickformat="%Y-%m-%d\n%H:%M"),
        yaxis=dict(title="Variable Cost (€)"),
        legend_title="Technology",
        height=600,
        margin=dict(t=80, l=60, r=20, b=40)
    )
    return fig

# --------- PLOT 3: Utilization --------- #
def plot_utilization(df):
    TRANSMISSION_PREFIXES = [
        "transmission_hvac","free_co2_transmission","free_co2_stored_transmission",
        "free_gas_transmission","free_hyd_transmission","free_sink_transmission",
        "interconnector_"
    ]
    df = df[~df.technology.str.startswith(tuple(TRANSMISSION_PREFIXES))]
    TECH_LABELS = {
        "curtailment_elc": "Curtailment",
        "demand_elc": "Demand",
        "ES_BESS_households": "BESS Households",
        "ES_BESS_IDES": "BESS IDES",
        "ES_BESS_MDES": "BESS MDES",
        "ES_pumped_hydro": "Pumped Hydro",
        "pp_biomass_standalone": "Biomass",
        "pp_ccgt_gas": "CCGT Gas",
        "pp_ccgt_hyd": "CCGT Hydrogen",
        "pp_ocgt_gas": "OCGT Gas",
        "pp_ocgt_hyd": "OCGT Hydrogen",
        "pp_elektrolyser_onshore": "Elektrolyser - Onshore",
        "pp_elektrolyser_offshore": "Elektrolyser - Offshore",
        "pp_nuclear_conventional": "Nuclear Conventional",
        "pp_nuclear_smr": "Nuclear SMR",
        "pp_SMR_CHP_generic": "Nuclear CHP SMR",
        "pp_SMR_CHH2P_generic": "Nuclear CHH2P SMR",  
        "pp_SMR_Hitachi_CHP_1": "CHP Hitachi unit 1",
        "pp_SMR_RollsRoyce_CHP_1": "CHP RollsRoyce unit 1",
        "pp_SMR_Thorizon_CHP_1": "CHP Thorizon unit 1",
        "pp_SMR_RollsRoyce_CH2P_1": "CH2P RollsRoyce unit 1",
        "pp_SMR_Thorizon_CH2P_1": "CH2P Thorizon unit 1",
        "pp_SMR_Hitachi_CH2P_1": "CH2P Hitachi unit 1",
        "pp_SMR_RollsRoyce_CHH2P_1": "CHH2P RollsRoyce unit 1",
        "pp_SMR_Thorizon_CHH2P_1": "CHH2P Thorizon unit 1",
        "pp_SMR_Hitachi_CHH2P_1": "CHH2P Hitachi unit 1",
        "pp_SMR_Hitachi_CHP_2": "CHP Hitachi unit 2",
        "pp_SMR_RollsRoyce_CHP_2": "CHP RollsRoyce unit 2",
        "pp_SMR_Thorizon_CHP_2": "CHP Thorizon unit 2",
        "pp_SMR_RollsRoyce_CH2P_2": "CH2P RollsRoyce unit 2",
        "pp_SMR_Thorizon_CH2P_2": "CH2P Thorizon unit 2",
        "pp_SMR_Hitachi_CH2P_2": "CH2P Hitachi unit 2",
        "pp_SMR_RollsRoyce_CHH2P_2": "CHH2P RollsRoyce unit 2",
        "pp_SMR_Thorizon_CHH2P_2": "CHH2P Thorizon unit 2",
        "pp_SMR_Hitachi_CHH2P_2": "CHH2P Hitachi unit 2",
        "pp_SMR_Hitachi_CHP_3": "CHP Hitachi unit 3",
        "pp_SMR_RollsRoyce_CHP_3": "CHP RollsRoyce unit 3",
        "pp_SMR_Thorizon_CHP_3": "CHP Thorizon unit 3",
        "pp_SMR_RollsRoyce_CH2P_3": "CH2P RollsRoyce unit 3",
        "pp_SMR_Thorizon_CH2P_3": "CH2P Thorizon unit 3",
        "pp_SMR_Hitachi_CH2P_3": "CH2P Hitachi unit 3",
        "pp_SMR_RollsRoyce_CHH2P_3": "CHH2P RollsRoyce unit 3",
        "pp_SMR_Thorizon_CHH2P_3": "CHH2P Thorizon unit 3",
        "pp_SMR_Hitachi_CHH2P_3": "CHH2P Hitachi unit 3",
        "pp_waste_incinerator": "Waste Incinerator",
        "pth_electric_boiler": "Electric Boiler",
        "pv_rooftop": "PV Rooftop",
        "pv_utility": "PV Utility",
        "wind_offshore": "Wind Offshore",
        "wind_onshore": "Wind Onshore"
    }
    df["tech_label"] = df["technology"].map(TECH_LABELS).fillna(df["technology"])
    util = df[["time","location","tech_label","prod_utilization","con_utilization","capacity"]].copy()
    util.rename(columns={"prod_utilization":"prod_util","con_utilization":"con_util"}, inplace=True)
    util = util.drop_duplicates(subset=["time","location","tech_label"])
    mask = util.capacity > 0
    agg_prod = (
        util[mask]
        .groupby(["time","tech_label"])["prod_util"]
        .mean()
        .reset_index(name="prod_util")
    )
    agg_con = (
        util[mask]
        .groupby(["time","tech_label"])["con_util"]
        .mean()
        .reset_index(name="con_util")
    )
    TECH_GROUPS = {
        "Nuclear":       ["Nuclear Conventional","Nuclear SMR","Nuclear CHP SMR","Nuclear CHH2P SMR",  
                            "pp_SMR_Hitachi_CHP_1", "pp_SMR_RollsRoyce_CHP_1", "pp_SMR_Thorizon_CHP_1", 
                            "pp_SMR_Hitachi_CHP_2", "pp_SMR_RollsRoyce_CHP_2", "pp_SMR_Thorizon_CHP_2",
                            "pp_SMR_Hitachi_CHP_3", "pp_SMR_RollsRoyce_CHP_3", "pp_SMR_Thorizon_CHP_3",
                            "pp_SMR_Hitachi_CH2P_1", "pp_SMR_RollsRoyce_CH2P_1", "pp_SMR_Thorizon_CH2P_1",
                            "pp_SMR_Hitachi_CH2P_2", "pp_SMR_RollsRoyce_CH2P_2", "pp_SMR_Thorizon_CH2P_2",
                            "pp_SMR_Hitachi_CH2P_3", "pp_SMR_RollsRoyce_CH2P_3", "pp_SMR_Thorizon_CH2P_3",
                            "pp_SMR_Hitachi_CHH2P_1", "pp_SMR_RollsRoyce_CHH2P_1", "pp_SMR_Thorizon_CHH2P_1",
                            "pp_SMR_Hitachi_CHH2P_2", "pp_SMR_RollsRoyce_CHH2P_2", "pp_SMR_Thorizon_CHH2P_2",
                            "pp_SMR_Hitachi_CHH2P_3", "pp_SMR_RollsRoyce_CHH2P_3", "pp_SMR_Thorizon_CHH2P_3"],
        "Gas":           ["CCGT Gas","OCGT Gas"],
        "Hydrogen":      ["CCGT Hydrogen","OCGT Hydrogen"],
        "VRE":           ["Wind Offshore","Wind Onshore","PV Utility","PV Rooftop"],
        "Other RES":     ["Biomass","Waste Incinerator","Pumped Hydro"],
        "Storage":       ["BESS IDES","BESS MDES","BESS Households","Pumped Hydro"],
        "Conversion":    ["Elektrolyser - Onshore","Elektrolyser - Offshore"],
        "Heat":          ["Electric Boiler"],
        "Import":        ["Import DIE","Import SIE","Import DEN","Import NOR","Import EYC","Import WSL","Import UK","Import GRO","Import ZAN"],
        "Export":        ["Export DIE","Export SIE","Export DEN","Export NOR","Export EYC","Export WSL","Export UK","Export GRO","Export ZAN"]
    }
    LINE_COLORS = {
        "Nuclear Conventional":"#006d77",
        "Nuclear SMR":"#83c5be", 
        "Nuclear CHP SMR": "#83c5be",
        "Nuclear CHH2P SMR":"#83c5be",
        "CHP RollsRoyce unit 1": "#2d9e40",
        "CHP Thorizon unit 1": "#2ca83d",
        "CHP Hitachi unit 1": "#a0d468",
        "CH2P RollsRoyce unit 1": "#ddaf30",
        "CH2P Thorizon unit 1": "#ca9a21",
        "CH2P Hitachi unit 1": "#f8b712",
        "CHH2P RollsRoyce unit 1": "#30dda6",
        "CHH2P Thorizon unit 1": "#21ca86",
        "CHH2P Hitachi unit 1": "#12f891",
        "CHP RollsRoyce unit 2": "#2d9e40",
        "CHP Thorizon unit 2": "#2ca83d",
        "CHP Hitachi unit 2": "#a0d468",
        "CH2P RollsRoyce unit 2": "#ddaf30",
        "CH2P Thorizon unit 2": "#ca9a21",
        "CH2P Hitachi unit 2": "#f8b712",
        "CHH2P RollsRoyce unit 2": "#30dda6",
        "CHH2P Thorizon unit 2": "#21ca86",
        "CHH2P Hitachi unit 2": "#12f891",
        "CHP RollsRoyce unit 3": "#2d9e40",
        "CHP Thorizon unit 3": "#2ca83d",
        "CHP Hitachi unit 3": "#a0d468",
        "CH2P RollsRoyce unit 3": "#ddaf30",
        "CH2P Thorizon unit 3": "#ca9a21",
        "CH2P Hitachi unit 3": "#f8b712",
        "CHH2P RollsRoyce unit 3": "#30dda6",
        "CHH2P Thorizon unit 3": "#21ca86",
        "CHH2P Hitachi unit 3": "#12f891",
        "CCGT Gas":"#34a0a4","OCGT Gas":"#34a0a4",
        "CCGT Hydrogen":"#168aad","OCGT Hydrogen":"#168aad",
        "Wind Offshore":"#b5e48c","Wind Onshore":"#d9ed92",
        "PV Utility":"#ffc300","PV Rooftop":"#ffd000",
        "Biomass":"#76c893","Waste Incinerator":"#76c893","Pumped Hydro":"#c19ee0",
        "BESS IDES":"#d2b7e5","BESS MDES":"#c19ee0","BESS Households":"#d2b7e5",
        "Elektrolyser - Onshore":"#02cecb","Elektrolyser - Offshore":"#02cecb",
        "Electric Boiler":"#ffb4a2",
        "Import DIE":"#888888","Export DIE":"#555555"
    }
    fig = go.Figure()
    for group, techs in TECH_GROUPS.items():
        for tech in techs:
            df_p = agg_prod[agg_prod.tech_label == tech]
            df_c = agg_con[agg_con.tech_label == tech]
            if not df_p.empty:
                fig.add_trace(go.Scatter(
                    x=df_p.time, y=df_p.prod_util * 100,
                    mode="lines", name=f"{tech} (prod)",
                    line=dict(color=LINE_COLORS.get(tech, "gray"), width=2),
                    visible=(group == "Nuclear"),
                    customdata=[group] * len(df_p),
                    legendgroup=tech
                ))
            if not df_c.empty:
                fig.add_trace(go.Scatter(
                    x=df_c.time, y=df_c.con_util * 100,
                    mode="lines", name=f"{tech} (cons)",
                    line=dict(color=LINE_COLORS.get(tech, "gray"), width=2, dash="dot"),
                    visible=(group == "Nuclear"),
                    customdata=[group] * len(df_c),
                    legendgroup=tech
                ))
    buttons = []
    groups = list(TECH_GROUPS.keys())
    for grp in groups:
        vis = [(trace.customdata[0] == grp) for trace in fig.data]
        buttons.append(dict(
            method="update",
            label=grp,
            args=[{"visible": vis},
                  {"title": f"{grp} Utilization (%)"}]
        ))
    fig.update_layout(
        updatemenus=[dict(
            active=groups.index("Nuclear"),
            buttons=buttons,
            x=0,
            y=1.15,
            xanchor="left",
            yanchor="top"
        )],
        title="Nuclear Utilization (%)",
        xaxis=dict(title="Time", tickformat="%Y-%m-%d\n%H:%M"),
        yaxis=dict(title="Utilization (%)", range=[0, 100]),
        legend_title="Tech & Flow",
        height=600,
        margin=dict(t=100, l=60, r=20, b=40)
    )
    return fig

# --------- MAIN DRIVER FUNC --------- #
def generate_report(nc_file_path, processed_csv_path, output_html_file):
    # 1. Postprocess
    df = postprocess(nc_file_path, processed_csv_path)
    # 2. Generate figures
    fig1 = plot_carrier_flows(df)
    fig2 = plot_variable_costs(df)
    fig3 = plot_utilization(df)
    # 3. Combine in HTML
    with open(output_html_file, "w", encoding="utf-8") as f:
        f.write('<h1>Energy System Analysis Report</h1>')
        f.write('<h2>1. Carrier Flows</h2>')
        f.write(pio.to_html(fig1, full_html=False, include_plotlyjs='cdn'))
        f.write('<h2>2. Variable Costs</h2>')
        f.write(pio.to_html(fig2, full_html=False, include_plotlyjs=False))
        f.write('<h2>3. Utilization</h2>')
        f.write(pio.to_html(fig3, full_html=False, include_plotlyjs=False))
    print(f"Combined report written to {output_html_file}")

# ---------- CLI ENTRYPOINT ---------- #
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Postprocess and visualize energy system outputs (SMR & VRE focus)")
    parser.add_argument("--nc_file", type=str, required=True, help="Input NetCDF file")
    parser.add_argument("--csv_file", type=str, required=True, help="Intermediate processed CSV")
    parser.add_argument("--output_html", type=str, required=True, help="Output HTML file (all plots)")
    args = parser.parse_args()
    generate_report(args.nc_file, args.csv_file, args.output_html)
