"""
Created on 08/26/2025
Unit tests for Python federate
@author: Nathan Gray
nathan.gray@pnnl.gov
"""

import unittest
import logging
from unittest.mock import patch
from cosim_toolbox.sims import Federate

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)


class MockHelicsInput:
    def __init__(self):
        self.name = "_input_testName"
        self.target = "EVehicle/EV1_voltage"
        self.value = "testValue"
        self.double = 11.13
        self.string = "test_string"
        self.integer = 3
        self.boolean = True
        self.complex = 5 + 7j
        self.vector = [17.19, 23.29]
        self.complex_vector = [31 + 37j, 14 + 43j]


class MockHelicsEndpoint:
    def __init__(self):
        self.name = "Battery/EV1_voltage"
        self.default_destination = "EVehicle/EV1_current"
        self.n_pending_messages = 1

    def get_message(self):
        return "test_helics_message"


class MockHelicsFederate:
    def __init__(self):
        self.name = "Battery"  # Add missing name attribute
        self.n_inputs = 1
        self.n_endpoints = 1

    def get_subscription_by_index(self, idx):
        return MockHelicsInput()

    def get_endpoint_by_index(self, idx):
        return MockHelicsEndpoint()


class MockTimeSeriesManager:
    """Mock for the new time-series data manager"""

    def __init__(self, *args, **kwargs):
        self.connected = False
        self.buffer = []
        self.connect_called = False
        self.disconnect_called = False

    def connect(self):
        self.connected = True
        self.connect_called = True
        return True

    def disconnect(self):
        self.connected = False
        self.disconnect_called = True

    def write_records(self, records):
        self.buffer.extend(records)
        return True

    def add_record(self, record):
        self.buffer.append(record)

    def flush(self):
        return True

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class MockMetadataManager:
    """Mock for the new metadata manager"""

    def __init__(self, *args, **kwargs):
        self.connected = False
        self.connect_called = False
        self.disconnect_called = False
        self.scenario_dict = {
            "federation": "test_federation",
            "start_time": "2023-12-07T15:31:27",
            "stop_time": "2023-12-07T15:32:27",
            "analysis": "test_analysis",
        }
        self.federation_dict = {
            "federation": {
                "Battery": {
                    "image": "python/3.11.7-slim-bullseye",
                    "command": "python3 simple_federate.py TE30 EVehicle",
                    "federate_type": "value",
                    "time_step": 120,
                    "HELICS_config": {
                        "name": "Battery",
                        "core_type": "zmq",
                        "log_level": "warning",
                        "period": 60,
                        "uninterruptible": False,
                        "terminate_on_error": True,
                        "wait_for_current_time_update": True,
                        "publications": [
                            {
                                "global": True,
                                "key": "Battery/EV1_current",
                                "type": "double",
                                "unit": "A",
                            }
                        ],
                        "subscriptions": [
                            {
                                "global": True,
                                "key": "EVehicle/EV1_voltage",
                                "type": "double",
                                "unit": "V",
                            }
                        ],
                        "endpoints": [
                            {
                                "global": True,
                                "name": "Battery/EV1_voltage",
                                "destination": "EVehicle/EV1_current",
                            }
                        ],
                    },
                }
            }
        }

    def connect(self):
        self.connected = True
        self.connect_called = True
        return True

    def disconnect(self):
        self.connected = False
        self.disconnect_called = True

    def read_scenario(self, name):
        return self.scenario_dict

    def read_federation(self, name):
        return self.federation_dict

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class TestCreateFederate2(unittest.TestCase):
    def setUp(self):
        self.test_fed = Federate(fed_name="Battery")
        self.mock_metadata_manager = MockMetadataManager()
        self.mock_timeseries_manager = MockTimeSeriesManager()

    @patch("cosim_toolbox.federate.h.helicsCreateCombinationFederateFromConfig")
    @patch("cosim_toolbox.federate.h.helicsCreateMessageFederateFromConfig")
    @patch("cosim_toolbox.federate.h.helicsCreateValueFederateFromConfig")
    @patch("cosim_toolbox.federate.create_timeseries_manager")
    @patch("cosim_toolbox.federate.create_metadata_manager")
    def test_create_federate(
        self,
        mock_create_metadata_manager,
        mock_create_timeseries_manager,
        mock_create_value_federate,
        mock_create_message_federate,
        mock_create_combo_federate,
    ):
        # Setup mocks
        mock_create_metadata_manager.return_value = self.mock_metadata_manager
        mock_create_timeseries_manager.return_value = self.mock_timeseries_manager
        mock_helics_federate = MockHelicsFederate()

        # Test federate type value
        mock_create_value_federate.return_value = mock_helics_federate
        self.mock_metadata_manager.federation_dict["federation"]["Battery"][
            "federate_type"
        ] = "value"
        self.test_fed.create_federate("test_scenario")
        mock_create_value_federate.assert_called_once()

        # Reset mocks for next test
        mock_create_value_federate.reset_mock()

        # Test federate type message
        mock_create_message_federate.return_value = mock_helics_federate
        self.mock_metadata_manager.federation_dict["federation"]["Battery"][
            "federate_type"
        ] = "message"
        self.test_fed.create_federate("test_scenario")
        mock_create_message_federate.assert_called_once()

        # Reset mocks for next test
        mock_create_message_federate.reset_mock()

        # Test federate type combo
        mock_create_combo_federate.return_value = mock_helics_federate
        self.mock_metadata_manager.federation_dict["federation"]["Battery"][
            "federate_type"
        ] = "combo"
        self.test_fed.create_federate("test_scenario")
        mock_create_combo_federate.assert_called_once()

        # Test federate type invalid
        self.mock_metadata_manager.federation_dict["federation"]["Battery"][
            "federate_type"
        ] = "invalid"
        with self.assertRaises(ValueError):
            self.test_fed.create_federate("test_scenario")

        # Test federate attributes
        self.assertEqual(self.test_fed.period, 60)
        self.assertEqual(self.test_fed.stop_time, 60)
        self.assertEqual(len(self.test_fed.pubs), 1)
        self.assertEqual(len(self.test_fed.inputs), 1)
        self.assertEqual(len(self.test_fed.endpoints), 1)

        # Test None scenario name
        with self.assertRaises(NameError):
            self.test_fed.create_federate(None)

    @patch("cosim_toolbox.federate.h.helicsCreateCombinationFederateFromConfig")
    @patch("cosim_toolbox.federate.h.helicsCreateMessageFederateFromConfig")
    @patch("cosim_toolbox.federate.h.helicsCreateValueFederateFromConfig")
    @patch("cosim_toolbox.federate.create_timeseries_manager")
    @patch("cosim_toolbox.federate.create_metadata_manager")
    def test_run_cosim_loop(
        self,
        mock_create_metadata_manager,
        mock_create_timeseries_manager,
        mock_create_value_federate,
        mock_create_message_federate,
        mock_create_combo_federate,
    ):
        # Test without HELICS federate
        self.test_fed.hfed = None
        with self.assertRaises(ValueError):
            self.test_fed.run_cosim_loop()

        # Setup mocks
        mock_create_metadata_manager.return_value = self.mock_metadata_manager
        mock_create_timeseries_manager.return_value = self.mock_timeseries_manager
        mock_helics_federate = MockHelicsFederate()
        mock_create_value_federate.return_value = mock_helics_federate

        # Test with value federate
        self.mock_metadata_manager.federation_dict["federation"]["Battery"][
            "federate_type"
        ] = "value"
        self.test_fed.create_federate("test_scenario")

        # Test time calculation
        self.test_fed.granted_time = 100
        self.test_fed.time_step = 50
        self.test_fed.calculate_next_requested_time()
        self.assertEqual(self.test_fed.next_requested_time, 160)

        # Test data collection from federation
        self.test_fed.get_data_from_federation()
        expected_data_from_federation = {
            "endpoints": {"EVehicle/EV1_current": ["test_helics_message"]},
            "inputs": {"EVehicle/EV1_voltage": 11.13},
        }
        self.assertEqual(
            self.test_fed.data_from_federation, expected_data_from_federation
        )

        # Test data structure for sending to federation
        expected_data_to_federation = {
            "endpoints": {"Battery/EV1_voltage": None},
            "publications": {"Battery/EV1_current": None},
        }
        self.assertEqual(self.test_fed.data_to_federation, expected_data_to_federation)

    @patch("cosim_toolbox.federate.h.helicsCreateValueFederateFromConfig")
    @patch("cosim_toolbox.federate.create_timeseries_manager")
    @patch("cosim_toolbox.federate.create_metadata_manager")
    def test_data_managers_integration(
        self,
        mock_create_metadata_manager,
        mock_create_timeseries_manager,
        mock_create_value_federate,
    ):
        """Test that the federate properly integrates with new data managers"""

        # Setup mocks
        mock_create_metadata_manager.return_value = self.mock_metadata_manager
        mock_create_timeseries_manager.return_value = self.mock_timeseries_manager
        mock_helics_federate = MockHelicsFederate()
        mock_create_value_federate.return_value = mock_helics_federate

        # Create federate
        self.test_fed.create_federate("test_scenario")

        # Verify metadata manager was created and used
        mock_create_metadata_manager.assert_called_once()
        # Check that connect was called (even though it's disconnected after context manager)
        self.assertTrue(self.mock_metadata_manager.connect_called)
        self.assertTrue(self.mock_metadata_manager.disconnect_called)

        # Verify timeseries manager was created and connected
        mock_create_timeseries_manager.assert_called_once()
        self.assertTrue(self.mock_timeseries_manager.connect_called)
        # Timeseries manager should still be connected after create_federate
        self.assertTrue(self.mock_timeseries_manager.connected)

        # Test that federate has access to both managers
        self.assertIsNotNone(self.test_fed.metadata_manager)
        self.assertIsNotNone(self.test_fed.timeseries_manager)

    @patch("cosim_toolbox.federate.h.helicsCreateValueFederateFromConfig")
    @patch("cosim_toolbox.federate.create_timeseries_manager")
    @patch("cosim_toolbox.federate.create_metadata_manager")
    def test_scenario_and_federation_reading(
        self,
        mock_create_metadata_manager,
        mock_create_timeseries_manager,
        mock_create_value_federate,
    ):
        """Test that scenario and federation data is properly read from new metadata system"""

        # Setup mocks
        mock_create_metadata_manager.return_value = self.mock_metadata_manager
        mock_create_timeseries_manager.return_value = self.mock_timeseries_manager
        mock_helics_federate = MockHelicsFederate()
        mock_create_value_federate.return_value = mock_helics_federate

        # Create federate
        self.test_fed.create_federate("test_scenario")

        # Verify scenario data was read correctly
        self.assertEqual(self.test_fed.scenario_name, "test_scenario")
        self.assertEqual(self.test_fed.start, "2023-12-07T15:31:27")
        self.assertEqual(self.test_fed.stop, "2023-12-07T15:32:27")
        self.assertEqual(self.test_fed.analysis_name, "test_analysis")

        # Verify federation data was read correctly
        self.assertEqual(self.test_fed.federation_name, "test_federation")
        self.assertEqual(self.test_fed.federate_type, "value")
        self.assertEqual(self.test_fed.period, 60)

    @patch("cosim_toolbox.federate.h.helicsCreateValueFederateFromConfig")
    @patch("cosim_toolbox.federate.create_timeseries_manager")
    @patch("cosim_toolbox.federate.create_metadata_manager")
    def test_federate_initialization_options(
        self,
        mock_create_metadata_manager,
        mock_create_timeseries_manager,
        mock_create_value_federate,
    ):
        """Test federate initialization with different options"""

        # Setup mocks
        mock_create_metadata_manager.return_value = self.mock_metadata_manager
        mock_create_timeseries_manager.return_value = self.mock_timeseries_manager
        mock_helics_federate = MockHelicsFederate()
        mock_create_value_federate.return_value = mock_helics_federate

        # Test with use_mdb=False (should use JSON)
        federate_json = Federate(fed_name="Battery")
        federate_json.metadata_location = "/tmp/test"
        federate_json.create_federate("test_scenario")

        # Verify JSON metadata manager was requested
        mock_create_metadata_manager.assert_called_with(
            backend="json", location="/tmp/test"
        )

        # Reset mock
        mock_create_metadata_manager.reset_mock()

        # Test with use_mdb=True (should use MongoDB)
        federate_mongo = Federate(fed_name="Battery", use_mdb=True)
        federate_mongo.create_federate("test_scenario")

        # Verify MongoDB metadata manager was requested
        self.assertTrue(mock_create_metadata_manager.called)
        call_kwargs = mock_create_metadata_manager.call_args[1]
        self.assertEqual(call_kwargs["backend"], "mongo")


if __name__ == "__main__":
    unittest.main()
