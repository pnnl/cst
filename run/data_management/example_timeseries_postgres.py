from cosim_toolbox.dbms import create_timeseries_manager, TSRecord
from datetime import datetime

records = [
    TSRecord(
        real_time=datetime.now(),
        sim_time=0,
        scenario="test_scenario",
        federate="test_fed",
        data_name="value",
        data_value=1,
    ),
    TSRecord(
        real_time=datetime.now(),
        sim_time=0,
        scenario="test_scenario",
        federate="test_fed",
        data_name="value",
        data_value=2.0,
    ),
    TSRecord(
        real_time=datetime.now(),
        sim_time=0,
        scenario="test_scenario",
        federate="test_fed",
        data_name="value",
        data_value=True,
    ),
    TSRecord(
        real_time=datetime.now(),
        sim_time=0,
        scenario="test_scenario",
        federate="test_fed",
        data_name="value",
        data_value="hello world",
    ),
]

with create_timeseries_manager(backend="postgres", analysis_name="example_data") as mgr:
    mgr.delete_scenario_data(scenario_name="test_scenario")
    mgr.write_records(records=records)
    print(f"scenarios: {mgr.list_scenarios()}")
    print(f"federates: {mgr.list_federates()}")
    print(f"data_types: {mgr.list_data_types()}")
    df = mgr.read_data(scenario_name="test_scenario")


print(df.head())
