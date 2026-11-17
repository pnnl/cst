from datetime import datetime

from cosim_toolbox.dbms import create_timeseries_manager
from cosim_toolbox.dbms.time_series_record import TSRecord

records = [
    TSRecord(datetime.now(), 0, "test_scenario", "test_fed", "value", 1),
    TSRecord(datetime.now(), 0, "test_scenario", "test_fed", "value", 2.0),
    TSRecord(datetime.now(), 0, "test_scenario", "test_fed", "value", True),
    TSRecord(datetime.now(), 0, "test_scenario", "test_fed", "value", "hello world"),
    TSRecord(datetime.now(), 1, "test_scenario", "test_fed", "value", "hello world"),
    TSRecord(datetime.now(), 0, "test_scenario", "test_fed", "value", "hello world", "receiver_endpoint", "receiver"),
    TSRecord(datetime.now(), 0, "test_scenario", "test_fed2", "value", "hello world"),
    TSRecord(datetime.now(), 0, "test_scenario", "test_fed2", "value", "hello world", "receiver_endpoint", "receiver"),
    TSRecord(datetime.now(), 0, "test_scenario", "test_fed3", "value", 1),
    TSRecord(datetime.now(), 0, "test_scenario", "test_fed3", "value", 2.0),
]

with create_timeseries_manager(backend="postgres", analysis_name="example_data") as mgr:
    mgr.connect()
    mgr.delete_scenario_data(scenario_name="test_scenario")
    mgr.write_records(records=records)
    print(f"scenarios: {mgr.list_scenarios()}")
    print(f"federates: {mgr.list_federates()}")
    print(f"data_types: {mgr.list_data_types()}")
    df = mgr.read_data(
        scenario_name="test_scenario",
        federate_name=["test_fed", "test_fed2"],
    )


print(df.sort_values("real_time"))
