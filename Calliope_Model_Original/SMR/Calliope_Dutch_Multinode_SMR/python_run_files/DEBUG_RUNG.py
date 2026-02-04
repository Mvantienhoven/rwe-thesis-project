import os
from pathlib import Path
import calliope
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_FILE = BASE_DIR / "DEBUG_RUN.yaml"
SCENARIOS = []
OUTPUT_DIR = BASE_DIR / "output"
LOG_VERBOSITY = "DEBUG"  # Set to DEBUG for more detail

def create_versioned_filename(base_name, extension, output_dir=OUTPUT_DIR):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"{base_name}_{timestamp}.{extension}"
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, filename)

if __name__ == "__main__":
    calliope.set_log_verbosity(LOG_VERBOSITY, include_solver_output=True)
    scenario_string = ",".join(SCENARIOS)
    print(f"\n{'='*50}")
    print(f"RUNNING BASELINE MODEL")
    print(f"Scenarios: {scenario_string}")
    print(f"{'='*50}\n")
    model = calliope.Model(str(MODEL_FILE), scenario=scenario_string)
    model.run()

    # --- MILP variable check ---
    pyomo_model = getattr(model, "_backend_model", None)
    if pyomo_model is None:
        print("\n[DEBUG] Backend model not available; skipping MILP variable check.")
    else:
        int_vars = []
        bin_vars = []
        for v in pyomo_model.component_objects():
            if hasattr(v, "is_integer") and hasattr(v, "is_binary"):
                for index in v:
                    var = v[index]
                    if var.is_integer():
                        int_vars.append(var.name)
                    if var.is_binary():
                        bin_vars.append(var.name)
        print(f"\n[DEBUG] Number of integer variables: {len(int_vars)}")
        print(f"[DEBUG] Number of binary variables: {len(bin_vars)}")
        if int_vars or bin_vars:
            print("[DEBUG] Example integer variables:", int_vars[:5])
            print("[DEBUG] Example binary variables:", bin_vars[:5])
        else:
            print("[DEBUG] No integer or binary variables detected.")

    nc_file = create_versioned_filename("Run_1_Baseline_No_SMR", "nc")
    model.to_netcdf(nc_file)
    print(f"\n✅ Model results saved to {nc_file}")
    html_file = create_versioned_filename("Summary_Run_1", "html")
    model.plot.summary(to_file=html_file)
    print(f"✅ HTML summary saved to {html_file}")
    print("\nBaseline model run completed successfully!")
