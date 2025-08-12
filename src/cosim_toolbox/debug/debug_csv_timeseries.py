import pytest
from datetime import datetime, timedelta
from cosim_toolbox.metadata_factory import create_metadata_manager
from data_management.timeseries_factory import create_timeseries_manager
from cosim_toolbox.data_management import TSRecord
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

sample_federation_data = {
    "federation": {
        "Battery": {
            "logger": False,
            "image": "cosim-cst:latest",
            "command": "python3 simple_federate.py Battery MyScenario",
            "federate_type": "value",
            "HELICS_config": {
                "name": "Battery",
                "core_type": "zmq",
                "log_level": "warning",
                "period": 60,
                "uninterruptible": False,
                "terminate_on_error": True,
                "wait_for_current_time_update": True,
                "publications": [
                    {
                        "global": True,
                        "key": "Battery/EV1_current",
                        "type": "double",
                        "unit": "A",
                    }
                ],
                "subscriptions": [
                    {"key": "EVehicle/EV1_voltage", "type": "double", "unit": "V"}
                ],
            },
        },
        "EVehicle": {
            "logger": False,
            "image": "cosim-cst:latest",
            "command": "python3 simple_federate.py EVehicle MyScenario",
            "federate_type": "value",
            "HELICS_config": {
                "name": "EVehicle",
                "core_type": "zmq",
                "log_level": "warning",
                "period": 60,
                "uninterruptible": False,
                "terminate_on_error": True,
                "wait_for_current_time_update": True,
                "publications": [
                    {
                        "global": True,
                        "key": "EVehicle/EV1_voltage",
                        "type": "double",
                        "unit": "V",
                    }
                ],
                "subscriptions": [
                    {"key": "Battery/EV1_current", "type": "double", "unit": "A"}
                ],
            },
        },
    }
}


sample_scenario_data = {
    "schema": "MySchema",
    "federation": "MyFederation",
    "start_time": "2023-12-07T15:31:27",
    "stop_time": "2023-12-08T15:31:27",
    "docker": False,
}


def test_complete_simulation_workflow(temp_directory):
    """Test complete workflow: metadata + time-series data."""

    # Step 1: Set up metadata
    metadata_manager = create_metadata_manager("json", temp_directory + "/metadata")
    timeseries_manager = create_timeseries_manager(
        "csv", temp_directory + "/timeseries", analysis_name="MyAnalysis"
    )

    with metadata_manager, timeseries_manager:
        # Store federation and scenario configuration
        metadata_manager.write_federation("MyFederation", sample_federation_data)
        metadata_manager.write_scenario("MyScenario", sample_scenario_data)

        # Step 2: Simulate federate execution generating time-series data
        base_time = datetime.now()
        simulation_records = []

        # Simulate Battery federate data over 5 minutes
        for minute in range(5):
            sim_time = float(minute * 60)  # 0, 60, 120, 240, 300 seconds

            # Battery current varies
            current_value = 10.0 + (minute * 2.0)  # 10, 12, 14, 16, 18 Amps
            simulation_records.append(
                TSRecord(
                    real_time=base_time + timedelta(seconds=sim_time),
                    sim_time=sim_time,
                    scenario="MyScenario",
                    federate="Battery",
                    data_name="Battery/EV1_current",
                    data_value=current_value,
                )
            )

            # EVehicle voltage is more stable
            voltage_value = 120.0 + (minute * 0.5)  # 120, 120.5, 121, 121.5, 122 Volts
            simulation_records.append(
                TSRecord(
                    real_time=base_time + timedelta(seconds=sim_time),
                    sim_time=sim_time,
                    scenario="MyScenario",
                    federate="EVehicle",
                    data_name="EVehicle/EV1_voltage",
                    data_value=voltage_value,
                )
            )

        # Write time-series data
        success = timeseries_manager.write_records(simulation_records)
        assert success is True

        # Step 3: Verify we can query the data using metadata context
        scenario = metadata_manager.read_scenario("MyScenario")
        federation = metadata_manager.read_federation(scenario["federation"])

        # Get the federates from metadata
        federates = list(federation["federation"].keys())
        assert set(federates) == {"Battery", "EVehicle"}

        # Verify time-series data exists for each federate
        for federate_name in federates:
            df = timeseries_manager.read_data(
                scenario_name="MyScenario", federate_name=federate_name
            )
            assert len(df) == 5  # 5 time points
            assert all(df["scenario"] == "MyScenario")
            assert all(df["federate"] == federate_name)

        # Step 4: Analyze the simulation results

        # Get Battery current over time
        battery_df = timeseries_manager.read_data(
            scenario_name="MyScenario",
            federate_name="Battery",
            data_name="Battery/EV1_current",
        )

        assert len(battery_df) == 5
        assert battery_df["data_value"].min() == 10.0
        assert battery_df["data_value"].max() == 18.0

        # Get EVehicle voltage over time
        evehicle_df = timeseries_manager.read_data(
            scenario_name="MyScenario",
            federate_name="EVehicle",
            data_name="EVehicle/EV1_voltage",
        )

        assert len(evehicle_df) == 5
        assert evehicle_df["data_value"].min() == 120.0
        assert evehicle_df["data_value"].max() == 122.0

        # Step 5: Verify time-based analysis
        time_range = timeseries_manager.get_time_range(scenario_name="MyScenario")
        assert time_range["min_time"] == 0.0
        assert time_range["max_time"] == 240.0  # 4 minutes

        # Get data for middle portion of simulation
        mid_df = timeseries_manager.read_data(
            scenario_name="MyScenario",
            start_time=60.0,
            duration=120.0,  # From 1 minute to 3 minutes
        )

        assert len(mid_df) == 4  # 2 federates * 2 time points (60, 120)
        assert mid_df["sim_time"].min() == 60.0
        assert mid_df["sim_time"].max() == 120.0


if __name__ == "__main__":
    test_complete_simulation_workflow("src/cosim_toolbox/debug/data")
