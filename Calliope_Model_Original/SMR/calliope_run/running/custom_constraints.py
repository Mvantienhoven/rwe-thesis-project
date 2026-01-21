def load_constraint_dicts(scenario):

    object_dict = {
                    'tow_platform',
                    'ab_platform',
                    'bcd_apron',
                    'efgh_apron',
                    'r_platform',
                    's_platform',
                    }
    
    asset_loc_dict = {
                        'tow_platform': ['towtrucks_nabo',
                                            'towtrucks_wibo'],
                        'ab_platform': [
                            'gpus_ab_platform_nabo',
                            'pcas_ab_platform_nabo',
                            'gse_ab_platform'
                            ],
                        'bcd_apron': [
                            'gpus_bcd_apron_nabo',
                            'gpus_bcd_apron_wibo',
                            'pcas_bcd_apron_nabo',
                            'pcas_bcd_apron_wibo',
                            'gse_bcd_apron',
                                ],
                        'efgh_apron': [
                            'gpus_efgh_apron_nabo',
                            'gpus_efgh_apron_wibo',
                            'pcas_efgh_apron_nabo',
                            'pcas_efgh_apron_wibo',
                            'gse_efgh_apron',
                            ],
                        'r_platform': [
                            'gpus_r_platform_wibo',
                            'gse_r_platform',
                            ],
                        's_platform': [
                            'gpus_s_platform_wibo',
                            'gse_s_platform',
                            ],
                        } 
    
    asset_tech_dict = {
                        'towtrucks_nabo': 'truck_tow_electric',
                        'towtrucks_wibo': 'truck_tow_electric',
                        
                        'gpus_ab_platform_nabo': 'gpu_electric',
                        'pcas_ab_platform_nabo': 'pca_electric',
                        'gse_ab_platform': 'gse_electric',
                        
                        'gpus_bcd_apron_nabo': 'gpu_electric',
                        'gpus_bcd_apron_wibo': 'gpu_electric',
                        'pcas_bcd_apron_nabo': 'pca_electric',
                        'pcas_bcd_apron_wibo': 'pca_electric',
                        'gse_bcd_apron': 'gse_electric',
                                                        
                        'gpus_efgh_apron_nabo': 'gpu_electric',
                        'gpus_efgh_apron_wibo': 'gpu_electric',
                        'pcas_efgh_apron_nabo': 'pca_electric',
                        'pcas_efgh_apron_wibo': 'pca_electric',
                        'gse_efgh_apron': 'gse_electric',
                        
                        'gpus_r_platform_wibo': 'gpu_electric',
                        'gse_r_platform': 'gse_electric',
                        
                        'gpus_s_platform_wibo': 'gpu_electric',
                        'gse_s_platform': 'gse_electric',
                        }
    
    asset_cap_dict = {
                        'towtrucks_nabo': 200, # kW per unit
                        'towtrucks_wibo': 533, # kW per unit
                        
                        'gpus_ab_platform_nabo': 28.8, # kW per unit
                        'pcas_ab_platform_nabo': 54, # kW per unit
                        'gse_ab_platform': 32, # kW per unit
                        
                        'gpus_bcd_apron_nabo': 28.8, # kW per unit
                        'gpus_bcd_apron_wibo': 57.6, # kW per unit
                        'pcas_bcd_apron_nabo': 54, # kW per unit
                        'pcas_bcd_apron_wibo': 54, # kW per unit
                        'gse_bcd_apron': 32, # kW per unit
                                                        
                        'gpus_efgh_apron_nabo': 28.8, # kW per unit
                        'gpus_efgh_apron_wibo': 57.6, # kW per unit
                        'pcas_efgh_apron_nabo': 54, # kW per unit
                        'pcas_efgh_apron_wibo': 54, # kW per unit
                        'gse_efgh_apron': 32, # kW per unit
                        
                        'gpus_r_platform_wibo': 57.6, # kW per unit
                        'gse_r_platform': 32, # kW per unit
                        
                        'gpus_s_platform_wibo': 57.6, # kW per unit
                        'gse_s_platform': 32, # kW per unit
                        }
    
    storage_tech_dict = {
                        'towtrucks_nabo': 'truck_tow_battery',
                        'towtrucks_wibo': 'truck_tow_battery',
                        
                        'gpus_ab_platform_nabo': 'gpu_battery',
                        'pcas_ab_platform_nabo': 'pca_battery',
                        'gse_ab_platform': 'gse_battery',
                        
                        'gpus_bcd_apron_nabo': 'gpu_battery',
                        'gpus_bcd_apron_wibo': 'gpu_battery',
                        'pcas_bcd_apron_nabo': 'pca_battery',
                        'pcas_bcd_apron_wibo': 'pca_battery',
                        'gse_bcd_apron': 'gse_battery',
                                                        
                        'gpus_efgh_apron_nabo': 'gpu_battery',
                        'gpus_efgh_apron_wibo': 'gpu_battery',
                        'pcas_efgh_apron_nabo': 'pca_battery',
                        'pcas_efgh_apron_wibo': 'pca_battery',
                        'gse_efgh_apron': 'gse_battery',
                        
                        'gpus_r_platform_wibo': 'gpu_battery',
                        'gse_r_platform': 'gse_battery',
                        
                        'gpus_s_platform_wibo': 'gpu_battery',
                        'gse_s_platform': 'gse_battery',
                        }
    
    if '2030' in scenario:
        charge_to_discharge_ratio_dict = {
                            'towtrucks_nabo': 2.5, # Assume 500 kW charging, 300 kW discharging
                            'towtrucks_wibo': 0.93, # Assume 500 kW charging, 800 kW discharging
                            
                            'gpus_ab_platform_nabo': 1.74, # Assume 50 kW charging, 28.8 kW discharging
                            'gpus_bcd_apron_nabo': 1.74, # Assume 50 kW charging, 28.8 kW discharging
                            'gpus_efgh_apron_nabo': 1.74, # Assume 50 kW charging, 28.8 kW discharging
                            
                            'gpus_bcd_apron_wibo': 0.87, # Assume 50 kW charging, 57.6 kW discharging
                            'gpus_efgh_apron_wibo': 0.87, # Assume 50 kW charging, 57.6 kW discharging
                            'gpus_r_platform_wibo': 0.87, # Assume 50 kW charging, 57.6 kW discharging
                            'gpus_s_platform_wibo': 0.87, # Assume 50 kW charging, 57.6 kW discharging
                            
                            'pcas_ab_platform_nabo': 0.93, # Assume 50 kW charging, 53 kW discharging
                            'pcas_bcd_apron_nabo': 0.93, # Assume 50 kW charging, 53 kW discharging
                            'pcas_efgh_apron_nabo': 0.93, # Assume 50 kW charging, 53 kW discharging
                            
                            'pcas_bcd_apron_wibo': 0.93, # Assume 50 kW charging, 57.6 kW discharging
                            'pcas_efgh_apron_wibo': 0.93, # Assume 50 kW charging, 57.6 kW discharging
                            # 'pcas_r_platform_wibo': 0.93, # Assume 50 kW charging, 57.6 kW discharging
                            # 'pcas_s_platform_wibo': 0.93, # Assume 50 kW charging, 57.6 kW discharging
                            
                            'gse_bcd_apron': 1.56, # Assume 50 kW charging, 32 kW discharging
                            'gse_ab_platform': 1.56, # Assume 50 kW charging, 32 kW discharging
                            'gse_efgh_apron': 1.56, # Assume 50 kW charging, 32 kW discharging
                            'gse_r_platform': 1.56, # Assume 50 kW charging, 32 kW discharging
                            'gse_s_platform': 1.56, # Assume 50 kW charging, 32 kW discharging
                                }
        
        charger_tech_dict = {                                    
                            'tow_platform': 'charger_dc_500kw',
                            'ab_platform': 'charger_dc_50kw',
                            'bcd_apron': 'charger_dc_50kw',
                            'efgh_apron': 'charger_dc_50kw',
                            'r_platform': 'charger_dc_50kw',
                            's_platform': 'charger_dc_50kw',      
                                }
        
        charger_cap_dict = {                                    
                            'tow_platform': 500,
                            'ab_platform': 50,
                            'bcd_apron': 50,
                            'efgh_apron': 50,
                            'r_platform': 50,
                            's_platform': 50,      
                                }
        
    if '2050' in scenario:
        charge_to_discharge_ratio_dict = {
                            'towtrucks_nabo': 5, # Assume 1000 kW charging, 300 kW discharging
                            'towtrucks_wibo': 1.875, # Assume 1000 kW charging, 800 kW discharging
                            
                            'gpus_ab_platform_nabo': 3.47, # Assume 100 kW charging, 28.8 kW discharging
                            'gpus_bcd_apron_nabo': 3.47, # Assume 100 kW charging, 28.8 kW discharging
                            'gpus_efgh_apron_nabo': 3.47, # Assume 100 kW charging, 28.8 kW discharging
                            
                            'gpus_bcd_apron_wibo': 1.74, # Assume 100 kW charging, 57.6 kW discharging
                            'gpus_efgh_apron_wibo': 1.74, # Assume 100 kW charging, 57.6 kW discharging
                            'gpus_r_platform_wibo': 1.74, # Assume 100 kW charging, 57.6 kW discharging
                            'gpus_s_platform_wibo': 1.74, # Assume 100 kW charging, 57.6 kW discharging
                            
                            'pcas_ab_platform_nabo': 1.85, # Assume 100 kW charging, 54 kW discharging
                            'pcas_bcd_apron_nabo': 1.85, # Assume 100 kW charging, 54 kW discharging
                            'pcas_efgh_apron_nabo': 1.85, # Assume 100 kW charging, 54 kW discharging
                            
                            'pcas_bcd_apron_wibo': 1.85, # Assume 100 kW charging, 54 kW discharging
                            'pcas_efgh_apron_wibo': 1.85, # Assume 100 kW charging, 54 kW discharging
                            # 'pcas_r_platform_wibo': 1.86, # Assume 100 kW charging, 54 kW discharging
                            # 'pcas_s_platform_wibo': 1.86, # Assume 100 kW charging, 54 kW discharging
                            
                            'gse_bcd_apron': 3.125, # Assume 100 kW charging, 32 kW discharging
                            'gse_ab_platform': 3.125, # Assume 100 kW charging, 32 kW discharging
                            'gse_efgh_apron': 3.125, # Assume 100 kW charging, 32 kW discharging
                            'gse_r_platform': 3.125, # Assume 100 kW charging, 32 kW discharging
                            'gse_s_platform': 3.125, # Assume 100 kW charging, 32 kW discharging
                                }
        
        charger_tech_dict = {                                    
                            'tow_platform': 'charger_dc_1000kw',
                            'ab_platform': 'charger_dc_100kw',
                            'bcd_apron': 'charger_dc_100kw',
                            'efgh_apron': 'charger_dc_100kw',
                            'r_platform': 'charger_dc_100kw',
                            's_platform': 'charger_dc_100kw',      
                                }
            
        charger_cap_dict = {                                    
                            'tow_platform': 1000,
                            'ab_platform': 100,
                            'bcd_apron': 100,
                            'efgh_apron': 100,
                            'r_platform': 100,
                            's_platform': 100,      
                                }
        
    charger_carrier_dict = {
                        'tow_platform': 'electricity',
                        'ab_platform': 'electricity',
                        'bcd_apron': 'electricity',
                        'efgh_apron': 'electricity',
                        'r_platform': 'electricity',
                        's_platform': 'electricity',      
                                }
    
    return (object_dict, 
            asset_loc_dict, 
            asset_tech_dict, 
            asset_cap_dict,
            storage_tech_dict, 
            charger_tech_dict, 
            charger_cap_dict,
            charge_to_discharge_ratio_dict,
            charger_carrier_dict,
            )
    

