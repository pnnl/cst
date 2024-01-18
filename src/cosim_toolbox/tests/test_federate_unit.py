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

class MockMetadataDB:
    cu_uri = None
    cu_database = None
    cu_federations = "federations"
    cu_scenarios = "scenarios"

    def __init__(self, uri, db_name):
        self.uri = uri
        self.db_name = db_name
        self.config = 
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
                        }
                    ],
                    "subscription": [
                        {
                            "key": "mock_sub",
                        }
                    ],
                    "input": [
                        {
                            "name": "mock_input",
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
        self.assertEqual(len(self.test_fed.inputs), 2)
        self.assertEqual(len(self.test_fed.endpoints), 2)

    def test_scenario_name_error(self):
        self.test_fed.create_federate()
        self.assertRaises(NameError)
        






    