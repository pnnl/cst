from cosim_toolbox import pg_data_db, csv_data_db
from cosim_toolbox.dbms import HybridCSVtoPostgresManager, TSRecord
from datetime import datetime

# Initialize the hybrid manager
manager = HybridCSVtoPostgresManager(
    csv_location=csv_data_db["location"],
    analysis_name="test_hybrid_backend_analysis",
    **pg_data_db
)

# Use as a context manager
with manager:
    # Write data to CSV during operation
    record = TSRecord(
        real_time=datetime.now(),
        sim_time=1.0,
        scenario="test_scenario",
        federate="fed1",
        data_name="value1",
        data_value=42.0,
    )
    manager.add_record(record)
    data = manager.read_data(scenario_name="test_hybrid_backend")
    print(data)
    manager.flush()
    data = manager.read_data(scenario_name="test_hybrid_backend")
    print(data)

# Upon exiting the context, data is uploaded to PostgreSQL
# Subsequent read operations will use the PostgreSQL backend if upload succeeded
data = manager.read_data(scenario_name="test_hybrid_backend")
print(data)
