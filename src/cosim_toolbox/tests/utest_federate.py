import unittest
import collections
collections.Callable = collections.abc.Callable
from unittest.mock import MagicMock
from cosim_toolbox.federate import Federate
from cosim_toolbox import cosim_mongo, cosim_mongo_db, cu_scenarios

class TestFederate(unittest.TestCase):

    def setUp(self):
        self.mock_helics = MagicMock()
        self.mock_DBConfig = MagicMock()
        self.federate = Federate(fed_name="TestFederate")

    def test_connect_to_metadataDB(self):
        uri = "mock_uri"
        db_name = "mock_db"
        scenario_name = "mock_scenario"
        self.federate.scenario = {
          "schema": "cst_s1",
          "federation": "cst_f1",
          "start_time": "2023-12-07T15:31:27",
          "stop_time": "2023-12-07T16:31:27",
          "docker": False }
        self.federate.mddb = self.mock_DBConfig
        self.federate.connect_to_metadataDB = MagicMock()
        self.federate.connect_to_metadataDB(uri, db_name)
        self.mock_DBConfig.get_dict.assert_called_with(cu_scenarios, None, scenario_name)

    def test_connect_to_helics_config(self):
        self.federate.federation = {"TestFederate": {"federate_type": "combo", "HELICS_config": {"period": 30}}}
        self.federate.connect_to_helics_config()
        self.assertEqual(self.federate.federate_type, "combo")
        self.assertEqual(self.federate.period, 30)
        self.assertEqual(self.federate.config, {"period": 30})

    def test_create_federate(self):
        scenario_name = "TestScenario"
        self.federate.connect_to_metadataDB = MagicMock()
        self.federate.connect_to_helics_config = MagicMock()
        self.federate.create_helics_fed = MagicMock()
        self.federate.create_federate(scenario_name)
        self.federate.connect_to_metadataDB.assert_called_with(cosim_mongo, cosim_mongo_db)
        self.federate.connect_to_helics_config.assert_called()
        self.federate.create_helics_fed.assert_called()

    # Add more tests for other methods as needed

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()