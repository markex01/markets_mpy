# Mapping dicts for Aurora data processing
# Take into account that for any new country added in the config/api_params.yaml,
# a corresponding entry should be added here if not already present.

region_tracker_map = {
    'esp': 'Spain',
    'fra': 'France',
    'deu': 'Germany',
    'ita': 'Italy',
    'pol': 'Poland',
    'prt': 'Portugal',
    'irx': 'Ireland',
    'gbr': 'GB',
    'ita_cal': 'Italy Calabria',
    'ita_cnor': 'Italy Central North',
    'ita_csud': 'Italy Central South',
    'ita_nor': 'Italy North',
    'ita_sar': 'Italy Sardinia',
    'ita_sic': 'Italy Sicily',
    'ita_sud': 'Italy South',
}

country_tracker_map = {
    'esp': 'Spain',
    'fra': 'France',
    'deu': 'Germany',
    'ita': 'Italy',
    'ita_cal': 'Italy',
    'ita_cnor': 'Italy',
    'ita_csud': 'Italy',
    'ita_nor': 'Italy',
    'ita_sar': 'Italy',
    'ita_sic': 'Italy',
    'ita_sud': 'Italy',
    'pol': 'Poland',
    'prt': 'Portugal',
    'irx': 'Ireland',
    'gbr': 'GB',
}

# Mapping for Curtailed/uncurtailed column in processed dataframe
curtailment_type_dict = {
    "Uncurtailed capture price" : "Uncurtailed",
    "Curtailed capture price (M0)" : "Curtailed",
    "M0 reference price" : "Curtailed",
    "Capture price curtailed - fleet wide" : "Curtailed",
    "Capture price curtailed below zero" : "Curtailed below zero",
}

# Mapping for Scope column in prices dataframe
commodity_scope_dict = {
    "Baseload price" : "Baseload",
    "Carbon price" : "Commodity",
    "Gas price" : "Commodity",
    "Coal price" : "Commodity",
}

demand_drivers_tracker_mappings = {
    'Data centre demand' : 'Data centre',
    'EV demand' : 'Electric Vehicles',
    'Electric heat demand' : 'Electric heating',
    'Electrolyser demand' : 'Electrolysis',
    'Peak demand' : 'Peak demand',
    'Total demand' : 'Electricity demand'
}