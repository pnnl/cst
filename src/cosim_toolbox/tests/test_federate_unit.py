"""
Created on 01/16/2024

Unit tests for Python federate

@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""
import datetime
import json
import logging

import helics as h

import cosim_toolbox.metadataDB as mDB

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)

from unittest import TestCase
from unittest.mock import patch, MagicMock
import unittest
from cosim_toolbox.federate import Federate



class MockHelicsInput:
    def __init__(self):
        pass        

    def helicsInputGetDouble(self):
        return 11.13
    
    def helicsInputGetString(self):
        return "test_string"
    
    def helicsInputGetInteger(self):
        return 3
    
    def helicsInputGetBoolean(self):
        return True
    
    def helicsInputGetBoolean(self):
        return 5+7j
    
    def helicsInputGetVector(self):
        return [17.19, 23.29]

    def helicsInputGetComplexVector(self):
        return [31+37j, 14+43j]


class MockHelicsEndpoint:
    def __init__(self):
        mock_message = MockHelicsMessage()    

    def helicsEndpointPendingMessageCount(self):
        return 1
    
    def helicsEndpointGetMessage(self):
        return self.mock_message.helicsMessageGetString()
    
    def helicsEndpointSendMessage(self):
        return


class MockHelicsMessage:
    def __init__(self):
        pass   

    def helicsMessageGetString(self):
        return "test_message_string"


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
            "federation": "test_federation",
            "test_fed": {
                "federate_type": "value",
                "HELICS config":{
                    "period": 3,
                    "publications": [
                        {
                            "key": "mock_pub",
                            "type": "double"
                        }
                    ],
                    "subscription": [
                        {
                            "key": "mock_sub",
                            "type": "double"
                        }
                    ],
                    "input": [
                        {
                            "name": "mock_input_double",
                            "type": "double"
                        },
                        {
                            "name": "mock_input_integer",
                            "type": "integer"
                        },
                        {
                            "name": "mock_input_complex",
                            "type": "complex"
                        },
                        {
                            "name": "mock_input_string",
                            "type": "string"
                        },
                        {
                            "name": "mock_input_vector",
                            "type": "vector"
                        },
                        {
                            "name": "mock_input_complex_vector",
                            "type": "complex vector"
                        },
                        {
                            "name": "mock_input_boolean",
                            "type": "boolean"
                        }
                    ],
                    "endpoint": [
                        {
                            "name": "mock_endpoint_2",
                            "key": "mock_key_2"
                        },
                        {
                            "name": "mock_endpoint_1",
                            "destination": "mock_destination_1"
                        }
                    ]
                }
            }
        }
    
    def get_dict(self, test_scenario, object_id, dict_name):
        if test_scenario == "scenarios":
            return self.scenario_dict
        if test_scenario == "federations":
            return self.federation_dict
        
        


@patch("cosim_toolbox.metadataDB", MockMetadataDB)
class TestCreateFederate(unittest.TestCase):
    def __init__(self):
        self.test_fed = Federate(fed_name = "test_fed")

    
    def test_ctmDB_attributes(self):
        self.test_fed.create_federate("test_scenario")
        self.assertEqual(self.test_fed.stop_time, 60)

    def test_cthc_attributes(self):
        self.test_fed.create_federate("test_scenario")
        self.assertEqual(self.test_fed.time_step, 3)

    def test_helics_interface_count(self):
        self.test_fed.create_federate("test_scenario")
        self.assertEqual(len(self.test_fed.pubs), 1)
        self.assertEqual(len(self.test_fed.inputs), 8)
        self.assertEqual(len(self.test_fed.endpoints), 2)

    def test_scenario_name_error(self):
        self.test_fed.create_federate()
        self.assertRaises(NameError)
        
@patch("cosim_toolbox.metadataDB", MockMetadataDB)
@patch("helics.HelicsInput", MockHelicsInput)
@patch("helics.helicsEndpoint", MockHelicsEndpoint)
@patch("helics.helicsMessage", MockHelicsMessage)
class TestRunCoSimLoop(unittest.TestCase):
    def __init__(self):
        self.test_fed = Federate(fed_name = "test_fed")

    def test_no_hfed_error(self):
        self.test_fed.create_federate("test_scenario")
        self.test_fed.hfed = None
        self.test_fed.run_cosim_loop()
        self.assertRaises(ValueError)

    def test_calculate_next_requested_time(self):
        self.test_fed.create_federate("test_scenario")
        self.test_fed.granted_time = 100
        self.test_fed.time_step = 50
        self.test_fed.calculate_next_requested_time()
        self.assertEqual(self.test_fed.next_requested_time, 150)

    def test_get_data_from_federation(self):
        self.test_fed.create_federate("test_scenario")
        self.test_fed.get_data_from_federation()
        self.assertEqual(self.test_fed.data_from_federation["inputs"]["mock_input_double"], 11.13)
        self.assertEqual(self.test_fed.data_from_federation["inputs"]["mock_input_integer"], "test_string")
        self.assertEqual(self.test_fed.data_from_federation["inputs"]["mock_input_complex"], 3)
        self.assertEqual(self.test_fed.data_from_federation["inputs"]["mock_input_string"], True)
        self.assertEqual(self.test_fed.data_from_federation["inputs"]["mock_input_vector"], 5+7j)
        self.assertEqual(self.test_fed.data_from_federation["inputs"]["mock_input_complex_vector"], [17.19, 23.29])
        self.assertEqual(self.test_fed.data_from_federation["inputs"]["mock_input_boolean"], [31+37j, 14+43j])
        self.assertEqual(self.test_fed.data_from_federation["endpoints"]["mock_endpoint_1"], "test_message_string")

    def test_update_internal_model_debug(self):
        self.test_fed.create_federate("test_scenario")
        self.test_fed.debug = False
        self.test_fed.update_internal_model()
        self.assertRaises(NotImplementedError)

@patch("cosim_toolbox.metadataDB", MockMetadataDB)
@patch("helics.HelicsInput", MockHelicsInput)
@patch("helics.helicsEndpoint", MockHelicsEndpoint)
@patch("helics.helicsMessage", MockHelicsMessage)

class TestRunSendDataToFederation(unittest.TestCase):
    def __init__(self):
        self.test_fed = Federate(fed_name = "test_fed")
        self.test_fed.data_to_federation = {
            "publications": {
                "mock_pub": 20.1
            },
            "endpoints": {
                    "mock_endpoint_1": [

                    ]
            }
        }

    def test_send_data_to_federation(self):
        pass





    