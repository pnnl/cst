"""
Comprehensive test suite for CoSim Toolbox data management system.
Tests all components: TSRecord, JSON, MongoDB, factory, and base functionality.
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys

# Add source path
sys.path.insert(0, "src/cosim_toolbox")

# Import our modules
from cosim_toolbox.dbms import TSRecord
from cosim_toolbox.dbms import JSONMetadataManager
from cosim_toolbox.dbms import create_metadata_manager

# Try to import MongoDB components
try:
    from cosim_toolbox.dbms import MongoMetadataManager

    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False


class TestTSRecord(unittest.TestCase):
    """Test TSRecord dataclass functionality."""

    def test_tsrecord_creation(self):
        """Test basic TSRecord creation."""
        now = datetime.now()
        record = TSRecord(
            real_time=now,
            sim_time=120.5,
            scenario="TestScenario",
            federate="TestFederate",
            data_name="test/voltage",
            data_value=240.5,
        )

        self.assertEqual(record.real_time, now)
        self.assertEqual(record.sim_time, 120.5)
        self.assertEqual(record.scenario, "TestScenario")
        self.assertEqual(record.federate, "TestFederate")
        self.assertEqual(record.data_name, "test/voltage")
        self.assertEqual(record.data_value, 240.5)

    def test_tsrecord_different_types(self):
        """Test TSRecord with different data value types."""
        now = datetime.now()
        test_cases = [
            ("double", 123.45),
            ("integer", 42),
            ("string", "active"),
            ("boolean", True),
            ("complex", 3 + 4j),
            ("list", [1, 2, 3]),
            ("dict", {"voltage": 120, "frequency": 60}),
        ]

        for data_type, value in test_cases:
            with self.subTest(data_type=data_type):
                record = TSRecord(
                    real_time=now,
                    sim_time=0.0,
                    scenario="test",
                    federate="test_fed",
                    data_name=f"test_{data_type}",
                    data_value=value,
                )
                self.assertEqual(record.data_value, value)
                self.assertEqual(type(record.data_value), type(value))


class TestJSONMetadataManager(unittest.TestCase):
    """Test JSON metadata manager functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = JSONMetadataManager(self.temp_dir)
        self.sample_federation = {
            "federation": {
                "Battery": {
                    "federate_type": "value",
                    "period": 60,
                    "HELICS_config": {"name": "Battery", "core_type": "zmq"},
                }
            }
        }
        self.sample_scenario = {
            "analysis": "TestAnalysis",
            "federation": "TestFederation",
            "start_time": "2023-12-07T15:31:27",
            "stop_time": "2023-12-08T15:31:27",
            "docker": False,
        }

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_connection_management(self):
        """Test connection and disconnection."""
        self.assertFalse(self.manager.is_connected)

        success = self.manager.connect()
        self.assertTrue(success)
        self.assertTrue(self.manager.is_connected)

        # Check directories were created
        self.assertTrue(Path(self.temp_dir).exists())
        self.assertTrue((Path(self.temp_dir) / "federations").exists())
        self.assertTrue((Path(self.temp_dir) / "scenarios").exists())

        self.manager.disconnect()
        self.assertFalse(self.manager.is_connected)

    def test_context_manager(self):
        """Test context manager functionality."""
        with self.manager as mgr:
            self.assertTrue(mgr.is_connected)
            success = mgr.write_federation("TestFed", self.sample_federation)
            self.assertTrue(success)
        self.assertFalse(self.manager.is_connected)

    def test_federation_operations(self):
        """Test federation CRUD operations."""
        with self.manager as mgr:
            # Test write
            success = mgr.write_federation("TestFed", self.sample_federation)
            self.assertTrue(success)

            # Test read
            fed_data = mgr.read_federation("TestFed")
            self.assertIsNotNone(fed_data)
            self.assertEqual(fed_data, self.sample_federation)

            # Test exists
            self.assertTrue(mgr.exists_federation("TestFed"))
            self.assertFalse(mgr.exists_federation("NonExistent"))

            # Test list
            federations = mgr.list_federations()
            self.assertIn("TestFed", federations)

            # Test delete
            success = mgr.delete_federation("TestFed")
            self.assertTrue(success)
            self.assertFalse(mgr.exists_federation("TestFed"))

    def test_scenario_operations(self):
        """Test scenario CRUD operations."""
        with self.manager as mgr:
            # Test write
            success = mgr.write_scenario("TestScenario", self.sample_scenario)
            self.assertTrue(success)

            # Test read
            scenario_data = mgr.read_scenario("TestScenario")
            self.assertIsNotNone(scenario_data)
            self.assertEqual(scenario_data, self.sample_scenario)

            # Test exists
            self.assertTrue(mgr.exists_scenario("TestScenario"))

            # Test list
            scenarios = mgr.list_scenarios()
            self.assertIn("TestScenario", scenarios)

            # Test delete
            success = mgr.delete_scenario("TestScenario")
            self.assertTrue(success)
            self.assertFalse(mgr.exists_scenario("TestScenario"))

    def test_generic_operations(self):
        """Test generic write/read operations."""
        test_data = {"param1": 42, "param2": "test"}

        with self.manager as mgr:
            # Test generic write
            success = mgr.write("custom_collection", "test_item", test_data)
            self.assertTrue(success)

            # Test generic read
            read_data = mgr.read("custom_collection", "test_item")
            self.assertEqual(read_data, test_data)

            # Test generic exists
            self.assertTrue(mgr.exists("custom_collection", "test_item"))

            # Test generic list
            items = mgr.list_items("custom_collection")
            self.assertIn("test_item", items)

            # Test list custom collections
            collections = mgr.list_custom_collections()
            self.assertIn("custom_collection", collections)

            # Test generic delete
            success = mgr.delete("custom_collection", "test_item")
            self.assertTrue(success)
            self.assertFalse(mgr.exists("custom_collection", "test_item"))

    def test_overwrite_protection(self):
        """Test overwrite protection functionality."""
        with self.manager as mgr:
            # First write should succeed
            success1 = mgr.write_federation("TestFed", self.sample_federation)
            self.assertTrue(success1)

            # Second write should fail (overwrite=False by default)
            success2 = mgr.write_federation("TestFed", self.sample_federation)
            self.assertFalse(success2)

            # Third write with overwrite=True should succeed
            success3 = mgr.write_federation(
                "TestFed", self.sample_federation, overwrite=True
            )
            self.assertTrue(success3)

    def test_name_validation(self):
        """Test name validation."""
        invalid_names = [
            "",  # Empty
            "a" * 256,  # Too long
#            "test/bad",  # Invalid character
            "test\\bad",  # Invalid character
            "test:bad",  # Invalid character
            "test*bad",  # Invalid character
            " test ",  # Leading/trailing space
            ".test",  # Leading period
            "CON",  # Reserved name
            "PRN",  # Reserved name
        ]

        with self.manager as mgr:
            for invalid_name in invalid_names:
                with self.subTest(name=invalid_name):
                    success = mgr.write_federation(invalid_name, self.sample_federation)
                    self.assertFalse(success)

    def test_file_structure(self):
        """Test that correct file structure is created."""
        with self.manager as mgr:
            mgr.write_federation("TestFed", self.sample_federation)
            mgr.write_scenario("TestScenario", self.sample_scenario)
            mgr.write("custom_collection", "test_item", {"test": "data"})

        base_path = Path(self.temp_dir)

        # Check standard directories
        self.assertTrue((base_path / "federations").exists())
        self.assertTrue((base_path / "scenarios").exists())
        self.assertTrue((base_path / "custom_collection").exists())

        # Check files
        self.assertTrue((base_path / "federations" / "TestFed.json").exists())
        self.assertTrue((base_path / "scenarios" / "TestScenario.json").exists())
        self.assertTrue((base_path / "custom_collection" / "test_item.json").exists())

        # Verify file contents
        with open(base_path / "federations" / "TestFed.json", "r") as f:
            data = json.load(f)
            self.assertEqual(data, self.sample_federation)


