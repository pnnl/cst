
import collections
collections.Callable = collections.abc.Callable

import subprocess
from os import environ
import unittest

import cosim_toolbox.dataLogger as dL
import cosim_toolbox.metadataDB as mDB
from cosim_toolbox.helicsConfig import HelicsMsg


_data_db = {
    "host": environ.get("POSTGRES_HOST", "gage.pnl.gov"),
    "port": environ.get("POSTGRES_PORT", 5432),
    "dbname": environ.get("COSIM_DB", "copper"),
    "user": environ.get("COSIM_USER", "worker"),
    "password": environ.get("COSIM_PASSWORD", "worker")
}

_meta_db = {
    "host": environ.get("MONGO_HOST", "mongodb://gage.pnl.gov"),
    "port": environ.get("MONGO_POST", "27017"),
    "dbname": environ.get("COSIM_DB", "copper"),
    "user": environ.get("COSIM_USER", "worker"),
    "password": environ.get("COSIM_PASSWORD", "worker")
}


class Singleton(object):
    _instance = None
    scenario_name = "test_scenario"
    schema_name = "test_my_schema"
    federation_name = "test_federation"
    docker = True

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(
                            cls, *args, **kwargs)
            # PUT YOUR SETUP ONCE CODE HERE!
            uri = f"{_meta_db['host']}:{_meta_db['port']}"
            db = mDB.MetaDB(uri, _meta_db['dbname'])

            prefix = "source /home/worker/venv/bin/activate && exec python3 "
            names = ["Battery", "EVehicle"]
            t1 = HelicsMsg(names[0], 30)
            if cls.docker:
                t1.config("brokeraddress", "10.5.0.2")
            t1.config("core_type", "zmq")
            t1.config("log_level", "warning")
            t1.config("period", 30)
            t1.config("uninterruptible", False)
            t1.config("terminate_on_error", True)
            #        t1.config("wait_for_current_time_update", True)

            t1.pubs_e(True, names[0] + "/current", "double", "V")
            t1.subs_e(True, names[1] + "/voltage", "double", "V")
            t1.pubs_e(True, names[0] + "/current2", "integer", "A")
            t1.subs_e(True, names[1] + "/voltage2", "integer", "V")
            t1.pubs_e(True, names[0] + "/current3", "boolean", "A")
            t1.subs_e(True, names[1] + "/voltage3", "boolean", "V")
            t1.pubs_e(True, names[0] + "/current4", "string", "A")
            t1.subs_e(True, names[1] + "/voltage4", "string", "V")
            t1.pubs_e(True, names[0] + "/current5", "complex", "A")
            t1.subs_e(True, names[1] + "/voltage5", "complex", "V")
            t1.pubs_e(True, names[0] + "/current6", "vector", "A")
            t1.subs_e(True, names[1] + "/voltage6", "vector", "V")
            f1 = {
                "image": "cosim-python:latest",
                "command": prefix + "simple_federate.py " + names[0] + " " + cls.scenario_name,
                "federate_type": "value",
                "time_step": 120,
                "HELICS_config": t1.write_json()
            }

            t2 = HelicsMsg(names[1], 30)
            if cls.docker:
                t2.config("brokeraddress", "10.5.0.2")
            t2.config("core_type", "zmq")
            t2.config("log_level", "warning")
            t2.config("period", 60)
            t2.config("uninterruptible", False)
            t2.config("terminate_on_error", True)
            #        t2.config("wait_for_current_time_update", True)

            t2.subs_e(True, names[0] + "/current", "double", "V")
            t2.pubs_e(True, names[1] + "/voltage", "double", "V")
            t2.subs_e(True, names[0] + "/current2", "integer", "A")
            t2.pubs_e(True, names[1] + "/voltage2", "integer", "V")
            t2.subs_e(True, names[0] + "/current3", "boolean", "A")
            t2.pubs_e(True, names[1] + "/voltage3", "boolean", "V")
            t2.subs_e(True, names[0] + "/current4", "string", "A")
            t2.pubs_e(True, names[1] + "/voltage4", "string", "V")
            t2.subs_e(True, names[0] + "/current5", "complex", "A")
            t2.pubs_e(True, names[1] + "/voltage5", "complex", "V")
            t2.subs_e(True, names[0] + "/current6", "vector", "A")
            t2.pubs_e(True, names[1] + "/voltage6", "vector", "V")
            f2 = {
                "image": "cosim-python:latest",
                "command": prefix + "simple_federate2.py " + names[1] + " " + cls.scenario_name,
                "env": "",
                "federate_type": "value",
                "time_step": 120,
                "HELICS_config": t2.write_json()
            }
            diction = {
                "federation": {
                    names[0]: f1,
                    names[1]: f2
                }
            }

            db.remove_document(mDB.cu_federations, None, cls.federation_name)
            db.add_dict(mDB.cu_federations, cls.federation_name, diction)
            scenario = db.scenario(cls.schema_name,
                                   cls.federation_name,
                                   "2023-12-07T15:31:27",
                                   "2023-12-08T15:31:27",
                                   cls.docker)
            db.remove_document(mDB.cu_scenarios, None, cls.scenario_name)
            db.add_dict(mDB.cu_scenarios, cls.scenario_name, scenario)

            # command string for psql to load database
            cmd = ('docker exec -i $(docker container ls --all --quiet --filter "name=database") '
                   f'/bin/bash -c "PGPASSWORD={_meta_db["user"]} psql --username '
                   f'{_meta_db["user"]} {(_meta_db["dbname"])}" < ')

            # remove federation data in postgres database
            subprocess.Popen(cmd + f'del_{cls.schema_name}.sql', shell=True).wait()
            # load federation data in postgres database
            subprocess.Popen(cmd + f'{cls.schema_name}.sql', shell=True).wait()

            cls.setUpBool = True

        return cls._instance


