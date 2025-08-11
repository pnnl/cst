"""
Tests for metadata factory functions.
"""

import pytest
from cosim_toolbox.metadata_factory import (
    create_metadata_manager,
    create_json_manager,
    create_mongo_manager
)
from cosim_toolbox.json_metadata import JSONMetadataManager
from cosim_toolbox.mongo_metadata import MongoMetadataManager


class TestMetadataFactory:
    """Test metadata factory functions."""
    
    def test_create_json_manager(self, temp_directory):
        """Test creating JSON manager via factory."""
        manager = create_metadata_manager("json", temp_directory)
        assert isinstance(manager, JSONMetadataManager)
        assert manager.location == temp_directory
    
    def test_create_json_manager_convenience(self, temp_directory):
        """Test convenience function for JSON manager."""
        manager = create_json_manager(temp_directory)
        assert isinstance(manager, JSONMetadataManager)
        assert manager.location == temp_directory
    
    @pytest.mark.mongo
    def test_create_mongo_manager(self):
        """Test creating MongoDB manager via factory."""
        uri = "mongodb://localhost:27017"
        manager = create_metadata_manager("mongo", uri, db_name="test_db")
        assert isinstance(manager, MongoMetadataManager)
        assert manager.location == uri
        assert manager.db_name == "test_db"
    
    @pytest.mark.mongo
    def test_create_mongo_manager_convenience(self):
        """Test convenience function for MongoDB manager."""
        uri = "mongodb://localhost:27017"
        manager = create_mongo_manager(uri, "test_db")
        assert isinstance(manager, MongoMetadataManager)
        assert manager.location == uri
        assert manager.db_name == "test_db"
    
    @pytest.mark.mongo
    def test_create_mongo_manager_default_db(self):
        """Test MongoDB manager with default database name."""
        uri = "mongodb://localhost:27017"
        manager = create_metadata_manager("mongo", uri)
        assert isinstance(manager, MongoMetadataManager)
        assert manager.db_name == "cst"
    
    def test_invalid_backend(self):
        """Test error handling for invalid backend."""
        with pytest.raises(ValueError, match="Unknown backend"):
            create_metadata_manager("invalid", "location")
    
    def test_case_insensitive_backend(self, temp_directory):
        """Test that backend names are case insensitive."""
        manager1 = create_metadata_manager("JSON", temp_directory)
        manager2 = create_metadata_manager("json", temp_directory)
        manager3 = create_metadata_manager("Json", temp_directory)
        
        assert all(isinstance(m, JSONMetadataManager) for m in [manager1, manager2, manager3])