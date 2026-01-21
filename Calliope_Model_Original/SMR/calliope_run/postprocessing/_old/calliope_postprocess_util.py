
import os

import pandas as pd

import numpy as np
import traceback

# from run_calliope_manual_constraint_dicts import load_constraint_dicts


from calliope_run.running._old.calliope_settings import calliope_postprocess_settings

pd.options.mode.chained_assignment = None  # default='warn'

def update_on_action(action,kpi=None,run=None, msg=None):
    
    print_str = f"{action:<15}"
    
    if kpi:
        print_str += f"{'kpi `' + kpi + '`':<40}"
        
    if run:
        print_str += f"{'for run `' + run + '` '}"
        
    if msg:
        print_str += f"with msg: {msg}"
        
    print (print_str)
    # print (f"{action:<15} {'kpi ' + kpi:<40} for run `{run}`")
    
def find_column(df, str):

    cols = [c for c in df.columns if str in c]
    
    if cols:
        col = cols[0]
    else:
        col = None
    return col
            
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
    

def add_levelized_cost(solved_models):
    """
        Calculate LCOE of all technologies. Calliope has the tendency to ignore transmission technologies.
    
    """
    
    for solved_model in solved_models:
    
        # Inform user.
        # print (f"CALCULATING `loctech_lcoe` and `systemwide_lcoe` for run `{solved_model}`")
        # print (f"{'CALCULATING':<15} {'kpi `loctech_levelized_cost` and `systemwide_levelized_cost`':<80} for run `{solved_model}`")
        
        update_on_action('CALCULATING','loctech_levelized_cost',solved_model)
        update_on_action('CALCULATING','systemwide_levelized_cost',solved_model)
        
        # The resource dataframe is the basis of determining the available resource.
        # Load `resource` dataframe.
        cost = load_solved_model(solved_models[solved_model],'cost')
        carrier_prod = load_solved_model(solved_models[solved_model],'carrier_prod')
        
        # Check if the resource dataframe is empty; if so, push to the next iteration in the for loop.
        if cost.empty or carrier_prod.empty:
            print (f"WARNING, inputs not found for run {solved_model}, NOT CALCULATING lcoe.")
            continue
        
        systemwide_key_list = ['techs']
        spores_key_1 = find_column(cost, 'spore')
        spores_key_2 = find_column(carrier_prod, 'spore')
        
        if spores_key_1 and spores_key_2:
            systemwide_key_list += ['spores']
        
        loctech_key_list = systemwide_key_list + ['locs']
                
        # Set indices. carrier_prod requires a groupby to sum over the carrier and timestep dimensions.
        systemwide_cost = cost.groupby(systemwide_key_list+['costs']).sum().reset_index().set_index(systemwide_key_list)
        systemwide_prod = carrier_prod.groupby(systemwide_key_list).sum()
        
        loctech_cost = cost.set_index(loctech_key_list)
        loctech_prod = carrier_prod.groupby(loctech_key_list).sum()
        
        # Get a list with unique cost indicators. 
        cost_list = cost.costs.unique()
        
        # Consider cost types one by one, so loop through all unique cost types mentioned in the `costs` column. 
        # We will build a new dataframe from the frames per cost type.
        # Create a container to hold the calculated avoided cost dataframes.
        loctech_lcoes = []
        systemwide_lcoes = []
        # .reset_index().rename(columns={0:'powerdistance'})
        # Loop trhough all unique cost types and calculate lcoe per cost type.
        for cost_type in cost_list:
        
            # First we will calculate the LCOE of location-specific technologies.
            # Filter the specific cost_type.
            locspecific_type_cost = loctech_cost[loctech_cost['costs'] == cost_type]
            
            # The values are accessed by calling the column `.cost` and `.carrier_prod`.
            loctech_lcoe = locspecific_type_cost.cost/loctech_prod.carrier_prod
            loctech_lcoe = loctech_lcoe.reset_index().rename(columns={0:'loctech_levelized_cost'})
            loctech_lcoe['costs'] = cost_type
            
            # Now we will do the same for the systemwide costs, i.e. summed over all locations.
            # Filter the specific cost_type.
            systemwide_type_cost = systemwide_cost[systemwide_cost['costs'] == cost_type]
            
            # The values are accessed by calling the column `.cost` and `.carrier_prod`.
            systemwide_lcoe = systemwide_type_cost.cost/systemwide_prod.carrier_prod
            systemwide_lcoe = systemwide_lcoe.reset_index().rename(columns={0:'systemwide_levelized_cost'})
            systemwide_lcoe['costs'] = cost_type
            
            loctech_lcoes += [loctech_lcoe]
            systemwide_lcoes += [systemwide_lcoe]
            
        solved_models[solved_model]['loctech_levelized_cost'] = pd.concat(loctech_lcoes)
        solved_models[solved_model]['systemwide_levelized_cost'] = pd.concat(systemwide_lcoes)
        
    return solved_models
            
        # carrier_prod = carrier_prod.set_index(['locs', 'techs'])
    

