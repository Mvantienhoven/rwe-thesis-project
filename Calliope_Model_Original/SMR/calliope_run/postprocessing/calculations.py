import numpy as np
import pandas as pd
import copy

from calliope_run.postprocessing.util import update_on_action, find_column, find_common_keys, map_model_to_model, load_solved_model
# from calliope_run.postprocessing.model_handling import load_solved_model

def add_levelized_cost(solved_models):
    """
        Calculate LCOE of all technologies. Calliope has the tendency to ignore transmission technologies.
    
    """
    
    update_on_action('CALCULATING','levelized_cost')
    
    for solved_model in solved_models:
        
        # The resource dataframe is the basis of determining the available resource.
        # Load `resource` dataframe.
        cost = load_solved_model(solved_models[solved_model],'cost')
        carrier_prod = load_solved_model(solved_models[solved_model],'carrier_prod')
        
        # Check if the resource dataframe is empty; if so, push to the next iteration in the for loop.
        if cost.empty or carrier_prod.empty:
            print (f"WARNING, inputs not found for run {solved_model}, NOT CALCULATING lcoe.")
            continue
        
        # If `spores` not in target_model, expand in dimension  if it is present in the source_model.
        if 'carriers' in carrier_prod.columns and 'carriers' not in cost.columns:
            # Get list with spores numbers.
            carrier_types = carrier_prod['carriers'].unique()
            # Fill dataframe with list of spores numbers.
            cost['carriers'] = [carrier_types]*len(cost)
            # Now expand whole database with spores numbers.
            cost = cost.explode('carriers')

        for kpi in ['loctech_levelized_cost','systemwide_levelized_cost']:
            
            update_on_action('CALCULATING',kpi,solved_model)
            
            index_keys = find_common_keys(cost,carrier_prod)
            
            drop_kpi = 'techs'
            if 'systemwide' in kpi and drop_kpi in index_keys:
                index_keys.remove(drop_kpi)
            
            # Set indices. carrier_prod requires a groupby to sum over the carrier and timestep dimensions.
            grouped_cost = cost.groupby(index_keys).sum()
            grouped_prod = carrier_prod.groupby(index_keys).sum()
                
            # Finally map the KPI.
            grouped_cost = map_model_to_model('carrier_prod',grouped_cost,grouped_prod).reset_index().dropna()
            
            grouped_cost[kpi] = grouped_cost['cost']/grouped_cost['carrier_prod']
            
            grouped_cost.loc[((grouped_cost['cost'] > 0) & (grouped_cost['carrier_prod'] == 0)), kpi] = 'inf'
            grouped_cost = grouped_cost.dropna()
        
            solved_models[solved_model][kpi] = grouped_cost
        
    return solved_models
            

