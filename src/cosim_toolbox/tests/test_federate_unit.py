"""
Created on 01/16/2024

Unit tests for Python federate

@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""
import collections
collections.Callable = collections.abc.Callable

import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)

from unittest.mock import patch
import unittest
from cosim_toolbox.federate import Federate


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
        self.name = "test_helics_endpoint"
        self.n_pending_messages = 1

    def get_message(self):
        return MockHelicsMessage()


class MockHelicsMessage:
    def __init__(self):
        self.data = "test_helics_message"


class MockHelicsFederate:

    def __init__(self):
        self.n_inputs = 1
        self.n_endpoints = 1
        self.get_endpoint_by_index = MockHelicsEndpoint()

    def get_subscription_by_index(self, idx):
        return MockHelicsInput()


class MockMetadataDB:
    cosim_mongo_host = None
    cosim_mongo_db = None
    cu_federations = "federations"
    cu_scenarios = "scenarios"

    def __init__(self, uri, db_name):
        self.uri = uri
        self.db_name = db_name
        self.config = ""
        self.scenario_dict = {
            "federation": "test_federation",
            "start_time": "2023-12-07T15:31:27",
            "stop_time": "2023-12-07T15:32:27"
        }

        self.federation_dict = {
            "cu_name": "BT1_EV1",
            "federation": {
                "Battery": {
                    "image": "python/3.11.7-slim-bullseye",
                    "command": "exec python3 simple_federate.py TE30 EVehicle",
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
                                "unit": "A"
                            }
                        ],
                        "subscriptions": [
                            {
                                "global": True,
                                "key": "EVehicle/EV1_voltage",
                                "type": "double",
                                "unit": "V"
                            }
                        ]
                    }
                }
            }
        }

    def get_dict(self, test_scenario, object_id, dict_name):
        if test_scenario == "scenarios":
            return self.scenario_dict
        if test_scenario == "federations":
            return self.federation_dict


@patch('helics.helicsCreateCombinationFederateFromConfig')
@patch('helics.helicsCreateMessageFederateFromConfig')
@patch('helics.helicsCreateValueFederateFromConfig')
@patch("cosim_toolbox.federate.mDB.MetaDB")
@patch("cosim_toolbox.metadataDB", MockMetadataDB)
class TestCreateFederate(unittest.TestCase):

    def setUp(self):
        self.test_fed = Federate(fed_name="Battery")
        self.mock_meta_db_instance = MockMetadataDB("fake_uri", "fake_db_name")

    def test_create_federate(self,
                             mock_meta_db_class,
                             mock_create_value_federate,
                             mock_create_message_federate,
                             mock_create_combo_federate):
        mock_meta_db_class.return_value = self.mock_meta_db_instance

        # federate type value
        self.mock_meta_db_instance.federation_dict["federation"]["Battery"]["federate_type"] = "value"
        self.test_fed.create_federate("test_scenario")
        mock_create_value_federate.assert_called_once()

        # federate type message
        self.mock_meta_db_instance.federation_dict["federation"]["Battery"]["federate_type"] = "message"
        self.test_fed.create_federate("test_scenario")
        mock_create_message_federate.assert_called_once()

        # federate type combo
        self.mock_meta_db_instance.federation_dict["federation"]["Battery"]["federate_type"] = "combo"
        self.test_fed.create_federate("test_scenario")
        mock_create_combo_federate.assert_called_once()

        # federate type invalid
        self.mock_meta_db_instance.federation_dict["federation"]["Battery"]["federate_type"] = "invalid"
        with self.assertRaises(ValueError):
            self.test_fed.create_federate("test_scenario")

        self.assertEqual(self.test_fed.time_step, 60)
        self.assertEqual(self.test_fed.stop_time, 60)
        self.assertEqual(len(self.test_fed.pubs), 1)
        self.assertEqual(len(self.test_fed.inputs), 1)
        self.assertEqual(len(self.test_fed.endpoints), 0)

        with self.assertRaises(NameError):
            self.test_fed.create_federate(None)

    def test_run_cosim_loop(self,
                            mock_meta_db_class,
                            mock_create_value_federate,
                            mock_create_message_federate,
                            mock_create_combo_federate):
        self.test_fed.hfed = None
        with self.assertRaises(ValueError):
            self.test_fed.run_cosim_loop()

        mock_meta_db_class.return_value = self.mock_meta_db_instance

        mock_helics_federate = MockHelicsFederate()
        mock_create_value_federate.return_value = mock_helics_federate

        # federate type value
        self.mock_meta_db_instance.federation_dict["federation"]["Battery"]["federate_type"] = "value"
        self.test_fed.create_federate("test_scenario")
        self.test_fed.granted_time = 100
        self.test_fed.time_step = 50
        self.test_fed.calculate_next_requested_time()
        self.assertEqual(self.test_fed.next_requested_time, 150)

        self.test_fed.get_data_from_federation()
        expected_data_from_federation = {'endpoints': {'test_helics_endpoint': ['test_helics_message']},
                                         'inputs': {'EVehicle/EV1_voltage': 11.13}, 'test_helics_endpoint': []}
        self.assertEqual(self.test_fed.data_from_federation, expected_data_from_federation)

        expected_data_to_federation = {'endpoints': {}, 'publications': {'Battery/EV1_current': None}}
        self.assertEqual(self.test_fed.data_to_federation, expected_data_to_federation)
