from calliope_run.postprocessing.util import update_on_action, find_column, map_model_to_model, load_solved_model
# from calliope_run.postprocessing.model_handling2 import load_solved_model
from calliope_run.calliope_settings import calliope_postprocess_settings

"""

List of defintions

KPI                             - Refers to the parameter names as used in Calliope and as printed to files (e.g. `names` or `energy_cap`), typically has a .csv belonging to it
Derived KPI                     - Names of parameters that are calculated in the postprocessing routine (e.g. `systemwide_levelized_cost`)

KPI (target)                    - In mapping, the dataframe to which new information is mapped.
KPI (source)                    - In mapping, the dataframe from which the information is sourced.

Keys                            - name of the column in a KPI dataframe. KPIs have multiple columns, such as `techs`, `locs` or `energy_cap`. Often a KPI dataframe has a column with the same name containing the KPI values.
Keys with unlimited dimension   - Keys that in principle can have large and potentially unlimited dimension, think of `loc` or `tech`, which is dependent on the user
Keys with limited dimension     - Keys that in principle have small dimensions, think of `cost` types or specification whether a coordinate refers to its`lon` or `lat` component.
Keys to repeat                  - In mapping, some information should be mapped not once but to multiple columns, e.g. location coordinates can be mapped the `locs` of technologies, but also to the `to_locs` of transmission technologies.

Index keys target               - List of keys found in the target model column list.
Index keys source               - List of keys found in the source model column list.
Index keys                      - List of intersecting keys between target and source model used as index of the models.

"""

def replace_value(replace_val,with_val,in_list):
    # Function to replace a value in a list with another value.
    return [with_val if x==replace_val else x for x in in_list]

