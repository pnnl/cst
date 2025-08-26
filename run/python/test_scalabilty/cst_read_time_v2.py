"""
Create the initial version of cst_results_validator.py.

This script runs after the co-simulation is complete and validates
that all data that was published was correctly logged. This will
require either querying the time-series database or reading CSVs
written by the scalability federates. This can be included as part
of the test post-processing.

See full definition in "scalability_testing.md" in the "docs" folder
in the repo.

"""
import json
import logging
import os
import sys
import time
from enum import Enum
from pathlib import Path
import numpy as np
import pandas as pd

import cosim_toolbox as env
from cosim_toolbox.dbResults import DBResults
from cosim_toolbox.dbConfigs import DBConfigs

class ScenarioReader:
    def __init__(self, scenario_name: str):
        self.name = scenario_name
        # open Mongo Database to retrieve scenario data (metadata)
        self.meta_db = DBConfigs(uri=env.cst_mg_host, db_name=env.cst_mongo_db)
        # retrieve data from MongoDB
        self.scenario = self.meta_db.get_dict(env.cst_scenarios, None, scenario_name)
        self.schema_name = self.scenario.get("schema")
        self.federation_name = self.scenario.get("federation")
        self.start_time = self.scenario.get("start_time")
        self.stop_time = self.scenario.get("stop_time")
        self.use_docker = self.scenario.get("docker")
        if self.federation_name is not None:
            self.federation = self.meta_db.get_dict(env.cst_federations, None, self.federation_name)
        # close MongoDB client
        if self.meta_db.client is not None:
            self.meta_db.client.close()
        self.meta_db = None




class ValueType(Enum):
    STRING = 'HDT_STRING'
    DOUBLE = 'HDT_DOUBLE'
    INTEGER = 'HDT_INTEGER'
    COMPLEX = 'HDT_COMPLEX'
    VECTOR = 'HDT_VECTOR'
    COMPLEX_VECTOR = 'HDT_COMPLEX_VECTOR'
    NAMED_POINT = 'HDT_NAMED_POINT'
    BOOLEAN = 'HDT_BOOLEAN'
    TIME = 'HDT_TIME'
    JSON = 'HDT_JSON'
    ENDPOINT = 'HDT_ENDPOINT'


