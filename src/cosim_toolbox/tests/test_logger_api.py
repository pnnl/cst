import os
import sys

from pathlib import Path
sys.path.insert(0, "e:\projects\copper\src\cosim_toolbox")

import cosim_toolbox.cu_logger_api as cla
import unittest
cu_uri = 'mongodb://gage.pnl.gov:27017'
cu_database = "copper"
cu_federations = "federations"
cu_scenarios = "scenarios"
cu_logger = "cu_logger"
 

class Test_Logger_Api(unittest.TestCase):
    # db_conn = None

    # def test_open_scenario_database(self):
    #     self.db_mdb = cla.open_scenario_database(cu_uri, cu_database)
    #     self.assertIsNotNone(self.db_mdb)

    # def test_open_logger(self):
    #     self.db_conn = cla.open_logger("gage", "copper", "postgres", "postgres", 5432)
    #     self.assertIsNotNone(self.db_conn)
    #     db_conn2 = cla.open_logger("Xgage", "copper", "postgres", "postgres", 5432)
    #     self.assertIsNone( db_conn2)

    def test_open_databases(self):
        test_db = cla.Cu_Logger_Data_API()
        test_db.open_database_connections()
        self.assertIsNotNone(test_db.logger_db_conn)
        self.assertIsNotNone(test_db.mongo_connection)
        test_db.close_database_connections()

    def test_get_select_string(self):
        test_db = cla.Cu_Logger_Data_API()
        qry_string = test_db.get_select_string("test_schema", "hdt_double")
        self.assertEqual(qry_string,"SELECT * FROM test_schema.hdt_double WHERE ")

    def test_get_time_select_string(self):
        test_db = cla.Cu_Logger_Data_API()
        qry_string = test_db.get_time_select_string(500, 1000)
        self.assertEqual(qry_string,"time>=500 AND time<=1500")
        qry_string2 = test_db.get_time_select_string(None, None)
        self.assertEqual(qry_string2,"")

    def test_get_scenario_select_string(self):
        test_db = cla.Cu_Logger_Data_API()
        qry_string = test_db.get_scenario_select_string("test_scenario")
        self.assertEqual(qry_string,"scenario='test_scenario'")
        qry_string2 = test_db.get_scenario_select_string(None)
        self.assertEqual(qry_string2,"")

    def test_get_federate_select_string(self):
        test_db = cla.Cu_Logger_Data_API()
        qry_string = test_db.get_federate_select_string("test_federate")
        self.assertEqual(qry_string,"federate='test_federate'")
        qry_string2 = test_db.get_federate_select_string(None)
        self.assertEqual(qry_string2,"")

    def test_get_data_name_select_string(self):
        test_db = cla.Cu_Logger_Data_API()
        qry_string = test_db.get_data_name_select_string("test_data_name")
        self.assertEqual(qry_string,"data_name='test_data_name'")
        qry_string2 = test_db.get_data_name_select_string(None)
        self.assertEqual(qry_string2,"")

    def test_get_query_string(self):
        test_db = cla.Cu_Logger_Data_API()
        qry_string = test_db.get_query_string("test_myschema2",500,1000,"test_MyTest","DataLogger","Battery/current3","hdt_boolean")
        self.assertEqual(qry_string,"SELECT * FROM test_myschema2.hdt_boolean WHERE time>=500 AND time<=1500 AND scenario='test_MyTest' AND federate='DataLogger' AND data_name='Battery/current3'")
        qry_string2 = test_db.get_query_string("test_myschema2",None,1000,"test_MyTest","DataLogger","Battery/current3","hdt_boolean")
        self.assertEqual(qry_string2,"SELECT * FROM test_myschema2.hdt_boolean WHERE time<=1000 AND scenario='test_MyTest' AND federate='DataLogger' AND data_name='Battery/current3'")
        qry_string3 = test_db.get_query_string("test_myschema2",500,None,"test_MyTest","DataLogger","Battery/current3","hdt_boolean")
        self.assertEqual(qry_string3,"SELECT * FROM test_myschema2.hdt_boolean WHERE time>=500 AND scenario='test_MyTest' AND federate='DataLogger' AND data_name='Battery/current3'")
        qry_string4 = test_db.get_query_string("test_myschema2",500,1000,None,"DataLogger","Battery/current3","hdt_boolean")
        self.assertEqual(qry_string4,"SELECT * FROM test_myschema2.hdt_boolean WHERE time>=500 AND time<=1500 AND federate='DataLogger' AND data_name='Battery/current3'")
        qry_string5 = test_db.get_query_string("test_myschema2",500,1000,"test_MyTest",None,"Battery/current3","hdt_boolean")
        self.assertEqual(qry_string5,"SELECT * FROM test_myschema2.hdt_boolean WHERE time>=500 AND time<=1500 AND scenario='test_MyTest' AND data_name='Battery/current3'")
        qry_string6 = test_db.get_query_string("test_myschema2",500,1000,"test_MyTest","DataLogger",None,"hdt_boolean")
        self.assertEqual(qry_string6,"SELECT * FROM test_myschema2.hdt_boolean WHERE time>=500 AND time<=1500 AND scenario='test_MyTest' AND federate='DataLogger'")
        qry_string7 = test_db.get_query_string("test_myschema2",None,None,None,None,None,"hdt_boolean")
        self.assertEqual(qry_string7,"SELECT * FROM test_myschema2.hdt_boolean")

    def test_query_logger_time_series(self):
        test_db = cla.Cu_Logger_Data_API()
        test_db.open_database_connections()
        df = test_db.query_logger_time_dataframe("test_myschema2",500,1000,"test_MyTest","DataLogger","Battery/current3","hdt_boolean")
        self.assertTrue(len(df)>0)
        df2 = test_db.query_logger_time_dataframe("test_myschema2",None,1000,"test_MyTest","DataLogger","Battery/current3","hdt_boolean")
        self.assertTrue(len(df2)>0)
        df3 = test_db.query_logger_time_dataframe("test_myschema2",500,None,"test_MyTest","DataLogger","Battery/current3","hdt_boolean")
        self.assertTrue(len(df3)>0)
        df4 = test_db.query_logger_time_dataframe("test_myschema2",500,1000,None,"DataLogger","Battery/current3","hdt_boolean")
        self.assertTrue(len(df4)>0)
        df5 = test_db.query_logger_time_dataframe("test_myschema2",500,1000,"test_MyTest",None,"Battery/current3","hdt_boolean")
        self.assertTrue(len(df5)>0)
        df6 = test_db.query_logger_time_dataframe("test_myschema2",500,1000,"test_MyTest","DataLogger",None,"hdt_boolean")
        self.assertTrue(len(df6)>0)
        df7 = test_db.query_logger_time_dataframe("test_myschema2",None,None,None,None,None,"hdt_boolean")
        self.assertTrue(len(df7)>0)
        test_db.close_database_connections()

    def test_query_logger_scenario_all_times(self):
        test_db = cla.Cu_Logger_Data_API()
        test_db.open_database_connections()
        df = test_db.query_logger_scenario_all_times("test_myschema2","test_MyTest","hdt_boolean")
        test_db.close_database_connections()
        self.assertTrue(len(df)>0)


    def test_query_logger_federate_all_times(self):
        test_db = cla.Cu_Logger_Data_API()
        test_db.open_database_connections()
        df = test_db.query_logger_federate_all_times("test_myschema2","DataLogger","hdt_boolean")
        test_db.close_database_connections()
        self.assertTrue(len(df)>0)

    def test_get_scenario_list(self):
        test_db = cla.Cu_Logger_Data_API()
        test_db.open_database_connections()
        df = test_db.get_scenario_list("test_myschema2","hdt_boolean")
        test_db.close_database_connections()
        self.assertTrue(len(df)>0)

    def test_get_federate_list(self):
        test_db = cla.Cu_Logger_Data_API()
        test_db.open_database_connections()
        df = test_db.get_federate_list("test_myschema2","hdt_boolean")
        test_db.close_database_connections()
        self.assertTrue(len(df)>0)

    def test_get_data_name_list(self):
        test_db = cla.Cu_Logger_Data_API()
        test_db.open_database_connections()
        df = test_db.get_data_name_list("test_myschema2","hdt_boolean")
        test_db.close_database_connections()
        self.assertTrue(len(df)>0)

    def test_get_time_range(self):
        test_db = cla.Cu_Logger_Data_API()
        test_db.open_database_connections()
        df = test_db.get_time_range("test_myschema2", "hdt_boolean","test_MyTest","DataLogger")
        test_db.close_database_connections()
        self.assertTrue(len(df)>0)


if __name__ == '__main__':
    unittest.main()







