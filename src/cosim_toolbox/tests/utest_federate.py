import unittest
from unittest.mock import MagicMock
from cosim_toolbox.federate import Federate


class TestFederate(unittest.TestCase):

    def setUp(self):
        self.mock_helics = MagicMock()
        self.mock_metadataDB = MagicMock()
        self.federate = Federate(fed_name="TestFederate")

    def test_connect_to_metadataDB(self):
        uri = "mock_uri"
        db_name = "mock_db"
        self.federate.mddb = self.mock_metadataDB
        self.federate.connect_to_metadataDB(uri, db_name)
        self.mock_metadataDB.get_dict.assert_called_with(self.mock_metadataDB.cu_scenarios, None, self.federate.scenario_name)

    def test_connect_to_helics_config(self):
        self.federate.federation = {"federation": {"TestFederate": {"HELICS_config": {"period": 30}}}}
        self.federate.connect_to_helics_config()
        self.assertEqual(self.federate.federate_type, "combo")
        self.assertEqual(self.federate.time_step, 30)
        self.assertEqual(self.federate.config, {"period": 30})

    def test_create_federate(self):
        scenario_name = "TestScenario"
        self.federate.connect_to_metadataDB = MagicMock()
        self.federate.connect_to_helics_config = MagicMock()
        self.federate.create_helics_fed = MagicMock()
        self.federate.create_federate(scenario_name)
        self.federate.connect_to_metadataDB.assert_called_with(self.federate.mddb.cosim_mongo_host, self.federate.mddb.cosim_mongo_db)
        self.federate.connect_to_helics_config.assert_called()
        self.federate.create_helics_fed.assert_called()

    # Add more tests for other methods as needed

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()