def toggle_custom_constraints(model, scenario=None, flag=False):

    if flag:
        print ("ADDING custom constraints to model")
            
        # Make sure that the supply and demand assets of the E market do not activate simultaneously.
        # add_market_synchronous_supply_demand_constraint(model)
        
        # Load in the dictionaries containing relevant data for defining the manual constraints.
        (object_dict, 
        asset_loc_dict, 
        asset_tech_dict, 
        asset_cap_dict,
        storage_tech_dict, 
        charger_tech_dict, 
        charger_cap_dict,
        charge_to_discharge_ratio_dict,
        charger_carrier_dict,
        ) = load_constraint_dicts(scenario)
        
        # Loop through the different objects to define the respective constraints.
        for object in object_dict:
            for asset_loc in asset_loc_dict[object]:
            
                asset_tech = asset_tech_dict[asset_loc]
                storage_tech = storage_tech_dict[asset_loc]
                charge_to_discharge_ratio = charge_to_discharge_ratio_dict[asset_loc]
                charger_tech = charger_tech_dict[object]
                charger_carrier = charger_carrier_dict[object]
            
                # 1) Battery capacity equals convertor capacity 
                add_couple_battery_to_vehicle_linear_constraint(model,asset_loc,asset_tech,storage_tech,charge_to_discharge_ratio)
                # 2) Cable output equals battery input
                add_connect_battery_connector_flow_constraint(model, object,asset_loc,storage_tech,charger_tech,charger_carrier)
                # 3) Battery output equals convertor input
                # Constraint implicitly met through absence of other technology that can consume charger_carrier
                # 4) Charger output is limited by charger capacity and battery input
                add_limit_charger_flow_constraint(model, object,asset_loc,storage_tech,charger_tech,charger_carrier,charge_to_discharge_ratio)
                # add_limit_connector_capacity_linear_constraint(model, object,asset_loc,asset_tech,charger_tech,charge_to_discharge_ratio)
                # 5)
                # add_couple_charger_to_vehicle_linear_constraint(model,object,asset_loc,charger_tech,storage_tech)
    
    
