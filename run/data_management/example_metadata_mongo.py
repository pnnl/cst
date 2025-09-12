from cosim_toolbox.dbms import create_metadata_manager

scenario_in = {
    "analysis": "example_analysis",
    "federation": "example_federation",
    "start_time": 0.0,
    "stop_time": 10.0,
    "docker": False,
}

# Either set environment variable CST_HOST=server_address 
# or supply as "location" keyword argument to create_timeseries_manager.
with create_metadata_manager(backend="mongo") as mgr:
    mgr.writer.write_scenario(
        name="example_scenario", scenario_data=scenario_in, overwrite=True
    )
    print(f"scenarios: {mgr.reader.list_scenarios()}")
    scenario_out = mgr.reader.read_scenario(name="example_scenario")

print(scenario_out)
