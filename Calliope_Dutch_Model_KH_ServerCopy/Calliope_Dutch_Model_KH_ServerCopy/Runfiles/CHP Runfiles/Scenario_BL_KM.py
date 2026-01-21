import os
import calliope
from datetime import datetime
from pathlib import Path
import logging
from pathlib import Path
from pyomo.environ import Var, Constraint, Binary, NonNegativeReals, value
import pandas as pd
import ruamel.yaml as yaml
import pyomo.environ as pyo


# ======================
# CONFIGURATION SECTION
# ======================
base_dir = Path.cwd()  
MODEL_FILE = base_dir / "Research_Runs" / "Scenario_BL.yaml"
OUTPUT_DIR = base_dir / "output"    / "1.Baseline"
LOG_VERBOSITY = "INFO" #INFO  # Set to "DEBUG" for detailed solver output

SCENARIOS = ["base_run_KM"]


# ======================
# HELPER FUNCTIONS
# ======================
def create_versioned_filename(base_name, extension, output_dir=OUTPUT_DIR):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"{base_name}_{timestamp}.{extension}"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir / filename

if __name__ == "__main__":
    calliope.set_log_verbosity(LOG_VERBOSITY, include_solver_output=True)
    
    scenario_string = ",".join(SCENARIOS)
    print(f"\n{'='*50}")
    print(f"RUNNING MODEL")
    print(f"Scenarios: {scenario_string}")
    print(f"{'='*50}\n")
    
    # Load and run the model
    model = calliope.Model(str(MODEL_FILE), scenario=scenario_string)

    model.run()
    # Save the fully merged and commented model YAML for inspection
    yaml_file = create_versioned_filename("BL_" + scenario_string, "yaml")
    model.save_commented_model_yaml(yaml_file)
    print(f" Fully merged model YAML saved to {yaml_file}")

    model._model_data = results_ds
    
    nc_file = create_versioned_filename("BL_" + scenario_string, "nc")
    model.backend.to_netcdf(str(nc_file))
    print(f" Model run completed. Results saved to {nc_file}")

    print("\nModel run completed successfully!")

