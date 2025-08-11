"""
Tests for base metadata manager functionality.
"""

import pytest
from cosim_toolbox.base_metadata import BaseMetadataManager


class MockMetadataManager(BaseMetadataManager):
    """Mock implementation for testing base functionality."""
    
    def __init__(self, location: str):
        super().__init__(location)
        self._data = {}  # Simple in-memory storage
        self._collections = set()
    
    def _write_data(self, collection_type: str, name: str, data: dict, overwrite: bool = False) -> bool:
        key = f"{collection_type}:{name}"
        if key in self._data and not overwrite:
            return False
        self._data[key] = data.copy()
        self._collections.add(collection_type)
        return True
    
    def _read_data(self, collection_type: str, name: str) -> dict:
        key = f"{collection_type}:{name}"
        return self._data.get(key)
    
    def _delete_data(self, collection_type: str, name: str) -> bool:
        key = f"{collection_type}:{name}"
        if key in self._data:
            del self._data[key]
            return True
        return False
    
    def _list_data(self, collection_type: str) -> list[str]:
        prefix = f"{collection_type}:"
        return sorted([key[len(prefix):] for key in self._data.keys() if key.startswith(prefix)])
    
    def _list_collections(self) -> list[str]:
        custom_collections = [c for c in self._collections if c not in ["federations", "scenarios"]]
        return sorted(custom_collections)
    
    def connect(self) -> bool:
        self._is_connected = True
        return True
    
    def disconnect(self) -> None:
        self._is_connected = False


class TestBaseMetadataManager:
    """Test the BaseMetadataManager functionality."""
    
    def test_name_validation_valid_names(self):
        """Test valid name validation."""
        manager = MockMetadataManager("test")
        
        valid_names = [
            "ValidName",
            "valid_name",
            "Valid-Name",
            "Valid123",
            "a" * 255  # Maximum length
        ]
        
        for name in valid_names:
            # Should not raise exception
            manager._validate_name(name)
    
    def test_name_validation_invalid_names(self):
        """Test invalid name validation."""
        manager = MockMetadataManager("test")
        
        invalid_names = [
            "",  # Empty
            "a" * 256,  # Too long
            "invalid/name",  # Contains slash
            "invalid\\name",  # Contains backslash
            "invalid:name",  # Contains colon
            "invalid*name",  # Contains asterisk
            "CON",  # Reserved name
            "com1",  # Reserved name (case insensitive)
            " invalid",  # Starts with space
            "invalid ",  # Ends with space
            ".invalid",  # Starts with period
            "invalid.",  # Ends with period
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError):
                manager._validate_name(name)
    
    def test_generic_write_read_delete(self, sample_federation_data):
        """Test generic write, read, and delete operations."""
        manager = MockMetadataManager("test")
        manager.connect()
        
        # Test write
        success = manager.write("test_collection", "test_item", sample_federation_data)
        assert success is True
        
        # Test read
        data = manager.read("test_collection", "test_item")
        assert data == sample_federation_data
        
        # Test exists
        assert manager.exists("test_collection", "test_item") is True
        assert manager.exists("test_collection", "nonexistent") is False
        
        # Test delete
        success = manager.delete("test_collection", "test_item")
        assert success is True
        
        # Verify deletion
        data = manager.read("test_collection", "test_item")
        assert data is None
        assert manager.exists("test_collection", "test_item") is False
    
    def test_overwrite_protection(self, sample_federation_data):
        """Test overwrite protection functionality."""
        manager = MockMetadataManager("test")
        manager.connect()
        
        # First write should succeed
        success1 = manager.write("test_collection", "test_item", sample_federation_data)
        assert success1 is True
        
        # Second write should fail (overwrite=False by default)
        success2 = manager.write("test_collection", "test_item", {"new": "data"})
        assert success2 is False
        
        # Data should be unchanged
        data = manager.read("test_collection", "test_item")
        assert data == sample_federation_data
        
        # Third write with overwrite=True should succeed
        new_data = {"new": "data"}
        success3 = manager.write("test_collection", "test_item", new_data, overwrite=True)
        assert success3 is True
        
        # Data should be updated
        data = manager.read("test_collection", "test_item")
        assert data == new_data
    
    def test_convenience_methods(self, sample_federation_data, sample_scenario_data):
        """Test convenience methods for federations and scenarios."""
        manager = MockMetadataManager("test")
        manager.connect()
        
        # Test federation methods
        assert manager.write_federation("TestFed", sample_federation_data) is True
        assert manager.read_federation("TestFed") == sample_federation_data
        assert manager.exists_federation("TestFed") is True
        assert "TestFed" in manager.list_federations()
        
        # Test scenario methods
        assert manager.write_scenario("TestScenario", sample_scenario_data) is True
        assert manager.read_scenario("TestScenario") == sample_scenario_data
        assert manager.exists_scenario("TestScenario") is True
        assert "TestScenario" in manager.list_scenarios()
        
        # Test deletion
        assert manager.delete_federation("TestFed") is True
        assert manager.delete_scenario("TestScenario") is True
        assert manager.exists_federation("TestFed") is False
        assert manager.exists_scenario("TestScenario") is False
    
    def test_list_operations(self, sample_federation_data, sample_custom_data):
        """Test listing operations."""
        manager = MockMetadataManager("test")
        manager.connect()
        
        # Add some data
        manager.write_federation("Fed1", sample_federation_data)
        manager.write_federation("Fed2", sample_federation_data)
        manager.write_scenario("Scenario1", {"test": "data"})
        manager.write("custom_collection", "item1", sample_custom_data)
        manager.write("custom_collection", "item2", sample_custom_data)
        manager.write("another_collection", "item1", sample_custom_data)
        
        # Test lists
        federations = manager.list_federations()
        scenarios = manager.list_scenarios()
        custom_collections = manager.list_custom_collections()
        custom_items = manager.list_items("custom_collection")
        
        assert set(federations) == {"Fed1", "Fed2"}
        assert set(scenarios) == {"Scenario1"}
        assert set(custom_collections) == {"custom_collection", "another_collection"}
        assert set(custom_items) == {"item1", "item2"}
    
    def test_connection_required(self, sample_federation_data):
        """Test that operations require connection."""
        manager = MockMetadataManager("test")
        # Don't connect
        
        # Operations should fail when not connected
        assert manager.write("test", "item", sample_federation_data) is False
        assert manager.read("test", "item") is None
        assert manager.list_items("test") == []
    
    def test_context_manager(self, sample_federation_data):
        """Test context manager functionality."""
        with MockMetadataManager("test") as manager:
            assert manager.is_connected is True
            success = manager.write("test", "item", sample_federation_data)
            assert success is True
        
        # Should be disconnected after context
        assert manager.is_connected is False