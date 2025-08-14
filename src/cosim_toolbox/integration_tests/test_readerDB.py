
import collections
collections.Callable = collections.abc.Callable

import os
import subprocess
import unittest

import cosim_toolbox as env
from cosim_toolbox.dbResults import DBResults
from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox.helicsConfig import HelicsMsg, Collect

class Singleton(object):
    _instance = None
    scenario_name = "test_my_scenario"
    schema_name = "test_my_schema"
    federation_name = "test_federation"
    docker = True

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(
                            cls, *args, **kwargs)
            # PUT YOUR SETUP ONCE CODE HERE!
            db = DBConfigs(env.cst_mongo, env.cst_mongo_db)

            names = ["Battery", "EVehicle"]
            t1 = HelicsMsg(names[0], period=60)
            if cls.docker:
                t1.config("broker_address", "10.5.0.2")
            t1.config("log_level", "warning")
            t1.config("terminate_on_error", True)
            #        t1.config("wait_for_current_time_update", True)

            t1.pubs_e(names[0] + "/current", "double", "V", True, Collect.YES)
            t1.subs_e(names[1] + "/voltage", "double", "V")
            t1.pubs_e(names[0] + "/current2", "integer", "A", True, Collect.NO)
            t1.subs_e(names[1] + "/voltage2", "integer", "V")
            t1.pubs_e(names[0] + "/current3", "boolean", "A")
            t1.subs_e(names[1] + "/voltage3", "boolean", "V")
            t1.pubs_e(names[0] + "/current4", "string", "A")
            t1.subs_e(names[1] + "/voltage4", "string", "V")
            t1.pubs_e(names[0] + "/current5", "complex", "A", True, Collect.MAYBE)
            t1.subs_e(names[1] + "/voltage5", "complex", "V")
            t1.pubs_e(names[0] + "/current6", "vector", "A", True, Collect.NO)
            t1.subs_e(names[1] + "/voltage6", "vector", "V")
            f1 = {
                "image": "cosim-cst:latest",
                "command": f"python3 simple_federate.py {names[0]} {cls.scenario_name}",
                "federate_type": "value",
                "HELICS_config": t1.write_json()
            }

            t2 = HelicsMsg(names[1], period=60)
            if cls.docker:
                t2.config("broker_address", "10.5.0.2")
            t2.config("log_level", "warning")
            t2.config("terminate_on_error", True)
            #        t2.config("wait_for_current_time_update", True)

            t2.subs_e(names[0] + "/current", "double", "V")
            t2.pubs_e(names[1] + "/voltage", "double", "V")
            t2.subs_e(names[0] + "/current2", "integer", "A")
            t2.pubs_e(names[1] + "/voltage2", "integer", "V")
            t2.subs_e(names[0] + "/current3", "boolean", "A")
            t2.pubs_e(names[1] + "/voltage3", "boolean", "V", True, Collect.NO)
            t2.subs_e(names[0] + "/current4", "string", "A")
            t2.pubs_e(names[1] + "/voltage4", "string", "V")
            t2.subs_e(names[0] + "/current5", "complex", "A")
            t2.pubs_e(names[1] + "/voltage5", "complex", "V")
            t2.subs_e(names[0] + "/current6", "vector", "A")
            t2.pubs_e(names[1] + "/voltage6", "vector", "V")
            f2 = {
                "image": "cosim-cst:latest",
                "command": f"python3 simple_federate2.py {names[1]} {cls.scenario_name}",
                "federate_type": "value",
                "HELICS_config": t2.write_json()
            }
            diction = {
                "federation": {
                    names[0]: f1,
                    names[1]: f2
                }
            }

            db.remove_document(env.cst_federations, None, cls.federation_name)
            db.add_dict(env.cst_federations, cls.federation_name, diction)
            scenario = db.scenario(cls.schema_name,
                                   cls.federation_name,
                                   "2023-12-07T15:31:27",
                                   "2023-12-08T15:31:27",
                                   cls.docker)
            db.remove_document(env.cst_scenarios, None, cls.scenario_name)
            db.add_dict(env.cst_scenarios, cls.scenario_name, scenario)

            cmd = (f'docker cp {os.path.dirname(os.path.abspath(__file__))}'
                   f'/data/del_{cls.schema_name}.sql '
                   f'$(docker container ls --all --quiet --filter "name=database"):'
                   f'/docker-entrypoint-initdb.d/del_{cls.schema_name}.sql')
            subprocess.Popen(cmd, shell=True).wait()
            cmd = (f'docker cp {os.path.dirname(os.path.abspath(__file__))}'
                   f'/data/{cls.schema_name}.sql '
                   f'$(docker container ls --all --quiet --filter "name=database"):'
                   f'/docker-entrypoint-initdb.d/{cls.schema_name}.sql')
            subprocess.Popen(cmd, shell=True).wait()
            # command string for psql to load database
            cmd = ('docker exec -i $(docker container ls --all --quiet --filter "name=database") '
                   f'/bin/bash -c "export PGPASSWORD={env.cst_data_db["user"]} && psql '
                   f'-U {env.cst_data_db["user"]} -d {env.cst_data_db["dbname"]} < ')
            # remove federation data in postgres database
            subprocess.Popen(cmd + f'/docker-entrypoint-initdb.d/del_{cls.schema_name}.sql"', shell=True).wait()
            # load federation data in postgres database
            subprocess.Popen(cmd + f'/docker-entrypoint-initdb.d/{cls.schema_name}.sql"', shell=True).wait()

            # # command string for psql to load database
            # cmd = (f' | docker exec -i $(docker container ls --all --quiet --filter "name=database")'
            #        f' psql -U {env.cst_data_db["user"]} -d {env.cst_data_db["dbname"]}')
            # # remove federation data in postgres database
            # dell = f'cat {os.path.dirname(os.path.abspath(__file__))}/data/del_{cls.schema_name}.sql' + cmd
            # subprocess.Popen(dell, shell=True).wait()
            # # load federation data in postgres database
            # subprocess.Popen(f'cat {os.path.dirname(os.path.abspath(__file__))}/data/{cls.schema_name}.sql' + cmd, shell=True).wait()

            cls.setUpBool = True

        return cls._instance


