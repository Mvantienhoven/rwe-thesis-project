
import pandas as pd
import os
import traceback
from calliope_run.postprocessing.util import update_on_action, find_column #, map_model_to_model
# from calliope_run.calliope_settings import calliope_postprocess_settings

pd.options.mode.chained_assignment = None  # default='warn'



def load_solved_model(solved_model,key):
    """ 
    
    Check if key can be found in the solved_model key list, if so load the model, if not print warning and return an empty dataframe.
    
    """
    if key in solved_model.keys():
        return solved_model[key]
    else:
        print (f"WARNING, {key} not found when LOADING results.")
        
        return pd.DataFrame()

def get_model_csvs(folders,load_kpi_list=[],str_list=[],ignore_list=[],nrows=None):
    # This for loop is used to read each file from files, create a solved model for it, and append it to the previously declared list. It also assigns the attrs ['scenario'] == 'basecase' if not specified
    solved_models = {}
    timseries_kpis = set()
    load_kpi_list_exists = bool(load_kpi_list)
    ignore_kpi_list_exists = bool(ignore_list)
    for run in folders.keys():
        
        folder = folders[run]
        
        # Make new dictionary
        solved_model = {}
        
        # Get name of particular run from folder reference
        # run = folder.split("\\")[-1]
        # run = folder
        
        files = os.listdir(folder)
        
        files = [ filename for filename in files if filename.endswith( '.csv' ) ]
        
        for file in files:
            
            if ('input' in file) | ('result' in file):
                kpi = '_'.join(file.split('.')[0].split('_')[1:])
            else:
                kpi = file.split('.')[0]
            
            if kpi not in load_kpi_list or kpi in ignore_list:
                continue
             
            # print (f"{'LOADING':<15} {'kpi `' + kpi + '`':<40} for run `{run}`")
            
            update_on_action('LOADING',kpi,run)
            
            # Mark all columns as string type by default to prevent Python from applying very slow format searching algorithm.
            solved_model_kpi = pd.read_csv(folder+'\\'+file,dtype=str,keep_default_na=False,nrows=nrows)
            
            # if 'Unnamed: 0' in solved_model_kpi.columns:
                # print (kpi)
                # solved_model_kpi = solved_model_kpi.rename(columns={'Unnamed: 0':'carriers'})
                
            if 'Unnamed: 0' in solved_model_kpi.columns and kpi in ['systemwide_capacity_factor','systemwide_levelised_cost','total_levelised_cost']:
                solved_model_kpi = solved_model_kpi.rename(columns={'Unnamed: 0':'carriers'})
            
            # Data is loaded as string by default. Adjust KPI type as specified by user.
            solved_model_kpi[kpi] = solved_model_kpi[kpi].astype(load_kpi_list[kpi])
            
            # TODO Perform this check for all keys and replace key check later in code with lookups??
            # Check if there are any datetime columns in the dataframe, and if so convert these to datatime format.            
            time_key = find_column(solved_model_kpi, 'time')
            
            if time_key:                
                solved_model_kpi[time_key]= pd.to_datetime(solved_model_kpi[time_key])
                
                # Keep list of timeseries KPIs.
                timseries_kpis.add(kpi)
                
            # Often old nameless index columns are present in CSV files, remove these.
            if 'Unnamed: 0' in solved_model_kpi.columns:
                solved_model_kpi = solved_model_kpi.drop('Unnamed: 0',axis=1)
            
            # Add kpi to the model dictionary.
            solved_model[kpi] = solved_model_kpi  # new key, add
        
            
        solved_model['case'] = run
        solved_model['scenario'] = run
            
        solved_models[run] = solved_model
            
    return solved_models,timseries_kpis

# def map_model_to_model(map_kpi,model,key,map_model,map_key):

        

def aggregate_model_results(solved_models,kpi_list):
    aggregated_kpis = {}
    
    for kpi in kpi_list:

        for i,solved_model in enumerate(solved_models):
            
            print (f"AGGREGATING RESULTS FOR KPI `{kpi}` for RUN `{solved_model}`")
            
            if kpi not in solved_models[solved_model].keys():
                # i0 += 1
                aggregated_kpi = None
            else:
                solved_model_kpi = solved_models[solved_model][kpi]
                
                if i == 0:
                    # If initial loop, assign result as output 
                    aggregated_kpi = solved_model_kpi
                else:
                    # Else, use pd.concat to merge previous output with current solved_model_kpi 
                    aggregated_kpi = pd.concat([aggregated_kpi,solved_model_kpi])
        
        aggregated_kpis[kpi] = aggregated_kpi
        
    return aggregated_kpis

    
def print_aggregated_model(aggregated_outputs,kpi_list,targetdir,test=False,string=None):
    status=[]
    for kpi in kpi_list:
            
        try:  
            output = aggregated_outputs[kpi]
            # Print destination 
            print (f'WRITING to `{targetdir}/{kpi}.csv`')
            # Finally, export results to csv file    
            if test:
                output.to_csv(f'{targetdir}/test_{kpi}.csv')
            elif string:
                output.to_csv(f'{targetdir}/{kpi}_{string}.csv')
            else:
                output.to_csv(f'{targetdir}/{kpi}.csv')
        except Exception as e:
            status+=[f'For KPI {kpi} failed with exception {traceback.format_exc()}']
        else:
            status+=[f'For KPI {kpi} succesful']
    return status