def add_capacity_factor(solved_models):
    """
        Calculate Capacity factors of all technologies. Calliope has the tendency to ignore transmission technologies.
        
        Assumes that energy  is in units of Wh of any scale (kilo, mega, giga etc)
    
    """
    
    for solved_model in solved_models:
    
        # Inform user.
        # print (f"CALCULATING `loctech_cf` and `systemwide_cf` for run `{solved_model}`")
        # print (f"{'CALCULATING':<15} {'kpi `loctech_capacity_factor` and `systemwide_capacity_factor`':<80} for run `{solved_model}`")
        
        # update_on_action('CALCULATING','loctech_capacity_factor',solved_model)
        # update_on_action('CALCULATING','systemwide_capacity_factor',solved_model)
        
        # The resource dataframe is the basis of determining the available resource.
        # Load `resource` dataframe.
        energy_cap = load_solved_model(solved_models[solved_model],'energy_cap')
        carrier_prod = load_solved_model(solved_models[solved_model],'carrier_prod')
        
        # Check if the resource dataframe is empty; if so, push to the next iteration in the for loop.
        if energy_cap.empty or carrier_prod.empty:
            print (f"WARNING, inputs not found for run {solved_model}, NOT CALCULATING lcoe.")
            continue
        
        # If `spores` not in target_model, expand in dimension  if it is present in the source_model.
        if 'carriers' in carrier_prod.columns and 'carriers' not in energy_cap.columns:
            # Get list with spores numbers.
            carrier_types = carrier_prod['carriers'].unique()
            # Fill dataframe with list of spores numbers.
            energy_cap['carriers'] = [carrier_types]*len(energy_cap)
            # Now expand whole database with spores numbers.
            energy_cap = energy_cap.explode('carriers')
            
        # loctech is per individual loc_tech, 
        for kpi in ['loctech_capacity_factor','systemwide_capacity_factor']:
            
            update_on_action('CALCULATING',kpi,solved_model)
            
            index_keys = find_common_keys(energy_cap,carrier_prod)
            
            drop_kpi = 'techs'
            if 'systemwide' in kpi and drop_kpi in index_keys:
                index_keys.remove(drop_kpi)
                
            # Set indices. carrier_prod requires a groupby to sum over the carrier and timestep dimensions.
            grouped_cap = energy_cap.groupby(index_keys).sum()
            grouped_prod = carrier_prod.groupby(index_keys).sum()
                    
            # Map the KPI and remove any NaN.
            grouped_cap = map_model_to_model('carrier_prod',grouped_cap,grouped_prod).reset_index().dropna()

            # TODO exchange hardcoded hours per year with timestep_resolution
            hours_per_year = 8760
            
            # Calculate the capacity factor
            grouped_cap[kpi] = grouped_cap['carrier_prod']/grouped_cap['energy_cap']/hours_per_year
            
            grouped_cap.loc[((grouped_cap['energy_cap'] > 0) & (grouped_cap['carrier_prod'] == 0)), kpi] = np.NaN
            
            grouped_cap = grouped_cap.dropna()
        
            solved_models[solved_model][kpi] = grouped_cap
            
        # # systemwide_key_list = ['techs']
        # # spores_key_1 = find_column(energy_cap, 'spore')
        # # spores_key_2 = find_column(carrier_prod, 'spore')
        
        # # if spores_key_1 and spores_key_2:
        # #     systemwide_key_list += ['spores']
        
        # # loctech_key_list = systemwide_key_list + ['locs']
            
        # # Set indices. carrier_prod requires a groupby to sum over the carrier and timestep dimensions.
        # systemwide_cap = energy_cap.groupby(systemwide_key_list).sum().reset_index().set_index(systemwide_key_list)
        # systemwide_prod = carrier_prod.groupby(systemwide_key_list).sum()
        
        # loctech_cap = energy_cap.set_index(loctech_key_list)
        # loctech_prod = carrier_prod.groupby(loctech_key_list).sum()
                
        # # .reset_index().rename(columns={0:'powerdistance'})
        # # Loop trhough all unique cost types and calculate lcoe per cost type.
        
        # # First we will calculate the LCOE of location-specific technologies.
        # # Filter the specific cost_type.
        # # locspecific_type_cost = locspecific_cost[locspecific_cost['costs'] == cost_type]
        
        # hours_per_year = 8760
        
        # # The values are accessed by calling the column `.cost` and `.carrier_prod`.
        # loctech_capfactor = loctech_prod.carrier_prod/loctech_cap.energy_cap/hours_per_year
        # loctech_capfactor = loctech_capfactor.reset_index().rename(columns={0:'loctech_capacity_factor'})
        
        # # Now we will do the same for the systemwide costs, i.e. summed over all locations.
        # # Filter the specific cost_type.
        # # systemwide_type_cost = systemwide_cost[systemwide_cost['costs'] == cost_type]
        
        # # The values are accessed by calling the column `.cost` and `.carrier_prod`.
        # systemwide_capfactor = systemwide_prod.carrier_prod/systemwide_cap.energy_cap/hours_per_year
        # systemwide_capfactor = systemwide_capfactor.reset_index().rename(columns={0:'systemwide_capacity_factor'})
                    
        # solved_models[solved_model]['loctech_capacity_factor'] = loctech_capfactor
        # solved_models[solved_model]['systemwide_capacity_factor'] = systemwide_capfactor
        
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

