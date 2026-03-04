import pandas as pd
import xarray as xr
import yaml
import json
from pathlib import Path
import folium
from folium.plugins import PolyLineTextPath

# ---- Processing Functions (from your postprocessing script, adapted) ----

def process_primary_energy_flows(input_csv_path, exclude_prefixes=None):
    df = pd.read_csv(input_csv_path, parse_dates=["time"])
    is_interconnector = df["technology"].str.startswith("interconnector_base:")
    df_interconnectors = df[is_interconnector].copy()
    df_other = df[~is_interconnector].copy()
    if "var_cost_category" in df_other.columns:
        df_other = df_other[df_other["var_cost_category"] == "primary_energy"].copy()
    df_combined = pd.concat([df_other, df_interconnectors], ignore_index=True)
    cols = [
        "time", "location", "technology", "carrier",
        "production", "consumption"
    ]
    # Some postprocessing files may have extra columns
    existing_cols = [c for c in cols if c in df_combined.columns]
    df_combined = df_combined[existing_cols]
    link_prefixes = ("transmission_hvac:", "interconnector_base:")
    if exclude_prefixes is None:
        exclude_prefixes = []
    is_link = df_combined["technology"].str.startswith(link_prefixes)
    df_links = df_combined[is_link].copy()
    for prefix in exclude_prefixes:
        df_links = df_links[~df_links.technology.str.startswith(prefix)]
    df_nodes = df_combined[~is_link].copy()
    df_links[["tech_prefix", "target_node"]] = df_links["technology"].str.split(":", n=1, expand=True)
    df_links["location"] = df_links.apply(
        lambda row: ":".join(sorted([row["location"], row["target_node"]])), axis=1
    )
    def merge_pair(group):
        if len(group) == 2:
            a, b = group.iloc
            prod, cons = (a, b) if a.production > 0 else (b, a)
        else:
            prod = group.iloc[0]
            cons = prod
        n1, n2 = group.name[1].split(":")
        tech = f"{prod.tech_prefix}:{n1}:{n2}"
        return {
            "time": prod.time,
            "location": group.name[1],
            "technology": tech,
            "carrier": prod.carrier,
            "production": prod.production,
            "consumption": cons.consumption
        }
    merged = df_links.groupby(["time", "location", "carrier"]).apply(merge_pair)
    df_links = pd.DataFrame(list(merged))
    return pd.concat([df_nodes, df_links], ignore_index=True)


def extract_demand_all_timesteps(nc_path):
    ds = xr.open_dataset(nc_path)
    da = ds["required_resource"]
    df = da.to_series().reset_index()
    df[["location", "tech_full"]] = df["loc_techs_balance_demand_constraint"].str.split("::", expand=True)
    df["raw_carrier"] = df["tech_full"].str.replace("demand_", "", regex=False)
    df = df[df["raw_carrier"] != "curtailment_elc"]
    carrier_map = {"elc": "electricity", "gas": "gas", "hyd": "hydrogen", "pth": "heat"}
    df["carrier"] = df["raw_carrier"].map(carrier_map).fillna(df["raw_carrier"])
    df = df.rename(columns={"required_resource": "demand"})
    df = df.groupby(["timesteps", "carrier", "location"], as_index=False)["demand"].sum()
    df = df.rename(columns={"timesteps": "time"})
    ds.close()
    return df

def aggregate_by_carrier_for_time(flows, demand, t):
    df_f = flows[flows.time == t]
    df_sum = df_f.groupby(["carrier", "location"], as_index=False)[["production", "consumption"]].sum()
    df_dem = demand[demand.time == t]
    df_agg = pd.merge(df_sum, df_dem, how="left", on=["carrier", "location"]).fillna({"demand": 0.0})
    out = {}
    for carrier, grp in df_agg.groupby("carrier"):
        out[carrier] = grp.set_index("location")[["production", "consumption", "demand"]].to_dict(orient="index")
    return out

def load_locations(yaml_path):
    with open(yaml_path) as f:
        return yaml.safe_load(f)["locations"]

def build_base_map(locations, geojson_path):
    m = folium.Map(location=[52.2, 5.3], zoom_start=7, tiles="cartodbpositron")
    with open(geojson_path) as f:
        folium.GeoJson(
            json.load(f),
            style_function=lambda _: {"fillColor": "#ffffff00", "color": "#444444", "weight": 1}
        ).add_to(m)
    return m