def add_capacity_factor(solved_models):
    """
        Calculate Capacity factors of all technologies. Calliope has the tendency to ignore transmission technologies.
        
        Assumes that energy  is in units of Wh of any scale (kilo, mega, giga etc)
    
    """
    
    for solved_model in solved_models:
    
        # Inform user.
        # print (f"CALCULATING `loctech_cf` and `systemwide_cf` for run `{solved_model}`")
        # print (f"{'CALCULATING':<15} {'kpi `loctech_capacity_factor` and `systemwide_capacity_factor`':<80} for run `{solved_model}`")
        
        update_on_action('CALCULATING','loctech_capacity_factor',solved_model)
        update_on_action('CALCULATING','systemwide_capacity_factor',solved_model)
        
        # The resource dataframe is the basis of determining the available resource.
        # Load `resource` dataframe.
        energy_cap = load_solved_model(solved_models[solved_model],'energy_cap')
        carrier_prod = load_solved_model(solved_models[solved_model],'carrier_prod')
        
        # Check if the resource dataframe is empty; if so, push to the next iteration in the for loop.
        if energy_cap.empty or carrier_prod.empty:
            print (f"WARNING, inputs not found for run {solved_model}, NOT CALCULATING lcoe.")
            continue
        
        systemwide_key_list = ['techs']
        spores_key_1 = find_column(energy_cap, 'spore')
        spores_key_2 = find_column(carrier_prod, 'spore')
        
        if spores_key_1 and spores_key_2:
            systemwide_key_list += ['spores']
        
        loctech_key_list = systemwide_key_list + ['locs']
            
        # Set indices. carrier_prod requires a groupby to sum over the carrier and timestep dimensions.
        systemwide_cap = energy_cap.groupby(systemwide_key_list).sum().reset_index().set_index(systemwide_key_list)
        systemwide_prod = carrier_prod.groupby(systemwide_key_list).sum()
        
        loctech_cap = energy_cap.set_index(loctech_key_list)
        loctech_prod = carrier_prod.groupby(loctech_key_list).sum()
                
        # .reset_index().rename(columns={0:'powerdistance'})
        # Loop trhough all unique cost types and calculate lcoe per cost type.
        
        # First we will calculate the LCOE of location-specific technologies.
        # Filter the specific cost_type.
        # locspecific_type_cost = locspecific_cost[locspecific_cost['costs'] == cost_type]
        
        hours_per_year = 8760
        
        # The values are accessed by calling the column `.cost` and `.carrier_prod`.
        loctech_capfactor = loctech_prod.carrier_prod/loctech_cap.energy_cap/hours_per_year
        loctech_capfactor = loctech_capfactor.reset_index().rename(columns={0:'loctech_capacity_factor'})
        
        # Now we will do the same for the systemwide costs, i.e. summed over all locations.
        # Filter the specific cost_type.
        # systemwide_type_cost = systemwide_cost[systemwide_cost['costs'] == cost_type]
        
        # The values are accessed by calling the column `.cost` and `.carrier_prod`.
        systemwide_capfactor = systemwide_prod.carrier_prod/systemwide_cap.energy_cap/hours_per_year
        systemwide_capfactor = systemwide_capfactor.reset_index().rename(columns={0:'systemwide_capacity_factor'})
                    
        solved_models[solved_model]['loctech_capacity_factor'] = loctech_capfactor
        solved_models[solved_model]['systemwide_capacity_factor'] = systemwide_capfactor
        
    return solved_models

def add_transmission_powerdistance(solved_models):
    """
    While installed capacities of typical assets can be fairly easily compared between cases, this is more difficult for infrastructure.
    Infrastructure spans a distance, and a unit of energy can flow through several cables with a particular power capacity.
    For example, a 1MW cable with a length of 1km would show up as 1MW, while two 1MW cables of both 500m would show up as 2MW.
    They have the same power-distance though, namely 1MW-km.
    To compare infrastructure properly, one can integrate the capacity of cables, pipes etc over its distance, providing a value for MW-km.
    """
    
    for solved_model in solved_models:
    
        # Inform user.
        # print (f"CALCULATING `powerdistance` for run `{solved_model}`")
        print (f"{'CALCULATING':<15} {'kpi `powerdistance`':<40} for run `{solved_model}`")
        
        # The resource dataframe is the basis of determining the available resource.
        # Load `resource` dataframe.
        energy_cap = load_solved_model(solved_models[solved_model],'energy_cap')
        distance = load_solved_model(solved_models[solved_model],'distance')
        
        energy_cap = energy_cap.set_index(['locs','techs']).astype(float)
        distance = distance.set_index(['locs','techs']).astype(float)
        
        powerdistance = (distance.distance*energy_cap.energy_cap).dropna().reset_index().rename(columns={0:'powerdistance'})
    
        solved_models[solved_model]['powerdistance'] = powerdistance
    
    return solved_models

# def add_units_invested(solved_models):
#     """

