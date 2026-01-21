

reference_case = {
    'case':'base',
    'year':'2019',
    'scenario':'historic',
    'solution':'business as usual',
    }

# A list of KPIs is declared here, always include these KPIs or the routine may fail
input_kpi_list = [
    # Inputs
    'names', 
    'colors', 
    'inheritance', 
    'force_resource',
    'loc_coordinates',
    'lookup_loc_techs',
    'lookup_loc_techs_conversion',
    'lookup_loc_techs_conversion_plus',
    'resource_unit',
    'resource_scale',
    'distance',
]

map_kpi_list = [
    # KPIs to map
    'names', 
    'colors', 
    'inheritance',
    'loc_coordinates',
    'lookup_loc_techs',
    'lookup_loc_techs_conversion',
    'lookup_loc_techs_conversion_plus',
]
output_kpi_list = [
    # Outputs
    'cost',
    'cost_investment',
    'total_levelised_cost',
    'systemwide_levelised_cost',
    'systemwide_capacity_factor',
    'energy_cap',
    'storage_cap',
    'resource_area',
    ]

# This list contains the KPIs which are temporal
timeseries_kpi_list = [
    # Inputs
    'resource', # resource available to supply and demand technologies.
    
    # Outputs
    'carrier_prod',
    'carrier_con',
    # 'carrier_export',
    'resource_con',
    'required_resource',
    'available_resource',
    'storage',
    'unmet_demand',
    'resource',
    # 'cost_var',
    ]

mapplotter_kpi_list = [
    'names', 
    'loc_coordinates',
    'lookup_loc_carriers',
    'colors', 
    'energy_cap',
    
    'inheritance', 
]