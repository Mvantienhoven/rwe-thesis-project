# This code imports the necessary libraries for running a Calliope model, plotting results, and creating a Dash app.

"""
Folder structure

<main_dir>
|___<model_dir>
    |___<output_dir>
        |___temp
        |___<run_dir>
            |___<scenario_dir>
                |___csv
                |___netcdf
                |___plots


"""

import sys
import shutil

import calliope as cp

import pandas as pd
from datetime import datetime

import os
import tracemalloc

from calliope_run.calliope_settings import calliope_run_settings
from calliope_run.running.saving import savemodel_netcdf, savemodel_csv, saveplot_summary
from calliope_run.running.util import runmodel, create_directory


# This line stores the current working directory in the main_dir variable.
main_dir = os.getcwd()
sys.path.insert(0, './')

if calliope_run_settings['write_log_file']:
    log_file = main_dir+'/'+calliope_run_settings['model']+"/logs/calliope_run.log"
    # Open file to write terminal output
    log = open(log_file, 'w')
    sys.stdout = log

if calliope_run_settings['trace_memory_allocation']:
    tracemalloc.start()
    
    current = [] # memory trace containers
    peak = [] # memory trace containers

# @profile

# Load the right case folder
model_dir = main_dir + "/" + calliope_run_settings['model']
# Change directory to case_dir to keep Calliopes internal folder structure
os.chdir(model_dir)

# Set model generic output directory.
output_dir = model_dir+'/output'
# Check if directory exists, otherwise create it.
create_directory(output_dir)

# Create a timestamp for the run tag.
dateTimeObj = datetime.now()
time_stamp = dateTimeObj.strftime("%Y%m%d-%H%M%S")
# Create a run specific tag.
if calliope_run_settings['test']:
    run_tag = '/test_'+time_stamp+'_'+calliope_run_settings['model']
else:
    run_tag = '/results_'+time_stamp+'_'+calliope_run_settings['model']

# Set run directory.
run_dir = output_dir + run_tag
# Check if directory exists, otherwise create it.
create_directory(run_dir)

## Currently unavailable
# if calliope_run_settings['model']:
#     # Create a batch file
#     cp.generate_runs model.yaml run_model.bat --kind=windows --solved_scenarios "spores_run,spores_run_bioco2_cost_low,spores_run_bioco2_cost_high"

#### Run model

# We increase logging verbosity
cp.set_log_verbosity(calliope_run_settings['calliope_log_verbosity'], include_solver_output=True)

# Loop through all scenarios mentioned in `calliope_run_settings`.
for i,scenario in enumerate(calliope_run_settings['scenarios']):
    
    # Create scenario_tag
    if scenario == None:
        scenario_tag = '/reference'
    else:
        scenario_tag = '/'+scenario
    scenario_dir = run_dir + scenario_tag
    create_directory(scenario_dir)
    
    if scenario:
        if 'spores' in scenario:
            # Calliope needs a reference to an output folder to save the individual spores resuls in netCDF format.
            spores_dir = output_dir+'/_temp'
            create_directory(spores_dir)
            
            # Ultimately we want to move the folder with spores results into the scenario folder, which is done at the end of the scenario run.

    if calliope_run_settings['save_models']:
        csv_dir = scenario_dir + '/csvs'
        # Calliope automatically creates this directory.
        # create_directory(csv_dir)
        
        netcdf_dir = scenario_dir + '/netcdfs'
        create_directory(netcdf_dir)
        
    if calliope_run_settings['save_plots']:
        plot_dir = scenario_dir + '/plots'
        create_directory(plot_dir)
                       
    print (f"*****************************\nWorking on scenario {scenario}\n*****************************")
    
    # Define the Calliope model
    if scenario is None:
        model = cp.Model('model.yaml')
    else:
        model = cp.Model('model.yaml', scenario=scenario)

    # Toggle set_custom_constraints
    if scenario in calliope_run_settings['custom_constraints_exceptions']:
         calliope_run_settings['custom_constraints'] = False
    
    # Print the Calliope inputs
    # model.inputs
    
    print(model.info())
    
    
    try:
        run_model, duals = runmodel(
            model,
            scenario,
            calliope_run_settings['custom_constraints'],
            calliope_run_settings['shadowprices'],
            )
    except Exception as e:
        if calliope_run_settings['skip_when_failed']:
            print (f"FAILED TO RUN SCENARIO {scenario}, MOVING ONTO NEXT")
            print (e)
        else:
            raise
    else:

        # Make sure to move any spores files into the case folder.
        if 'spores' in scenario:
            # gather all files
            spores_files = os.listdir(spores_dir)
            
            # iterate on all files to move them to destination folder
            for f in spores_files:
                src_path = os.path.join(spores_dir, f)
                dst_path = os.path.join(netcdf_dir, f)
                shutil.move(src_path, dst_path)
                
            # shutil.move(spores_dir, scenario_dir)
            
        if calliope_run_settings['save_models']:
            # Save CSV model files.
            savemodel_csv(run_model, duals, csv_dir)
            # Save netCDF files.
            savemodel_netcdf(run_model, netcdf_dir)
            
        if calliope_run_settings['save_plots'] and 'spores' not in scenario:
            # Generate a summary plot.
            saveplot_summary(run_model,plot_dir,calliope_run_settings['mapbox_access_token'])
                
    if calliope_run_settings['trace_memory_allocation']:
            
        current_i, peak_i = tracemalloc.get_traced_memory()
        current.append(current_i/(1024*1024))
        peak.append(peak_i/(1024*1024))
        
        print (f"Current memory in use: [MB] {current[i]:.2f}, peak memory in use: [MB] {peak[i]:.2f}")


if calliope_run_settings['trace_memory_allocation']:
    memory = pd.DataFrame()
    memory['scenarios'] = calliope_run_settings['scenarios']
    memory['current'] = current
    memory['peak'] = peak
    
    print (f"Overview of memory use: {memory}")

print ("*******************************************************************************************,\n                   !! DONE !!")

if calliope_run_settings['write_log_file']:

    # Close output file
    log.close()
    
    shutil.copyfile(log_file, run_dir+"/calliope_run.log")