#     """
    
    
#     for solved_model in solved_models:
        
#         if ('2030' in solved_model) | ('2050' in solved_model):
#             # Load in the dictionaries containing relevant data for defining the manual constraints.
#             (
#                 object_dict, 
#                 asset_loc_dict, 
#                 asset_tech_dict, 
#                 asset_cap_dict,
#                 storage_tech_dict, 
#                 charger_tech_dict, 
#                 charger_cap_dict,
#                 charge_to_discharge_ratio_dict,
#                 charger_carrier_dict,
#                 ) = load_constraint_dicts(solved_model)
        
#             # Inform user.
#             print (f"CALCULATING NUMBER OF UNITS FOR RUN `{solved_model}`")
            
#             # The resource dataframe is the basis of determining the available resource.
#             # Load `resource` dataframe.
#             energy_cap = load_solved_model(solved_models[solved_model],'energy_cap')
            
#             energy_cap = energy_cap.set_index(['techs','locs']) # .astype(float)
            
#             energy_cap['units'] = 'nan'
            
#             for object in object_dict:
#                 for asset_loc in asset_loc_dict[object]:
                
#                     asset_tech = asset_tech_dict[asset_loc]
#                     asset_cap = asset_cap_dict[asset_loc]
#                     storage_tech = storage_tech_dict[asset_loc]
#                     charge_to_discharge_ratio = charge_to_discharge_ratio_dict[asset_loc]
#                     charger_tech = charger_tech_dict[object]
#                     charger_cap = charger_cap_dict[object]
#                     charger_carrier = charger_carrier_dict[object]
                    
#                     energy_cap['units'].loc[asset_tech,asset_loc] = asset_cap
            
#             # charger_cap = pd.DataFrame.from_dict(charger_cap_dict, orient='index')
#             # asset_cap = pd.DataFrame.from_dict(asset_cap_dict, orient='index')
            
            
            
        
#             solved_models[solved_model]['powerdistance'] = units_invested
    
