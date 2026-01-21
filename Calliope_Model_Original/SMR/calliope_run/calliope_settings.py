calliope_run_settings = {
    # Run settings amd logging
    "model":                    'Calliope_Dutch_Multinode_SMR', # dutch_calliope_single_node, dutch_calliope_multi_node, dutch_calliope_multi_node_cleaned
    "test":                     True, 
    "calliope_log_verbosity":   'info', # info/debug
    "skip_when_failed":         False,
    'trace_memory_allocation':  True,
    'write_log_file':           True,
    
    # Output settings
    "save_plots":               True,
    "save_models":              True,
    'mapbox_access_token':      'pk.eyJ1IjoiZnZhbmRlYmVlayIsImEiOiJjbDd5ZGZycXkxMHp3M3Bxa3k1enpqcDk1In0.gDODqzk_bv1ChMnqPIp3EQ',
    
    # Customization of Calliope
    "shadowprices":             False,
    "custom_constraints":       False,
    "custom_constraints_exceptions": [None],
    "scenarios": [
        None,
        
        # 'spores_method_rel',
        
        # # ## Reference single optimusation
        # # 'reference_opt',
        
        # ## Reference spores (200 results each)
        # 'reference_spores',

        # ## Min/max cases (5 results each)
        # # Wind
        # 'reference_max_wind',
        # 'reference_min_wind',
        # # Nuclear
        # 'reference_max_nuclear',
        # 'reference_min_nuclear',
        # # Solar
        # 'reference_max_pv',
        # 'reference_min_pv',
        # # Storage
        # 'reference_max_battery',
        # 'reference_min_battery',
        # # Electrolysers
        # 'reference_max_electrolyser',
        # 'reference_min_electrolyser',
        # # Reformers
        # 'reference_max_reformer',
        # 'reference_min_reformer',
        # # Interconnection
        # 'reference_max_interconnector',
        # 'reference_min_interconnector',
        # # Import terminals
        # 'reference_max_terminal',
        # 'reference_min_terminal',
        
        # ## Scoring methods (100 results each)
        # 'spores_method_int',
        # 'spores_method_evoavg',

        # ## Spores numbers
        # # 'spores_no_200',
        # # 'spores_no_400',

        # ## Slack values (100 each)
        # 'spores_slack_10',
        # 'spores_slack_05',
        
        # ## Nuclear capacities (100 each)
        # # 'spores_fix_nuclear_1GW',
        # # 'spores_fix_nuclear_2GW',
        # 'spores_fix_nuclear_4GW',
        
        ],
    
}

