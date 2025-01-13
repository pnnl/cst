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
import psutil
import pandas as pd

import cosim_toolbox as cst
from cosim_toolbox.dbResults import DBResults
from cosim_toolbox.readConfig import ReadConfig

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
fh = logging.FileHandler("validation_scale2.log", mode="w")
fh.setLevel(level=logging.INFO)
logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setLevel(level=logging.INFO)
logger.addHandler(ch)


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
        self.scenario_reader = ReadConfig(scenario_name)
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

    def open_database_connections(self, meta_connection: dict = None, data_connection: dict = None) -> bool:
        self.data_db = self._connect_logger_database(data_connection)
        if self.data_db is None:
            return False
        return True

    def close_database_connections(self, commit: bool = True) -> None:
        if self.data_db:
            if commit:
                self.data_db.commit()
            self.data_db.close()
        self.data_db = None

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
        federate_string = f"federate='{federate_name}'" if federate_name is not None and federate_name != "" else ""
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
        if data_type not in self.hdt_type.keys():
            logger.warning(f"data_type, {data_type} not in {list(self.hdt_type.keys())}")
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

def scenario_map(cu_scalability: str):
    cu_scalability = Path(cu_scalability)
    # os.chdir(cu_scalability)
    scenario_dict = {}
    for scenario_dir_path in cu_scalability.iterdir():
        scenario_dir_name = scenario_dir_path.name
        cnt = int(scenario_dir_name.split("_")[-1])
        scenario_name = f"scenario_{cnt}"
        name = f"{scenario_dir_path}/scalability_{cnt}.json"
        with open(name, "r") as f:
            scalability = json.load(f)
        _f = scalability["number of feds"]
        _s = scalability["number of pubs"]
        _e = scalability["use endpoints"]
        _d = scalability["use CST logger"]
        _p = scalability["use profiling"]
        scenario_dict[f"{_f}:{_s}:{_e}:{_d}:{_p}"] = scenario_dir_path / "federate_outputs"
    return scenario_dict


def validate_scenarios(cu_scalability: str):
    cu_scalability = Path(cu_scalability)
    scenario_dict = scenario_map(cu_scalability)
    # run_only = None
    run_only = list(range(1, 2))

    for scenario_dir_path in cu_scalability.iterdir():
        scenario_dir_name = scenario_dir_path.name
        cnt = int(scenario_dir_name.split("_")[-1])
        if run_only is not None and cnt not in run_only:
            continue
        scenario_name = f"scenario_{cnt}"
        name = scenario_dir_path/f"scalability_{cnt}.json"
        with open(name, "r") as f:
            scalability = json.load(f)
        _f = scalability["number of feds"]
        _s = scalability["number of pubs"]
        _e = scalability["use endpoints"]
        _d = scalability["use CST logger"]
        _p = scalability["use profiling"]
        logger.info(f"{scenario_name} -> feds:{_f}, subs:{_s}, end_pts:{_e}, cst_log:{_d}, profile:{_p}")
        if not _d:
            continue

        time_step = 30
        n_steps = 2880
        end_time = 86400
        dr = DataReader(scenario_name)
        if "ts_scale_test3" in dr.scenario_reader.schema_name:
            dr.scenario_reader.schema_name = dr.scenario_reader.schema_name.replace("ts_scale_test3", "scale_test2")
        csv_dir_path = scenario_dict[f"{_f}:{_s}:{_e}:{False}:{_p}"]
        for out_csv in csv_dir_path.iterdir():
            if out_csv.suffix != ".csv":
                continue
            federate = out_csv.stem.strip("_outputs")
            df = pd.read_csv(out_csv)
            # df_ept = df.loc[df.data_name.str.contains("pt_"), :]
            df_sub = df.loc[df.data_name.str.contains("v_"), :].copy()
            df_sub.real_time = pd.to_datetime(df_sub.real_time, utc=True)
            # df_ept_db = dr.get_results(federate_name=federate, data_type=ValueType.ENDPOINT)
            df_sub_db = dr.get_results(federate_name=federate, data_type=ValueType.DOUBLE)
            df_sub_db.index = df_sub_db.sim_time
            df_sub.index = df_sub.sim_time
            assert all(df_sub.loc[:86400].data_value.to_numpy() == df_sub_db.data_value.to_numpy())
        # if _e:
            # validate_endpoints_db(_f, dr, end_time, n_steps, time_step)
        validate_subs_db(_f, _s, dr, end_time, n_steps)


def validate_subs_db(_f, _s, dr: DataReader, end_time, n_steps):
    federate_list = dr.get_federate_list(dr.scenario_reader.schema_name, data_type=ValueType.DOUBLE.value)
    federate_list = np.sort(federate_list.to_numpy().flatten())
    assert len(federate_list) == _f
    for federate in federate_list:
        sub_list = dr.get_federate_subscription_list(
            dr.scenario_reader.schema_name,
            federate_name=federate,
            data_type=ValueType.DOUBLE.value
        )
        sub_list = np.sort(sub_list.to_numpy().flatten())
        assert len(sub_list) == _s
        for sub in sub_list:
            diff_max, diff_min, final_time, max_val, n_rows = query_validation_values(
                dr, federate, sub, ValueType.DOUBLE
            )
            try:
                assert max_val == n_rows - 2
                # assert n_rows == n_steps
                # assert final_time == end_time
                assert diff_max == 1.0
                assert diff_min == 1.0
            except AssertionError as er:
                logger.error(f"\t{federate}:{sub} test failed")