#     return solved_models

    
def add_available_resource(solved_models,include_techs,exclude_techs=False):
    """
    This function calculates the resource available to renewable supply technologies.
    The user specifies a list of supply techs identifiers, like `wind` or `solar`.
    The routine will look for technology definitions with these identifiers and derive the available resource based on the resource, resource_unit, resource_scale and resource_area.
    The available resource is calculated in an identical way as done in the Calliope model.
    The results can be used to calculate e.g. curtailment, residual loads etc.
    """
        
        
    for solved_model in solved_models:
        # Inform user.
        update_on_action('CALCULATING',kpi='available_resource',run=solved_model)
        # print (f"CALCULATING `available_resource` for run `{solved_model}`")
        # print (f"{'CALCULATING':<15} {'kpi `available_resource`':<40} for run `{solved_model}`")
        # The resource dataframe is the basis of determining the available resource.
        # Load `resource` dataframe.
        resource = load_solved_model(solved_models[solved_model],'resource')
        energy_cap = load_solved_model(solved_models[solved_model],'energy_cap')
        
        # Check if the resource dataframe is empty; if so, push to the next iteration in the for loop.
        if resource.empty:
            print (f"inputs not found for {solved_model}, NOT CALCULATING `available_resource`.")
            continue
        
        # Find definitions of locs and techs keys in dataframe.
        tech_key = find_column(resource, 'tech')
        loc_key = find_column(resource, 'loc')
        
        index_keys = [tech_key,loc_key]
        
        if not all(index_keys):
            print (f"..NOT FOUND FOR RUN {solved_model},.")
            continue
            
        
        # Get keys of all supply techs in tech column that add to the residual load.
        if include_techs:
            include_tech_keys = [c for t in include_techs for c in np.unique(resource[tech_key].values) if (t in c) & (":" not in c)]
        if exclude_techs:
            include_tech_keys = [c for c in include_tech_keys if c not in exclude_techs]
            
        if not include_tech_keys:
            # Otherwise assign an empty value and proceed with the routine.
            print (f'NO RELEVANT TECHS FOUND AFTER APPLYING `include_techs` AND `exclude_techs` FOR RUN {solved_model}, MOVING ON.')
            continue
        
        # Filter technologies based on list.
        available_resource = resource[resource[tech_key].isin(include_tech_keys)]
        
        # Set index of dataframe with keys.
        available_resource = available_resource.set_index(index_keys).sort_index()

        # Map unit, scale, area and energy_cap for each loc,tech combination
        for kpi in ['resource_unit','resource_scale','resource_area','force_resource']:
            
            # Make sure KPI is in dict keys, else create column with None values.
            if kpi in solved_models[solved_model].keys():
                
                # Load model
                source_model = solved_models[solved_model][kpi]
                
                # Find definitions of locs and techs keys in dataframe.
                source_tech_key = find_column(source_model, 'tech')
                source_loc_key = find_column(source_model, 'loc')
                source_index_keys = [source_tech_key,source_loc_key]
                
                # Filter out irrelevant technologies.
                source_model = source_model[source_model[source_tech_key].isin(include_tech_keys)]
                # Create multi index of dataframe.
                source_model = source_model.set_index(source_index_keys).sort_index()
                # Finally map the KPI.
                available_resource = map_model_to_model(kpi,available_resource,source_model).fillna(0)

            else:
                # If KPI is not present, create column with None values. These are later filled with correct standard values.
                available_resource[kpi] = None
                
            # Check if any entries need to be filled so thio.
            fillna = available_resource[kpi].isna().any()
            
            if fillna:
                # print (f"Mapped entries missing for {kpi}, filling NA.")
                # print (f"{'':<5} {'WARNING:':<15} (some) entries missing for {kpi} after mapping, filling NA.")
                update_on_action('WARNING',kpi=kpi,msg='(some) entries missing after mapping, filling NA.')
                
            if kpi == 'resource_unit':
                available_resource[kpi] = available_resource[kpi].fillna('energy')
            if kpi == 'resource_scale':
                available_resource[kpi] = available_resource[kpi].fillna(1.0)
                available_resource[kpi] = available_resource[kpi].astype(float)
            if kpi == 'resource_area':
                available_resource[kpi] = available_resource[kpi].fillna(0)
                available_resource[kpi] = available_resource[kpi].astype(float)
            if kpi == 'force_resource':
                available_resource[kpi] = available_resource[kpi].fillna(True)
                available_resource[kpi] = available_resource[kpi] == '1.0'
            
        # Now we add the energy_cap results.
        # Find definitions of locs and techs keys in dataframe.
        source_tech_key = find_column(energy_cap, 'tech')
        source_loc_key = find_column(energy_cap, 'loc')                
        source_index_keys = [source_tech_key,source_loc_key]
        
        if not all(source_index_keys):
            print (f"..NOT FOUND FOR RUN {solved_model},.")
            
            # Push to the next `solved_model` in the for loop.
            continue
        
        # Filter out all irrelevant techs.
        energy_cap = energy_cap[energy_cap[source_tech_key].isin(include_tech_keys)]
        
        # Check if a spores key exists.
        source_spores_key = find_column(energy_cap, 'spores')
        
        # As input parameter, the KPI `resource` won't contain any SPORES dimension, so we must add it.
        if source_spores_key:
            
            # Get list with spores numbers.
            spores_no = energy_cap[source_spores_key].unique()
            # Fill dataframe with list of spores numbers.
            available_resource[source_spores_key] = [spores_no]*len(available_resource)
            # Now expand whole database with spores numbers.
            available_resource = available_resource.explode(source_spores_key)
            
            index_keys += [source_spores_key]
            source_index_keys += [source_spores_key]

        # Reset index so we can set it later again.
        available_resource = available_resource.reset_index()
        # Create multi index of dataframe.
        energy_cap = energy_cap.set_index(source_index_keys).sort_index()
        available_resource = available_resource.set_index(index_keys).sort_index()
        # Finally map the KPI.
        available_resource = map_model_to_model('energy_cap',available_resource,energy_cap).fillna(0)            
        # Then we must map the energy_cap values to the ..
        
        # Now we have all relevant information in the same dataframe, we can use it to calculate the available resource.
        # print ('Calculating available resource')
        # Use 'apply' to calculate available resource
        available_resource['available_resource'] = available_resource.apply(lambda row: row.resource*row.resource_scale*row.resource_area if row.resource_unit == 'energy_per_area' else (row.resource*row.resource_scale*row.energy_cap if row.resource_unit == 'energy_per_cap' else row.resource*row.resource_scale),axis=1)
            
        # # Remove original data column.
        # available_resource = available_resource.drop('resource',axis=1)
        
        # Add to solved_models
        solved_models[solved_model]['available_resource'] = available_resource.reset_index()
            
        
    return solved_models

