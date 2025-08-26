"""
Tests for metadata factory functions.
"""

import pytest
from pathlib import Path
from data_management import create_metadata_manager
from data_management.json_metadata import JSONMetadataManager
from data_management.mongo_metadata import MongoMetadataManager


class TestMetadataFactory:
    """Test metadata factory functions."""

    def test_create_json_manager(self, temp_directory):
        """Test creating JSON manager via factory."""
        manager = create_metadata_manager("json", temp_directory)
        assert isinstance(manager, JSONMetadataManager)
        assert manager.location == Path(temp_directory)

    @pytest.mark.mongo
    def test_create_mongo_manager(self):
        """Test creating MongoDB manager via factory."""
        uri = "mongodb://localhost:27017"
        manager = create_metadata_manager("mongo", uri, database="test_db")
        assert isinstance(manager, MongoMetadataManager)
        assert manager.location == uri
        assert manager.database == "test_db"

    @pytest.mark.mongo
    def test_create_mongo_manager_default_db(self):
        """Test MongoDB manager with default database name."""
        uri = "mongodb://localhost:27017"
        manager = create_metadata_manager("mongo", uri)
        assert isinstance(manager, MongoMetadataManager)
        assert manager.database == "cst"

    def test_invalid_backend(self):
        """Test error handling for invalid backend."""
        with pytest.raises(ValueError, match="Unknown"):
            create_metadata_manager("invalid", "location")

    def test_case_insensitive_backend(self, temp_directory):
        """Test that backend names are case insensitive."""
        manager1 = create_metadata_manager("JSON", temp_directory)
        manager2 = create_metadata_manager("json", temp_directory)
        manager3 = create_metadata_manager("Json", temp_directory)

        assert all(
            isinstance(m, JSONMetadataManager) for m in [manager1, manager2, manager3]
        )
