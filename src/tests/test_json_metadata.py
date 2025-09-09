"""
Tests for JSON metadata manager.
"""

import json
from pathlib import Path
from cosim_toolbox.dbms import JSONMetadataManager


class TestJSONMetadataManager:
    """Test JSON metadata manager functionality."""

    def test_initialization(self, temp_directory):
        """Test JSON manager initialization."""
        manager = JSONMetadataManager(temp_directory)
        assert manager.location == Path(temp_directory)
        assert not manager.is_connected

    def test_connection(self, temp_directory):
        """Test connection creates directory structure."""
        manager = JSONMetadataManager(temp_directory)

        success = manager.connect()
        assert success is True
        assert manager.is_connected is True

        # Check directory structure
        base_path = Path(temp_directory)
        assert base_path.exists()
        assert (base_path / "federations").exists()
        assert (base_path / "scenarios").exists()

        manager.disconnect()
        assert manager.is_connected is False

    def test_write_read_federation(self, temp_directory, sample_federation_data):
        """Test writing and reading federation data."""
        with JSONMetadataManager(temp_directory) as manager:
            # Write federation
            success = manager.write_federation("TestFed", sample_federation_data)
            assert success is True

            # Check file was created
            fed_file = manager.federations_path / "TestFed.json"
            assert fed_file.exists()

            # Read federation
            data = manager.read_federation("TestFed")
            assert data == sample_federation_data

            # Verify file content directly
            with open(fed_file, "r") as f:
                file_data = json.load(f)
            assert file_data == sample_federation_data

    def test_write_read_scenario(self, temp_directory, sample_scenario_data):
        """Test writing and reading scenario data."""
        with JSONMetadataManager(temp_directory) as manager:
            success = manager.write_scenario("TestScenario", sample_scenario_data)
            assert success is True

            data = manager.read_scenario("TestScenario")
            assert data == sample_scenario_data

    def test_write_read_custom(self, temp_directory, sample_custom_data):
        """Test writing and reading custom data."""
        with JSONMetadataManager(temp_directory) as manager:
            success = manager.write("electrical_config", "main", sample_custom_data)
            assert success is True

            # Check custom directory was created
            custom_dir = manager.location / "electrical_config"
            assert custom_dir.exists()
            assert (custom_dir / "main.json").exists()

            data = manager.read("electrical_config", "main")
            assert data == sample_custom_data

    def test_overwrite_protection(self, temp_directory, sample_federation_data):
        """Test overwrite protection."""
        with JSONMetadataManager(temp_directory) as manager:
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

    def test_delete_operations(self, temp_directory, sample_federation_data):
        """Test delete operations."""
        with JSONMetadataManager(temp_directory) as manager:
            # Create some data
            manager.write_federation("TestFed", sample_federation_data)
            manager.write_scenario("TestScenario", {"test": "data"})
            manager.write("custom", "item", {"test": "data"})

            # Test deletions
            assert manager.delete_federation("TestFed") is True
            assert manager.delete_scenario("TestScenario") is True
            assert manager.delete("custom", "item") is True

            # Verify files are gone
            assert not (manager.federations_path / "TestFed.json").exists()
            assert not (manager.scenarios_path / "TestScenario.json").exists()
            assert not (manager.location / "custom" / "item.json").exists()

            # Deleting non-existent items should return False
            assert manager.delete_federation("NonExistent") is False

    def test_list_operations(self, temp_directory, sample_federation_data):
        """Test listing operations."""
        with JSONMetadataManager(temp_directory) as manager:
            # Create test data
            manager.write_federation("Fed1", sample_federation_data)
            manager.write_federation("Fed2", sample_federation_data)
            manager.write_scenario("Scenario1", {"test": "data"})
            manager.write_scenario("Scenario2", {"test": "data"})
            manager.write("collection1", "item1", {"test": "data"})
            manager.write("collection1", "item2", {"test": "data"})
            manager.write("collection2", "item1", {"test": "data"})

            # Test lists
            federations = manager.list_federations()
            scenarios = manager.list_scenarios()
            collections = manager.list_custom_collections()
            items = manager.list_items("collection1")

            assert set(federations) == {"Fed1", "Fed2"}
            assert set(scenarios) == {"Scenario1", "Scenario2"}
            assert set(collections) == {"collection1", "collection2"}
            assert set(items) == {"item1", "item2"}

    def test_exists_operations(self, temp_directory, sample_federation_data):
        """Test existence checking."""
        with JSONMetadataManager(temp_directory) as manager:
            # Initially nothing exists
            assert manager.exists_federation("TestFed") is False
            assert manager.exists_scenario("TestScenario") is False
            assert manager.exists("custom", "item") is False

            # Create some data
            manager.write_federation("TestFed", sample_federation_data)
            manager.write_scenario("TestScenario", {"test": "data"})
            manager.write("custom", "item", {"test": "data"})

            # Now they should exist
            assert manager.exists_federation("TestFed") is True
            assert manager.exists_scenario("TestScenario") is True
            assert manager.exists("custom", "item") is True

    def test_invalid_names(self, temp_directory):
        """Test handling of invalid names."""
        with JSONMetadataManager(temp_directory) as manager:
            invalid_names = ["", "test\bad", "con", " test "]

            for name in invalid_names:
                success = manager.write_federation(name, {"test": "data"})
                assert success is False

                data = manager.read_federation(name)
                assert data is None

    def test_nonexistent_reads(self, temp_directory):
        """Test reading non-existent data."""
        with JSONMetadataManager(temp_directory) as manager:
            assert manager.read_federation("NonExistent") is None
            assert manager.read_scenario("NonExistent") is None
            assert manager.read("custom", "NonExistent") is None

    def test_operations_without_connection(
        self, temp_directory, sample_federation_data
    ):
        """Test operations fail without connection."""
        manager = JSONMetadataManager(temp_directory)
        # Don't connect

        assert manager.write_federation("test", sample_federation_data) is False
        assert manager.read_federation("test") is None
        assert manager.list_federations() == []
