from cosim_toolbox.dbms import create_metadata_manager, create_timeseries_manager


meta_backend = "json"
#meta_backend = "mongo"
#data_backend = "csv"
data_backend = "parquet"
#data_backend = "postgres"


# Defaults to storing in ./meta_store
# to change storage location supply path as "location" keyword argument 
# to create_metadata_manager.
with create_metadata_manager(backend=meta_backend) as md_mgr:
    md_federation_name = md_mgr.reader.list_federations()[0]
    md_scenario_name = md_mgr.reader.list_scenarios()[0]
    print(f"Metadata scenario name: {md_scenario_name}")
    print(f"Metadata federation name: {md_federation_name}")
    scenario = md_mgr.reader.read_scenario(name=md_scenario_name)
    md_analysis_name = scenario['analysis']
    print(f"Metadata analysis name: {md_analysis_name}")
    federation = md_mgr.reader.read_federation(name=md_federation_name)
    #print(f"federation dictionary: {federation}")
    federates = list(federation["federation"].keys())
    print(f"Metadata federates list: {federates}")


# Defaults to storing in ./data_store
# to change storage location supply path as "location" keyword argument 
# to create_timeseries_manager.
with create_timeseries_manager(backend=data_backend, analysis_name=md_analysis_name) as ts_mgr:
    # Arbitrarily choosing to look at the data from the first federate
    ts_scenarios_list = ts_mgr.list_scenarios()
    print(f"Time-series scenarios list: {ts_scenarios_list}")
    ts_federates_list = ts_mgr.list_federates()
    print(f"Time-series federates list: {ts_federates_list}")
    ts_data_types_list = ts_mgr.list_data_types()
    print(f"Time-series data types list: {ts_data_types_list}")
    ts_range = ts_mgr.get_time_range(scenario_name=md_scenario_name)
    print(f"Time-series range: {ts_range}")
    df = ts_mgr.read_data(scenario_name=md_scenario_name, federate_name=ts_federates_list[0], data_type='hdt_endpoint')
    print(df.head(-1))
    df = ts_mgr.read_data(scenario_name=md_scenario_name, federate_name=ts_federates_list[1], data_type='hdt_endpoint')
    print(df.head(-1))
