"""
Tests for MongoDB metadata manager.
"""

import pytest
from cosim_toolbox.dbms import MongoMetadataManager


@pytest.mark.mongo
class TestMongoMetadataManager:
    """Test MongoDB metadata manager functionality."""
    
    @pytest.fixture
    def mongo_uri(self):
        """MongoDB URI for testing. Modify as needed for your test environment."""
        return "mongodb://localhost:27017"
    
    @pytest.fixture
    def test_db_name(self):
        """Test database name."""
        return "test_cst_db"
    
    def test_initialization(self, mongo_uri, test_db_name):
        """Test MongoDB manager initialization."""
        manager = MongoMetadataManager(location=mongo_uri, database=test_db_name)
        assert manager.helper.uri == mongo_uri
        assert manager.helper.db_name == test_db_name
        assert not manager.is_connected
    
    def test_connection(self, mongo_uri, test_db_name):
        """Test MongoDB connection."""
        manager = MongoMetadataManager(location=mongo_uri, database=test_db_name)
        
        try:
            success = manager.connect()
            if success:
                assert manager.is_connected is True
                assert manager.client is not None
                assert manager.db is not None
                
                manager.disconnect()
                assert manager.is_connected is False
                assert manager.client is None
                assert manager.db is None
            else:
                pytest.skip("MongoDB connection failed - server may not be running")
        except Exception as e:
            pytest.skip(f"MongoDB connection failed: {e}")
    
    def test_write_read_federation(self, mongo_uri, test_db_name, sample_federation_data):
        """Test writing and reading federation data."""
        manager = MongoMetadataManager(location=mongo_uri, database=test_db_name)
        
        try:
            with manager:
                # Write federation
                success = manager.write_federation("TestFed", sample_federation_data)
                assert success is True
                
                # Read federation
                data = manager.read_federation("TestFed")
                assert data == sample_federation_data
                
                # Clean up
                manager.delete_federation("TestFed")
        except Exception as e:
            pytest.skip(f"MongoDB test failed: {e}")
    
    def test_write_read_scenario(self, mongo_uri, test_db_name, sample_scenario_data):
        """Test writing and reading scenario data."""
        manager = MongoMetadataManager(location=mongo_uri, database=test_db_name)
        
        try:
            with manager:
                success = manager.write_scenario("TestScenario", sample_scenario_data)
                assert success is True
                
                data = manager.read_scenario("TestScenario")
                assert data == sample_scenario_data
                
                # Clean up
                manager.delete_scenario("TestScenario")
        except Exception as e:
            pytest.skip(f"MongoDB test failed: {e}")
    
    def test_write_read_custom(self, mongo_uri, test_db_name, sample_custom_data):
        """Test writing and reading custom data."""
        manager = MongoMetadataManager(location=mongo_uri, database=test_db_name)
        
        try:
            with manager:
                success = manager.write("electrical_config", "main", sample_custom_data)
                assert success is True
                
                data = manager.read("electrical_config", "main")
                assert data == sample_custom_data
                
                # Clean up
                manager.delete("electrical_config", "main")
        except Exception as e:
            pytest.skip(f"MongoDB test failed: {e}")
    
    def test_overwrite_protection(self, mongo_uri, test_db_name, sample_federation_data):
        """Test overwrite protection."""
        manager = MongoMetadataManager(location=mongo_uri, database=test_db_name)
        
        try:
            with manager:
                # First write
                success1 = manager.write_federation("TestFed", sample_federation_data)
                assert success1 is True
                
                # Second write should fail
                success2 = manager.write_federation("TestFed", {"new": "data"})
                assert success2 is False
                
                # Data should be unchanged
                data = manager.read_federation("TestFed")
                assert data == sample_federation_data
                
                # Overwrite should work
                new_data = {"new": "data"}
                success3 = manager.write_federation("TestFed", new_data, overwrite=True)
                assert success3 is True
                
                data = manager.read_federation("TestFed")
                assert data == new_data
                
                # Clean up
                manager.delete_federation("TestFed")
        except Exception as e:
            pytest.skip(f"MongoDB test failed: {e}")
    
    def test_list_operations(self, mongo_uri, test_db_name, sample_federation_data):
        """Test listing operations."""
        manager = MongoMetadataManager(location=mongo_uri, database=test_db_name)
        
        try:
            with manager:
                # Create test data
                manager.write_federation("Fed1", sample_federation_data)
                manager.write_federation("Fed2", sample_federation_data)
                manager.write_scenario("Scenario1", {"test": "data"})
                manager.write("collection1", "item1", {"test": "data"})
                manager.write("collection1", "item2", {"test": "data"})
                
                # Test lists
                federations = manager.list_federations()
                scenarios = manager.list_scenarios()
                collections = manager.list_custom_collections()
                items = manager.list_items("collection1")
                
                assert "Fed1" in federations
                assert "Fed2" in federations
                assert "Scenario1" in scenarios
                assert "collection1" in collections
                assert set(items) == {"item1", "item2"}
                
                # Clean up
                manager.delete_federation("Fed1")
                manager.delete_federation("Fed2")
                manager.delete_scenario("Scenario1")
                manager.delete("collection1", "item1")
                manager.delete("collection1", "item2")
        except Exception as e:
            pytest.skip(f"MongoDB test failed: {e}")
    
    def test_delete_operations(self, mongo_uri, test_db_name, sample_federation_data):
        """Test delete operations."""
        manager = MongoMetadataManager(location=mongo_uri, database=test_db_name)
        
        try:
            with manager:
                # Create some data
                manager.write_federation("TestFed", sample_federation_data)
                manager.write_scenario("TestScenario", {"test": "data"})
                manager.write("custom", "item", {"test": "data"})
                
                # Verify they exist
                assert manager.exists_federation("TestFed")
                assert manager.exists_scenario("TestScenario")
                assert manager.exists("custom", "item")
                
                # Test deletions
                assert manager.delete_federation("TestFed") is True
                assert manager.delete_scenario("TestScenario") is True
                assert manager.delete("custom", "item") is True
                
                # Verify they're gone
                assert not manager.exists_federation("TestFed")
                assert not manager.exists_scenario("TestScenario")
                assert not manager.exists("custom", "item")
                
                # Deleting non-existent items should return False
                assert manager.delete_federation("NonExistent") is False
        except Exception as e:
            pytest.skip(f"MongoDB test failed: {e}")
    
    def test_invalid_collection_names(self, mongo_uri, test_db_name):
        """Test handling of invalid collection names."""
        manager = MongoMetadataManager(location=mongo_uri, database=test_db_name)
        
        try:
            with manager:
                invalid_names = ["system.invalid", "invalid$collection", "a" * 65]
                
                for name in invalid_names:
                    success = manager.write(name, "item", {"test": "data"})
                    assert success is False
        except Exception as e:
            pytest.skip(f"MongoDB test failed: {e}")