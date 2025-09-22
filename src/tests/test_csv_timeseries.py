"""
Tests for CSV time-series data management with composition-based approach.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

from cosim_toolbox.dbms.csv_timeseries import (
    CSVTimeSeriesWriter,
    CSVTimeSeriesReader,
    CSVTimeSeriesManager,
    _CSVHelper,
)
from cosim_toolbox.dbms import TSRecord


@pytest.fixture
def sample_ts_records():
    """Sample time-series records for testing."""
    now = datetime.now()
    return [
        TSRecord(now, 0.0, "TestScenario", "Battery", "Battery/voltage", 120.5),
        TSRecord(
            now + timedelta(seconds=60),
            60.0,
            "TestScenario",
            "Battery",
            "Battery/voltage",
            119.8,
        ),
        TSRecord(now, 0.0, "TestScenario", "EVehicle", "EVehicle/voltage", 120.0),
    ]


class TestCSVTimeSeriesWriter:
    """Test standalone CSV time-series writer functionality."""

    def test_writer_initialization(self, temp_directory):
        """Test writer initialization for standalone use."""
        writer = CSVTimeSeriesWriter(
            location=temp_directory, analysis_name="test_analysis"
        )
        assert isinstance(writer.helper, _CSVHelper)
        assert writer.helper.location == Path(temp_directory)
        assert writer.helper.analysis_name == "test_analysis"
        assert not writer.is_connected

    def test_writer_connection(self, temp_directory):
        """Test writer connection creates directories."""
        writer = CSVTimeSeriesWriter(
            location=temp_directory, analysis_name="test_analysis"
        )
        with writer:
            assert writer.is_connected
            assert writer.helper.location.exists()
            assert writer.helper.analysis_path.exists()
        assert not writer.is_connected

    def test_data_type_classification(self, temp_directory):
        """Test data type classification via the helper."""
        helper = _CSVHelper(temp_directory, "test")
        assert helper.get_data_type(12.5) == "hdt_double"
        assert helper.get_data_type(42) == "hdt_integer"
        assert helper.get_data_type("test") == "hdt_string"
        assert helper.get_data_type(True) == "hdt_boolean"
        assert helper.get_data_type(3 + 4j) == "hdt_complex"
        assert helper.get_data_type([1, 2, 3]) == "hdt_vector"
        assert helper.get_data_type([1 + 2j]) == "hdt_complex_vector"

    def test_write_records(self, temp_directory, sample_ts_records):
        """Test writing time-series records."""
        writer = CSVTimeSeriesWriter(
            location=temp_directory, analysis_name="TestAnalysis"
        )
        with writer:
            assert writer.write_records(sample_ts_records)
            battery_file = writer.helper.get_file_path("Battery", "hdt_double")
            vehicle_file = writer.helper.get_file_path("EVehicle", "hdt_double")
            assert battery_file.exists() and vehicle_file.exists()
            df = pd.read_csv(battery_file)
            assert len(df) == 2

    def test_buffered_writing(self, temp_directory):
        """Test buffered writing functionality."""
        writer = CSVTimeSeriesWriter(
            location=temp_directory, analysis_name="TestAnalysis"
        )
        with writer:
            writer.add_record(TSRecord(datetime.now(), 0.0, "Test", "Fed", "v", 1.0))
            writer.add_record(TSRecord(datetime.now(), 1.0, "Test", "Fed", "v", 2.0))
            assert writer.buffer_size == 2
            assert writer.flush()
            assert writer.buffer_size == 0
            test_file = writer.helper.get_file_path("Fed", "hdt_double")
            assert test_file.exists()
            df = pd.read_csv(test_file)
            assert len(df) == 2

    def test_invalid_federate_name(self, temp_directory):
        """Test that invalid names cause write_records to fail."""
        writer = CSVTimeSeriesWriter(
            location=temp_directory, analysis_name="TestAnalysis"
        )
        invalid_record = TSRecord(datetime.now(), 0.0, "Test", "invalid\name", "v", 1.0)
        with writer:
            assert not writer.write_records([invalid_record])


class TestCSVTimeSeriesReader:
    """Test standalone CSV time-series reader functionality."""

    def test_reader_initialization(self, temp_directory):
        """Test reader initialization for standalone use."""
        reader = CSVTimeSeriesReader(
            location=temp_directory, analysis_name="test_analysis"
        )
        assert isinstance(reader.helper, _CSVHelper)
        assert not reader.is_connected

    def test_read_data_empty(self, temp_directory):
        """Test reading from empty/non-existent directory."""
        reader = CSVTimeSeriesReader(
            location=temp_directory, analysis_name="nonexistent"
        )
        with reader:
            df = reader.read_data()
            assert df.empty

    def test_list_utilities_empty(self, temp_directory):
        """Test list utilities with empty directory."""
        reader = CSVTimeSeriesReader(
            location=temp_directory, analysis_name="empty_analysis"
        )
        with reader:
            assert reader.list_federates() == []
            assert reader.list_data_types(["nonexistent"]) == []
            assert reader.list_scenarios() == []
            assert reader.get_time_range() == {"min_time": 0.0, "max_time": 0.0}


class TestCSVTimeSeriesManager:
    """Test the joint CSV time-series manager."""

    def test_manager_initialization(self, temp_directory):
        """Test manager initialization creates proper components."""
        manager = CSVTimeSeriesManager(
            location=temp_directory, analysis_name="TestAnalysis"
        )
        assert manager.helper.location == Path(temp_directory)
        assert manager.analysis_name == "TestAnalysis"
        assert isinstance(manager.writer, CSVTimeSeriesWriter)
        assert isinstance(manager.reader, CSVTimeSeriesReader)
        assert manager.writer.helper is manager.reader.helper

    def test_complete_workflow(self, temp_directory, sample_ts_records):
        """Test complete read/write workflow through manager."""
        manager = CSVTimeSeriesManager(
            location=temp_directory, analysis_name="TestAnalysis"
        )
        with manager:
            assert manager.write_records(sample_ts_records)
            df = manager.read_data()
            assert len(df) == 3
            battery_df = manager.read_data(federate_name="Battery")
            assert len(battery_df) == 2

    def test_utility_methods(self, temp_directory, sample_ts_records):
        """Test utility methods are correctly exposed by the manager."""
        manager = CSVTimeSeriesManager(
            location=temp_directory, analysis_name="TestAnalysis"
        )
        with manager:
            manager.write_records(sample_ts_records)
            assert set(manager.list_federates()) == {"Battery", "EVehicle"}
            assert "hdt_double" in manager.list_data_types(["Battery"])
            assert "TestScenario" in manager.list_scenarios()
            time_range = manager.get_time_range()
            assert time_range["min_time"] == 0.0
            assert time_range["max_time"] == 60.0

    def test_delete_federate_data(self, temp_directory, sample_ts_records):
        """Test deleting federate data."""
        manager = CSVTimeSeriesManager(
            location=temp_directory, analysis_name="TestAnalysis"
        )
        with manager:
            manager.write_records(sample_ts_records)
            assert "Battery" in manager.list_federates()
            assert manager.delete_federate_data("Battery")
            assert "Battery" not in manager.list_federates()

    def test_delete_scenario_data_not_implemented(self, temp_directory):
        """Test that scenario deletion raises NotImplementedError."""
        manager = CSVTimeSeriesManager(
            location=temp_directory, analysis_name="TestAnalysis"
        )
        with manager:
            with pytest.raises(NotImplementedError):
                manager.delete_scenario_data("TestScenario")

    def test_analysis_name_property(self, temp_directory):
        """Test that the analysis_name property updates the shared helper."""
        manager = CSVTimeSeriesManager(location=temp_directory, analysis_name="Initial")
        assert manager.analysis_name == "Initial"
        assert manager.writer.helper.analysis_name == "Initial"
        manager.analysis_name = "Modified"
        assert manager.analysis_name == "Modified"
        assert manager.writer.helper.analysis_name == "Modified"
        assert manager.reader.helper.analysis_name == "Modified"
        assert manager.writer.helper is manager.reader.helper
