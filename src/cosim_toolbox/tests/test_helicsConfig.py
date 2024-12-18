import collections
collections.Callable = collections.abc.Callable
import json
import os
import unittest

from cosim_toolbox.helicsConfig import HelicsMsg


class TestHelicsMsg(unittest.TestCase):

    def setUp(self):
        self.helics_msg = HelicsMsg("test_name", 1)

    def test_init(self):
        self.assertEqual(self.helics_msg._cnfg["name"], "test_name")
        self.assertEqual(self.helics_msg._cnfg["period"], 1)
        self.assertEqual(self.helics_msg._cnfg["logging"], "warning")
        self.assertEqual(self.helics_msg._subs, [])
        self.assertEqual(self.helics_msg._pubs, [])

    def test_write_json(self):
        expected_config = {
            "name": "test_name",
            "period": 1,
            "logging": "warning"
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

    # Additional tests for other methods like pubs_n, pubs_e, subs_e, subs_n can be added here

    def test_write_file(self):
        filename = "test_config.json"
        self.helics_msg.write_file(filename)

        with open(filename, 'r', encoding='utf-8') as file:
            data = json.load(file)

        self.assertEqual(data, self.helics_msg.write_json())

        # Clean up the file after test
        os.remove(filename)