def add_curtailment(solved_models):
    """
    Curtailment is defined as the amount of energy that was available to the technology as resource, but was not used.
    What is used is a model output (for techs with force_resource=False), so it must be calculated in postprocessing step.
    
    """
    for solved_model in solved_models:
        # print (f"CALCULATING CURTAILED LOADS FOR RUN `{solved_model}`")
        
        update_on_action('CALCULATING',kpi='curtailed_resource',run=solved_model)
        
        # Load dataframes with available resource and consumed resource.
        available_resource = load_solved_model(solved_models[solved_model],'available_resource')
        carrier_prod = load_solved_model(solved_models[solved_model],'carrier_prod')
        
        # Check if the available_resource and resource_con dataframes is empty; if so, push to the next iteration in the for loop.
        if available_resource.empty or carrier_prod.empty:
            print (f"INPUT(S) NOT FOUND FOR RUN {solved_model}, NOT CALCULATING CURTAILMENT.")
            
            # Push to the next `solved_model` in the for loop.
            continue

        # Find definitions of locs and techs keys in dataframe.
        tech_key = find_column(available_resource, 'tech')
        loc_key = find_column(available_resource, 'loc')
        time_key = find_column(available_resource, 'time')
        
        index_keys = [tech_key,loc_key,time_key]
        
        if all(index_keys):
            
            spores_key = find_column(available_resource, 'spores')
            
            if spores_key:
                index_keys += [spores_key]
                
            # Set correct indices.
            available_resource = available_resource.set_index(index_keys).sort_index()
            carrier_prod = carrier_prod.set_index(index_keys).sort_index()
            
            # Create a copy dataframe for new KPI curtailed_resource.
            curtailed_resource = pd.DataFrame()
            
            # Calculate curtailed resource as difference between available and consumed resource. 
            # Values of `resource_con` are defined positive.
            curtailed_resource['curtailed_resource'] = available_resource['available_resource'].sub(carrier_prod['carrier_prod'])
            
            # Clean up dataframe by removing NaN, original available_resource column and by resetting the index. 
            curtailed_resource = curtailed_resource.dropna().reset_index() # .drop('available_resource',axis=1)
        
            # Add new KPI to solved_models dictionary.
            solved_models[solved_model]['curtailed_resource'] = curtailed_resource
            
        else:
            print ("WARNING NO LOC OR TECH COLUMN FOUND IN RESOURCE, CHECK FILES")
            continue
        
    return solved_models
        
