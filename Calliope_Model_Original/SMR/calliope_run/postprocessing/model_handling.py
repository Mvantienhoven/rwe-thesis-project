
import pandas as pd
import os
import traceback
# from calliope_run.postprocessing.util import update_on_action, find_column, map_model_to_model
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

        
def merge_model_kpis(solved_models,merge_kpis):

    for merged_kpi in merge_kpis:
        
        target_kpi = merge_kpis[merged_kpi][0]
        source_kpis = merge_kpis[merged_kpi][1:]
        
        solved_models = map_model_kpis(solved_models,target_kpi,source_kpis,overwrite_name=merged_kpi)

    return solved_models

def map_model_kpis(solved_models,target_kpi,source_kpis,overwrite_name=None):
    
    #DONE MAP CARRIERS TO (STORAGE) TECHS
    
    # TODO:
    # Map lookup_loc_techs, split and keep carrier only
    # Then map 'inputs_lookup_loc_techs_conversion' and 'inputs_lookup_loc_techs_conversion_plus' and loop through carrier tiers, map out to `carrier`, map others to respective carrier tiers
    # Use same loop to expand columns for different cost types, but only if main dataframe has no cost types.
        
    for i,solved_model in enumerate(solved_models):
        
        # Make sure that target_kpi is in present in solved_models dict and that target_kpi is not part of source_kpis.
        if target_kpi not in solved_models[solved_model].keys() or target_kpi in source_kpis:
            # Push to the next `solved_model` in the for loop.
            continue
        
        # if (target_kpi in solved_models[solved_model].keys()) & (target_kpi not in source_kpis):
            
        # print (f"MAPPING CATEGORICAL DATA FOR KPI `{target_kpi}` FOR RUN `{solved_model}`")
        
        update_on_action('MAPPING',run=solved_model)
        
        # Load dataframe for current KPI.
        target_model = load_solved_model(solved_models[solved_model],target_kpi)
        
        # Check if the available_resource and resource_con dataframes is empty; if so, push to the next iteration in the for loop.
        # Temporarily do not map KPIs to timeseries data to reduce load.
        if target_model.empty:
            # Print warning.
            print (f"INPUT(S) NOT FOUND FOR RUN {solved_model}, NOT CORRELATION COEFFICIENTS.")
            
            # Push to the next `solved_model` in the for loop.
            continue
        
        # Find all keys with the string `case`.
        time_key = find_column(target_model, 'time')
        loc_key = find_column(target_model, 'loc')
        tech_key = find_column(target_model, 'tech')
        spores_key = find_column(target_model, 'spore')
            
        # case_key = find_column(solved_models[solved_model], 'case')
        
        # If case is specified, use if, otherwise use the solution/scenario/year tags.
        if 'case' in solved_models[solved_model].keys():
            target_model['case'] = solved_models[solved_model]['case']
        else:
            target_model['case'] = solved_model
        # except KeyError:
            
        # else:
        #     target_model['solutions'] = solved_models[solved_model]['solution']
        #     target_model['scenarios'] = solved_models[solved_model]['scenario']
        #     target_model['year'] = solved_models[solved_model]['year']                

        # Transmission technology names are always defined by a tech name and a location to which the tech leads, separated by a `:`, i.e. `cable:location:B`.
        # When mapping certain technology characteristics such as `names` and `colors`, only the tech name before the ":" should be used.
        # So we add a placeholder `temp_tech` which contains only the name of the techs, including those of transmission techs.
        
        # We only do this if we need to map purely technology related data, not when location definition is involved.
        if tech_key:
            # Check if `:` is found in tech definitions.
            if target_model[tech_key].str.contains(':').any():
                # Split the columns in two and use 
                target_model[['temp_tech', 'to_locs']] = target_model[tech_key].str.split(":",expand=True).fillna('')
                
                # target_model['to_locs'] = target_model['to_locs'].replace(0,'')
            
        # Now, find all keys with the string `to_loc` in case it was added above.
        to_loc_key = find_column(target_model, 'to_loc')
                            
        # Now we prepared the model dataframe onto which we would like to map our data.
        # So we loop through the list of KPIs that have been defined and need to be mapped onto our model.
        for source_kpi in source_kpis:
            
            # Make sure that target_kpi is in present in solved_models dict.
            if source_kpi not in solved_models[solved_model].keys():
                continue
            
            # Load in the dataframe of the KPI that is to be mapped to the target_model (e.g. `names` of techs, `colors` etc)
            # source_model = solved_models[solved_model][source_kpi]                        
            source_model = load_solved_model(solved_models[solved_model],source_kpi)
            
            # Sometimes, the KPI to be mapped has additional information in it, such as the KPI `lookup_loc_techs` which has loc::tech::kpi. 
            # This adds noise to the results, so we take out only the last (assuming that this is the valuable part, as is the case for `lookup_loc_techs`).
            # Note that this is not the same as we did previously, where we split by ":", the separator for transmission techs, e.g. loc::tech:to_loc.
            if calliope_postprocess_settings['load_kpis'][source_kpi] == str:
                split_values = True
            else:
                split_values = False
            
            if split_values and source_model[source_kpi].str.contains("::").any():
                
                # Split the columns.
                split_kpi = source_model[source_kpi].str.split("::",expand=True)
                
                # Find the key that corresponds with the last column, and overwrite the values in the original dataframe.
                source_model[source_kpi] = split_kpi[split_kpi.keys()[-1]]
            
            # Find the tech keys in the to-be-mapped dataframe.
            # source_tech_key = find_column(source_model, 'temp_tech')
            # if not source_tech_key:
            source_tech_key = find_column(source_model, 'tech')
            source_loc_key = find_column(source_model, 'loc')
            source_time_key = find_column(source_model, 'time')
            source_spores_key = find_column(source_model, 'spores')
            
            source_costs_key = find_column(source_model, 'costs')
            source_tiers_key = find_column(source_model, 'carrier_tiers')
            
            # source_carrier_key = find_column(source_model, 'carrier')
            
            # index_keys_target = []
            # index_keys_source = []
            
            # for key in ['tech','loc','time','spores','costs','carrier_tiers']:
                            
            #     # Do column checks
            #     key_target = find_column(target_model, key)
            #     key_source = find_column(source_model, key)
                
            #     # Add tech keys to index list if they exist. 
            #     # If any of the keys is present in the source dataframe, but not in the target, the mapping will produce ambiguous results, i.e. it will try to map multiple values to a single entry in the target dataframe, so the KPI should be skipped.
            #     if bool(key_target) and bool(key_source):
            #         index_keys_target += [key_target]
            #         index_keys_source += [key_source]
            #     elif not bool(key_target) and bool(key_source):
            #         continue
            
            # # Add additional loc key for end node locs of infrastructure.
            # if 'loc' in index_keys_target:
                
            #     # Create seprate one for coordinate mapping.
            #     loc_index_keys = [loc_key]
            #     loc_index_tags = ['']
                
            #     # Add additional loc key for end node locs of infrastructure.
            #     if to_loc_key:
            #         loc_index_keys += [to_loc_key]
            #         loc_index_tags += ['_end']
            
            # We only need to use the temp_tech key if the source data is purely tech related, like `names`.
            # Hence we need to repeat this step for every source model.
            # Determine whether we need to use the `tech` or `temp_tech` key.
            if 'temp_tech' in target_model.columns and source_tech_key and not source_loc_key:
                tech_key = 'temp_tech'
            # Make sure to set it back after `temp_tech` has become irrelevant.
            else:
                tech_key = find_column(target_model, 'tech')
            
            
            
            
            
            
            # Next we construct the mapping indices. This is based on overlap in indices between the two dataframes:
            # + If a key exists in both dataframes, use it for mapping;
            # = If a key exists only in the target dataframe, but not in the source dataframe, leave it as is;
            # = If a key exists only in neither of the two dataframes, leave it as is;
            # - If a key exists only in the SOURCE dataframe, but not in the TAGRET dataframe, the mapping will produce ambiguous results, i.e. it will try to map multiple values to a single entry in the target dataframe, so the KPI should be skipped.
            
            index_keys_target = []
            index_keys_source = []

            # Add TECH keys to index list if they exist. 
            # If any of the keys is present in the source dataframe, but not in the target, skip to next source_kpi.
            if bool(tech_key) and bool(source_tech_key):
                index_keys_target += [tech_key]
                index_keys_source += [source_tech_key]
            elif not bool(tech_key) and bool(source_tech_key):
                continue
                
            # Add LOC keys to index list if they exist.
            if bool(loc_key) and bool(source_loc_key):
                index_keys_target += [loc_key]
                index_keys_source += [source_loc_key]
                
                # Create seprate one for coordinate mapping.
                loc_index_keys = [loc_key]
                loc_index_tags = ['']
                
                # Add additional loc key for end node locs of infrastructure.
                if to_loc_key:
                    loc_index_keys += [to_loc_key]
                    loc_index_tags += ['_end']
            elif not bool(loc_key) and bool(source_loc_key):
                continue
            
            # Add TIME key to index if they exist. 
            if bool(time_key) and bool(source_time_key):
                index_keys_target += [time_key]
                index_keys_source += [source_time_key]
            elif not bool(time_key) and bool(source_time_key):
                continue

            # Add SPORES key to index if they exist. 
            if bool(spores_key) and bool(source_spores_key):
                index_keys_target += [spores_key]
                index_keys_source += [source_spores_key]
            elif not bool(spores_key) and bool(source_spores_key):
                continue
            
            expand_columns_for_keys = []
            
            # Expand column keys
            for key in ['costs','coordinates','carrier_tiers']:
                
                key_target = find_column(target_model, key)
                key_source = find_column(source_model, key)
                
            # Add key to index if they exist. 
                if bool(key_target) and bool(key_source):
                    index_keys_target += [key_target]
                    index_keys_source += [key_source]
                elif not bool(key_target) and bool(key_source):
                    expand_columns_for_keys += [key]
                        
            # Now check if there is any overlap in keys. If not, skip current source_kpi.
            if not index_keys_target or not index_keys_source:
                # print (f"{'':<5} No overlap in indices between `{target_kpi}` and `{source_kpi}`, jumping to next kpi.")
                
                update_on_action("WARNING",msg=f"No overlap in indices between `{target_kpi}` and `{source_kpi}`, jumping to next kpi.")
                continue
            else:
                update_on_action("MAPPING",kpi=source_kpi,msg=f"onto `{target_kpi}` with index keys {index_keys_target}")
                # print (f"{'':<5} Mapping KPI `{target_kpi}` onto `{source_kpi}` using index keys {index_keys_target}")
            
            check = False
            if 'coordinates' in source_kpi:
                check = True
                print ('check')
                
                
                

                
            # 
            if expand_columns_for_keys and check:
                target_model = target_model.set_index(index_keys_target).sort_index()
                source_model = source_model.set_index(index_keys_source).sort_index()
                
                for expand_key in expand_columns_for_keys:
                    
                    expand_list = source_model[expand_key].unique()
                    
                    for expand_col in expand_list:
                        
                        source_model_col = source_model[source_model[expand_key] == expand_col]
                        
                        key_temp = f'{expand_col}_coords{loc_index_tags[i]}'
                        
                        # Map force_resource to required_resource dataframe.
                        target_model = map_model_to_model(source_kpi,target_model,source_model_col).fillna('')
                        
                        # Merge the columns
                        if key_temp in target_model.columns:
                            target_model[key_temp] = target_model[[key_temp, source_kpi]].astype(str).agg(''.join,axis=1)
                        else:
                            target_model[key_temp] = target_model[source_kpi]
            
            
            # Now we start the mapping. First check if coordinates is in source kpi as we need to apply special indexing to the target model.
            if 'coordinates' in source_kpi:
                # target_model = target_model.reset_index()
                
                source_model = source_model.set_index(source_loc_key).sort_index()
                    
                for i,loc_index_key in enumerate(loc_index_keys):
                    target_model = target_model.set_index(loc_index_key).sort_index()
                    
                    for tier in ['lat','lon']:
                        
                        # Filter the map_to_solved_model for `lat` coordinates.
                        source_model_tier = source_model[source_model['coordinates'] == tier]
                        
                        key_temp = f'{tier}_coords{loc_index_tags[i]}'
                        
                            # Map force_resource to required_resource dataframe.
                        target_model = map_model_to_model(source_kpi,target_model,source_model_tier).fillna('')
                        
                        if key_temp in target_model.columns:
                            target_model[key_temp] = target_model[[key_temp, source_kpi]].astype(str).agg(''.join,axis=1)
                        else:
                            target_model[key_temp] = target_model[source_kpi]
                        
                        target_model = target_model.drop(source_kpi,axis=1)
                        
                    target_model = target_model.reset_index()
            else:
                        
                # Make sure to reset index of target model when finished with current source model.
                target_model = target_model.set_index(index_keys_target).sort_index()
                source_model = source_model.set_index(index_keys_source).sort_index()

                # Check if the KPI is a lookup dataframe for carriers.
                if 'lookup' in source_kpi:
                    
                    # Check if this contains conversions(_plus) technologies. If so, we need to select from different carrier tiers.
                    if 'conversion' in source_kpi:
                        
                        for tier in ['in','out']:
                            
                            # Filter dataframe before mapping and map per carrier tier.
                            source_model_tier = source_model[source_model['carrier_tiers'] == tier]
                            key_temp = 'carrier_' + tier
                            
                            # Map force_resource to required_resource dataframe.
                            target_model = map_model_to_model(source_kpi,target_model,source_model_tier).fillna('')
                            
                            if key_temp in target_model.columns:
                                target_model[key_temp] = target_model[[key_temp, source_kpi]].astype(str).agg(''.join,axis=1)

                            else:
                                
                                # Map force_resource to required_resource dataframe.
                                # Careful: newly created column name 'carrier_in' differs from KPI, hence the extra step the line below.
                                target_model[key_temp] = target_model[source_kpi]
                                
                            target_model = target_model.drop(source_kpi,axis=1)
                                

                    # Otherwise there is just one carrier definition, use it for both '_in' and '_out'.
                    else:
                        target_model = map_model_to_model(source_kpi,target_model,source_model)
                        if 'carrier_in' in target_model.columns:
                            target_model['carrier_in'] = target_model[[key_temp, source_kpi]].astype(str).agg(''.join,axis=1)
                            # target_model['carrier_in'] = target_model[['carrier_in', source_kpi]].sum(1)
                        else:
                            target_model['carrier_in'] = target_model[source_kpi]
                        target_model = target_model.drop(source_kpi,axis=1)
                        
                        target_model['carrier_out'] = target_model['carrier_in']                                                

                else:
                    # Apply normal mapping.
                    target_model = map_model_to_model(source_kpi,target_model,source_model).fillna(0)
                    
                target_model = target_model.reset_index()

        # Time for clean up.
        if 'inheritance' in target_model.columns:
            target_model[['asset_group','inheritance']] = target_model['inheritance'].str.split('.',expand=True)

        # Time for clean up.
        if 'to_loc' in target_model.columns:
            target_model['techs'] = target_model['techs'].str.split(':',n=1)
            
        if 'temp_tech' in target_model.columns:
            
            # Remove temporary tech column from target_model
            target_model = target_model.drop('temp_tech',axis=1)
        
        # Put the dataframe back into the solved_models dictionary. 
        if overwrite_name:
            # Add the dataframe under the new name.
            solved_models[solved_model][overwrite_name] = target_model
        else:
            # Oterwise use the original KPI name.
            solved_models[solved_model][target_kpi] = target_model
        
            
    return solved_models

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