def draw_nodes_and_links(m, locations, exclude_prefixes):
    fg_nodes = folium.FeatureGroup(name="Nodes", show=True)
    fg_links = folium.FeatureGroup(name="Links", show=True)
    for node, attrs in locations.items():
        lat, lon = attrs["coordinates"]["lat"], attrs["coordinates"]["lon"]
        folium.CircleMarker([lat, lon], radius=6, color="#023047", fill=True, fill_color="#023047", tooltip=node).add_to(fg_nodes)
    for node, attrs in locations.items():
        src = attrs["coordinates"]
        for tgt, link in attrs.get("links", {}).items():
            for tech in link.get("techs", {}):
                if any(tech.startswith(p) for p in exclude_prefixes):
                    continue
                dst = locations[tgt]["coordinates"]
                folium.PolyLine([(src["lat"], src["lon"]), (dst["lat"], dst["lon"])],
                                color="#8ecae6" if not tech.startswith("interconnector_base") else "#ffb703",
                                weight=2, tooltip=tech).add_to(fg_links)
    fg_nodes.add_to(m)
    fg_links.add_to(m)

def overlay_arrows(m, locations, flows, exclude_prefixes):
    fg = folium.FeatureGroup(name="Arrows", show=False)
    df_links = flows[flows.technology.str.contains("transmission_hvac:|interconnector_base:")]
    for prefix in exclude_prefixes:
        df_links = df_links[~df_links.technology.str.startswith(prefix)]
    df_links["origin"], df_links["dest"] = zip(*df_links.location.str.split(":", n=1))
    for _, row in df_links.iterrows():
        lat1, lon1 = locations[row.origin]["coordinates"].values()
        lat2, lon2 = locations[row.dest]["coordinates"].values()
        line = folium.PolyLine([(lat1, lon1), (lat2, lon2)], color="transparent", weight=2).add_to(fg)
        PolyLineTextPath(line, "➤", repeat=True, offset=7,
                         attributes={"fill": "#9B9494", "font-size": "8px"}).add_to(fg)
    fg.add_to(m)

def overlay_carrier_layers(m, locations, stats):
    node_offset, link_offset = 0.02, -0.02
    for carrier, loc_stats in stats.items():
        fg = folium.FeatureGroup(name=carrier, show=False)
        for node, attrs in locations.items():
            lat = attrs["coordinates"]["lat"] + node_offset
            lon = attrs["coordinates"]["lon"]
            s = loc_stats.get(node, {"production": 0, "consumption": 0, "demand": 0})
            html = (
                f"<div style='font-size:10px;text-align:center;"
                f"background:rgba(255,255,255,0.8);padding:2px;border-radius:2px;'>"
                f"p:{s['production']:.2f}<br>c:{s['consumption']:.2f}<br>d:{s['demand']:.2f}"
                f"</div>"
            )
            folium.map.Marker([lat, lon], icon=folium.DivIcon(html=html), z_index_offset=1000).add_to(fg)
        for node, attrs in locations.items():
            src = attrs["coordinates"]
            for tgt in attrs.get("links", {}):
                loc_key = ":".join(sorted([node, tgt]))
                s = loc_stats.get(loc_key, {"production": 0, "consumption": 0, "demand": 0})
                if all(v == 0 for v in s.values()):
                    continue
                dst = locations[tgt]["coordinates"]
                mid_lat = (src["lat"] + dst["lat"]) / 2 + link_offset
                mid_lon = (src["lon"] + dst["lon"]) / 2
                html = (
                    f"<div style='font-size:8px;text-align:center;"
                    f"background:rgba(255,255,255,0.8);padding:1px;border-radius:2px;'>"
                    f"{s['production']:.2f}/{s['consumption']:.2f}/{s['demand']:.2f}"
                    f"</div>"
                )
                folium.map.Marker([mid_lat, mid_lon], icon=folium.DivIcon(html=html), z_index_offset=500).add_to(fg)
        fg.add_to(m)