def add_residual_load(solved_models):
    """
    The residual load is defined as the sum of all resource available to renewable technologies minus
    This method assumes all supply/demand technologies under consideration to have an efficiency of 100%!
    """
    #DONE CALCULATE CURTAILMENT USING `RESOURCE_UNIT` AND `RESOURCE`
    #DONE USE CURTAILMENT TO CALCULATE ACCURATE RESIDUALS
    #TODO CALCULATE CO2 ABATEMENT COST USING basecase AS REFERENCE
    
    
    for i,solved_model in enumerate(solved_models):
        # print (f"CALCULATING RESIDUAL LOADS FOR RUN `{solved_model}`")
        update_on_action('CALCULATING','residual_load',solved_model)
        update_on_action('CALCULATING','system_imbalance',solved_model)
        
        # Residual load 
        # Load the dataframes of 
        available_resource = load_solved_model(solved_models[solved_model],'available_resource')
        required_resource = load_solved_model(solved_models[solved_model],'required_resource')
        
        force_resource = load_solved_model(solved_models[solved_model],'force_resource')
        
        # Mark force_resource as boolean.
        force_resource['force_resource'] = force_resource['force_resource'] == '1.0'
        
        # Check if the available_resource and resource_con dataframes is empty; if so, push to the next iteration in the for loop.
        if available_resource.empty or required_resource.empty:
            print (f"INPUT(S) NOT FOUND FOR RUN {solved_model}, NOT CALCULATING CURTAILMENT.")
            
            # Push to the next `solved_model` in the for loop.
            continue
        
        carriers = load_solved_model(solved_models[solved_model],'lookup_loc_techs')
        
        # This method only works for supply/demand technologies where in/out carrier is the same. 
        # For conversion technologies, carriers are logged in `inputs_lookup_primary_loc_tech_carriers_in`.
        # `lookup_loc_techs` consists of three parts: the loc, the tech and the carrier. Extract the carrier.
        carriers['carriers'] = carriers['lookup_loc_techs'].str.split("::", expand=True)[2]
        
        # The required_resource contains the resource data that is required by demand technologies.
        # This dataframe makes no distinction between must run and optional demand technologies.
        # To calculate the residual load, we only need the must run technologies, so we must filter using the force_resource. 
        # Identify the mapping tech keys.
        
        # Prepare for mapping
        # Find definitions of locs and techs keys in dataframe.
        tech_key = find_column(required_resource, 'tech')
        loc_key = find_column(required_resource, 'loc')
        
        index_keys = [tech_key, loc_key]
        
        # Only proceed with both tech and loc keys were found.
        if not all(index_keys):
            print ("WARNING NO LOC OR TECH COLUMN FOUND IN RESOURCE, CHECK FILES")
            continue 
        
        # Find definitions of locs and techs keys in dataframe.
        source_tech_key = find_column(force_resource, 'tech')
        source_loc_key = find_column(force_resource, 'loc')

        source_index_keys = [source_tech_key,source_loc_key]
        
        if not all(source_index_keys):
            print (f"WARNING NO LOC OR TECH COLUMN FOUND IN `FORCE_RESOURCE` for model {solved_model}, CHECK FILES")
            continue 
        
        # Create (multi) index of dataframe.
        required_resource = required_resource.set_index(index_keys).sort_index()
        force_resource = force_resource.set_index(source_index_keys).sort_index()
        
        # Map force_resource to required_resource dataframe.
        required_resource = map_model_to_model('force_resource',required_resource,force_resource).fillna(0)

        # Filter out resources that are not forced. Force_resource is either a string, or False by default.
        required_resource = required_resource[required_resource.force_resource].reset_index()
        
        # available_resource['timesteps'] = pd.to_datetime(available_resource['timesteps'], format='%Y-%m-%d %H:%M:%S')
        # required_resource['timesteps'] = pd.to_datetime(required_resource['timesteps'], format='%Y-%m-%d %H:%M:%S')
        
        # # ADD RESAMPLING TO HOURLY VALUES TO OBTAIN MW and MWh values.
        # available_resource = available_resource.resample("H",on='timesteps').sum()
        # required_resource = required_resource.resample("H",on='timesteps').sum()
        
        time_key = find_column(required_resource, 'time')
        if not time_key:
            print (f"WARNING NO TIMESTEPS COLUMN FOUND IN `REQUIRED_RESOURCE` for model {solved_model}, CHECK FILES")
            continue 
        
        # We omit the tech_key to prevent an error during concatination, as the available an required resources dataframes contain different technologies.
        index_keys += [time_key]
        
        spores_key = find_column(available_resource, 'spores')
        
        if spores_key:
            index_keys += [spores_key]
                
        
        # available_resource = available_resource.set_index(index_keys).sort_index()
        # required_resource = required_resource.set_index(index_keys).sort_index()
        
        if 'resource' in available_resource.columns:
            available_resource = available_resource.drop(['resource'],axis=1)
        
        # Rename columns to identical values and add key to index list.
        available_resource = available_resource.rename(columns={'available_resource':'resource'})
        required_resource = required_resource.rename(columns={'required_resource':'resource'})
        index_keys += ['resource']
        
        # We concat the two `available_resource` and `required_resource` dataframes into one.
        # To achieve this we need to match indices and column names first.
        # Set correct indices.
        available_resource = available_resource[index_keys]
        required_resource = required_resource[index_keys]
        
        # Combine required_resource and available_resource dataframes so they can be grouped.
        all_resources = pd.concat([available_resource,required_resource]).reset_index()
        # We redefine the index keys again  for mapping of the energy carriers.
        index_keys = [tech_key, loc_key]
        
        # Find definitions of locs and techs keys in dataframe.
        source_tech_key = find_column(carriers, 'tech')
        source_loc_key = find_column(carriers, 'loc')

        source_index_keys = [source_tech_key,source_loc_key]
        
        if not all(source_index_keys):
            print (f"WARNING NO LOC OR TECH COLUMN FOUND IN `FORCE_RESOURCE` for model {solved_model}, CHECK FILES")
            continue 
        
        # Create (multi) index of dataframe.
        all_resources = all_resources.set_index(index_keys).sort_index()
        carriers = carriers.set_index(source_index_keys).sort_index()
        
        # Map force_resource to required_resource dataframe.
        all_resources = map_model_to_model('carriers',all_resources,carriers).fillna(0)
        
        # Reset index for the next step.
        all_resources = all_resources.reset_index()
        
        # We redefine the index keys again, now for grouping to calculate the residual loads.
        index_keys = [loc_key,time_key,'carriers']
        
        if spores_key:
            index_keys += [spores_key]
            
        # # Residual load calculation must be done per carrier, so we must map this data to the all_resource dataframe.
        # map_tech_keys = [c for c in carriers.columns if 'tech' in c]
        
        # if map_tech_keys:
        #     # Get the first keys, assuming these are the correct keys.
        #     map_tech_key = map_tech_keys[0]

        #     # Map map_kpi to all_resource dataframe.
        #     all_resources['carriers'] = map_model_to_model('carriers',all_resources,tech_key,carriers,map_tech_key)
        
        # all_resources['force_resource'] = map_model_to_model('force_resource',all_resources,tech_key,force_resource,tech_key)
        # all_resources['carriers'] = map_model_to_model('carriers',all_resources,tech_key,carriers,tech_key)
        # mapping = carriers.set_index(tech_key)['carriers']
        # all_resources['carriers'] = all_resources[tech_key].map(dict(zip(mapping.index.values,mapping.values))).fillna('')
        
        # Calculate curtailed resource as the sum of available and required resource.
        # This is the net residual load, which can be either positive (oversupply/long) or negative (overdemand/short).
        # When taking the annual sum of this KPI, you will get the net system balance (total resource available versus required).
        # Since `available_resource` and `required_resource` have opposite signs, we can simply take the sum.
        residual_load = all_resources.groupby(index_keys).sum()['resource'].reset_index().rename(columns={'resource':'residual_load'})
        
        # This is the absolute sum of the residual load and so the net imbalance in the system, regardless of the direction of the imbalance.
        # When taking to annual sum of this KPI, you will get the total imbalance of the system.
        # Since `available_resource` and `required_resource` have opposite signs, we can simply take the sum.
        system_imbalance = all_resources.groupby(by=index_keys, as_index=False)['resource'].apply(lambda c: c.abs().sum()).rename(columns={'resource':'system_imbalance'})
    
        # Add new KPI to solved_models dictionary.
        solved_models[solved_model]['system_imbalance'] = system_imbalance
        solved_models[solved_model]['residual_load'] = residual_load
            


       
    return solved_models