def map_model_kpis(solved_models,target_kpi,source_kpis,overwrite_name=None):
        
    """
    This function maps values from a list of source models to a target model.
    The name of the target model is determined by the value of `target_kpi`. 
    The name(s) of the source model(s) is provided in the list of `source_kpis`.
    
    The output is the target_model with an additional column from each of the `source_kpi` model.
    The routine searches for overlapping index keys to be used. The user specifies for which keys to search below.
    
    
    For some KPIs, the source_kpi has higher dimensions than the target KPI, meaning the indices won't naturally overlap.
    If this is the case for a KPI of potentially unlimited dimension, the mapping does not take place.
    If this is the case for a KPI of finite dimension (such as different cost types), the routine adds an additional column for each dimension.
    
    Examples:
     - Coordinates has 2 dimensions (lon/lat)
     - Costs has n dimensions (monetary/spores_score/..)
     - Carrier tiers has 6 dimensions (carrier in 1/2/3, carriet out 1/2/3)
     
    The overwite_name parameter can be used to add the final output back into the solved_models dictionary under another name than the original target_kpi.0 
    
    """

    # Start with defining the keys for which to search in the columns of the target and source models.
    unlimited_dim_keys = ['timesteps', 'locs', 'techs', 'spores']
    # limited_dim_keys = ['costs','coordinates','carrier_tiers']
    limited_dim_keys = {
        # Name of the column key and whether to add the source_kpi to the new column name (False) or use a custom value (str).
        'costs': False,
        'coordinates': False,
        'carrier_tiers': 'carriers',
        }
    
    repeat_for_other_keys = {
        'coordinates': {
            # Define the key that is originally used in the mapping (one of values in `unlimited_dim_keys` or `limited_dim_keys`)
            'locs': 'start_', 
            
            # Define all keys for which the routine needs to be repeated (can be endless, as long as they exist in the `target_model` dataframe)
            'to_locs': 'end_',
            # 'X':'_X',
    },
        }
    
    # At the very end of the routine, the following dictionary will be used to merge a KPI into others.
    # This was too compelx to automate, so make sure the columns you insert below are present in the target_model at the end of the routine.
    merge_columns = {
        # Which KPI column to merge
        'lookup_loc_techs':
            # Into which other existing columns
            ['carriers - in','carriers - out']
                 }
    
    # Combine keys 
    all_dim_keys = unlimited_dim_keys + list(limited_dim_keys.keys())
    
    
    for key in repeat_for_other_keys:
        if key not in all_dim_keys:
            update_on_action('WARNING',msg=f"Key {key} was mentioned in dict `repeat_for_other_keys` but not anywhere else. Check your input in function `map_model_kpis()` in `model_mapping.py`")
    
    for i,solved_model in enumerate(solved_models):
        
        # Make sure that target_kpi is in present in solved_models dict and that target_kpi is not part of source_kpis.
        if target_kpi not in solved_models[solved_model].keys() or target_kpi in source_kpis:
            # Push to the next `solved_model` in the for loop.
            continue
        
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
        
        
        index_keys_target = []
        
        for key in all_dim_keys:
            column_key = find_column(target_model, key)
            
            if column_key:
                index_keys_target += [column_key]
        
        # If case is specified, use if, otherwise use the solution/scenario/year tags.
        if 'case' in solved_models[solved_model].keys():
            target_model['case'] = solved_models[solved_model]['case']
        else:
            target_model['case'] = solved_model

        # Transmission technology names are always defined by a tech name and a location to which the tech leads, separated by a `:`, i.e. `cable:location:B`.
        # When mapping certain technology characteristics such as `names` and `colors`, only the tech name before the ":" should be used.
        # So we add a placeholder `temp_tech` which contains only the name of the techs, including those of transmission techs.
        
        # We only do this if we need to map purely technology related data, not when location definition is involved.
        # if tech_key:
        if 'techs' in index_keys_target: 
            if target_model['techs'].str.contains(':').any():
                # Check if `:` is found in tech definitions.
                # if target_model[tech_key].str.contains(':').any():
                # Split the columns in two and use 
                target_model[['techs_short', 'to_locs']] = target_model['techs'].str.split(":",expand=True).fillna('')
                target_model = target_model.rename({'techs':'techs_long'},axis=1)
                    
        # Now we prepare the model dataframe onto which we would like to map our data.
        # So we loop through the list of KPIs that have been defined and need to be mapped onto our model.
        for source_kpi in source_kpis:

            if source_kpi == 'inheritance':
                print ()
                pass
            
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
            
            # We only need to use the temp_tech key if the source data is purely tech related, like `names`.
            # Hence we need to repeat this step for every source model.
            # Determine whether we need to use the `tech` or `temp_tech` key.
            if 'techs_short' in target_model.columns and 'techs' in source_model.columns and not 'locs' in source_model.columns:
                
                # index_keys_target = replace_value('techs','techs_short',index_keys_target)
                if not 'techs_long' in target_model.columns:
                    target_model = target_model.rename({'techs':'techs_long'},axis=1)
                    
                target_model = target_model.rename({'techs_short':'techs'},axis=1)
                
            # Make sure to set it back after `temp_tech` has become irrelevant.
            else:
                if not 'techs_short' in target_model.columns:
                    target_model = target_model.rename({'techs':'techs_short'},axis=1)
                    
                target_model = target_model.rename({'techs_long':'techs'},axis=1)
            
            # Find the tech keys in the to-be-mapped dataframe. We need to do this for every source dataframe.
            index_keys_source = []
            
            for key in all_dim_keys:
                column_key = find_column(source_model, key)
                
                if column_key:
                    index_keys_source += [column_key]
            
            # Next we construct the mapping indices. This is based on overlap in indices between the two dataframes:
            # + If a key exists in both dataframes, use it for mapping;
            # = If a key exists only in the target dataframe, but not in the source dataframe, leave it as is;
            # = If a key exists only in neither of the two dataframes, leave it as is;
            # - If a key exists only in the SOURCE dataframe, but not in the TAGRET dataframe, the mapping will produce ambiguous results, i.e. it will try to map multiple values to a single entry in the target dataframe, so the KPI should be skipped.
            
            # Now find the intersection between the two index lists.
            # index_keys = list(set(index_keys_target) & set(index_keys_source))
            index_keys = []
            
            for key in unlimited_dim_keys:
            # for key in source_model.columns:
                if key in index_keys_target and key in index_keys_source:
                    index_keys += [key]
                elif key not in index_keys_target and key in index_keys_source:
                    update_on_action("WARNING",kpi=key,msg=f"Mismatch in indices between `{target_kpi}` and `{source_kpi}`, jumping to next kpi.")
                    # Move on to the next source KPI
                    continue
            
            # For the next columns though, we'd like to expand the dimension of the KPI into columns rather than skipping the whole mapping.
            expand_columns_for_keys = []
            
            for key in limited_dim_keys:
                if key in index_keys_target and key in index_keys_source:
                    index_keys += [key]
                elif key not in index_keys_target and key in index_keys_source:
                    expand_columns_for_keys += [key]
                        
            # Now check if there is any overlap in keys. If not, skip current source_kpi.
            if not index_keys:                
                update_on_action("WARNING",msg=f"No overlap in indices between `{target_kpi}` and `{source_kpi}`, jumping to next kpi.")
                continue
            else:
                update_on_action("MAPPING",kpi=source_kpi,msg=f"onto `{target_kpi}` with index keys {index_keys_target}")

            
            # For loop 1. Do we need to expand columns in the TARGET dataframe to deal with additional dimensions? Think of coordinate mapping with `lon` and `lat` dimensions.
            # For loop 2. Do we need to repeat the routine for different columns in the SOURCE dataframe? Think of coordinate mapping for both `loc` and `to_loc` for transmission technologies.
            
            # Mapping is to take place with existing 
            if not expand_columns_for_keys and source_kpi not in repeat_for_other_keys:
                # Make sure to reset index of target model when finished with current source model.
                target_model = target_model.set_index(index_keys).sort_index()
                source_model = source_model.set_index(index_keys).sort_index()
                
                target_model = map_model_to_model(source_kpi,target_model,source_model).reset_index()
                
                if calliope_postprocess_settings['load_kpis'][source_kpi] == str:
                    target_model[source_kpi] = target_model[source_kpi].fillna('')
                
                
                # target_model = target_model.rename({source_kpi:new_column_name},axis=1)
                            
            else:
                # We start up a loop to go through the items for which the columns need to be expended (typically just 1).
                # For example, `coordinates` has a lon and lat dimension.
                for key in expand_columns_for_keys:
                    
                    # We first find a list with unique values in the column.
                    expand_column_by_dimensions = source_model[key].unique()
                    
                    # Then we loop through the list and map the source data onto the target data for each subset.
                    for dim in expand_column_by_dimensions:
                        
                        # First, we take a subset of the source model, change its index and then map it in the conventional way.
                        source_model_subset = source_model[source_model[key] == dim]
                        source_model_subset = source_model_subset.set_index(index_keys).sort_index()
                        
                        # TODO Set index here? Or before first if statement?
                        target_model = target_model.set_index(index_keys).sort_index()
                        
                        # Map subset tot target model.
                        target_model = map_model_to_model(source_kpi,target_model,source_model_subset).reset_index()
                        
                        if calliope_postprocess_settings['load_kpis'][source_kpi] == str:
                            target_model[source_kpi] = target_model[source_kpi].fillna('')
                            
                        # The mapping routine automatically takes the name of the `source_kpi`, but we will repeat this step for each dimension of the source_kpi column, so we need to change the name.
                        # The `limited_dim_keys` dict should contain a boolean to indicate whether we want to add the `source_kpi` to the column name.
                        if limited_dim_keys[key]:
                            # If existing, we use the custom value provided by the user.
                            new_column_name = f'{limited_dim_keys[key]} - {dim}'
                        else:
                            # Otherwise we  use the `source_kpi`.
                            new_column_name = f'{source_kpi} - {dim}'
                        
                        # Change the name of the column; if the 'new' name already exist, make sure to merge the existing with the new column.
                        if new_column_name in target_model.columns:
                            # We use an aggregate function, assuming that there is no overlap between the newly mapped data and the data in the original column, i.e. cells that have a value in one column are empty in the other.
                            target_model[new_column_name] = target_model[[new_column_name, source_kpi]].astype(str).agg(''.join,axis=1)
                            
                            # Drop the original column.
                            target_model = target_model.drop(source_kpi,axis=1)
                        
                        # Otherwise just go ahead and rename it.
                        else:
                            target_model = target_model.rename({source_kpi:new_column_name},axis=1)
                        
                        # Now we finished the basic mapping for this particular dimension of the source_kpi, let's see if we need to repear this step for other column in the target dataframe that contain the same type of data.
                        if key not in repeat_for_other_keys:
                            continue
                        
                        # Store the original column key (like `loc`)
                        original_key = list(repeat_for_other_keys[key].keys())[0]
                        
                        # Then loop through the dictionary `repeat_for_other_keys` that describes for which source_kpi (e.g. `coordinates`) the routine needs to be repeated (e.g. for `loc` as well as `to_loc`).
                        for other_key in repeat_for_other_keys[key]:
                            
                            if other_key not in target_model.columns:
                                update_on_action("WARNING",msg=f"Tried to repeat mapping for key `{other_key}` but could not be found as a column of `target_model`.")
                                continue
                            
                            # Retrieve the substring that should be added to the column to distinguish between the different mappings of the same source_kpi (e.g. `loc` and `to_loc` for the same source_kpi `coordinates`).
                            substring = repeat_for_other_keys[key][other_key]
                            new_column_name_w_substring = substring + new_column_name
                            # # We've already mapped the first, just change the column name.
                            if other_key == original_key:
                                
                                target_model = target_model.rename({new_column_name:new_column_name_w_substring},axis=1)
                                
                            else:
                                
                                # We replace the original key with the other key in the index.
                                # Use temporary index to prevent issues later on.
                                other_index_keys = replace_value(original_key,other_key,index_keys)
                                
                                # We set the index of the target model.
                                target_model = target_model.set_index(other_index_keys).sort_index()
                                
                                # We apply the mapping.
                                target_model = map_model_to_model(source_kpi,target_model,source_model_subset).reset_index()
                                
                                if calliope_postprocess_settings['load_kpis'][source_kpi] == str:
                                    target_model[source_kpi] = target_model[source_kpi].fillna('')

                                # Now change the column name.
                                target_model = target_model.rename({source_kpi:new_column_name_w_substring},axis=1)

        # Time for clean up.
        if 'inheritance' in target_model.columns:
            target_model[['asset_group','inheritance']] = target_model['inheritance'].str.split('.',expand=True)

        if 'to_loc' in target_model.columns:
            target_model['techs'] = target_model['techs'].str.split(':',n=1)
            
        if 'techs_short' in target_model.columns:
            
            # Remove temporary tech column from target_model
            # The functionality of this column is covered by KPI `names`.
            target_model = target_model.drop('techs_short',axis=1)
        
        # Perform column merging if set up by user.
        # Make sure dictionary is not empty.
        if merge_columns:
            update_on_action("MERGING",msg=f"Dictionary `merge_columns` found.")
            # Loop through dictionary 
            for source_column in merge_columns:
                if source_column not in target_model.columns:
                    continue
                    
                for target_column in merge_columns[source_column]:
                    if target_column not in target_model.columns:
                        continue
                    
                    update_on_action("MERGING",kpi=source_column,msg=f"onto `{target_column}` for mapped targer KPI `{target_kpi}`")
                    target_model[target_column] = target_model[[target_column, source_column]].astype(str).agg(''.join,axis=1)
                
                # Remove source column from target_model
                target_model = target_model.drop(source_column,axis=1)
        else:
            update_on_action("MERGING",msg=f"Dictionary `merge_columns` is empty, not merging any columns after mapping.")
                
        # Finally sort columns alphabetically.
        target_model = target_model.reindex(sorted(target_model.columns), axis=1)
        
        # Put the dataframe back into the solved_models dictionary. 
        if overwrite_name:
            # Add the dataframe under the new name.
            solved_models[solved_model][overwrite_name] = target_model
        else:
            # Oterwise use the original KPI name.
            solved_models[solved_model][target_kpi] = target_model
            
        
            
    return solved_models