@unittest.skipUnless(MONGO_AVAILABLE, "pymongo not available")
class TestMongoMetadataManager(unittest.TestCase):
    """Test MongoDB metadata manager functionality."""

    def setUp(self):
        """Set up test environment with mocked MongoDB."""
        # Sample data
        self.sample_federation = {
            "federation": {"Battery": {"federate_type": "value", "period": 60}}
        }

    def _setup_mock_client(self):
        """Create properly configured mock MongoDB client."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        # Configure the mock chain: client -> db -> collection
        mock_client.admin.command.return_value = True  # ping success
        mock_client.__getitem__.return_value = mock_db
        mock_db.federations = mock_collection  # db.federations = mock_collection
        mock_db.scenarios = (
            mock_collection  # db.scenarios = mock_collection (if needed)
        )
        mock_db.__getitem__.return_value = (
            mock_collection  # db[collection_name] = mock_collection
        )
        mock_db.list_collection_names.return_value = []

        return mock_client, mock_db, mock_collection

    @patch("cosim_toolbox.dbms.mongo_metadata.MongoClient")
    def test_connection_management(self, mock_mongo_client):
        """Test MongoDB connection management."""
        mock_client, mock_db, mock_collection = self._setup_mock_client()
        mock_mongo_client.return_value = mock_client

        manager = MongoMetadataManager(location="localhost", database="test_db")

        success = manager.connect()
        self.assertTrue(success)
        self.assertTrue(manager.is_connected)

        # Verify connection was attempted with correct URI (including auth params)
        expected_uri = (
            "mongodb://localhost/?authSource=test_db&authMechanism=SCRAM-SHA-1"
        )
        mock_mongo_client.assert_called_once_with(
            expected_uri, serverSelectionTimeoutMS=5000
        )
        mock_client.admin.command.assert_called_once_with("ping")

        manager.disconnect()
        self.assertFalse(manager.is_connected)
        mock_client.close.assert_called_once()

    @patch("cosim_toolbox.dbms.mongo_metadata.MongoClient")
    def test_federation_operations(self, mock_mongo_client):
        """Test MongoDB federation operations."""
        mock_client, mock_db, mock_collection = self._setup_mock_client()
        mock_mongo_client.return_value = mock_client

        # Mock successful operations - no existing document first
        mock_collection.find_one.return_value = None  # Explicitly return None
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = "mock_id"
        mock_collection.insert_one.return_value = mock_insert_result

        manager = MongoMetadataManager(location="localhost", database="test_db")

        with manager as mgr:
            # Test write
            success = mgr.write_federation("TestFed", self.sample_federation)
            self.assertTrue(success)

            # Verify MongoDB calls - note: the actual field name is 'cst_007'
            expected_doc = self.sample_federation.copy()
            expected_doc["cst_007"] = "TestFed"
            mock_collection.insert_one.assert_called_once_with(expected_doc)

    @patch("cosim_toolbox.dbms.mongo_metadata.MongoClient")
    def test_overwrite_protection(self, mock_mongo_client):
        """Test MongoDB overwrite protection."""
        mock_client, mock_db, mock_collection = self._setup_mock_client()
        mock_mongo_client.return_value = mock_client

        manager = MongoMetadataManager(location="localhost", database="test_db")

        with manager as mgr:
            # Test 1: Should fail without overwrite when document exists
            existing_doc = {"cst_007": "TestFed", "data": "old"}
            mock_collection.find_one.return_value = existing_doc

            success = mgr.write_federation(
                "TestFed", self.sample_federation, overwrite=False
            )
            self.assertFalse(success)

            # Test 2: Should succeed with overwrite
            mock_replace_result = MagicMock()
            mock_replace_result.modified_count = 1
            mock_replace_result.matched_count = 1
            mock_collection.replace_one.return_value = mock_replace_result

            success = mgr.write_federation(
                "TestFed", self.sample_federation, overwrite=True
            )
            self.assertTrue(success)

            # Verify replace_one was called
            expected_doc = self.sample_federation.copy()
            expected_doc["cst_007"] = "TestFed"
            mock_collection.replace_one.assert_called_once_with(
                {"cst_007": "TestFed"}, expected_doc
            )

    @patch("cosim_toolbox.dbms.mongo_metadata.MongoClient")
    def test_read_operations(self, mock_mongo_client):
        """Test MongoDB read operations."""
        mock_client, mock_db, mock_collection = self._setup_mock_client()
        mock_mongo_client.return_value = mock_client
        mock_collection.find_one.return_value = self.sample_federation

        manager = MongoMetadataManager(location="localhost", database="test_db")

        with manager as mgr:
            # Test read - should return data without _id and cst_007 fields
            federation_data = mgr.read_federation("TestFed")
            self.assertEqual(federation_data, self.sample_federation)

            # Verify correct query was made
            mock_collection.find_one.assert_called_with({"cst_007": "TestFed"})


class TestMetadataFactory(unittest.TestCase):
    """Test metadata factory functionality."""

    def test_create_json_manager(self):
        """Test creating JSON manager via factory."""
        temp_dir = tempfile.mkdtemp()
        try:
            manager = create_metadata_manager("json", location=temp_dir)
            self.assertIsInstance(manager, JSONMetadataManager)
            self.assertEqual(manager.location, Path(temp_dir))
        finally:
            shutil.rmtree(temp_dir)

    @unittest.skipUnless(MONGO_AVAILABLE, "pymongo not available")
    def test_create_mongo_manager(self):
        """Test creating MongoDB manager via factory."""
        manager = create_metadata_manager(
            backend="mongo", location="localhost", database="test"
        )
        self.assertIsInstance(manager, MongoMetadataManager)
        # Check that the URI was constructed correctly
        self.assertEqual(manager.database, "test")

    def test_unknown_backend(self):
        """Test factory with unknown backend."""
        with self.assertRaises(ValueError) as context:
            create_metadata_manager("unknown", location="location")
        self.assertIn("Unknown", str(context.exception))


class TestFederationRunnerCompatibility(unittest.TestCase):
    """Test compatibility with the federation runner structure."""

    def setUp(self):
        """Set up federation runner compatible data."""
        self.temp_dir = tempfile.mkdtemp()

        # Data structure matching runner2.py
        self.federation_data = {
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
                        "tags": {"logger": "no"},
                        "publications": [
                            {
                                "global": True,
                                "key": "Battery/EV_current",
                                "type": "double",
                                "unit": "A",
                            }
                        ],
                        "subscriptions": [
                            {
                                "key": "EVehicle/EV_voltage",
                                "type": "double",
                                "unit": "V",
                            }
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
                        "tags": {"logger": "no"},
                        "publications": [
                            {
                                "global": True,
                                "key": "EVehicle/EV_voltage",
                                "type": "double",
                                "unit": "V",
                            }
                        ],
                        "subscriptions": [
                            {"key": "Battery/EV_current", "type": "double", "unit": "A"}
                        ],
                    },
                },
            }
        }

        self.scenario_data = {
            "analysis": "MyAnalysis",
            "federation": "MyFederation",
            "start_time": "2023-12-07T15:31:27",
            "stop_time": "2023-12-08T15:31:27",
            "docker": False,
        }

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_federation_runner_workflow(self):
        """Test the complete federation runner workflow."""
        manager = create_metadata_manager("json", location=self.temp_dir)

        with manager as mgr:
            # Store federation and scenario (like FederationConfig.define_scenario)
            fed_success = mgr.write_federation("MyFederation", self.federation_data)
            scenario_success = mgr.write_scenario("MyScenario", self.scenario_data)

            self.assertTrue(fed_success)
            self.assertTrue(scenario_success)

            # Simulate federate reading its configuration
            scenario = mgr.read_scenario("MyScenario")
            self.assertIsNotNone(scenario)

            federation_name = scenario["federation"]
            self.assertEqual(federation_name, "MyFederation")

            federation = mgr.read_federation(federation_name)
            self.assertIsNotNone(federation)

            # Extract Battery configuration (like federate.py does)
            battery_config = federation["federation"]["Battery"]
            self.assertEqual(battery_config["federate_type"], "value")
            self.assertEqual(battery_config["HELICS_config"]["period"], 60)

            # Verify all required fields exist
            required_scenario_fields = [
                "analysis",
                "federation",
                "start_time",
                "stop_time",
            ]
            for field in required_scenario_fields:
                self.assertIn(field, scenario)

            required_federate_fields = ["federate_type", "HELICS_config"]
            for field in required_federate_fields:
                self.assertIn(field, battery_config)

            helics_config = battery_config["HELICS_config"]
            required_helics_fields = ["name", "period", "publications", "subscriptions"]
            for field in required_helics_fields:
                self.assertIn(field, helics_config)

    def test_multiple_federates_configuration(self):
        """Test handling multiple federates like in the runner."""
        manager = create_metadata_manager("json", loaction=self.temp_dir)

        with manager as mgr:
            mgr.write_federation("MyFederation", self.federation_data)
            federation = mgr.read_federation("MyFederation")

            federates = federation["federation"]
            self.assertEqual(len(federates), 2)
            self.assertIn("Battery", federates)
            self.assertIn("EVehicle", federates)

            # Test that each federate has proper HELICS configuration
            for fed_name, fed_config in federates.items():
                with self.subTest(federate=fed_name):
                    helics_config = fed_config["HELICS_config"]

                    # Each should have publications and subscriptions
                    self.assertIn("publications", helics_config)
                    self.assertIn("subscriptions", helics_config)

                    pubs = helics_config["publications"]
                    subs = helics_config["subscriptions"]

                    # Each should have exactly one pub and one sub
                    self.assertEqual(len(pubs), 1)
                    self.assertEqual(len(subs), 1)

                    # Publications should have required fields
                    pub = pubs[0]
                    self.assertIn("key", pub)
                    self.assertIn("type", pub)
                    self.assertIn("unit", pub)

                    # Subscriptions should have required fields
                    sub = subs[0]
                    self.assertIn("key", sub)
                    self.assertIn("type", sub)
                    self.assertIn("unit", sub)


class TestErrorHandlingAndEdgeCases(unittest.TestCase):
    """Test error handling and edge cases."""

    def test_operations_without_connection(self):
        """Test operations when not connected."""
        temp_dir = tempfile.mkdtemp()
        try:
            manager = JSONMetadataManager(temp_dir)
            # Don't connect

            # All operations should fail gracefully
            self.assertFalse(manager.write_federation("test", {}))
            self.assertIsNone(manager.read_federation("test"))
            self.assertFalse(manager.delete_federation("test"))
            self.assertEqual(manager.list_federations(), [])
        finally:
            shutil.rmtree(temp_dir)

    def test_large_data_handling(self):
        """Test handling of large data structures."""
        temp_dir = tempfile.mkdtemp()
        try:
            manager = JSONMetadataManager(temp_dir)

            # Create large data structure
            large_data = {
                "large_array": list(range(10000)),
                "nested_data": {f"key_{i}": f"value_{i}" for i in range(1000)},
            }

            with manager as mgr:
                success = mgr.write("large_collection", "large_item", large_data)
                self.assertTrue(success)

                read_data = mgr.read("large_collection", "large_item")
                self.assertEqual(read_data, large_data)
        finally:
            shutil.rmtree(temp_dir)

    def test_concurrent_access_simulation(self):
        """Simulate concurrent access scenarios."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create two managers pointing to the same location
            manager1 = JSONMetadataManager(temp_dir)
            manager2 = JSONMetadataManager(temp_dir)

            data1 = {"source": "manager1", "value": 1}
            data2 = {"source": "manager2", "value": 2}

            with manager1 as mgr1, manager2 as mgr2:
                # Both write to the same location
                success1 = mgr1.write("test_collection", "shared_item", data1)
                success2 = mgr2.write(
                    "test_collection", "shared_item", data2, overwrite=True
                )

                self.assertTrue(success1)
                self.assertTrue(success2)

                # The last write should win
                final_data = mgr1.read("test_collection", "shared_item")
                self.assertEqual(final_data["source"], "manager2")
        finally:
            shutil.rmtree(temp_dir)


