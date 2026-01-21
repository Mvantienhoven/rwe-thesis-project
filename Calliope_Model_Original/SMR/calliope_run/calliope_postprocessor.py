import calliope as cp
import pandas as pd
import os
import numpy as np

# import sys
# sys.path.append("./")

# from calliope_run.postprocessing.calculations import *

from calliope_run.calliope_settings import calliope_run_settings, calliope_postprocess_settings
from calliope_run.postprocessing.util import *
from calliope_run.postprocessing.calculations import *
from calliope_run.postprocessing.model_mapping import *
# from calliope_run.postprocessing.model_handling2import *

from calliope_run.running.util import create_directory

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

def check_kpi_presence(check_kpi={},in_kpi={}):
    for kpi in check_kpi:
        if kpi not in in_kpi.keys():
            print (f"WARNING: kpi {kpi} was mentioned but was NOT LOADED. Add kpi `calliope_postprocess_settings`.")
            exit()

def postprocess_calliope(run_tag, test_postprocessor=False,test_with_n=None,skip=[]):
    
    # Define the directory of the Calliope run that contains the results.
    run_dir = calliope_run_settings['model']+'/output/'+run_tag
    folders = os.listdir(run_dir)

    # Define the folder where to write the output files of the script to.
    target_dir = run_dir + '/postprocessed_csvs/'
    create_directory(target_dir)

    # Perform a check whether all KPIs mentioned in the `map_kpi` list are present in the `load_kpis` dict in calliope_postprocess_settings.
    # If not, warn the user and exit the routine.
    check_kpi_presence(calliope_postprocess_settings["map_kpis"],calliope_postprocess_settings["load_kpis"])
    
    # # Perform a check whether all KPIs mentioned in the `merge_kpi` subdicts are present in the `load_kpis` dict in calliope_postprocess_settings.
    # # If not, warn the user and exit the routine.
    # for merge_kpi in calliope_postprocess_settings["merge_kpis"].keys():
    #     check_kpi_presence(calliope_postprocess_settings["merge_kpis"][merge_kpi],calliope_postprocess_settings["load_kpis"])
            
    # Create container list with folder locations of scenarios.
    process_folders = {}

    print (f"\n*** PROCESSING folders")
    # This for loop splits the filename to extract the scenario for each file and appends it to the above declared list
    # if test_postprocessor:
    for i,scenario in enumerate(folders):
        
        # Define location  of location of scenario csvs.
        csv_dir = run_dir +'/' + scenario + '/csvs/'
        check_csv_dir = os.path.isdir(csv_dir)
        
        if scenario == 'postprocessed_csvs' or test_postprocessor and scenario in skip:
            # print (f"SKIPPING folder {scenario}")
            print (f"{'SKIPPING':<15} 'folder `{scenario}`")
            # increase test_with_n to make sure we test with actual scenarios, and not with skipped scenarios.
            test_with_n += 1
            continue
        
        if not check_csv_dir:
            print (f"{'SKIPPING':<15} 'folder `{scenario}`")
            # increase test_with_n to make sure we test with actual scenarios, and not with skipped scenarios.
            test_with_n += 1
            continue
        
        process_folders[scenario] = csv_dir
        
        # print (f"PROCESSING {scenario}")
        print (f"{'PROCESSING':<15} 'folder `{scenario}`")
        
        if test_postprocessor and i + 1 == test_with_n:
            print (f"{'BREAKING OFF':<15} 'scenario initialization as number of test scenarios has been reached (`test_with_n` = {test_with_n})")
            
            # print (f"BREAKING off scenario initialization as number of test scenarios has been reached (`test_with_n` = {test_with_n})")
            break
    # else:
        # process_scenarios = scenarios
        
    # input_kpi_list = calliope_postprocess_settings["input_kpi_list"]
    # timeseries_kpi_list = calliope_postprocess_settings["timeseries_kpi_list"]
        
    # Printing out all the scenarios obtained by splitting the filenames earlier
    
    # calliope_postprocess_settings["derived_kpis"] = {}
    
    # Initializing two empty lists which will contain the solved models and duals per run
    # solved_models = get_model_csvs(process_folders,all_kpi_list,input_kpi_list)
    print (f"\n*** LOADING data")
    solved_models, timeseries_kpis = get_model_csvs(process_folders,calliope_postprocess_settings["load_kpis"])

    print (f"\n*** CALCULATING derived KPIs")
    if 'levelized_cost' in calliope_postprocess_settings["derive_kpis"]:
        solved_models = add_levelized_cost(solved_models)
        calliope_postprocess_settings["load_kpis"]['loctech_levelized_cost'] = float
        calliope_postprocess_settings["load_kpis"]['systemwide_levelized_cost'] = float

    if 'capacity_factor' in calliope_postprocess_settings["derive_kpis"]:
        solved_models = add_capacity_factor(solved_models)
        calliope_postprocess_settings["load_kpis"]['loctech_capacity_factor'] = float
        calliope_postprocess_settings["load_kpis"]['systemwide_capacity_factor'] = float
        
    # # 
    if 'available_resource' in calliope_postprocess_settings["derive_kpis"]:
        solved_models = add_available_resource(solved_models,calliope_postprocess_settings["include_resource_techs"],exclude_techs=calliope_postprocess_settings["exclude_resource_techs"])
        calliope_postprocess_settings["load_kpis"]['available_resource'] = float
        timeseries_kpis.add('available_resource')
    # timeseries_kpi_list += ['available_resource']

    if 'curtailed_resource' in calliope_postprocess_settings["derive_kpis"]:
        solved_models = add_curtailment(solved_models)
        calliope_postprocess_settings["load_kpis"]['curtailed_resource'] = float
        timeseries_kpis.add('curtailed_resource')
    # timeseries_kpi_list += ['curtailed_resource']
            
    # Compute residual curve from time dependent KPIs per run
    if 'residual_load' in calliope_postprocess_settings["derive_kpis"]:
        solved_models = add_residual_load(solved_models)
        calliope_postprocess_settings["load_kpis"]['residual_load'] = float
        calliope_postprocess_settings["load_kpis"]['system_imbalance'] = float
    # timeseries_kpi_list += ['residual_load', 'system_imbalance']

    # all_kpi_list = list(set(calliope_postprocess_settings["load_kpis"]+calliope_postprocess_settings["map_kpis"]
    #                         ))
    
    if 'annual_totals' in calliope_postprocess_settings["derive_kpis"]:
        
        for kpi in timeseries_kpis:
            # Compute annual totals of all timeseries 
            solved_models = add_annual_totals(solved_models,kpi)
            
            calliope_postprocess_settings["load_kpis"]["total_"+kpi] = float
            
    print (f"\n*** MAPPING data")
    # if calliope_postprocess_settings["map_kpis"]:
        
    #     # Map KPIs to dataframes of load_kpis.
    #     for kpi in calliope_postprocess_settings["load_kpis"]:
    #         solved_models = map_model_kpis(solved_models,kpi,calliope_postprocess_settings["map_kpis"])
            
        # Remove the mapped KPIs from the solved_models dict.
        # for kpi in calliope_postprocess_settings["map_kpis"]:
            # calliope_postprocess_settings["load_kpis"].pop(kpi)
            
    if calliope_postprocess_settings["merge_kpis"]:
        
        for merged_kpi in calliope_postprocess_settings["merge_kpis"]:
        
            target_kpi = calliope_postprocess_settings["merge_kpis"][merged_kpi][0]
            source_kpis = calliope_postprocess_settings["merge_kpis"][merged_kpi][1:]
            
            solved_models = map_model_kpis(solved_models,target_kpi,source_kpis,overwrite_name=merged_kpi)
            
        # Merge KPIs as described in calliope_postprocess_settings.
        # solved_models = merge_model_kpis(solved_models,calliope_postprocess_settings["merge_kpis"])

    
    #TODO Check which kpips to print
        # Loaded KPIs necessary?? Or is merged KPIs enough
    print (f"\n*** AGGREGATING data")    
    aggregate_kpis = []
    for aggregate_kpi in calliope_postprocess_settings["print_kpis"]:
        
        aggregate_kpis += list(calliope_postprocess_settings[aggregate_kpi].keys())
        
    # The data is now organised per simulation run per KPI. What we would like is to have all data organised per KPI, with the simulation run tags as additional column.
    # Aggregate all different runs per KPI
    aggregated_outputs = aggregate_model_results(solved_models,aggregate_kpis)

    # Print all aggregated models to files 
    print (f"\n*** WRITING output")
    printed_outputs = print_aggregated_model(aggregated_outputs,aggregate_kpis,target_dir)

if __name__ == '__main__':
        
    # run_tag = 'results_20240819-190804_dutch_calliope_single_node'
    # run_tag = 'test_20240916-111722_dutch_calliope_single_node'

    postprocess_calliope(
        calliope_postprocess_settings["run_tag"],
        calliope_postprocess_settings["test_postprocessor"],
        calliope_postprocess_settings["test_with_n"],
        calliope_postprocess_settings["skip_cases_when_testing"]
        )
    