from cosim_toolbox.dbms import create_metadata_manager

scenario_in = {
    "analysis": "example_analysis",
    "federation": "example_federation",
    "start_time": 0.0,
    "stop_time": 10.0,
    "docker": False,
}

# Defaults to storing in ./meta_store
# to change storage location supply path as "location" keyword argument 
# to create_metadata_manager.
with create_metadata_manager(backend="json") as mgr:
    mgr.writer.write_scenario(
        name="example_scenario", scenario_data=scenario_in, overwrite=True
    )
    print(f"scenarios: {mgr.list_scenarios()}")
    print(f"federations: {mgr.list_federations()}")
    scenario_out = mgr.read_scenario(name="example_scenario")

print(scenario_out)
