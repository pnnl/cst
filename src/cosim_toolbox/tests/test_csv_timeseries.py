"""
Tests for CSV time-series data management with composition-based approach.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

from cosim_toolbox.csv_timeseries import (
    CSVTimeSeriesWriter,
    CSVTimeSeriesReader,
    CSVTimeSeriesManager,
)
from cosim_toolbox.data_management import TSRecord


class TestCSVTimeSeriesWriter:
    """Test CSV time-series writer functionality."""

    def test_writer_initialization(self, temp_directory):
        """Test writer initialization with connection info."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "test_analysis",
            "analysis_name": "test_analysis",
        }
        writer = CSVTimeSeriesWriter(connection_info)
        assert writer.connection_info == connection_info
        assert writer.base_path == Path(temp_directory)
        assert writer.analysis_name == "test_analysis"
        assert not writer.is_connected

    def test_writer_connection(self, temp_directory):
        """Test writer connection creates directories."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "test_analysis",
            "analysis_name": "test_analysis",
        }
        writer = CSVTimeSeriesWriter(connection_info)

        success = writer.connect()
        assert success is True
        assert writer.is_connected is True
        assert writer.base_path.exists()
        assert writer.analysis_path.exists()

        writer.disconnect()
        assert writer.is_connected is False

    def test_data_type_classification(self, temp_directory):
        """Test data type classification for different value types."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "test_analysis",
            "analysis_name": "test_analysis",
        }
        writer = CSVTimeSeriesWriter(connection_info)

        # Test various data types
        assert writer._get_data_type(12.5) == "hdt_double"
        assert writer._get_data_type(42) == "hdt_integer"
        assert writer._get_data_type("test") == "hdt_string"
        assert writer._get_data_type(True) == "hdt_boolean"
        assert writer._get_data_type(False) == "hdt_boolean"
        assert writer._get_data_type(3 + 4j) == "hdt_complex"
        assert writer._get_data_type([1, 2, 3]) == "hdt_vector"
        assert writer._get_data_type([1 + 2j, 3 + 4j]) == "hdt_complex_vector"

    def test_write_records(self, temp_directory, sample_ts_records):
        """Test writing time-series records."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "TestAnalysis",
            "analysis_name": "TestAnalysis",
        }
        writer = CSVTimeSeriesWriter(connection_info)

        with writer:
            writer.connect()
            success = writer.write_records(sample_ts_records)
            assert success is True

            # Verify files were created
            battery_file = writer.analysis_path / "Battery" / "hdt_double.csv"
            evehicle_file = writer.analysis_path / "EVehicle" / "hdt_double.csv"

            assert battery_file.exists()
            assert evehicle_file.exists()

            # Verify file content
            battery_df = pd.read_csv(battery_file)
            assert len(battery_df) == 2  # Two Battery records
            assert all(battery_df["federate"] == "Battery")

    def test_buffered_writing(self, temp_directory):
        """Test buffered writing functionality."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "TestAnalysis",
            "analysis_name": "TestAnalysis",
        }
        writer = CSVTimeSeriesWriter(connection_info)

        with writer:
            writer.connect()

            # Add records to buffer
            record1 = TSRecord(
                real_time=datetime.now(),
                sim_time=0.0,
                scenario="Test",
                federate="TestFed",
                data_name="test_value",
                data_value=10.0,
            )
            record2 = TSRecord(
                real_time=datetime.now(),
                sim_time=60.0,
                scenario="Test",
                federate="TestFed",
                data_name="test_value",
                data_value=20.0,
            )

            writer.add_record(record1)
            writer.add_record(record2)
            assert writer.buffer_size == 2

            # Flush buffer
            success = writer.flush()
            assert success is True
            assert writer.buffer_size == 0

            # Verify data was written
            test_file = writer.analysis_path / "TestFed" / "hdt_double.csv"
            assert test_file.exists()
            df = pd.read_csv(test_file)
            assert len(df) == 2

    def test_invalid_federate_names(self, temp_directory):
        """Test handling of invalid federate names."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "TestAnalysis",
            "analysis_name": "TestAnalysis",
        }
        writer = CSVTimeSeriesWriter(connection_info)

        invalid_record = TSRecord(
            real_time=datetime.now(),
            sim_time=0.0,
            scenario="Test",
            federate="invalid/name",  # Invalid character
            data_name="test_value",
            data_value=10.0,
        )

        with writer:
            writer.connect()
            success = writer.write_records([invalid_record])
            assert success is False


class TestCSVTimeSeriesReader:
    """Test CSV time-series reader functionality."""

    def test_reader_initialization(self, temp_directory):
        """Test reader initialization."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "test_analysis",
            "analysis_name": "test_analysis",
        }
        reader = CSVTimeSeriesReader(connection_info)
        assert reader.connection_info == connection_info
        assert reader.base_path == Path(temp_directory)
        assert reader.analysis_name == "test_analysis"
        assert not reader.is_connected

    def test_reader_connection(self, temp_directory):
        """Test reader connection."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "test_analysis",
            "analysis_name": "test_analysis",
        }
        reader = CSVTimeSeriesReader(connection_info)

        # Should connect even if directory doesn't exist yet
        success = reader.connect()
        assert success is True
        assert reader.is_connected is True

        reader.disconnect()
        assert reader.is_connected is False

    def test_read_data_empty(self, temp_directory):
        """Test reading from empty/non-existent directory."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "nonexistent",
            "analysis_name": "nonexistent",
        }
        reader = CSVTimeSeriesReader(connection_info)

        with reader:
            reader.connect()
            df = reader.read_data()
            assert df.empty

    def test_value_parsing(self, temp_directory):
        """Test parsing values from CSV back to proper types."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "test_analysis",
            "analysis_name": "test_analysis",
        }
        reader = CSVTimeSeriesReader(connection_info)

        # Test parsing different data types
        assert reader._parse_value_from_csv("12.5", "hdt_double") == 12.5
        assert reader._parse_value_from_csv("42", "hdt_integer") == 42
        assert reader._parse_value_from_csv("test", "hdt_string") == "test"
        assert reader._parse_value_from_csv("true", "hdt_boolean") is True
        assert reader._parse_value_from_csv("false", "hdt_boolean") is False
        assert reader._parse_value_from_csv("(3+4j)", "hdt_complex") == 3 + 4j
        assert reader._parse_value_from_csv("[1, 2, 3]", "hdt_vector") == [1, 2, 3]

    def test_list_utilities_empty(self, temp_directory):
        """Test list utilities with empty directory."""
        connection_info = {
            "base_path": Path(temp_directory),
            "analysis_path": Path(temp_directory) / "empty_analysis",
            "analysis_name": "empty_analysis",
        }
        reader = CSVTimeSeriesReader(connection_info)

        with reader:
            reader.connect()
            assert reader.list_federates() == []
            assert reader.list_data_types("nonexistent") == []
            assert reader.get_scenarios() == []
            time_range = reader.get_time_range()
            assert time_range == {"min_time": 0.0, "max_time": 0.0}


class TestCSVTimeSeriesManager:
    """Test the joint CSV time-series manager."""

    def test_manager_initialization(self, temp_directory):
        """Test manager initialization creates proper components."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        assert manager.location == temp_directory
        assert manager.analysis_name == "TestAnalysis"
        assert hasattr(manager, "writer")
        assert hasattr(manager, "reader")
        assert isinstance(manager.writer, CSVTimeSeriesWriter)
        assert isinstance(manager.reader, CSVTimeSeriesReader)

        # Verify shared connection info
        assert manager.writer.connection_info == manager.reader.connection_info
        assert manager.writer.analysis_name == "TestAnalysis"
        assert manager.reader.analysis_name == "TestAnalysis"

    def test_manager_connection_coordination(self, temp_directory):
        """Test that manager coordinates reader/writer connections."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        # Connect manager
        success = manager.connect()
        assert success is True
        assert manager.is_connected is True
        assert manager.writer.is_connected is True
        assert manager.reader.is_connected is True

        # Disconnect manager
        manager.disconnect()
        assert manager.is_connected is False
        assert manager.writer.is_connected is False
        assert manager.reader.is_connected is False

    def test_complete_workflow(self, temp_directory, sample_ts_records):
        """Test complete read/write workflow through manager."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        with manager:
            # Write data
            success = manager.write_records(sample_ts_records)
            assert success is True

            # Read all data back
            df = manager.read_data()
            assert len(df) == 3  # Three sample records
            assert set(df["federate"].unique()) == {"Battery", "EVehicle"}
            assert set(df["scenario"].unique()) == {"TestScenario"}

            # Test filtered reads
            battery_df = manager.read_data(federate_name="Battery")
            assert len(battery_df) == 2
            assert all(battery_df["federate"] == "Battery")

            evehicle_df = manager.read_data(federate_name="EVehicle")
            assert len(evehicle_df) == 1
            assert all(evehicle_df["federate"] == "EVehicle")

            # Test time-based filtering
            early_df = manager.read_data(start_time=0.0, duration=30.0)
            assert len(early_df) == 2  # Records at t=0

    def test_buffered_operations(self, temp_directory):
        """Test buffered writing through manager."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        with manager:
            # Add records to buffer
            for i in range(5):
                record = TSRecord(
                    real_time=datetime.now(),
                    sim_time=float(i * 60),
                    scenario="BufferTest",
                    federate="TestFed",
                    data_name="test_value",
                    data_value=float(i * 10),
                )
                manager.add_record(record)

            assert manager.buffer_size == 5

            # Flush buffer
            success = manager.flush()
            assert success is True
            assert manager.buffer_size == 0

            # Verify data was written and can be read
            df = manager.read_data(scenario_name="BufferTest")
            assert len(df) == 5
            assert list(df["data_value"]) == [0.0, 10.0, 20.0, 30.0, 40.0]

    def test_utility_methods(self, temp_directory, sample_ts_records):
        """Test utility methods through manager."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        with manager:
            manager.write_records(sample_ts_records)

            # Test list methods
            federates = manager.list_federates()
            assert set(federates) == {"Battery", "EVehicle"}

            battery_types = manager.list_data_types("Battery")
            assert "hdt_double" in battery_types

            scenarios = manager.get_scenarios()
            assert "TestScenario" in scenarios

            # Test time range
            time_range = manager.get_time_range()
            assert time_range["min_time"] == 0.0
            assert time_range["max_time"] == 60.0

    def test_delete_federate_data(self, temp_directory, sample_ts_records):
        """Test deleting federate data."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        with manager:
            manager.write_records(sample_ts_records)

            # Verify data exists
            federates = manager.list_federates()
            assert "Battery" in federates

            # Delete Battery data
            success = manager.delete_federate_data("Battery")
            assert success is True

            # Verify Battery data is gone
            federates = manager.list_federates()
            assert "Battery" not in federates
            assert "EVehicle" in federates  # Should still exist

    def test_delete_scenario_data_not_implemented(self, temp_directory):
        """Test that scenario deletion raises NotImplementedError."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        with manager:
            with pytest.raises(NotImplementedError):
                manager.delete_scenario_data("TestScenario")

    def test_context_manager(self, temp_directory, sample_ts_records):
        """Test context manager functionality."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        # Use as context manager
        with manager as mgr:
            assert mgr.is_connected is True
            success = mgr.write_records(sample_ts_records)
            assert success is True

        # Should be disconnected after context
        assert manager.is_connected is False

    def test_error_handling(self, temp_directory):
        """Test error handling in various scenarios."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        # Operations without connection should fail gracefully
        success = manager.write_records([])
        assert success is False  # Writer not connected

        df = manager.read_data()
        assert df.empty  # Reader not connected

        # Invalid operations should be handled
        with manager:
            # Writing empty list should succeed
            success = manager.write_records([])
            assert success is True

    def test_different_data_types(self, temp_directory):
        """Test handling of different data types in records."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        base_time = datetime.now()
        records = [
            TSRecord(base_time, 0.0, "Test", "Fed1", "double_val", 12.5),
            TSRecord(base_time, 1.0, "Test", "Fed1", "int_val", 42),
            TSRecord(base_time, 2.0, "Test", "Fed1", "string_val", "test"),
            TSRecord(base_time, 3.0, "Test", "Fed1", "bool_val", True),
            TSRecord(base_time, 4.0, "Test", "Fed1", "complex_val", 3 + 4j),
            TSRecord(base_time, 5.0, "Test", "Fed1", "list_val", [1, 2, 3]),
        ]

        with manager:
            success = manager.write_records(records)
            assert success is True

            # Verify different file types were created
            data_types = manager.list_data_types("Fed1")
            expected_types = {
                "hdt_double",
                "hdt_integer",
                "hdt_string",
                "hdt_boolean",
                "hdt_complex",
                "hdt_vector",
            }
            assert set(data_types) == expected_types

            # Read back and verify data types are preserved
            df = manager.read_data(federate_name="Fed1")
            assert len(df) == 6

            # Check that values are properly parsed back
            double_df = manager.read_data(federate_name="Fed1", data_type="hdt_double")
            assert len(double_df) == 1
            assert double_df.iloc[0]["data_value"] == 12.5

            bool_df = manager.read_data(federate_name="Fed1", data_type="hdt_boolean")
            assert len(bool_df) == 1
            assert bool_df.iloc[0]["data_value"] == True

    def test_shared_connection_info(self, temp_directory):
        """Test that reader and writer truly share connection info."""
        manager = CSVTimeSeriesManager(temp_directory, "TestAnalysis")

        # Verify they share the same connection_info object
        assert manager.writer.connection_info is manager.reader.connection_info

        # Test the analysis_name property setter
        original_analysis_name = manager.analysis_name
        assert original_analysis_name == "TestAnalysis"

        # Change analysis name through property setter
        manager.analysis_name = "ModifiedAnalysis"

        # Verify all components are updated
        assert manager.analysis_name == "ModifiedAnalysis"
        assert manager.writer.analysis_name == "ModifiedAnalysis"
        assert manager.reader.analysis_name == "ModifiedAnalysis"
        assert manager.connection_info["analysis_name"] == "ModifiedAnalysis"

        # Restore original for cleanup
        manager.analysis_name = original_analysis_name


class TestCSVIntegrationScenarios:
    """Integration tests for complex CSV scenarios."""

    def test_multi_federate_simulation(self, temp_directory):
        """Test simulation with multiple federates generating different data types."""
        manager = CSVTimeSeriesManager(temp_directory, "MultiSim")

        base_time = datetime.now()
        records = []

        # Simulate 3 federates over 5 time steps
        federates = ["Battery", "Solar", "Load"]
        for step in range(5):
            sim_time = float(step * 300)  # Every 5 minutes
            timestamp = base_time + timedelta(seconds=sim_time)

            # Battery: current (double) and status (string)
            records.append(
                TSRecord(
                    timestamp,
                    sim_time,
                    "MultiSim",
                    "Battery",
                    "Battery/current",
                    10.0 + step * 2.0,
                )
            )
            records.append(
                TSRecord(
                    timestamp,
                    sim_time,
                    "MultiSim",
                    "Battery",
                    "Battery/status",
                    f"charging_{step}",
                )
            )

            # Solar: power (double) and active (boolean)
            records.append(
                TSRecord(
                    timestamp,
                    sim_time,
                    "MultiSim",
                    "Solar",
                    "Solar/power",
                    100.0 + step * 50.0,
                )
            )
            records.append(
                TSRecord(
                    timestamp,
                    sim_time,
                    "MultiSim",
                    "Solar",
                    "Solar/active",
                    step % 2 == 0,
                )
            )

            # Load: demand (double) and profile (list)
            records.append(
                TSRecord(
                    timestamp,
                    sim_time,
                    "MultiSim",
                    "Load",
                    "Load/demand",
                    80.0 - step * 5.0,
                )
            )
            records.append(
                TSRecord(
                    timestamp,
                    sim_time,
                    "MultiSim",
                    "Load",
                    "Load/profile",
                    [step, step + 1, step + 2],
                )
            )

        with manager:
            success = manager.write_records(records)
            assert success is True

            # Verify file structure
            federates_found = manager.list_federates()
            assert set(federates_found) == set(federates)

            # Verify data types per federate
            battery_types = set(manager.list_data_types("Battery"))
            assert battery_types == {"hdt_double", "hdt_string"}

            solar_types = set(manager.list_data_types("Solar"))
            assert solar_types == {"hdt_double", "hdt_boolean"}

            load_types = set(manager.list_data_types("Load"))
            assert load_types == {"hdt_double", "hdt_vector"}

            # Test cross-federate queries
            all_double_data = manager.read_data(data_type="hdt_double")
            assert len(all_double_data) == 15  # 3 federates * 5 steps * 1 double each

            # Test time-based analysis
            mid_period = manager.read_data(start_time=600.0, duration=600.0)
            expected_records = 6 * 2  # 2 time points * 6 records per time point
            assert len(mid_period) == expected_records

    def test_concurrent_access_simulation(self, temp_directory):
        """Test simulation of multiple writers (federate simulation)."""
        # This test simulates what would happen if multiple federates
        # were writing simultaneously (potential file conflict scenario)

        # Create separate managers for different "federates"
        battery_manager = CSVTimeSeriesManager(temp_directory, "ConcurrentSim")
        solar_manager = CSVTimeSeriesManager(temp_directory, "ConcurrentSim")

        base_time = datetime.now()

        battery_records = [
            TSRecord(base_time, 0.0, "ConcurrentSim", "Battery", "current", 10.0),
            TSRecord(base_time, 60.0, "ConcurrentSim", "Battery", "current", 12.0),
        ]

        solar_records = [
            TSRecord(base_time, 0.0, "ConcurrentSim", "Solar", "power", 100.0),
            TSRecord(base_time, 60.0, "ConcurrentSim", "Solar", "power", 150.0),
        ]

        # Write from different managers (simulating different processes)
        with battery_manager, solar_manager:
            battery_success = battery_manager.write_records(battery_records)
            solar_success = solar_manager.write_records(solar_records)

            assert battery_success is True
            assert solar_success is True

            # Verify both datasets are accessible from either manager
            battery_data = battery_manager.read_data(federate_name="Battery")
            solar_data = solar_manager.read_data(federate_name="Solar")

            assert len(battery_data) == 2
            assert len(solar_data) == 2

            # Cross-manager access should work
            all_data_via_battery = battery_manager.read_data()
            all_data_via_solar = solar_manager.read_data()

            assert len(all_data_via_battery) == 4
            assert len(all_data_via_solar) == 4