def run_all_tests():
    """Run all test suites."""
    print("=== CoSim Toolbox Data Management Comprehensive Test Suite ===\n")

    # Create test suite
    test_suites = [
        unittest.TestLoader().loadTestsFromTestCase(TestTSRecord),
        unittest.TestLoader().loadTestsFromTestCase(TestJSONMetadataManager),
        unittest.TestLoader().loadTestsFromTestCase(TestMetadataFactory),
        unittest.TestLoader().loadTestsFromTestCase(TestFederationRunnerCompatibility),
        unittest.TestLoader().loadTestsFromTestCase(TestErrorHandlingAndEdgeCases),
    ]

    # Add MongoDB tests if available
    if MONGO_AVAILABLE:
        test_suites.append(
            unittest.TestLoader().loadTestsFromTestCase(TestMongoMetadataManager)
        )
        print("MongoDB tests included")
    else:
        print("MongoDB tests skipped (pymongo not available)")

    print(f"\nRunning {len(test_suites)} test suites...\n")

    # Combine all test suites
    combined_suite = unittest.TestSuite(test_suites)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)
    result = runner.run(combined_suite)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    if result.skipped:
        print("\nSKIPPED:")
        for test, reason in result.skipped:
            print(f"  - {test}: {reason}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall result: {'✅ PASSED' if success else '❌ FAILED'}")
    return success


if __name__ == "__main__":
    _success = run_all_tests()
    sys.exit(0 if _success else 1)