# ---- The main function to call from notebook or CLI ----
def run_energy_flow_visualization(
    title,
    netcdf_path,
    flow_csv_path,
    yaml_path,
    geojson_path,
    output_html_path,
    exclude_prefixes=None
):
    if exclude_prefixes is None:
        exclude_prefixes = [
            "free_gas_transmission", "free_hyd_transmission", "free_co2_stored_transmission",
            "free_solid_fuel_transmission", "free_ets_budget_transmission",
            "free_ets_penalty_transmission", "free_sink_transmission", "free_co2_transmission"
        ]
    # FLOW PROCESSING
    df_flows = process_primary_energy_flows(flow_csv_path, exclude_prefixes=exclude_prefixes)
    df_demand = extract_demand_all_timesteps(netcdf_path)
    locations = load_locations(yaml_path)
    times = sorted(df_flows.time.unique())
    # Per-timestep map output
    per_map_dir = Path(output_html_path).parent / "maps"
    per_map_dir.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(times):
        stats = aggregate_by_carrier_for_time(df_flows, df_demand, t)
        m = build_base_map(locations, geojson_path)
        draw_nodes_and_links(m, locations, exclude_prefixes)
        overlay_arrows(m, locations, df_flows, exclude_prefixes)
        overlay_carrier_layers(m, locations, stats)
        folium.LayerControl(collapsed=False).add_to(m)
        m.save(per_map_dir / f"map_t{i}.html")
    # Master HTML
    n = len(times)
    master_html = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8"/>
    <title>{title}</title>
    <style>
        body {{ font-family: sans-serif; margin: 1rem; }}
        .maps-container {{
        display: flex;
        gap: 1rem;
        flex-wrap: nowrap;
        }}
        .map-section {{
        flex: 1;
        display: flex;
        flex-direction: column;
        }}
        #map1, #map2 {{
        width: 100%; height: 80vh; border: none;
        }}
        .selector {{
        margin-top: 0.5rem;
        }}
    </style>
    </head>
    <body>
    <h2>{title}</h2>
    <div class="maps-container">
        <!-- First map with its dropdown -->
        <div class="map-section">
        <label for="timestep-selector-1">Map 1 Timestep:</label>
        <select id="timestep-selector-1" class="selector"></select>
        <iframe id="map1" src=""></iframe>
        </div>
        <!-- Second map with its dropdown -->
        <div class="map-section">
        <label for="timestep-selector-2">Map 2 Timestep:</label>
        <select id="timestep-selector-2" class="selector"></select>
        <iframe id="map2" src=""></iframe>
        </div>
    </div>
    <script>
        const times = {n};
        
        // Setup for Map 1
        const selector1 = document.getElementById('timestep-selector-1');
        const iframe1 = document.getElementById('map1');

        for (let i = 0; i < times; i++) {{
        const opt = document.createElement('option');
        opt.value = i;
        opt.textContent = 'Timestep ' + i;
        selector1.appendChild(opt);
        }}
        selector1.value = 0;
        iframe1.src = 'maps/map_t0.html';

        selector1.addEventListener('change', function() {{
        iframe1.src = 'maps/map_t' + this.value + '.html';
        }});
        
        // Setup for Map 2
        const selector2 = document.getElementById('timestep-selector-2');
        const iframe2 = document.getElementById('map2');

        for (let i = 0; i < times; i++) {{
        const opt = document.createElement('option');
        opt.value = i;
        opt.textContent = 'Timestep ' + i;
        selector2.appendChild(opt);
        }}
        selector2.value = 0;
        iframe2.src = 'maps/map_t0.html';

        selector2.addEventListener('change', function() {{
        iframe2.src = 'maps/map_t' + this.value + '.html';
        }});
    </script>
    </body>
    </html>"""

    Path(output_html_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_html_path, "w") as f:
        f.write(master_html)
    print(f"[{title}] Generated {n} map files and master HTML at {output_html_path}")

# ---- CLI entrypoint ----
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True, type=str, help="Title of the page")
    parser.add_argument("--netcdf", required=True, type=str, help="Path to netcdf file")
    parser.add_argument("--flow_csv", required=True, type=str, help="Path to flow_with_utilization_and_coords.csv")
    parser.add_argument("--yaml", required=True, type=str, help="Path to YAML model file")
    parser.add_argument("--geojson", required=True, type=str, help="Path to geojson file")
    parser.add_argument("--output_html", required=True, type=str, help="Path to output master HTML file")
    args = parser.parse_args()
    run_energy_flow_visualization(
        args.title, args.netcdf, args.flow_csv, args.yaml, args.geojson, args.output_html
    )