def get_correlation_between(pivot,with_pivot):
    
    # Create an empty dataframe with specified columns.
    corr_df = pd.DataFrame(columns=['techs','with_techs','correlation'])
    
        # We populate the dataframe by looping through the techs of both input dataframes and calculate the time-based correlation between them.
    for i,tech in enumerate(pivot.columns):
        for j,with_tech in enumerate(with_pivot.columns):
            
            # Provide a unique identifier for the row.
            row = (i+1)*j
            
            # We skip autocorrelation.
            if tech != with_tech:
                
                # Calculate the correlation between the technologies.
                corr_value = pivot[tech].corr(with_pivot[with_tech], method='pearson')
                
                # Populate the corr_df dataframe.
                corr_df.loc[row] = [tech, with_tech, corr_value]
    
    return corr_df.dropna()

def add_correlation_coeffs(solved_models):
    """
    This function calculates and adds correlation coefficients between technology timeseries.
    Correlation coefficients can provide insights in the behaviour of assets with other assets, 
    for example to what extend stationary batteries follow renewable profiles, and to what extend this 
    renewable energy is consumed directly.
    
    Together with e.g. a Sankey diagram, that shows 
    """
    
    # Specify which KPIs to correlate with which other KPIs.
    # In this case, we want to investigate the correlation between energy consumed by techs and resource that was available, 
    # and the energy produced by techs and the resource that was required.
    # 
    correlation_dict = {'carrier_con':'available_resource', 
                        'carrier_prod':'required_resource'}
    
    # Create a list to hold the correlation tables. A table will be created for each entry in the `correlation_dict`.
    corr_tables = []
    
    # Loop through the solved_models provided.
    for i,solved_model in enumerate(solved_models):
        
        # Inform user.
        print (f"CALCULATING CORRELATION COEFFS FOR RUN `{solved_model}`")
        
        # Loop through the entries in the correlation dictionary and calculate a table per entry.
        for kpi in correlation_dict:
            with_kpi = correlation_dict[kpi]
            
            # Load all relevant dataframes.
            energy = load_solved_model(solved_models[solved_model],kpi).set_index('timesteps')
            resource = load_solved_model(solved_models[solved_model],with_kpi).set_index('timesteps')
            
            # Filter out all technologies that are mentioned in available_resource and required_resource frames.
            filtered_energy = energy[~energy['techs'].isin(resource.techs.unique())]

            # First calculate the correlation between supply of resources and consumed energy in the system.
            tech_keys = [c for c in resource.columns if 'tech' in c]
            with_tech_keys = [c for c in filtered_energy.columns if 'tech' in c]            

            # Check if all keys were found. Also check if resource is not empty, which may happen. Energy should never be empty.
            if tech_keys and with_tech_keys and resource[with_kpi].any():
                tech_key = tech_keys[0]
                with_tech_key = with_tech_keys[0]
                
                # Translate all transmission technologies identifiers into pure tech identifiers.
                filtered_energy[tech_key] = filtered_energy[tech_key].str.split(":",expand=True)[0]
                resource[with_tech_key] = resource[with_tech_key].str.split(":",expand=True)[0]
                
                # Group dataframes over any other dimensions other than timesteps and technologies.
                grouped_energy = filtered_energy.groupby(['timesteps',tech_key]).sum() # .rename(columns= {kpi:'value'})
                grouped_resource = resource.groupby(['timesteps',with_tech_key]).sum() # .rename(columns= {with_kpi:'value'})
                
                # Prepare pivot tables.
                pivot_energy = grouped_energy.pivot_table(values=kpi,columns=tech_key,index='timesteps')
                pivot_resource = grouped_resource.pivot_table(values=with_kpi,columns=with_tech_key,index='timesteps')
                
                # Calculate correlation table.
                corr_table = get_correlation_between(pivot_energy,pivot_resource)
                
            else:
                # print (f"INPUT(S) NOT FOUND FOR RUN {solved_model}, NOT CORRELATION COEFFICIENTS.")
                corr_table = pd.DataFrame()
            
            # Add the correlation table to the list.
            corr_tables.append(corr_table)
            
        # When finished, append all correlation tables in the list into one table and add to solved_models.
        solved_models[solved_model]['correlation'] = pd.concat(corr_tables)
        
    return solved_models

def add_annual_totals(solved_models,kpi):
    """
    This function aggregrates timeseries data into annual totals by grouping them together with pandas groupby functionality.
    """

    for i,solved_model in enumerate(solved_models):

        if kpi in solved_models[solved_model].keys():
            
            # print (f"CALCULATING TIMESERIES DATA TOTALS FOR KPI `{kpi}` for RUN `{solved_model}`")
            update_on_action('CALCULATING','total_'+kpi,solved_model)
            
            # Load the results. We apply a fillna to make sure that no NaN data is contained within the dataframe.
            # Otherwise this may cause the groupby function to disregard the rows containing NaN values, leading to missing data.
            results = solved_models[solved_model][kpi].fillna(0)
            columns = results.columns.drop(['timesteps',kpi]).to_list()
            
            solved_models[solved_model]['total_'+kpi] = results.groupby(by=columns, as_index=False)[kpi].sum().rename(columns={kpi:f'total_{kpi}'})
            
        else:
            # Print warning.
            print (f"KPI `{kpi}` NOT FOUND FOR RUN `{solved_model}`")

    return solved_models

