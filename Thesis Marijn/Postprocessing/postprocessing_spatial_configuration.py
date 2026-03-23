import argparse
import json
from datetime import datetime
from pathlib import Path

import folium

from postprocessing import exclude_prefixes, load_and_process_data


LINK_TECH_COLORS = {
    "interconnector_base": "#ffb703",
    "transmission_hvac": "#8ecae6",
    "offshore_cable_hvdc": "#8ecae6",
}


def _resolve_geojson_path() -> Path:
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir / "NUTS2.geojson",
        script_dir / "Postprocessing" / "NUTS2.geojson",
        Path.cwd() / "Research_Runs" / "Postprocessing" / "NUTS2.geojson",
        Path.cwd() / "Postprocessing" / "NUTS2.geojson",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("NUTS2.geojson not found in expected Postprocessing locations.")


def create_spatial_configuration_map(
    df_cap,
    locations,
    geojson_path: Path,
    fixed_link_width: float = 1.1,
    node_radius: int = 5,
):
    m = folium.Map(location=[52.2, 5.3], zoom_start=7, tiles="cartodbpositron")

    nuts2 = json.load(open(geojson_path, "r", encoding="utf-8"))
    folium.GeoJson(
        nuts2,
        style_function=lambda _: {"fillColor": "#ffffff00", "color": "#444444", "weight": 1},
    ).add_to(m)

    # Keep only installed links from model results.
    link_caps = {(r.node, r.tech): r.capacity for r in df_cap.itertuples(index=False)}
    drawn_links = set()

    for node, attrs in locations.items():
        coords = attrs.get("coordinates")
        if not coords:
            continue
        folium.CircleMarker(
            [coords["lat"], coords["lon"]],
            radius=node_radius,
            color="#023047",
            fill=True,
            fill_color="#023047",
            fill_opacity=0.95,
            tooltip=node,
        ).add_to(m)

    for node, attrs in locations.items():
        src = attrs.get("coordinates")
        if not src:
            continue
        for tgt, link in attrs.get("links", {}).items():
            if tgt not in locations:
                continue
            dst = locations[tgt].get("coordinates")
            if not dst:
                continue

            for tech in link.get("techs", {}):
                if any(tech.startswith(pref) for pref in exclude_prefixes):
                    continue

                cap = link_caps.get((node, f"{tech}:{tgt}"), 0)
                if not cap:
                    continue

                # Draw each undirected tech-link once.
                key = (tech, tuple(sorted([node, tgt])))
                if key in drawn_links:
                    continue
                drawn_links.add(key)

                color = LINK_TECH_COLORS.get(tech, "#8ecae6")
                folium.PolyLine(
                    [(src["lat"], src["lon"]), (dst["lat"], dst["lon"])],
                    color=color,
                    weight=fixed_link_width,
                    opacity=0.85,
                    tooltip=tech,
                ).add_to(m)

    return m


def run_spatial_configuration_map(
    netcdf_path: str,
    model_yaml_path: str,
    output_html_path: str = "",
):
    df_cap, locations = load_and_process_data(netcdf_path, model_yaml_path)
    geojson_path = _resolve_geojson_path()

    if output_html_path:
        out_path = Path(output_html_path)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        out_path = (
            Path.cwd().parent
            / "analysis_results"
            / f"Spatial_Configuration_{stamp}.html"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    m = create_spatial_configuration_map(
        df_cap=df_cap,
        locations=locations,
        geojson_path=geojson_path,
        fixed_link_width=1.1,
        node_radius=5,
    )
    m.save(str(out_path))
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a spatial-configuration map with uniform thin link widths."
    )
    parser.add_argument("--netcdf", required=True, help="Path to model output .nc")
    parser.add_argument("--model-yaml", required=True, help="Path to model output .yaml")
    parser.add_argument(
        "--output-html",
        default="",
        help="Optional output html path (default: analysis_results/Spatial_Configuration_<timestamp>.html)",
    )
    args = parser.parse_args()

    output = run_spatial_configuration_map(
        netcdf_path=args.netcdf,
        model_yaml_path=args.model_yaml,
        output_html_path=args.output_html,
    )
    print(f"Spatial configuration map saved to: {output}")
