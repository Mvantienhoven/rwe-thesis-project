import os
import sys
from datetime import datetime
from pathlib import Path

import calliope

# ── Paths ────────────────────────────────────────────────────────────────────
base_dir = Path.cwd()
MODEL_FILE = base_dir / "Research_Runs" / "Scenario_BL.yaml"

USER = os.environ.get("USER", "unknown_user")
OUTPUT_ROOT = Path("/scratch") / USER / "DELFTBLUE_SET" / "output" / "BL"

LOG_VERBOSITY = "INFO"


def create_versioned_filename(base_name: str, extension: str, output_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{base_name}_{timestamp}.{extension}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / filename


def main() -> None:
    if len(sys.argv) != 2:
        raise ValueError(
            "Usage: python Runfile_BL_generic.py <scenario_name>\n"
            "Example: python Runfile_BL_generic.py base_run_KM_W1_L1_P1"
        )

    scenario_name = sys.argv[1].strip()
    if not scenario_name:
        raise ValueError("Scenario name is empty.")

    output_dir = OUTPUT_ROOT / scenario_name

    calliope.set_log_verbosity(LOG_VERBOSITY, include_solver_output=True)

    print(f"\n{'=' * 50}")
    print("RUNNING MODEL")
    print(f"Scenario: {scenario_name}")
    print(f"Working directory: {base_dir}")
    print(f"Model file: {MODEL_FILE}")
    print(f"Output directory: {output_dir}")
    print(f"{'=' * 50}\n")

    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_FILE}")

    model = calliope.Model(str(MODEL_FILE), scenario=scenario_name)
    model.run()

    yaml_file = create_versioned_filename(scenario_name, "yaml", output_dir)
    model.save_commented_model_yaml(yaml_file)
    print(f"Fully merged model YAML saved to {yaml_file}")

    nc_file = create_versioned_filename(scenario_name, "nc", output_dir)
    model.results.to_netcdf(str(nc_file))
    print(f"Model run completed. Results saved to {nc_file}")

    print("\nModel run completed successfully!")


if __name__ == "__main__":
    main()