def validate_endpoints_db(_f, dr, end_time, n_steps, time_step):
    fed_ept_list = dr.get_federate_list(dr.scenario_reader.schema_name, data_type=ValueType.ENDPOINT.value)
    fed_ept_list = np.sort(fed_ept_list.to_numpy().flatten())
    fed_list = np.unique(np.array([fed_ept.split("/")[0] for fed_ept in fed_ept_list]))
    ept_list = np.unique(np.array([fed_ept.split("/")[1] for fed_ept in fed_ept_list]))
    assert len(fed_list) == _f
    for federate in fed_ept_list:
        destination_list = dr.get_federate_subscription_list(
            dr.scenario_reader.schema_name,
            federate_name=federate,
            data_type=ValueType.ENDPOINT.value
        )
        destination_list = np.sort(destination_list.to_numpy().flatten())
        assert len(destination_list) == 1
        destination = str(destination_list[0])
        diff_max, diff_min, final_time, max_val, n_rows = query_validation_values(
            dr, federate, destination, ValueType.ENDPOINT
        )
        try:
            assert max_val == n_rows - 1
            assert n_rows * time_step == final_time
            # assert n_rows == n_steps - 1
            # assert final_time == end_time - 30
            assert diff_max == 1.0
            assert diff_min == 1.0
        except AssertionError:
            logger.error(f"\tendpoint: {federate}:{destination} test failed")


def query_validation_values(dr, federate, data_name, value_type):
    max_val = dr.get_maximum_data_value(
        dr.scenario_reader.schema_name,
        federate_name=federate,
        data_name=data_name,
        data_type=value_type.value
    )
    n_rows = dr.get_length_data_value(
        dr.scenario_reader.schema_name,
        federate_name=federate,
        data_name=data_name,
        data_type=value_type.value
    )
    final_time = dr.get_maximum_sim_time(
        dr.scenario_reader.schema_name,
        federate_name=federate,
        data_name=data_name,
        data_type=value_type.value
    )
    diff_max = dr.get_max_val_diff(
        dr.scenario_reader.schema_name,
        federate_name=federate,
        data_name=data_name,
        data_type=value_type.value,
        start_time=60,
    )
    diff_min = dr.get_min_val_diff(
        dr.scenario_reader.schema_name,
        federate_name=federate,
        data_name=data_name,
        data_type=value_type.value,
        start_time=60,
    )
    return diff_max, diff_min, final_time, max_val, n_rows


def wait_for_helics():
    helics_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        if proc.info["name"] == "helics_broker":
            helics_procs.append(proc)
    psutil.wait_procs(helics_procs)


def kill_helics():
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        if proc.info["name"] == "helics_broker":
            proc.kill()

#
# def validate_scenario(scenario_name, n_federates, n_publications):
#     dr = DataReader(scenario_name)
#     df = dr.double_df.loc[dr.double_df.scenario == scenario_name].loc[dr.double_df.data_value >= -1e40].loc[
#         dr.double_df.data_value <= 1e40]
#
#     federate_list = np.unique(df.federate.to_numpy())
#     logger.info(federate_list)
#     assert len(federate_list) == n_federates
#     for federate in federate_list:
#         dff = df.loc[df.federate == federate]
#         pub_list = np.unique(dff.data_name.to_numpy())
#         assert len(pub_list) == n_publications
#         for pub in pub_list:
#             logger.debug(f"Publication: {pub}")
#             dffp = dff.loc[dff.data_name == pub]
#             dffp = dffp.sort_values(by="sim_time", ignore_index=True)
#             dx = dffp.data_value.diff()
#             assert np.max(dx.to_numpy()[1:]) == 1.0
#             assert np.min(dx.to_numpy()[1:]) == 1.0
#             logger.info(f"steps: {len(dffp.sim_time) + 1}, simulation time: {np.max(dffp.sim_time)}s")

if __name__ == '__main__':
    cst.cosim_mg_host = "mongodb://maxwell.pnl.gov"
    cst.cosim_mongo = cst.cosim_mg_host + ":" + cst.cosim_mg_port
    cst.cosim_pg_host = "maxwell.pnl.gov"
    cst.cosim_postgres = cst.cosim_pg_host + ":" + cst.cosim_pg_port
    tic = time.perf_counter()
    if len(sys.argv) > 1:
        validate_scenarios(sys.argv[1])
    else:
        validate_scenarios('scale_test2')
    toc = time.perf_counter()
    logger.info(f"elapsed time: {toc - tic}")