# def map_model_to_model(map_kpi,model,key,map_model,map_key):
def map_model_to_model(kpi,target_model,source_model, source_index=None,target_index=None):
    
    if isinstance(source_index, list) or isinstance(target_index, list): 
        if not target_index:
            target_index = source_index

        if not source_index:
            source_index = target_index
            
        mapping = source_model.set_index(source_index)[kpi]
        
        target_model[kpi] = target_model[target_index].map(dict(zip(mapping.index.values,mapping.values))).fillna('')
        
        return target_model
        
    elif type(target_model.index) == type(source_model.index):
        target_model[kpi] = target_model.index.to_numpy() #you get the index as tuple
        
        target_model[kpi] = target_model[kpi].map(source_model.to_dict()[kpi])
        
        return target_model
    
    else:
        print ("Warning, indices of target and source model are different and no index was specified (as a list), recheck your settings.")
        
        return
        
def merge_model_kpis(solved_models,merge_kpis):

    for merged_kpi in merge_kpis:
        
        target_kpi = merge_kpis[merged_kpi][0]
        source_kpis = merge_kpis[merged_kpi][1:]
        
        solved_models = map_model_kpis(solved_models,target_kpi,source_kpis,overwrite_name=merged_kpi)

    return solved_models

def map_model_kpis(solved_models,target_kpi,source_kpis,overwrite_name=None):
    
    #DONE MAP CARRIERS TO (STORAGE) TECHS
        
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
            source_spores_key = find_column(source_model, 'spore')
            
            # We only need to use the temp_tech key if the source data is purely tech related, like `names`.
            # Hence we need to repeat this step for every source model.
            # Determine whether we need to use the `tech` or `temp_tech` key.
            if 'temp_tech' in target_model.columns and source_tech_key and not source_loc_key:
                tech_key = 'temp_tech'
            # Make sure to set it back after `temp_tech` has become irrelevant.
            else:
                tech_key = find_column(target_model, 'tech')
                
            # map_tech_keys = [c for c in source_model.columns if ('tech' in c)] # & (c not in ['temp_tech'])
            # map_loc_keys = [c for c in source_model.columns if 'loc' in c]
            
            target_index_keys_2 = []
            source_index_keys_2 = []
            
            # Add tech keys to index list if they exist. 
            # If any of the keys is present in the source dataframe, but not in the target, skip to next source_kpi.
            if bool(tech_key) and bool(source_tech_key):
                target_index_keys_2 += [tech_key]
                source_index_keys_2 += [source_tech_key]
            elif not bool(tech_key) and bool(source_tech_key):
                continue
                
            # Add loc keys to index list if they exist.
            if bool(loc_key) and bool(source_loc_key):
                target_index_keys_2 += [loc_key]
                source_index_keys_2 += [source_loc_key]
                
                # Create seprate one for coordinate mapping.
                loc_index_keys = [loc_key]
                loc_index_tags = ['']
                
                # Add additional loc key for end node locs of infrastructure.
                if to_loc_key:
                    loc_index_keys += [to_loc_key]
                    loc_index_tags += ['_end']
            elif not bool(loc_key) and bool(source_loc_key):
                continue
            
            # Add time key to index if they exist. 
            if bool(time_key) and bool(source_time_key):
                target_index_keys_2 += [time_key]
                source_index_keys_2 += [source_time_key]
            elif not bool(time_key) and bool(source_time_key):
                continue

            if bool(spores_key) and bool(source_spores_key):
                target_index_keys_2 += [spores_key]
                source_index_keys_2 += [source_spores_key]
            # elif not bool(spores_key) and bool(source_spores_key):
            #     continue
                        
            # Now check if there is any overlap in keys. If not, skip current source_kpi.
            if not target_index_keys_2 or not source_index_keys_2:
                # print (f"{'':<5} No overlap in indices between `{target_kpi}` and `{source_kpi}`, jumping to next kpi.")
                
                update_on_action("WARNING",msg=f"No overlap in indices between `{target_kpi}` and `{source_kpi}`, jumping to next kpi.")
                continue
            else:
                update_on_action("MAPPING",kpi=source_kpi,msg=f"onto `{target_kpi}` with index keys {target_index_keys_2}")
                # print (f"{'':<5} Mapping KPI `{target_kpi}` onto `{source_kpi}` using index keys {target_index_keys_2}")
            
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
                target_model = target_model.set_index(target_index_keys_2).sort_index()
                source_model = source_model.set_index(source_index_keys_2).sort_index()

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
