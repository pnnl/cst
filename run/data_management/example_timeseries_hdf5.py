"""
Example: writing and reading time-series data with the HDF5 backend.

Run from this directory:  python example_timeseries_hdf5.py
Data is written to ./data_store/example_data/<federate>.h5
"""
from datetime import UTC, datetime, timedelta

from cosim_toolbox.dbms import create_timeseries_manager
from cosim_toolbox.dbms.time_series_record import TSRecord

start = datetime(2026, 1, 1, tzinfo=UTC)
records = [
    TSRecord(start, 0, "test_scenario", "test_fed", "test_fed/integer", 1),
    TSRecord(start, 0, "test_scenario", "test_fed", "test_fed/double", 2.0),
    TSRecord(start, 0, "test_scenario", "test_fed", "test_fed/boolean", True),
    TSRecord(start, 0, "test_scenario", "test_fed", "test_fed/complex", 1 + 2j),
    TSRecord(start, 0, "test_scenario", "test_fed", "test_fed/string", "hello world"),
    TSRecord(start, 0, "test_scenario", "test_fed", "test_fed/vector", [1.0, 2.0, 3.0]),
    TSRecord(start, 0, "test_scenario", "test_fed", "test_fed/complex_vector", [1 + 1j, 2 - 2j],
             data_type="hdt_complex_vector"),
    TSRecord(start, 0, "test_scenario", "test_fed", "test_fed/endpoint", b"\x00\x01binary",
             "test_fed2", "test_fed2/receiver"),
    TSRecord(start + timedelta(seconds=1), 1, "test_scenario", "test_fed2", "test_fed2/double", 4.5),
]

# Defaults to storing in ./data_store; supply a "location" keyword argument to change it.
with create_timeseries_manager(backend="hdf5", analysis_name="example_data") as mgr:
    for federate in ("test_fed", "test_fed2"):  # start fresh, removing only this example's own data
        if federate in mgr.list_federates():
            mgr.delete_federate_data(federate_name=federate)
    for record in records:          # buffered writing, as CST federates do
        mgr.add_record(record)
    assert mgr.flush(), "flush failed; see the log"
    print(f"scenarios:  {mgr.list_scenarios()}")
    print(f"federates:  {mgr.list_federates()}")
    print(f"data_types: {mgr.list_data_types()}")
    df = mgr.read_data(scenario_name="test_scenario", federate_name=["test_fed", "test_fed2"])
# leaving the "with" block consolidates the data into one file per federate

print(df[["sim_time", "federate", "data_name", "data_value"]].to_string())
