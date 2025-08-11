"""
Integration tests for CSV time-series with metadata management.
"""

import pytest
from datetime import datetime, timedelta
from cosim_toolbox.metadata_factory import create_metadata_manager
from cosim_toolbox.timeseries_factory import create_timeseries_manager
from cosim_toolbox.data_management import TSRecord


class TestCSVIntegration:
    """Integration tests for CSV time-series with metadata."""

    def test_complete_simulation_workflow(
        self, temp_directory, sample_federation_data, sample_scenario_data
    ):
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
                voltage_value = 120.0 + (
                    minute * 0.5
                )  # 120, 120.5, 121, 121.5, 122 Volts
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

            assert len(mid_df) == 4  # 2 federates * 2 time points (60, 120, 180)
            assert mid_df["sim_time"].min() == 60.0
            assert mid_df["sim_time"].max() == 120.0

    def test_multi_scenario_analysis(self, temp_directory):
        """Test analysis across multiple scenarios."""

        timeseries_manager = create_timeseries_manager(
            "csv", temp_directory, analysis_name="MultiScenario"
        )

        with timeseries_manager:
            base_time = datetime.now()

            # Create data for two different scenarios
            scenarios = ["Scenario_A", "Scenario_B"]
            records = []

            for scenario in scenarios:
                for minute in range(3):
                    sim_time = float(minute * 60)

                    # Different behavior for each scenario
                    if scenario == "Scenario_A":
                        value = 10.0 + minute  # Linear increase
                    else:
                        value = 20.0 - minute  # Linear decrease

                    records.append(
                        TSRecord(
                            real_time=base_time + timedelta(seconds=sim_time),
                            sim_time=sim_time,
                            scenario=scenario,
                            federate="TestFed",
                            data_name="test_data",
                            data_value=value,
                        )
                    )

            timeseries_manager.write_records(records)

            # Analyze scenarios separately
            scenario_a_df = timeseries_manager.read_data(scenario_name="Scenario_A")
            scenario_b_df = timeseries_manager.read_data(scenario_name="Scenario_B")

            assert len(scenario_a_df) == 3
            assert len(scenario_b_df) == 3

            # Verify different trends
            assert scenario_a_df["data_value"].is_monotonic_increasing
            assert scenario_b_df["data_value"].is_monotonic_decreasing

            # Verify scenario list
            scenarios = timeseries_manager.get_scenarios()
            assert set(scenarios) == {"Scenario_A", "Scenario_B"}

    def test_federate_pub_sub_analysis(self, temp_directory, sample_federation_data):
        """Test analyzing publication/subscription relationships with time-series data."""

        metadata_manager = create_metadata_manager("json", temp_directory + "/metadata")
        timeseries_manager = create_timeseries_manager(
            "csv", temp_directory + "/timeseries", analysis_name="PubSub"
        )

        with metadata_manager, timeseries_manager:
            # Store federation configuration
            metadata_manager.write_federation("TestFed", sample_federation_data)

            # Extract pub/sub information from metadata
            federation = metadata_manager.read_federation("TestFed")
            battery_config = federation["federation"]["Battery"]["HELICS_config"]
            evehicle_config = federation["federation"]["EVehicle"]["HELICS_config"]

            battery_pub = battery_config["publications"][0]["key"]
            evehicle_sub = evehicle_config["subscriptions"][0]["key"]

            # Verify they match (Battery publishes what EVehicle subscribes to)
            assert battery_pub == evehicle_sub == "Battery/EV1_current"

            # Generate corresponding time-series data
            base_time = datetime.now()
            records = []

            for minute in range(3):
                sim_time = float(minute * 60)
                current_value = 10.0 + minute

                # Battery publishes current
                records.append(
                    TSRecord(
                        real_time=base_time + timedelta(seconds=sim_time),
                        sim_time=sim_time,
                        scenario="TestScenario",
                        federate="Battery",
                        data_name=battery_pub,
                        data_value=current_value,
                    )
                )

            timeseries_manager.write_records(records)

            # Analyze the published data
            pub_data_df = timeseries_manager.read_data(
                federate_name="Battery", data_name=battery_pub
            )

            assert len(pub_data_df) == 3
            assert all(pub_data_df["data_name"] == battery_pub)

            # This data would be available to EVehicle as subscriber
            # (In a real simulation, EVehicle would have corresponding subscription data)
