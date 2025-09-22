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
    TSRecord(
        real_time=datetime.now(),
        sim_time=1,
        scenario="test_scenario",
        federate="test_fed",
        data_name="value",
        data_value="hello world",
    ),
    TSRecord(
        real_time=datetime.now(),
        sim_time=0,
        scenario="test_scenario",
        federate="test_fed",
        data_name="value",
        data_value="hello world",
        receiving_endpoint="receiver_endpoint",
        receiving_federate="receiver",
    ),
    TSRecord(
        real_time=datetime.now(),
        sim_time=0,
        scenario="test_scenario",
        federate="test_fed2",
        data_name="value",
        data_value="hello world",
    ),
    TSRecord(
        real_time=datetime.now(),
        sim_time=0,
        scenario="test_scenario",
        federate="test_fed2",
        data_name="value",
        data_value="hello world",
        receiving_endpoint="receiver_endpoint",
        receiving_federate="receiver",
    ),
    TSRecord(
        real_time=datetime.now(),
        sim_time=0,
        scenario="test_scenario",
        federate="test_fed3",
        data_name="value",
        data_value=1,
    ),
    TSRecord(
        real_time=datetime.now(),
        sim_time=0,
        scenario="test_scenario",
        federate="test_fed3",
        data_name="value",
        data_value=2.0,
    ),
]

# Defaults to storing in ./data_store
# to change storage location supply path as "location" keyword argument
# to create_timeseries_manager.
with create_timeseries_manager(backend="csv", analysis_name="example_data") as mgr:
    mgr.delete_federate_data(federate_name="test_fed")
    mgr.delete_federate_data(federate_name="test_fed2")
    mgr.delete_federate_data(federate_name="test_fed3")
    mgr.write_records(records=records)
    print(f"scenarios: {mgr.list_scenarios()}")
    print(f"federates: {mgr.list_federates()}")
    print(f"data_types: {mgr.list_data_types()}")
    print(mgr.helper.analysis_name)
    df = mgr.read_data(
        scenario_name="test_scenario",
        federate_name=["test_fed", "test_fed2"],
    )

print(df.sort_values("real_time"))
