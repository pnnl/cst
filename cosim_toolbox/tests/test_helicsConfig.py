import collections

collections.Callable = collections.abc.Callable
import json
import os
import unittest

from cosim_toolbox.sims import HelicsMsg
from cosim_toolbox.sims import FederateConfig
from cosim_toolbox.sims import FederationConfig


class TestHelicsMsg(unittest.TestCase):

    def setUp(self):
        self.helics_msg = HelicsMsg("test_name", period=1)
        self.federation = FederationConfig("MyTestScenario", "MyTestAnalysis", "MyTestFederation", False)

    def test_init(self):
        self.assertEqual(self.helics_msg._cnfg["name"], "test_name")
        self.assertEqual(self.helics_msg._cnfg["period"], 1)
        self.assertEqual(self.helics_msg._cnfg["log_level"], "warning")
        self.assertEqual(self.helics_msg._subs, [])
        self.assertEqual(self.helics_msg._pubs, [])

    def test_write_json(self):
        expected_config = {
            "name": "test_name",
            "period": 1,
            "log_level": "warning"
        }
        self.assertEqual(self.helics_msg.write_json(), expected_config)

    def test_config(self):
        self.helics_msg.config("core_type", "czmq")
        self.assertEqual(self.helics_msg._cnfg["core_type"], "czmq")

    def test_pubs_and_subs(self):
        self.helics_msg.pubs("key", "type", "object", "property", True)
        self.assertEqual(len(self.helics_msg._pubs), 1)

        self.helics_msg.subs("key", "type", "object", "property")
        self.assertEqual(len(self.helics_msg._subs), 1)

    def test_add_groups(self):
        names = ["a1", "b1"]
        load = {"src": {"from_fed": names[0],
                        "keys": ["", "network_node"],
                        "indices": []},
                "des": [{"from_fed": names[0],
                         "to_fed": names[1],
                         "keys": ["", ""],
                         "indices": []
                         }]}

        f1 = self.federation.add_federate_config(FederateConfig(names[0], period=15))
        f2 = self.federation.add_federate_config(FederateConfig(names[1], period=15))
        self.federation.add_group("distribution_load", "complex", load)
        self.federation.define_io()

        f1.config("image", "cosim-cst:latest")
        f2.config("image", "cosim-cst:latest")
        f1.config("command", f"gridlabd -D USE_HELICS -D METRICS_FILE=test_metrics.json test.glm")
        f2.config("command", f"python3 -c \"import tesp_support.api.substation as tesp;tesp.substation_loop('test_agent_dict.json','test',helicsConfig='{names[1]}.json')\"")

        self.assertEqual(f1._fed_cnfg["image"], "cosim-cst:latest")
        self.assertEqual(f2._fed_cnfg["image"], "cosim-cst:latest")
        self.assertEqual(f1._fed_cnfg["command"], f"gridlabd -D USE_HELICS -D METRICS_FILE=test_metrics.json test.glm")
        self.assertEqual(f2._fed_cnfg["command"],
                         f"python3 -c \"import tesp_support.api.substation as tesp;tesp.substation_loop('test_agent_dict.json','test',helicsConfig='{names[1]}.json')\"")
        # print(f1.helics.write_json())
        # print(f2.helics.write_json())
        f1_expected_config = {'name': 'a1', 'log_level': 'warning', 'period': 15, 'terminate_on_error': True,
                              'publications': [
                                  {'type': 'complex', 'key': 'distribution_load',
                                   'info': {'object': 'network_node', 'property': 'distribution_load'}}]}
        f2_expected_config = {'name': 'b1', 'log_level': 'warning', 'period': 15, 'terminate_on_error': True,
                              'subscriptions': [{'type': 'complex', 'key': 'a1/distribution_load'}]}

        self.assertEqual(f1.helics.write_json(), f1_expected_config)
        self.assertEqual(f2.helics.write_json(), f2_expected_config)

    # Additional tests for other methods like pubs_n, pubs_e, subs_e, subs_n can be added here

    def test_write_file(self):
        filename = "test_config.json"
        self.helics_msg.write_file(filename)

        with open(filename, 'r', encoding='utf-8') as file:
            data = json.load(file)

        self.assertEqual(data, self.helics_msg.write_json())

        # Clean up the file after test
        os.remove(filename)
