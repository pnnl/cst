import unittest
from unittest.mock import MagicMock
from cosim_toolbox.federateLogger import FederateLogger


class TestFederateLogger(unittest.TestCase):

    def setUp(self):
        # Mocking HelicsMsg and Federate to isolate the tests
        self.mock_helics_msg = MagicMock()
        self.mock_federate = MagicMock()
        self.federateLogger = FederateLogger(fed_name="TestFederate", schema_name="TestSchema", clear=True)

    def test_create_table(self):
        table_name = "test_table"
        data_type = "htd_double"
        expected_query = ("CREATE TABLE IF NOT EXISTS TestSchema.test_table ("
                          "time double precision NOT NULL, "
                          "scenario VARCHAR (255) NOT NULL, "
                          "federate VARCHAR (255) NOT NULL, "
                          "data_name VARCHAR (255) NOT NULL, "
                          f"data_value {data_type} NOT NULL);")
        actual_query = self.federateLogger.create_table(table_name, data_type)
        self.assertEqual(actual_query, expected_query)

    def test_make_logger_database(self):
        # Ensure that make_logger_database constructs the expected queries
        expected_query = ""  # Update this with the expected query based on your implementation
        self.assertEqual(self.federateLogger.make_logger_database(), expected_query)

    def test_remove_scenario(self):
        # Ensure that remove_scenario constructs the expected queries
        expected_query = ""  # Update this with the expected query based on your implementation
        self.assertEqual(self.federateLogger.remove_scenario(), expected_query)

    # Add more tests for other methods as needed

    def tearDown(self):
        self.federateLogger.conn.close()


if __name__ == '__main__':
    unittest.main()
