import os
import calliope
from datetime import datetime

# ======================
# CONFIGURATION SECTION
# ======================
MODEL_FILE = "SMR_model_1.yaml"
SCENARIOS = []
OUTPUT_DIR = "output"
LOG_VERBOSITY = "DEBUG"  # Set to "DEBUG" for detailed solver output

# ======================
# HELPER FUNCTIONS
# ======================
def create_versioned_filename(base_name, extension, output_dir=OUTPUT_DIR):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"{base_name}_{timestamp}.{extension}"
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, filename)

# ======================
# MAIN EXECUTION
# ======================
if __name__ == "__main__":
    # Set Calliope log verbosity and include solver output
    calliope.set_log_verbosity(LOG_VERBOSITY, include_solver_output=True)
    
    scenario_string = ",".join(SCENARIOS)
    print(f"\n{'='*50}")
    print(f"RUNNING BASELINE MODEL")
    print(f"Scenarios: {scenario_string}")
    print(f"{'='*50}\n")
    
    # Load and run the model
    model = calliope.Model(MODEL_FILE, scenario=scenario_string)
    model.run()

    # Fix invalid NetCDF attributes before saving
    if model._model_data.attrs.get('scenario', None) is None:
        model._model_data.attrs['scenario'] = ''

    # Save results to a NetCDF file
    nc_file = create_versioned_filename("Run_DEBUG", "nc")
    model._model_data.to_netcdf(nc_file, engine="netcdf4", encoding={var: {"zlib": False} for var in model._model_data.variables})
    print(f"✅ Model run completed. Results saved to {nc_file}")

    # Save the fully merged and commented model YAML for inspection
    yaml_file = create_versioned_filename("DEBUG_FULL_MODEL", "yaml")
    model.save_commented_model_yaml(yaml_file)
    print(f"✅ Fully merged model YAML saved to {yaml_file}")

    # Generate HTML summary
    html_file = create_versioned_filename("Summary_Run_1", "html")
    model.plot.summary(to_file=html_file)
    print(f"✅ HTML summary saved to {html_file}")

    print("\nBaseline model run completed successfully!")