# ############# Add your own constraints here ############# 

# def add_couple_battery_to_vehicle_constraint(model,asset_loc,asset_tech,storage_tech):
#     #### Hard couple the battery quantity of an asset/vehicle type to the quantity of that asset/vehicle
#     # Define the constraint
#     constraint_name = f'couple_battery_to_vehicle_{asset_loc}_constraint'
#     constraint_sets = []
    

#     def couple_battery_to_vehicle_constraint_rule(backend_model):

#         return backend_model.units[f'{asset_loc}::{asset_tech}'] == (
#             backend_model.units[f'{asset_loc}::{storage_tech}']
#         )

#     # Add the constraint
#     model.backend.add_constraint(constraint_name, constraint_sets, couple_battery_to_vehicle_constraint_rule)
    
def add_couple_battery_to_vehicle_linear_constraint(model,asset_loc,asset_tech,storage_tech,charge_to_discharge_ratio):
    #### Hard couple the battery quantity of an asset/vehicle type to the quantity of that asset/vehicle
    ## The battery capacity represents the storage capacity, whereas the asset capacity represents the discharge capacity. They are coupled through the charge to discharge ratio.
    
    # Define the constraint
    constraint_name = f'couple_battery_to_vehicle_linear_{asset_loc}_constraint'
    constraint_sets = []
    

    def couple_battery_to_vehicle_linear_constraint_rule(backend_model):

        return backend_model.energy_cap[f'{asset_loc}::{asset_tech}']*charge_to_discharge_ratio == (
            backend_model.energy_cap[f'{asset_loc}::{storage_tech}']
        )

    # Add the constraint
    model.backend.add_constraint(constraint_name, constraint_sets, couple_battery_to_vehicle_linear_constraint_rule)

