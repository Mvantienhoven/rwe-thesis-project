
import os
import pyomo.environ as pyo
import pandas as pd
# import plotly.express as px
import sys

import calliope as cp


# from run_calliope_manual_constraints import *
from calliope_customize_constraints_dicts import load_constraint_dicts


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
    