class TestLoggerApi(unittest.TestCase):

    scenario_name = "test_my_scenario"
    schema_name = "test_my_schema"
    federation_name = "test_federation"

    def setUp(self):
        Singleton()
        self.test_DL = DBResults()
        self.test_DL.open_database_connections(env.cst_data_db)

    def test_00_open_databases(self):
        self.assertIsNotNone(self.test_DL.data_db)

    def test_01_get_select_string(self):
        qry_string = self.test_DL.get_select_string(self.schema_name, "hdt_double")
        self.assertEqual(qry_string, f"SELECT * FROM {self.schema_name}.hdt_double WHERE ")

    def test_02_get_time_select_string(self):
        qry_string = self.test_DL.get_time_select_string(500, 1000)
        self.assertEqual(qry_string, "sim_time>=500 AND sim_time<=1500")
        qry_string2 = self.test_DL.get_time_select_string(None, None)
        self.assertEqual(qry_string2, "")

    def test_03_get_query_string(self):
        qry_string = self.test_DL.get_query_string(500, 1000, self.scenario_name, "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string, f"SELECT * FROM {self.schema_name}.hdt_boolean WHERE sim_time>=500 AND sim_time<=1500 AND scenario='{self.scenario_name}' AND federate='Battery' AND data_name='Battery/current3'")
        qry_string2 = self.test_DL.get_query_string(None, 1000, self.scenario_name, "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string2, f"SELECT * FROM {self.schema_name}.hdt_boolean WHERE sim_time<=1000 AND scenario='{self.scenario_name}' AND federate='Battery' AND data_name='Battery/current3'")
        qry_string3 = self.test_DL.get_query_string(500, None, self.scenario_name, "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string3, f"SELECT * FROM {self.schema_name}.hdt_boolean WHERE sim_time>=500 AND scenario='{self.scenario_name}' AND federate='Battery' AND data_name='Battery/current3'")
        qry_string4 = self.test_DL.get_query_string(500, 1000, None, "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string4, None)
        qry_string5 = self.test_DL.get_query_string(500, 1000, self.scenario_name, None, "Battery/current3", "hdt_boolean")
        self.assertEqual(qry_string5, f"SELECT * FROM {self.schema_name}.hdt_boolean WHERE sim_time>=500 AND sim_time<=1500 AND scenario='{self.scenario_name}' AND data_name='Battery/current3'")
        qry_string6 = self.test_DL.get_query_string(500, 1000, self.scenario_name, "Battery", None, "hdt_boolean")
        self.assertEqual(qry_string6, f"SELECT * FROM {self.schema_name}.hdt_boolean WHERE sim_time>=500 AND sim_time<=1500 AND scenario='{self.scenario_name}' AND federate='Battery'")
        qry_string7 = self.test_DL.get_query_string(None, None, None, None, None, "hdt_boolean")
        self.assertEqual(qry_string7, None)

    def test_04_query_scenario_federate_times(self):
        df = self.test_DL.query_scenario_federate_times(500, 1000, self.scenario_name,
                                                    "Battery", "Battery/current3", "hdt_boolean")
        self.assertTrue(len(df) == 34)
        df = self.test_DL.query_scenario_federate_times(None, 1000, self.scenario_name,
                                                    "Battery", "Battery/current3", "hdt_boolean")
        self.assertTrue(len(df) == 33)
        df = self.test_DL.query_scenario_federate_times(500, None, self.scenario_name,
                                                    "Battery", "Battery/current3", "hdt_boolean")
        self.assertTrue(len(df) == 2864)
        df = self.test_DL.query_scenario_federate_times(500, 1000, None,
                                                    "Battery", "Battery/current3", "hdt_boolean")
        self.assertEqual(df, None)
        df = self.test_DL.query_scenario_federate_times(500, 1000, self.scenario_name,
                                                    None, "Battery/current3", "hdt_boolean")
        self.assertTrue(len(df) == 34)
        df = self.test_DL.query_scenario_federate_times(500, 1000, self.scenario_name,
                                                    "Battery", None, "hdt_boolean")
        self.assertTrue(len(df) == 34)
        df = self.test_DL.query_scenario_federate_times(None, None, None,
                                                    None, None, "hdt_boolean")
        self.assertEqual(df, None)

    def test_05_query_scenario_all_times(self):
        df = self.test_DL.query_scenario_all_times(self.scenario_name, "hdt_boolean")
        self.assertTrue(len(df) == 2880)

    def test_06_query_scheme_federate_all_times(self):
        df = self.test_DL.query_scheme_federate_all_times(self.schema_name, "Battery", "hdt_boolean")
        self.assertTrue(len(df) == 2880)

    def test_07_get_scenario_list(self):
        df = self.test_DL.get_scenario_list(self.schema_name, "hdt_boolean")
        self.assertTrue(len(df) == 1)
        self.assertTrue(df.values[0][0] == self.scenario_name)

    def test_08_get_federate_list(self):
        df = self.test_DL.get_federate_list(self.schema_name, "hdt_boolean")
        df = df.sort_values(by=['federate'])
        self.assertTrue(len(df) == 1)
        self.assertTrue(df.values[0][0] == "Battery")
        # self.assertTrue(df.values[1][0] == "EVehicle")

    def test_09_get_data_name_list(self):
        df = self.test_DL.get_data_name_list(self.schema_name, "hdt_boolean")
        df = df.sort_values(by=['data_name'])
        self.assertTrue(len(df) == 1)
        self.assertTrue(df.values[0][0] == "Battery/current3")
        # self.assertTrue(df.values[1][0] == "EVehicle/voltage3")

    def test_10_get_time_range(self):
        df = self.test_DL.get_time_range(self.schema_name, "hdt_boolean", self.scenario_name, "Battery")
        self.assertTrue(len(df) > 0)

    def tearDown(self):
        self.test_DL.close_database_connections()
        self.assertIsNone(self.test_DL.data_db)
        pass


if __name__ == '__main__':
    unittest.main()