# def add_limit_connector_capacity_constraint(model,object,asset_loc,asset_tech,charger_tech):
#     #### Limit the connection capacity from the object to the asset by the total number of assets invested
#     # Define the constraint
#     constraint_name = f'limit_connector_capacity_{asset_loc}_constraint'
#     constraint_sets = []
    

#     def limit_connector_capacity_constraint_rule(backend_model):

#         return backend_model.units[f'{asset_loc}::{asset_tech}']* backend_model.energy_cap_per_unit[f'{asset_loc}::{asset_tech}'] == (
#             backend_model.energy_cap[f'{object}::{charger_tech}:{asset_loc}']
#         )

#     # Add the constraint
#     model.backend.add_constraint(constraint_name, constraint_sets, limit_connector_capacity_constraint_rule)

# def add_limit_connector_capacity_linear_constraint(model,object,asset_loc,asset_tech,charger_tech,charge_to_discharge_ratio):
#     #### Limit the connection capacity from the object to the asset by the total number of assets invested
#     # Define the constraint
#     constraint_name = f'limit_connector_capacity_{asset_loc}_constraint'
#     constraint_sets = []
    
#     # In case the `charge_to_discharge_ratio` is =>1, the asset_tech capacity is determined by the charge capacity, and Calliope will automatically handle sizing of the charging infra correctly.
#     # Only if the ratio is <1 should we limit the charging capacity, as it cannot charge as fast as the rated capacity of the asset_tech. Hence, we use the `min()` operator.
#     def limit_connector_capacity_linear_constraint_rule(backend_model):

#         return backend_model.energy_cap[f'{asset_loc}::{asset_tech}']*min(1.0,charge_to_discharge_ratio) >= (
#             backend_model.energy_cap[f'{object}::{charger_tech}:{asset_loc}']
#         )

#     # Add the constraint
#     model.backend.add_constraint(constraint_name, constraint_sets, limit_connector_capacity_linear_constraint_rule)
    
# def add_limit_connector_flow_constraint(model, object,asset_loc,asset_tech,charger_tech,charger_carrier,charge_to_discharge_ratio):

#     #### Limit the cable flow capacity to the eGPUs by the total number of aircrafts currently powered by eGPUs
#     # Define the constraint
#     constraint_name = f'limit_connector_flow_{asset_loc}_constraint'
#     constraint_sets = ['timesteps']

#     def limit_connector_flow_constraint_rule(backend_model, timestep):
        
#         return (-backend_model.carrier_con[f'{asset_loc}::{asset_tech}::{charger_carrier}',timestep]*charge_to_discharge_ratio
#                 + backend_model.carrier_prod[f'{asset_loc}::{charger_tech}:{object}::{charger_carrier}',timestep]) <= backend_model.energy_cap[f'{object}::{charger_tech}:{asset_loc}']

