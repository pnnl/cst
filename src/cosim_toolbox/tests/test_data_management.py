"""
Tests for core data management abstractions.
"""
from datetime import datetime
from cosim_toolbox.dbms import TSRecord


class TestTSRecord:
    """Test the TSRecord dataclass."""
    
    def test_tsrecord_creation(self):
        """Test basic TSRecord creation."""
        record = TSRecord(
            real_time=datetime.now(),
            sim_time=120.5,
            scenario="TestScenario",
            federate="Battery",
            data_name="Battery/current",
            data_value=15.7
        )
        
        assert record.sim_time == 120.5
        assert record.scenario == "TestScenario"
        assert record.federate == "Battery"
        assert record.data_name == "Battery/current"
        assert record.data_value == 15.7
        assert isinstance(record.real_time, datetime)
    
    def test_tsrecord_different_data_types(self):
        """Test TSRecord with different data value types."""
        base_time = datetime.now()
        
        records = [
            TSRecord(base_time, 0.0, "test", "fed1", "voltage", 120.5),  # float
            TSRecord(base_time, 1.0, "test", "fed1", "count", 42),      # int
            TSRecord(base_time, 2.0, "test", "fed1", "status", "active"), # string
            TSRecord(base_time, 3.0, "test", "fed1", "flag", True),     # bool
            TSRecord(base_time, 4.0, "test", "fed1", "complex", 3+4j),  # complex
            TSRecord(base_time, 5.0, "test", "fed1", "vector", [1,2,3]), # list
        ]
        
        assert records[0].data_value == 120.5
        assert records[1].data_value == 42
        assert records[2].data_value == "active"
        assert records[3].data_value is True
        assert records[4].data_value == 3+4j
        assert records[5].data_value == [1,2,3]
    
    def test_tsrecord_equality(self):
        """Test TSRecord equality comparison."""
        time1 = datetime(2023, 1, 1, 12, 0, 0)
        time2 = datetime(2023, 1, 1, 12, 0, 0)
        
        record1 = TSRecord(time1, 0.0, "test", "fed", "data", 100)
        record2 = TSRecord(time2, 0.0, "test", "fed", "data", 100)
        record3 = TSRecord(time1, 0.0, "test", "fed", "data", 200)
        
        assert record1 == record2
        assert record1 != record3