calliope_postprocess_settings = {
    
    ## @ISAI hier 
    'run_tag': 'results_20240819-190804_dutch_calliope_single_node',
    
    'test_postprocessor': True,
    'test_with_n':2,
    'skip_cases_when_testing':['spores_eur_2050'],
    
    'print_kpis': [
        # 'load_kpis',
        'merge_kpis',
        ],
    # `load_kpis` contains all KPIs that need to be LOADED in for succesful postprocessing of the data. The structure is a dict with the type of the KPI data (string, float, integer, boolean).
    # `map_kpis` contains all KPIs that need to be MAPPED onto the data of the other LOAD KPIs, e.g. names or color codes.
    # `derive_kpis` contains all KPIs that need to be DERIVED and ADDED to the results, as they are not part of Calliope output, e.g. curtailed load of renewables.
    # `include_resource_techs` contains all substrings of tech names (as implemented in calliope, e.g. pv_rooftop) which need to be INCLUDED from the available_resource calculation. Can be substrings like 'pv' or 'wind' instead of full tech names. These will be automatically used to calculated the residual load of the system.
    # `exclude_resource_techs` contains all substrings of tech names (as implemented in calliope, e.g. import_gas) which need to be EXCLUDED from the available_resource calculation. Can be substrings like 'import' or 'im' instead of full tech names.
    # 
    
    "load_kpis" : {
        # Inputs
        'names':    str, 
        'colors':   str, 
        'inheritance':          str, 
        'force_resource':       str,
        'loc_coordinates':      str,
        
        # 'inputs_lookup_loc_carriers':     str,
        'lookup_loc_techs':     str,
        'lookup_loc_techs_conversion':      str,
        'lookup_loc_techs_conversion_plus': str,
        'resource_unit':    str,
        'resource_scale':   float,
        'distance':         float,
        
        'resource': float, # resource available to supply and demand technologies.
        'timestep_resolution': float, # Resolution of timestep in relation to energy_cap unit
        ## Outputs
        # Costs
        'cost':                         float, # {'name':'Installed capacity [GW]','type':float,'unit':'MEUR/a'},
        'cost_investment':              float,
        'cost_depreciation_rate':       float,
        'cost_energy_cap':              float,
        'cost_storage_cap':             float,
        'cost_om_annual':               float,
        'cost_om_annual_investment_fraction':   float,
        'cost_om_con':                  float,
        'cost_om_prod':                 float,
        # 'cost_var':                     float, # Can be derived from `cost` and `cost_investment`
        
        # 
        'total_levelised_cost':         float,
        'systemwide_levelised_cost':    float,
        
        # Deployment
        'energy_cap':                   float,
        'storage_cap':                  float,
        'resource_area':                float,
        
        # Productivity
        'carrier_prod':                 float,
        'carrier_con':                  float,
        'systemwide_capacity_factor':   float,
        
        'resource_con':                 float,
        'required_resource':            float,
        'available_resource':           float,
        'storage':                      float,
        'unmet_demand':                 float,
        
        # 'carrier_export':               float,
        # 'cost_var':                     float,
    },

    "map_kpis" : [],
    # "map_kpis" : [
    #     # KPIs to map
    #     'names', 
    #     'colors', 
    #     'inheritance',
    #     'loc_coordinates',
    #     'lookup_loc_techs',
    #     'lookup_loc_techs_conversion',
    #     'lookup_loc_techs_conversion_plus',
    # ],
    
    "derive_kpis" : [
        # Outputs
        'levelized_cost',
        'capacity_factor',
        'available_resource',
        'curtailed_resource',
        'residual_load',
        'annual_totals',
        # values_flows
        
        # 'energy_cap',
        # 'storage_cap',
        # 'resource_area',
        ],

    # Specify which resource techs to include in calculating curtailment.
    "include_resource_techs" : ['pv','wind'],
    "exclude_resource_techs" : ['supply'],
    
    # This dictionary defines what KPIs are to be merged/mapped together.
    # The dictinary key is the name of the dataframe as it is added to the "solved_models" set.
    # The first KPI entry is always the "parent dataframe" to which the other KPIs are mapped.
    # Make sure they have overlapping indices (sharing either of "tech", "loc", "time", "carrier"), can be multiple
    
    "merge_kpis" : {
        "loc_tech_kpis":[
            # Loaded
            'energy_cap', # :'Installed capacity [GW]'
            'energy_eff', # :'Energy efficiency [%]'
            'resource_area', # :'Resource area [kHa/GW]'
            'cost', # :'Total cost [MEUR/a]'
            'cost_investment', # :'Investment cost [MEUR/a]'
            'cost_depreciation_rate', # :'CAPEX depreciation rate [% of CAPEX/a]'
            'cost_energy_cap', # :'CAPEX [MEUR/GW]'
            'cost_storage_cap', # :'CAPEX [MEUR/GWh]'
            'cost_om_annual', # :'Fixed O&M [MEUR/GW/a]'
            'cost_om_annual_investment_fraction', # :'Fixed O&M [% of CAPEX/a]'
            'cost_om_con', # :'Energy O&M [MEUR/GWh]'
            'cost_om_prod', # :'Variable O&M [MEUR/GWh]'
            'distance',  # :'Transmission distance [m]'
            
            # 'total_cost_var',
            'names',  # :'Technology name'
            'colors',   # :'Technology color'
            'inheritance',  # :'Technology inheritance'
            'loc_coordinates',  # :'Technology name'
            
            'lookup_loc_techs',
            'lookup_loc_techs_conversion',
            'lookup_loc_techs_conversion_plus',
            
            # Derived
            'loctech_levelized_cost',   # :'Technology LCOE [MEUR/GWh]'
            'loctech_capacity_factor',  # :'Technology capacity factor [%]'
            'total_curtailed_resource',   # :'Curtailed resource [GWh/a]'
            'total_available_resource',   # :'Available resource [GWh/a]'
            'total_carrier_prod',   # :'Carrier consumed [GWh/a]'
            'total_carrier_con',   # :'Carrier produced [GWh/a]'
        ],
        "loc_carrier_kpis":[
            # target
            'total_unmet_demand',
            
            # sources
            'total_levelised_cost',
            
            'total_residual_load',
            'total_system_imbalance',
        
            'systemwide_levelized_cost',
            'systemwide_capacity_factor',
            ],
        }
}