def calc_available_resource(row):
    if row['resource_unit'] == 'energy_per_area':
        val = row['resource']*row['resource_scale']*row['resource_area']
    elif row['resource_unit'] == 'energy_per_cap':
        val = row['resource']*row['resource_scale']*row['energy_cap']
    else:
        val = row['resource']*row['resource_scale']
        
    return val

    
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

        # The resource dataframe is the basis of determining the available resource.
        # Load `resource` dataframe.
        resource = load_solved_model(solved_models[solved_model],'resource')
        energy_cap = load_solved_model(solved_models[solved_model],'energy_cap')
        # timestep_resolution = load_solved_model(solved_models[solved_model],'timestep_resolution')
        
        # Check if the resource dataframe is empty; if so, push to the next iteration in the for loop.
        if resource.empty:
            print (f"inputs not found for {solved_model}, NOT CALCULATING `available_resource`.")
            continue            
        
        # Get keys of all supply techs in tech column that add to the residual load.
        if include_techs:
            include_tech_keys = [c for t in include_techs for c in np.unique(resource['techs'].values) if (t in c) & (":" not in c)]
        if exclude_techs:
            include_tech_keys = [c for c in include_tech_keys if c not in exclude_techs]
            
        if not include_tech_keys:
            # Otherwise assign an empty value and proceed with the routine.
            print (f'NO RELEVANT TECHS FOUND AFTER APPLYING `include_techs` AND `exclude_techs` FOR RUN {solved_model}, MOVING ON.')
            continue
        
        # Filter technologies based on list.
        available_resource = resource[resource['techs'].isin(include_tech_keys)]
        

        # Map unit, scale, area and energy_cap for each loc,tech combination
        for kpi in ['resource_unit','resource_scale','force_resource','timestep_resolution','resource_area','energy_cap']:
            
            # Make sure KPI is in dict keys, else create column with None values.
            if kpi in solved_models[solved_model].keys():
                
                # Load model
                source_model = load_solved_model(solved_models[solved_model],kpi)
                
                # If `spores` not in target_model, expand in dimension  if it is present in the source_model.
                if 'spores' in source_model.columns and 'spores' not in available_resource.columns:
                    # Get list with spores numbers.
                    spores_no = source_model['spores'].unique()
                    # Fill dataframe with list of spores numbers.
                    available_resource['spores'] = [spores_no]*len(available_resource)
                    # Now expand whole database with spores numbers.
                    available_resource = available_resource.explode('spores')
                
                # Find overlapping index keys.
                index_keys = find_common_keys(available_resource,source_model)
                
                # Set index of dataframes with keys.
                source_model = source_model.set_index(index_keys).sort_index()
                available_resource = available_resource.set_index(index_keys).sort_index()
                
                # Finally map the KPI.
                available_resource = map_model_to_model(kpi,available_resource,source_model).fillna(0).reset_index()

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

        # Calculate the default resource available using resource and resource_scale
        available_resource['available_resource'] = available_resource['resource'] * available_resource['resource_scale']
        
        # If the resource_unit indicates that the resource should be scaled per `_area` or `_cap`, multiply by `resource_area` or `energy_cap` respectively.
        available_resource.loc[available_resource['resource_unit'] == 'energy_per_cap','available_resource'] = available_resource['available_resource']*available_resource['energy_cap']
        available_resource.loc[available_resource['resource_unit'] == 'energy_per_area','available_resource'] = available_resource['available_resource']*available_resource['resource_area']

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
            
        index_keys = find_common_keys(available_resource,carrier_prod)
        
        if not index_keys:
            update_on_action('WARNING',kpi='curtailed_resource',run=solved_model,msg='No common index keys found between `available_resource` and `carrier_prod`. Check your inputs.')
            continue
        
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
        # tech_key = find_column(required_resource, 'tech')
        # loc_key = find_column(required_resource, 'loc')
        
        # index_keys = [tech_key, loc_key]
        
        
        # # Only proceed with both tech and loc keys were found.
        # if not all(index_keys):
        #     print ("WARNING NO LOC OR TECH COLUMN FOUND IN RESOURCE, CHECK FILES")
        #     continue 
        
        # # Find definitions of locs and techs keys in dataframe.
        # source_tech_key = find_column(force_resource, 'tech')
        # source_loc_key = find_column(force_resource, 'loc')

        # source_index_keys = [source_tech_key,source_loc_key]
        
        # if not all(source_index_keys):
        #     print (f"WARNING NO LOC OR TECH COLUMN FOUND IN `FORCE_RESOURCE` for model {solved_model}, CHECK FILES")
        #     continue 
        
        index_keys = find_common_keys(required_resource,force_resource)

        if not index_keys:
            update_on_action('WARNING',kpi='residual_load',run=solved_model,msg='No common index keys found between `required_resource` and `force_resource`. Check your inputs.')
            continue
        
        # Create (multi) index of dataframe.
        required_resource = required_resource.set_index(index_keys).sort_index()
        force_resource = force_resource.set_index(index_keys).sort_index()
        
        # Map force_resource to required_resource dataframe.
        required_resource = map_model_to_model('force_resource',required_resource,force_resource).fillna(0).reset_index()

        # Filter out resources that are not forced. Force_resource is either a string, or False by default.
        required_resource = required_resource[required_resource.force_resource]
        
        # # available_resource['timesteps'] = pd.to_datetime(available_resource['timesteps'], format='%Y-%m-%d %H:%M:%S')
        # # required_resource['timesteps'] = pd.to_datetime(required_resource['timesteps'], format='%Y-%m-%d %H:%M:%S')
        
        # # # ADD RESAMPLING TO HOURLY VALUES TO OBTAIN MW and MWh values.
        # # available_resource = available_resource.resample("H",on='timesteps').sum()
        # # required_resource = required_resource.resample("H",on='timesteps').sum()
        
        # time_key = find_column(required_resource, 'time')
        # if not time_key:
        #     print (f"WARNING NO TIMESTEPS COLUMN FOUND IN `REQUIRED_RESOURCE` for model {solved_model}, CHECK FILES")
        #     continue 
        
        # # We omit the tech_key to prevent an error during concatination, as the available an required resources dataframes contain different technologies.
        # index_keys += [time_key]
        
        # spores_key = find_column(available_resource, 'spores')
        
        # if spores_key:
        #     index_keys += [spores_key]
                
        
        # available_resource = available_resource.set_index(index_keys).sort_index()
        # required_resource = required_resource.set_index(index_keys).sort_index()
        
        if 'resource' in available_resource.columns:
            available_resource = available_resource.drop(['resource'],axis=1)
        
        # Rename columns to identical values and add key to index list.
        available_resource = available_resource.rename(columns={'available_resource':'resource'})
        required_resource = required_resource.rename(columns={'required_resource':'resource'})
        # index_keys += ['resource']
        
        index_keys = find_common_keys(required_resource,available_resource)
        if not index_keys:
            update_on_action('WARNING',kpi='residual_load',run=solved_model,msg='No common index keys found between `required_resource` and `available_resource`. Check your inputs.')
            continue
        
        # We concat the two `available_resource` and `required_resource` dataframes into one.
        # To achieve this we need to match indices and column names first.
        # Set correct indices.
        available_resource = available_resource[index_keys + ['resource']]
        required_resource = required_resource[index_keys + ['resource']]
        
        # Combine required_resource and available_resource dataframes so they can be grouped.
        all_resources = pd.concat([available_resource,required_resource]).reset_index()
        # We redefine the index keys again  for mapping of the energy carriers.
        # index_keys = [tech_key, loc_key]
        
        # Find definitions of locs and techs keys in dataframe.
        # source_tech_key = find_column(carriers, 'tech')
        # source_loc_key = find_column(carriers, 'loc')

        # source_index_keys = [source_tech_key,source_loc_key]
        
        index_keys = find_common_keys(all_resources,carriers)
        if not index_keys:
            update_on_action('WARNING',kpi='residual_load',run=solved_model,msg='No common index keys found between `all_resources` and `carriers`. Check your inputs.')
            continue
        
        # Create (multi) index of dataframe.
        all_resources = all_resources.set_index(index_keys).sort_index()
        carriers = carriers.set_index(index_keys).sort_index()
        
        # Map force_resource to required_resource dataframe.
        all_resources = map_model_to_model('carriers',all_resources,carriers).fillna('').reset_index()
                
        # # We redefine the index keys again, now for grouping to calculate the residual loads.
        # index_keys = [loc_key,time_key,'carriers']
        
        # if spores_key:
        #     index_keys += [spores_key]
        
        index_keys = find_common_keys(all_resources,by_keys=['locs','timesteps','spores','carriers'])
                    
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
        residual_load = all_resources.groupby(index_keys).sum()['resource']
        
        system_imbalance = residual_load.abs()
        
        residual_load = residual_load.reset_index().rename(columns={'resource':'residual_load'})
        system_imbalance = system_imbalance.reset_index().rename(columns={'resource':'system_imbalance'})
        
        # This is the absolute sum of the residual load and so the net imbalance in the system, regardless of the direction of the imbalance.
        # When taking to annual sum of this KPI, you will get the total imbalance of the system.
        # Since `available_resource` and `required_resource` have opposite signs, we can simply take the sum.
        # system_imbalance = all_resources.groupby(by=index_keys, as_index=False)['resource'].apply(lambda c: c.abs().sum()).rename(columns={'resource':'system_imbalance'})
    
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

        if not kpi in solved_models[solved_model].keys():
            print (f"KPI `{kpi}` NOT FOUND FOR RUN `{solved_model}`")
            continue
        
        # print (f"CALCULATING TIMESERIES DATA TOTALS FOR KPI `{kpi}` for RUN `{solved_model}`")
        
        # Load the results. We apply a fillna to make sure that no NaN data is contained within the dataframe.
        # Otherwise this may cause the groupby function to disregard the rows containing NaN values, leading to missing data.
        results = solved_models[solved_model][kpi].fillna(0)
                    
        # columns = results.columns.drop(['timesteps',kpi]).to_list()
        columns = [key for key in ['locs','techs','spores','carriers'] if key in results.columns]
        if len(columns) == 0:
            continue
        
        update_on_action('CALCULATING','total_'+kpi,solved_model)
        solved_models[solved_model]['total_'+kpi] = results.groupby(by=columns, as_index=False)[kpi].sum().rename(columns={kpi:f'total_{kpi}'})

    return solved_models