#     # Add the constraint
#     model.backend.add_constraint(constraint_name, constraint_sets, limit_connector_flow_constraint_rule)

# WIP!
def add_connect_battery_connector_flow_constraint(model, object,asset_loc,storage_tech,charger_tech,charger_carrier):

    #### Link the output of the charger with the input of the battery to ensure everything flows through the battery
    # Define the constraint
    constraint_name = f'connect_battery_connector_flow_{asset_loc}_constraint'
    constraint_sets = ['timesteps']

    def connect_battery_connector_flow_constraint(backend_model, timestep):
        
        return (backend_model.carrier_con[f'{asset_loc}::{storage_tech}::{charger_carrier}',timestep]
                + backend_model.carrier_prod[f'{asset_loc}::{charger_tech}:{object}::{charger_carrier}',timestep]) == 0

    # Add the constraint
    model.backend.add_constraint(constraint_name, constraint_sets, connect_battery_connector_flow_constraint)

def add_limit_charger_flow_constraint(model, object,asset_loc,storage_tech,charger_tech,charger_carrier,charge_to_discharge_ratio):

    #### Limit the charger flow capacity to the battery by the total number of aircrafts currently powered by eGPUs
    # Define the constraint
    constraint_name = f'limit_charger_flow_{asset_loc}_constraint'
    constraint_sets = ['timesteps']

    # TODO couple too resource "aircraft on stand" to improve constraint for PCA demand with variable power per aircraft
    def limit_charger_flow_constraint_rule(backend_model, timestep):
        return (backend_model.carrier_prod[f'{asset_loc}::{charger_tech}:{object}::{charger_carrier}',timestep]
            # <= backend_model.energy_cap[f'{object}::{charger_tech}:{asset_loc}'] - backend_model.carrier_prod[f'{asset_loc}::{storage_tech}::{charger_carrier}',timestep]*charge_to_discharge_ratio)
            <= backend_model.energy_cap[f'{asset_loc}::{storage_tech}']*backend_model.timestep_resolution[timestep] - backend_model.carrier_prod[f'{asset_loc}::{storage_tech}::{charger_carrier}',timestep]*charge_to_discharge_ratio)

    # Add the constraint
    model.backend.add_constraint(constraint_name, constraint_sets, limit_charger_flow_constraint_rule)

def add_couple_charger_to_vehicle_linear_constraint(model,object,asset_loc,charger_tech,storage_tech):
    #### Hard couple the battery quantity of an asset/vehicle type to the quantity of that asset/vehicle
    # Define the constraint
    constraint_name = f'couple_charger_to_vehicle_linear_{asset_loc}_constraint'
    constraint_sets = []
    

    def couple_charger_to_vehicle_linear_constraint_rule(backend_model):

        return backend_model.energy_cap[f'{object}::{charger_tech}:{asset_loc}'] <= (
            backend_model.energy_cap[f'{asset_loc}::{storage_tech}']
        )

    # Add the constraint
    model.backend.add_constraint(constraint_name, constraint_sets, couple_charger_to_vehicle_linear_constraint_rule)

def add_market_synchronous_supply_demand_constraint(model):
    #### Hard couple the battery quantity of an asset/vehicle type to the quantity of that asset/vehicle
    # Define the constraint
    constraint_name = 'market_synchronous_supply_demand_constraint'
    constraint_sets = ['timesteps']
    
    def market_synchronous_supply_demand_constraint_rule(backend_model,timestep):

        return backend_model.prod_con_switch['market_demand::free_transmission:ALLIANDER',timestep] == (
    backend_model.prod_con_switch['ALLIANDER::free_transmission:market_supply',timestep])

    # Add the constraint
    model.backend.add_constraint(constraint_name, constraint_sets, market_synchronous_supply_demand_constraint_rule)
    
def add_limit_curtailment_constraint(model,renewable_tech,curtailment_tech,loc):
    #### Hard couple the battery quantity of an asset/vehicle type to the quantity of that asset/vehicle
    # Define the constraint
    constraint_name = 'limit_curtailment_constraint'
    constraint_sets = ['timesteps']
    
    def limit_curtailment_constraint_rule(backend_model,timestep):

        return -backend_model.carrier_con[f'{loc}::{curtailment_tech}',timestep] <= (
    0.3*backend_model.energy_cap[f'{loc}::{renewable_tech}'])

    # Add the constraint
    model.backend.add_constraint(constraint_name, constraint_sets, limit_curtailment_constraint_rule)
    