class TestLoggerApi(unittest.TestCase):

    def setUp(self):
        Singleton()
        self.test_DL = dL.DataLogger()
        self.test_DL.open_database_connections(data_connection=_data_db, meta_connection=_meta_db)

    def test_00_open_databases(self):
        self.assertIsNotNone(self.test_DL.data_db)
        self.assertIsNotNone(self.test_DL.meta_db)

    def test_01_get_select_string(self):
        qry_string = self.test_DL.get_select_string("test_my_schema", "hdt_double")
        self.assertEqual(qry_string, "SELECT * FROM test_my_schema.hdt_double WHERE ")

    def test_02_get_time_select_string(self):
        qry_string = self.test_DL.get_time_select_string(500, 1000)
        self.assertEqual(qry_string, "sim_time>=500 AND sim_time<=1500")
        qry_string2 = self.test_DL.get_time_select_string(None, None)
        self.assertEqual(qry_string2, "")

    def test_03_get_query_string(self):
        qry_string = self.test_DL.get_query_string(500, 1000, "test_Scenario", "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string, "SELECT * FROM test_my_schema.hdt_boolean WHERE sim_time>=500 AND sim_time<=1500 AND scenario='test_Scenario' AND federate='Battery' AND sim_name='Battery/current3'")
        qry_string2 = self.test_DL.get_query_string(None, 1000, "test_Scenario", "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string2, "SELECT * FROM test_my_schema.hdt_boolean WHERE sim_time<=1000 AND scenario='test_Scenario' AND federate='Battery' AND sim_name='Battery/current3'")
        qry_string3 = self.test_DL.get_query_string(500, None, "test_Scenario", "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string3, "SELECT * FROM test_my_schema.hdt_boolean WHERE sim_time>=500 AND scenario='test_Scenario' AND federate='Battery' AND sim_name='Battery/current3'")
        qry_string4 = self.test_DL.get_query_string(500, 1000, None, "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string4, "SELECT * FROM test_my_schema.hdt_boolean WHERE sim_time>=500 AND sim_time<=1500 AND federate='Battery' AND sim_name='Battery/current3'")
        qry_string5 = self.test_DL.get_query_string(500, 1000, "test_Scenario", None, "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string5, "SELECT * FROM test_my_schema.hdt_boolean WHERE sim_time>=500 AND sim_time<=1500 AND scenario='test_Scenario' AND sim_name='Battery/current3'")
        qry_string6 = self.test_DL.get_query_string(500, 1000, "test_Scenario", "Battery", None, "hdt_boolean")
        self.assertEqual(qry_string6, "SELECT * FROM test_my_schema.hdt_boolean WHERE sim_time>=500 AND sim_time<=1500 AND scenario='test_Scenario' AND federate='Battery'")
        qry_string7 = self.test_DL.get_query_string(None, None, None, None, None, "hdt_boolean")
        self.assertEqual(qry_string7, "SELECT * FROM test_my_schema.hdt_boolean")

    def test_04_query_scenario_federate_times(self):
        df = self.test_DL.query_scenario_federate_times(500, 1000, "test_Scenario",
                                                   "Battery", "Battery/current3",
                                                   "hdt_boolean")
        self.assertTrue(len(df) == 34)
        df = self.test_DL.query_scenario_federate_times(None, 1000, "test_Scenario",
                                                    "Battery", "Battery/current3",
                                                    "hdt_boolean")
        self.assertTrue(len(df) == 33)
        df = self.test_DL.query_scenario_federate_times(500, None, "test_Scenario",
                                                    "Battery", "Battery/current3",
                                                    "hdt_boolean")
        self.assertTrue(len(df) == 2864)
        df = self.test_DL.query_scenario_federate_times(500, 1000, None,
                                                    "Battery","Battery/current3",
                                                    "hdt_boolean")
        self.assertTrue(len(df) == 34)
        df = self.test_DL.query_scenario_federate_times(500, 1000, "test_Scenario",
                                                    None, "Battery/current3",
                                                    "hdt_boolean")
        self.assertTrue(len(df) == 34)
        df = self.test_DL.query_scenario_federate_times(500, 1000, "test_Scenario",
                                                    "Battery", None,
                                                    "hdt_boolean")
        self.assertTrue(len(df) == 34)
        df = self.test_DL.query_scenario_federate_times(None, None, None,
                                                    None, None, "hdt_boolean")
        self.assertTrue(len(df) == 5760)

    def test_05_query_scenario_all_times(self):
        df = self.test_DL.query_scenario_all_times("test_Scenario", "hdt_boolean")
        self.assertTrue(len(df) == 5760)

    def test_06_query_scheme_federate_all_times(self):
        df = self.test_DL.query_scheme_federate_all_times("test_my_schema", "Battery", "hdt_boolean")
        self.assertTrue(len(df) == 2880)

    def test_07_get_scenario_list(self):
        df = self.test_DL.get_scenario_list("test_my_schema", "hdt_boolean")
        self.assertTrue(len(df) == 1)
        self.assertTrue(df.values[0][0] == "test_Scenario")

    def test_08_get_federate_list(self):
        df = self.test_DL.get_federate_list("test_my_schema", "hdt_boolean")
        df = df.sort_values(by=['federate'])
        self.assertTrue(len(df) == 2)
        self.assertTrue(df.values[0][0] == "Battery")
        self.assertTrue(df.values[1][0] == "EVehicle")

    def test_09_get_sim_name_list(self):
        df = self.test_DL.get_sim_name_list("test_my_schema", "hdt_boolean")
        df = df.sort_values(by=['sim_name'])
        self.assertTrue(len(df) == 2)
        self.assertTrue(df.values[0][0] == "Battery/current3")
        self.assertTrue(df.values[1][0] == "EVehicle/voltage3")

    def test_10_get_time_range(self):
        df = self.test_DL.get_time_range("test_my_schema", "hdt_boolean", "test_Scenario", "Battery")
        self.assertTrue(len(df) > 0)

    def test_11_make_logger_database(self):
        scheme_name = "test_my_schema"
        # Ensure that make_logger_database constructs the expected queries
        expected_query = ""  # Update this with the expected query based on your implementation
        # self.assertEqual(self.test_DL.make_logger_database(scheme_name), expected_query)

    def test_12_remove_scenario(self):
        scheme_name = "test_my_schema"
        scenario_name = "test_Scenario"
        # Ensure that remove_scenario constructs the expected queries
        expected_query = ""  # Update this with the expected query based on your implementation
        # self.assertEqual(self.test_DL.remove_scenario(scheme_name, scenario_name), expected_query)

    def test_20_close_databases(self):
        self.test_DL.close_database_connections()
        self.assertIsNone(self.test_DL.data_db)
        self.assertIsNone(self.test_DL.meta_db)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
