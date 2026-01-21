import os
import calliope
from datetime import datetime
from pathlib import Path
import logging
from pathlib import Path
import pandas as pd

base_dir = Path.cwd()  
MODEL_FILE = base_dir / "Research_Runs" / "Scenario_BL_H2.yaml"
OUTPUT_DIR = base_dir / "output"    / "BL"
LOG_VERBOSITY = "INFO" 
SCENARIOS = ["base_run_EV"]

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
    
    model = calliope.Model(str(MODEL_FILE), scenario=scenario_string)
    model.run()

    yaml_file = create_versioned_filename("BL_H2" + scenario_string, "yaml")
    model.save_commented_model_yaml(yaml_file)
    print(f" Fully merged model YAML saved to {yaml_file}")

    nc_file = create_versioned_filename("BL_H2" + scenario_string, "nc")
    model.results.to_netcdf(str(nc_file))
    print(f" Model run completed. Results saved to {nc_file}")
    print("\nModel run completed successfully!")

