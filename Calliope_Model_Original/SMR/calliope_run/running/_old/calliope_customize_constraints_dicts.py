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
    
# def load_curtailment_dicts(scenario):
    
#     if 'solar' in scenario:
        
        
#         loc_dict = {
#             'energyhotspot_airside',
#             'energyhotspot_noord',
#             'energyhotspot_zuidoost',
#             }
        
#         if '2050' in scenario:
#             loc_dict += {'onshore_solar_farm'}
            
#         renewable_tech_dict = {
#             'energyhotspot_airside':['pv_utility','st_utility'],
#             'energyhotspot_noord':['pv_utility','st_utility'],
#             'energyhotspot_zuidoost':['pv_utility','st_utility'],
#             'onshore_solar_farm':['pv_utility'],
#                                }
        
#         curtailment_tech_dict = {
#             'energyhotspot_airside':['curtailment_electricity','curtailment_heat'],
#             'energyhotspot_noord':['curtailment_electricity','curtailment_heat'],
#             'energyhotspot_zuidoost':['curtailment_electricity','curtailment_heat'],
#             'onshore_solar_farm':['curtailment_electricity'],
#                                }
        
#     if 'wind' in scenario:
        
        
#         loc_dict = {
#             'offshore_wind_farm',
#             'energyhotspot_airside',
#             'energyhotspot_noord',
#             'energyhotspot_zuidoost',
#             }
        
#         if '2050' in scenario:
#             loc_dict += {'onshore_solar_farm'}
            
#         renewable_tech_dict = {
#             'energyhotspot_airside':['pv_utility','st_utility'],
#             'energyhotspot_noord':['pv_utility','st_utility'],
#             'energyhotspot_zuidoost':['pv_utility','st_utility'],
#             'onshore_solar_farm':['pv_utility'],
#                                }
#         curtailment_tech_dict = {
#             'energyhotspot_airside':['curtailment_electricity','curtailment_heat'],
#             'energyhotspot_noord':['curtailment_electricity','curtailment_heat'],
#             'energyhotspot_zuidoost':['curtailment_electricity','curtailment_heat'],
#             'onshore_solar_farm':['curtailment_electricity'],
#                                }
    
#     return (
#         loc_dict,
#         renewable_tech_dict,
#         curtailment_tech_dict,
#     )