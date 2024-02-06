from os import environ
import unittest

# import sys
# sys.path.insert(0, "e:\projects\copper\src\cosim_toolbox")

import cosim_toolbox.dataLogger as dL


class TestLoggerApi(unittest.TestCase):

    _data_db = {
        "host": environ.get("POSTGRES_HOST", "maxwell.pnl.gov"),
        "port": environ.get("POSTGRES_PORT", 5432),
        "dbname": environ.get("COSIM_DB", "copper"),
        "user": environ.get("COSIM_USER", "worker"),
        "password": environ.get("COSIM_PASSWORD", "worker")
    }

    _meta_db = {
        "host": environ.get("MONGO_HOST", "mongo://maxwell.pnl.gov"),
        "port": environ.get("MONGO_POST", 27017),
        "dbname": environ.get("COSIM_DB", "copper"),
        "user": environ.get("COSIM_USER", "worker"),
        "password": environ.get("COSIM_PASSWORD", "worker")
    }

    def setUp(self):
        self.test_DL = dL.DataLogger()
        # self.test_DL.open_database_connections()

    def test_create_table(self):
        scheme_name = "test_Schema"
        table_name = "htd_double"
        data_type = "htd_double"
        expected_query = (f"CREATE TABLE IF NOT EXISTS {scheme_name}.{table_name} ("
                          "time double precision NOT NULL, "
                          "scenario VARCHAR (255) NOT NULL, "
                          "federate VARCHAR (255) NOT NULL, "
                          "data_name VARCHAR (255) NOT NULL, "
                          f"data_value {data_type} NOT NULL);")
        # actual_query = self.test_DL.create_table(scheme_name, table_name, data_type)
        # self.assertEqual(actual_query, expected_query)

    def test_make_logger_database(self):
        scheme_name = "test_Schema"
        # Ensure that make_logger_database constructs the expected queries
        expected_query = ""  # Update this with the expected query based on your implementation
        # self.assertEqual(self.test_DL.make_logger_database(scheme_name), expected_query)

    def test_remove_scenario(self):
        scheme_name = "test_Schema"
        scenario_name = "test_Scenario"
        # Ensure that remove_scenario constructs the expected queries
        expected_query = ""  # Update this with the expected query based on your implementation
        # self.assertEqual(self.test_DL.remove_scenario(scheme_name, scenario_name), expected_query)

    def test_open_databases(self):
        self.test_DL.open_database_connections()
        self.assertIsNotNone(self.test_DL.data_db)
        self.assertIsNotNone(self.test_DL.meta_db)
        self.test_DL.close_database_connections()

    def test_get_select_string(self):
        qry_string = self.test_DL.get_select_string("test_Schema", "hdt_double")
        self.assertEqual(qry_string, "SELECT * FROM test_Schema.hdt_double WHERE ")

    def test_get_time_select_string(self):
        qry_string = self.test_DL.get_time_select_string(500, 1000)
        self.assertEqual(qry_string, "time>=500 AND time<=1500")
        qry_string2 = self.test_DL.get_time_select_string(None, None)
        self.assertEqual(qry_string2, "")

    def test_get_scenario_select_string(self):
        qry_string = self.test_DL.get_scenario_select_string("test_Scenario")
        self.assertEqual(qry_string, "scenario='test_Scenario'")
        qry_string2 = self.test_DL.get_scenario_select_string(None)
        self.assertEqual(qry_string2, "")

    def test_get_federate_select_string(self):
        qry_string = self.test_DL.get_federate_select_string("test_Federate")
        self.assertEqual(qry_string, "federate='test_Federate'")
        qry_string2 = self.test_DL.get_federate_select_string(None)
        self.assertEqual(qry_string2, "")

    def test_get_data_name_select_string(self):
        qry_string = self.test_DL.get_data_name_select_string("test_data_name")
        self.assertEqual(qry_string, "data_name='test_data_name'")
        qry_string2 = self.test_DL.get_data_name_select_string(None)
        self.assertEqual(qry_string2, "")

    def test_get_query_string(self):
        self.test_DL.open_database_connections()
        qry_string = self.test_DL.get_query_string(500, 1000, "test_Scenario", "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string, "SELECT * FROM test_Schema.hdt_boolean WHERE time>=500 AND time<=1500 AND scenario='test_Scenario' AND federate='Battery' AND data_name='Battery/current3'")
        qry_string2 = self.test_DL.get_query_string(None, 1000, "test_Scenario", "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string2, "SELECT * FROM test_Schema.hdt_boolean WHERE time<=1000 AND scenario='test_Scenario' AND federate='Battery' AND data_name='Battery/current3'")
        qry_string3 = self.test_DL.get_query_string(500, None, "test_Scenario", "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string3, "SELECT * FROM test_Schema.hdt_boolean WHERE time>=500 AND scenario='test_Scenario' AND federate='Battery' AND data_name='Battery/current3'")
        # qry_string4 = self.test_DL.get_query_string(500, 1000, None, "Battery", "Battery/current3", "hdt_boolean")
        # self.assertEqual(qry_string4, "SELECT * FROM test_Schema.hdt_boolean WHERE time>=500 AND time<=1500 AND federate='Battery' AND data_name='Battery/current3'")
        qry_string5 = self.test_DL.get_query_string(500, 1000, "test_Scenario", None, "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string5, "SELECT * FROM test_Schema.hdt_boolean WHERE time>=500 AND time<=1500 AND scenario='test_Scenario' AND data_name='Battery/current3'")
        qry_string6 = self.test_DL.get_query_string(500, 1000, "test_Scenario", "Battery", None, "hdt_boolean")
        self.assertEqual(qry_string6, "SELECT * FROM test_Schema.hdt_boolean WHERE time>=500 AND time<=1500 AND scenario='test_Scenario' AND federate='Battery'")
        # qry_string7 = self.test_DL.get_query_string(None, None, None, None, None, "hdt_boolean")
        # self.assertEqual(qry_string7, "SELECT * FROM test_Schema.hdt_boolean")
        self.test_DL.close_database_connections()

    def test_query_scenario_federate_times(self):
        self.test_DL.open_database_connections()
        df = self.test_DL.query_scenario_federate_times(500, 1000, "test_Scenario",
                                                   "Battery", "Battery/current3",
                                                   "hdt_boolean")
        self.assertTrue(len(df) > 0)
        df2 = self.test_DL.query_scenario_federate_times(None, 1000, "test_Scenario",
                                                    "Battery", "Battery/current3",
                                                    "hdt_boolean")
        self.assertTrue(len(df2) > 0)
        df3 = self.test_DL.query_scenario_federate_times(500, None, "test_Scenario",
                                                    "Battery", "Battery/current3",
                                                    "hdt_boolean")
        self.assertTrue(len(df3) > 0)
        # df4 = self.test_DL.query_scenario_federate_times(500, 1000, None,
        #                                             "Battery","Battery/current3",
        #                                             "hdt_boolean")
        # self.assertTrue(len(df4) > 0)
        df5 = self.test_DL.query_scenario_federate_times(500, 1000, "test_Scenario",
                                                    None, "Battery/current3",
                                                    "hdt_boolean")
        self.assertTrue(len(df5) > 0)
        df6 = self.test_DL.query_scenario_federate_times(500, 1000, "test_Scenario",
                                                    "Battery", None,
                                                    "hdt_boolean")
        self.assertTrue(len(df6) > 0)
        # df7 = self.test_DL.query_scenario_federate_times(None, None, None,
        #                                             None, None, "hdt_boolean")
        # self.assertTrue(len(df7) > 0)
        self.test_DL.close_database_connections()

    def test_query_scenario_all_times(self):
        self.test_DL.open_database_connections()
        df = self.test_DL.query_scenario_all_times("test_Scenario", "hdt_boolean")
        self.test_DL.close_database_connections()
        self.assertTrue(len(df) > 0)

    def test_query_scheme_federate_all_times(self):
        self.test_DL.open_database_connections()
        df = self.test_DL.query_scheme_federate_all_times("test_Schema", "Battery", "hdt_boolean")
        self.test_DL.close_database_connections()
        self.assertTrue(len(df) > 0)

    def test_get_scenario_list(self):
        self.test_DL.open_database_connections()
        df = self.test_DL.get_scenario_list("test_Schema", "hdt_boolean")
        self.test_DL.close_database_connections()
        self.assertTrue(len(df) > 0)

    def test_get_federate_list(self):
        self.test_DL.open_database_connections()
        df = self.test_DL.get_federate_list("test_Schema", "hdt_boolean")
        self.test_DL.close_database_connections()
        self.assertTrue(len(df) > 0)

    def test_get_data_name_list(self):
        self.test_DL.open_database_connections()
        df = self.test_DL.get_data_name_list("test_Schema", "hdt_boolean")
        self.test_DL.close_database_connections()
        self.assertTrue(len(df) > 0)

    def test_get_time_range(self):
        self.test_DL.open_database_connections()
        df = self.test_DL.get_time_range("test_Schema", "hdt_boolean", "test_Scenario", "Battery")
        self.test_DL.close_database_connections()
        self.assertTrue(len(df) > 0)

    def tearDown(self):
        self.test_DL = None


if __name__ == '__main__':
    unittest.main()