class DataReader(DBResults):
    """
    alternative to ResultsDB
    """
    def __init__(self, scenario_name):
        super().__init__()
        self.is_connected = self.open_database_connections()
        self.scenario_reader = ScenarioReader(scenario_name)
        self.scenario = self.scenario_reader.scenario
        self.scenario_name = scenario_name

    def __enter__(self):
        return self  # The object returned here will be assigned to the variable after 'as' in the 'with' statement

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        if exc_type is not None:
            print(f"An exception occurred: {exc_type}, {exc_value}")
        # Return False to propagate the exception, True to suppress it
        return False

    def get_query_string(self, start_time: int,
                         duration: int,
                         scenario_name: str,
                         federate_name: str,
                         data_name: str,
                         data_type: str) -> str:
        """This function creates the query string to pull time series data from the
        logger database, and depends upon the keys identified by the user input arguments.

        Args:
            start_time (integer) - the starting time step to query data for
            duration (integer) - the duration in seconds to filter time data by
            If start_time and duration are entered as None then the query will return every
            time step that is available for the entered scenario, federate, pub_key,
            data_type combination.
            If start_time is None and a duration has been entered then all time steps that are
            less than the duration value will be returned
            If a start_time is entered and duration is None, the query will return all time steps
            greater than the starting time step
            If a value is entered for the start_time and the duration, the query will return all time steps
            that fall into the range of start_time to start_time + duration
            scenario_name (string) - the name of the scenario to filter the query results by. If
            None is entered for the scenario_name the query will not use scenario_name as a filter
            federate_name (string) - the name of the Federate to filter the query results by. If
            None is entered for the federate_name the query will not use federate_name as a filter
            data_name (string) - the name of the data to filter the query results by. If
            None is entered for the data_name the query will not use data_name as a filter
            data_type (string) - the id of the database table that will be queried. Must be
            one of the following options:
                [ hdt_boolean, hdt_complex, hdt_complex_vector, hdt_double, hdt_integer
                hdt_json, hdt_named_point, hdt_string, hdt_time, hdt_vector ]

        Returns:
            qry_string (string) - string representing the query to be used in pulling time series
            data from logger database
        """
        scheme = self.get_scenario(scenario_name)
        scheme_name = scheme["schema"]
        qry_string = self.get_select_string(scheme_name, data_type)
        time_string = self.get_time_select_string(start_time, duration)
        scenario_string = f"scenario='{scenario_name}'" if scenario_name is not None and scenario_name != "" else ""
        federate_string = ""
        if isinstance(federate_name, str):
            federate_string = f"federate='{federate_name}'"
        if isinstance(federate_name, list):
            federate_string = f"federate IN {tuple(federate_name)}"
        data_string = f"data_name='{data_name}'" if data_name is not None and data_name != "" else ""
        if time_string == "" and scenario_string == "" and federate_string == "" and data_string == "":
            qry_string = qry_string.replace(" WHERE ", "")
            return qry_string
        if time_string != "":
            qry_string += time_string
        if scenario_string != "":
            if time_string != "":
                qry_string += " AND " + scenario_string
            else:
                qry_string += scenario_string
        if federate_string != "":
            if time_string != "" or scenario_string != "":
                qry_string += " AND " + federate_string
            else:
                qry_string += federate_string
        if data_string != "":
            if time_string != "" or scenario_string != "" or federate_string != "":
                qry_string += " AND " + data_string
            else:
                qry_string += data_string
        qry_string += "ORDER BY sim_time;"
        return qry_string

    def get_results(
            self,
            start_time=None,
            duration=None,
            federate_name=None,
            data_name=None,
            data_type: ValueType | str = ValueType.DOUBLE):
        if isinstance(data_type, ValueType):
            data_type = data_type.value
        data_name_list = self.get_data_name_list(self.scenario_reader.schema_name, data_type=data_type).to_numpy()
        federate_list = self.get_federate_list(self.scenario_reader.schema_name, data_type=data_type).to_numpy()
        if data_name is not None and data_name not in data_name_list:
            logger.warning(f"data_name, {data_name}, not in {data_name_list}")
        if federate_name is not None and federate_name not in federate_list:
            logger.warning(f"federate_name, {federate_name} not in {federate_list}")
        if data_type not in self._hdt_type.keys():
            logger.warning(f"data_type, {data_type} not in {list(self._hdt_type.keys())}")
        return self.query_scenario_federate_times(start_time, duration, self.scenario_name, federate_name,
                                      data_name, data_type)

    def get_maximum_data_value(self, scheme_name: str, federate_name: str, data_name: str, data_type: str):
        if type(scheme_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        if type(federate_name) is not str:
            return None
        qry_string = (f"SELECT MAX(CAST(data_value AS FLOAT)) FROM {scheme_name}.{data_type} "
                      f"WHERE scenario='{self.scenario_name}' AND federate='{federate_name}' AND data_name='{data_name}'")
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["data_name"]
            data = cur.fetchall()
            # dataframe = pd.DataFrame(data, columns=column_names)
            return data[0][0]

    def get_maximum_sim_time(self, scheme_name: str, federate_name: str, data_name: str, data_type: str):
        if type(scheme_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        if type(federate_name) is not str:
            return None
        qry_string = (f"SELECT MAX(CAST(sim_time AS FLOAT)) FROM {scheme_name}.{data_type} "
                      f"WHERE scenario='{self.scenario_name}' AND federate='{federate_name}' AND data_name='{data_name}'")
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["data_name"]
            data = cur.fetchall()
            # dataframe = pd.DataFrame(data, columns=column_names)
            return data[0][0]

    def get_length_data_value(self, scheme_name: str, federate_name: str, data_name: str, data_type: str):
        if type(scheme_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        if type(federate_name) is not str:
            return None
        qry_string = (f"SELECT COUNT(CAST(data_value AS FLOAT)) FROM {scheme_name}.{data_type} "
                      f"WHERE scenario='{self.scenario_name}' AND federate='{federate_name}' AND data_name='{data_name}'")
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["data_name"]
            data = cur.fetchall()
            # dataframe = pd.DataFrame(data, columns=column_names)
            return data[0][0]

    def get_length_of_schema(self, schema_name: str, data_type: str):
        if type(schema_name) is not str:
            return None
        qry_string = (f"SELECT COUNT(CAST(data_value AS FLOAT)) FROM {schema_name}.{data_type}")
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            data = cur.fetchall()
            return data[0][0]

    def get_federate_subscription_list(self, scheme_name: str, federate_name: str, data_type: str) -> pd.DataFrame:
        """This function queries the distinct list of data names from the database table
        defined by scheme_name and data_type

        Args:
            scheme_name (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried. Must be

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if type(scheme_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        if type(federate_name) is not str:
            return None
        qry_string = (f"SELECT DISTINCT data_name FROM {scheme_name}.{data_type} "
                      f"WHERE scenario='{self.scenario_name}' AND federate='{federate_name}'")
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["data_name"]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    def get_max_val_diff(self, scheme_name: str, federate_name: str, data_name: str, data_type: str, start_time:int=0):
        if type(scheme_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        if type(federate_name) is not str:
            return None
        qry_string = f"""
        WITH val_diff AS (
            SELECT CAST(data_value AS FLOAT) - LAG(CAST(data_value AS FLOAT))
            OVER (
                ORDER BY sim_time
            ) 
            AS diff
            FROM {scheme_name}.{data_type}
            WHERE scenario='{self.scenario_name}'
            AND federate='{federate_name}'
            AND data_name='{data_name}'
            AND sim_time>={start_time}
            )
        SELECT MAX(diff) FROM val_diff
        """
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["data_name"]
            data = cur.fetchall()
            # dataframe = pd.DataFrame(data, columns=column_names)
            return data[0][0]

    def get_min_val_diff(self, scheme_name: str, federate_name: str, data_name: str, data_type: str, start_time:int=0):
        if type(scheme_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        if type(federate_name) is not str:
            return None
        qry_string = f"""
        WITH val_diff AS (
            SELECT CAST(data_value AS FLOAT) - LAG(CAST(data_value AS FLOAT))
            OVER (
                ORDER BY sim_time
            ) 
            AS diff
            FROM {scheme_name}.{data_type}
            WHERE scenario='{self.scenario_name}'
            AND federate='{federate_name}'
            AND data_name='{data_name}'
            AND sim_time>={start_time}
            )
        SELECT MIN(diff) FROM val_diff
        """
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["data_name"]
            data = cur.fetchall()
            # dataframe = pd.DataFrame(data, columns=column_names)
            return data[0][0]

    @property
    def string_df(self):
        return self.get_results(data_type=ValueType.STRING)

    @property
    def double_df(self):
        return self.get_results(data_type=ValueType.DOUBLE)

    @property
    def bool_df(self):
        return self.get_results(data_type=ValueType.BOOLEAN)

    @property
    def integer_df(self):
        return self.get_results(data_type=ValueType.INTEGER)

    @property
    def complex_df(self):
        return self.get_results(data_type=ValueType.COMPLEX)

    @property
    def vector_df(self):
        return self.get_results(data_type=ValueType.VECTOR)

    @property
    def complex_vector_df(self):
        return self.get_results(data_type=ValueType.COMPLEX_VECTOR)

    @property
    def named_point_df(self):
        return self.get_results(data_type=ValueType.NAMED_POINT)

    @property
    def time_df(self):
        return self.get_results(data_type=ValueType.TIME)

    @property
    def json_df(self):
        return self.get_results(data_type=ValueType.JSON)

    @property
    def endpoint_df(self):
        return self.get_results(data_type=ValueType.ENDPOINT)

    def close(self):
        self.close_database_connections()



def validate_scenarios(cst_scalability: str):
    scale_test_name = cst_scalability
    test_num = scale_test_name[-1]
    cst_scalability = Path(cst_scalability)
    run_only = None
    # run_only = list(range(13, 14))

    df = pd.DataFrame(data=[], columns=["scenario", "schema", "federate", "schema_rows", "selected_rows", "time"])
    for scenario_dir_path in cst_scalability.iterdir():
        if not scenario_dir_path.is_dir():
            continue
        scenario_dir_name = scenario_dir_path.name
        cnt = int(scenario_dir_name.split("_")[-1])
        if run_only is not None and cnt not in run_only:
            continue
        scenario_name = f"scale_test{test_num}_s_{cnt}"
        name = scenario_dir_path/Path(f"scale_test{test_num}_{cnt}.json")
        with open(name, "r") as f:
            scalability = json.load(f)
        _f = scalability["number of feds"]
        _s = scalability["number of pubs"]
        _e = scalability["use endpoints"]
        _d = scalability["use CST logger"]
        _p = scalability["use profiling"]
        if not _d:
            continue
        logger.info(f"{scenario_name} -> feds:{_f}, subs:{_s}, end_pts:{_e}, cst_log:{_d}, profile:{_p}")
        dr = DataReader(scenario_name)
        schema_rows = dr.get_length_of_schema(schema_name=dr.scenario_reader.schema_name, data_type=ValueType.DOUBLE.value)
        """
            We need to compare read times for Standard Postrgres using new federate.py vs TimescaleDB using new federate.py in the following way:
            1.	Reading all times for a given federate
            2.	Reading all federates for a given (non-exhaustive) time slice.
            3.	Reading a given set of federates  for a non-exhaustive time slice.
        """
        for fed_number in range(5):
            federate = f"fed_{fed_number}"
            # All times for a federate
            # 1. Reading all times for a given federate
            tic = time.perf_counter()
            df_sub_db = dr.get_results(federate_name=federate, data_type=ValueType.DOUBLE)
            toc = time.perf_counter()
            n_lines = df_sub_db.shape[0]
            logger.info(f"{federate}: time to read-all {n_lines} records from {schema_rows} items in schema: {toc-tic}s")
            data = [[scenario_name, dr.scenario_reader.schema_name, federate, schema_rows, n_lines, toc-tic]]
            df = pd.concat([df, pd.DataFrame(data, columns=df.columns)], ignore_index=True)
            # 2. Reading all federates for a given (non-exhaustive) time slice.
            tic = time.perf_counter()
            df_sub_db = dr.get_results(duration=300, data_type=ValueType.DOUBLE)
            toc = time.perf_counter()
            n_lines = df_sub_db.shape[0]
            data = [[scenario_name, dr.scenario_reader.schema_name, "all", schema_rows, n_lines, toc-tic]]
            df = pd.concat([df, pd.DataFrame(data, columns=df.columns)], ignore_index=True)
            # 3. Reading a given set of federates  for a non-exhaustive time slice.
            tic = time.perf_counter()
            df_sub_db = dr.get_results(duration=300, federate_name=["fed_0", "fed_1", "fed_2"], data_type=ValueType.DOUBLE)
            toc = time.perf_counter()
            n_lines = df_sub_db.shape[0]
            data = [[scenario_name, dr.scenario_reader.schema_name, "3 feds", schema_rows, n_lines, toc-tic]]
            df = pd.concat([df, pd.DataFrame(data, columns=df.columns)], ignore_index=True)
    df.to_csv(f"{scale_test_name}_read_test5x.csv")

if __name__ == '__main__':
    env.cst_mg_host = "mongodb://tapteal-ubu.pnl.gov"
    env.cst_mongo = env.cst_mg_host + ":" + env.cst_mg_port
    env.cst_pg_host = "tapteal-ubu.pnl.gov"
    env.cst_postgres = env.cst_pg_host + ":" + env.cst_pg_port
    for test_name in ["scale_test7", "scale_test8", "scale_test9"]:

        logger = logging.getLogger(__name__)
        logger.setLevel(level=logging.INFO)
        fh = logging.FileHandler(f"read_time_{test_name}.log", mode="w")
        fh.setLevel(level=logging.INFO)
        logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setLevel(level=logging.INFO)
        logger.addHandler(ch)

        tic = time.perf_counter()
        validate_scenarios(test_name)
        toc = time.perf_counter()
        logger.info(f"elapsed time: {toc - tic}")