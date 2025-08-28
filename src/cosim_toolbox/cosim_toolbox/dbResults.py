"""
Created on 12/14/2023

Provides underlying methods for interacting with the time-series database

TODO: Should we rename this to something like "cst_ts_postgres.py" and the
class to "CSTTimeSeriesPostgres" as all the methods are Postgres specific?
I can image a more abstract class used for interacting with databases that
codifies the terminology (_e.g._ "analysis", "scenario") and this class
inherits from it and implements the methods in a Postgres-specific way.

@authors:
fred.rutz@pnnl.gov
mitch.pelton@pnnl.gov
nathan.gray@pnnl.gov
"""

import logging

import pandas as pd
from datetime import timedelta
from psycopg2 import connect

import cosim_toolbox as env
from cosim_toolbox.readConfig import ReadConfig

logger = logging.getLogger(__name__)

# TODO: The databases referenced in these APIs should be "metadata"
# and "time_series" and should be updated across the codebase.

class DBResults:
    """Methods for writing to and reading from the time-series database. This
    class does not provide HELICS federate functionality.

    """
    hdt_type = {'HDT_STRING': 'text',
                'HDT_DOUBLE': 'double precision',
                'HDT_INTEGER': 'bigint',
                'HDT_COMPLEX': 'VARCHAR (255)',
                'HDT_VECTOR': 'text',
                'HDT_COMPLEX_VECTOR': 'text',
                'HDT_NAMED_POINT': 'VARCHAR (255)',
                'HDT_BOOLEAN': 'boolean',
                'HDT_TIME': 'TIMESTAMP',
                'HDT_JSON': 'text',
                'HDT_ENDPOINT': 'text'}

    def __init__(self):
        self.data_db = None
        self._scenario = None
        self.use_timescale = False

    @staticmethod
    def _connect_logger_database(connection: dict = None):
        """This function defines the connection to the data database
        and opens a connection to the postgres database

        Returns:
            psycopg2 connection object - connection object that provides
            access to the postgres database
        """
        if connection is None:
            connection = env.cst_data_db
        logger.info(connection)
        try:
            return connect(**connection)
        except Exception as ex:
            logger.exception(f"{ex}\nFailed to create PostgresDB instance.")
            return None

    def close_database_connections(self, commit: bool = True) -> None:
        """Closes connections to the time-series and metadata databases

        Args:
            commit (bool, optional): Flag to indicate whether data should be
            committed to the time-series DB prior to closing the connection.
            Defaults to True.
        """
        if self.data_db:
            if commit:
                self.data_db.commit()
            self.data_db.close()
        self.data_db = None

    def open_database_connections(self, data_connection: dict = None) -> bool:
        """Opens connections to the time-series and metadata databases

        Args:
            data_connection (dict, optional): Defines connection to time-series
            database. Defaults to None.

        Returns:
            bool: _description_
        """
        self.data_db = self._connect_logger_database(data_connection)
        if self.data_db is None:
            return False
        else:
            return True

    def check_version(self) -> None:
        """Checks the version of the time-series database

            TODO: This method name should make it clear it is
            just checking the time-series database version and
            not the metadata DB version. Maybe rename to
            "check_tsdb_version"?
        """
        with self.data_db.cursor() as cur:
            logger.info('PostgresSQL database version:')
            cur.execute('SELECT version()')
            db_version = cur.fetchone()
            logger.info(db_version)

    def create_schema(self, scheme_name: str) -> None:
        """Creates a new scheme in the time-series database

        TODO: "schema" should not be in the method name. In CSTs when using
        the Postgres database "schemes" are called "analysis". This
        name needs to be updated. This also applies to other methods in
        this class.

        Args:
            scheme_name (str): _description_
        """
        query = f"CREATE SCHEMA IF NOT EXISTS {scheme_name}; "
        query += f"GRANT USAGE ON SCHEMA {scheme_name} TO reader;"
        with self.data_db.cursor() as cur:
            cur.execute(query)
            self.data_db.commit()

    def drop_schema(self, scheme_name: str) -> None:
        """Removes the scheme from the database.

        Args:
            scheme_name (str): _description_
        """
        query = f"DROP SCHEMA IF EXISTS {scheme_name} CASCADE;"
        with self.data_db.cursor() as cur:
            cur.execute(query)
            self.data_db.commit()

    def remove_scenario(self, analysis_name: str, scenario_name: str) -> None:
        """Removes all data from the specified analysis_name with the specified
        scenario_name

        Args:
            analysis_name (str): Analysis containing the data to be deleted
            scenario_name (str): Scenario to be removed from the analysis
        """
        query = ""
        for key in self.hdt_type:
            query += f" DELETE FROM {analysis_name}.{key} WHERE scenario='{scenario_name}'; "
        with self.data_db.cursor() as cur:
            cur.execute(query)
            self.data_db.commit()

    def schema_exist(self, scheme_name: str) -> bool:
        """Checks to see if the specified schema exist in the database

        Args:
            scheme_name (str): schema name whose existence is being checked

        Returns:
            bool: specified schema exist or not
        """
        exist = False
        with self.data_db.cursor() as cur:
            cur.execute("select * from information_schema.tables "
                        "where table_schema=%s",
                        (scheme_name,))
            if cur.rowcount > 0:
                exist = True
        return exist

    def table_exist(self, analysis_name: str, table_name: str) -> bool:
        """Checks to see if the specified tables exist in the specified analysis

        Args:
            analysis_name (str): Name of analysis where table may exist
            table_name (str): Table name whose existence is being checked

        Returns:
            bool: specified tables exist or not
        """
        exist = False
        with self.data_db.cursor() as cur:
            cur.execute("select * from information_schema.tables "
                        "where table_schema=%s and table_name=%s",
                        (analysis_name,table_name))
            if cur.rowcount > 0:
                exist = True
        return exist

    def make_logger_database(self, analysis_name: str) -> None:
        """_summary_

        Args:
            analysis_name (str): Name of analysis under which various
            scenarios will be collected
        """

        query = ""
        for key in self.hdt_type:
            query += ("CREATE TABLE IF NOT EXISTS "
                      f"{analysis_name}.{key} ("
                      "real_time timestamp with time zone NOT NULL, "
                      "sim_time double precision NOT NULL, "
                      "scenario VARCHAR (255) NOT NULL, "
                      "federate VARCHAR (255) NOT NULL, "
                      "data_name VARCHAR (255) NOT NULL, "
                      f"data_value {self.hdt_type[key]} NOT NULL);")
            if self.use_timescale:
                query += f" SELECT create_hypertable('{analysis_name}.{key}', 'real_time');"
                # query += f" CREATE INDEX ix_{scheme_name}_{key} ON {scheme_name}.{key} (scenario, real_time DESC);"
        query += f" GRANT SELECT ON ALL TABLES IN SCHEMA {analysis_name} TO reader;"
        query += f" GRANT USAGE ON ALL SEQUENCES IN SCHEMA {analysis_name} TO reader;"
        query += f" GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {analysis_name} TO reader;"
        query += f" ALTER ROLE reader SET search_path = {analysis_name};"
        with self.data_db.cursor() as cur:
            cur.execute(query)
            self.data_db.commit()

    def get_scenario(self, scenario_name: str) ->  None | ReadConfig:
        """Gets the metadata associated with the specified scenario from the
        metadata database.

        Args:
            scenario_name (str): Name of scenario for which the metadata
            is to be retrieved

        Returns:
            dict: scenario metadata requested
        """
        if scenario_name is None or scenario_name == "":
            return None
        if self._scenario is None:
            self._scenario = ReadConfig(scenario_name)
        else:
            if self._scenario.scenario_name == scenario_name:
                return self._scenario
            else:
                self._scenario = ReadConfig(scenario_name)
        return self._scenario

    @staticmethod
    def get_select_string(scheme_name: str, data_type: str) ->  None | str:
        """This method creates the SELECT portion of the query string

        Args:
            scheme_name (string) - the name of the database to be queried
            data_type (string) - the name of the database table to be queried

        Returns:
            qry_string (string) - string containing the select portion of the sql query
            'SELECT * FROM scheme_name.data_type WHERE'
        """
        if scheme_name is None or scheme_name == "":
            return None
        if data_type is None or data_type == "":
            return None
        qry_string = "SELECT * FROM " + scheme_name + "." + data_type + " WHERE "
        return qry_string

    @staticmethod
    def get_time_select_string(start_time: int, duration: int) -> str:
        """This method creates the time filter portion of the query string

        Args:
            start_time (int) - the lowest time step in seconds to start the filtering
            If None is entered for the start_time the query will return only times that are
            less than the duration entered
            duration (int) - the number of seconds to be queried
            If None is entered for the duration the query will return only times that are greater
            than the start time entered
            If None is entered for both the start_time and duration all times will be returned

        Returns:
            qry_string (string) - string containing the time filter portion of the sql query
            'sim_time>=start_time AND sim_time<= end_time'
        """
        if start_time is None and duration is None:
            return ""
        elif start_time is not None and duration is None:
            return "sim_time>=" + str(start_time)
        elif start_time is None and duration is not None:
            return "sim_time<=" + str(duration)
        else:
            end_time = start_time + duration
        return "sim_time>=" + str(start_time) + " AND sim_time<=" + str(end_time)

    def get_query_string(self, start_time: int,
                         duration: int,
                         scenario_name: str,
                         federate_name: str,
                         data_name: str,
                         data_type: str) ->  None | str:
        """This method creates the query string to pull time series data from the
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
        scenario = self.get_scenario(scenario_name)
        if scenario is None:
            return None
        scheme_name = scenario.schema_name
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
        return qry_string

    def query_scenario_federate_times(self, start_time: int,
                                      duration: int,
                                      scenario_name: str,
                                      federate_name: str,
                                      data_name: str,
                                      data_type: str) ->  None | pd.DataFrame:
        """This method queries time series data from the logger database and
        depends upon the keys identified by the user input arguments.

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
                [ hdt_boolean, hdt_complex, hdt_complex_vector, hdt_double, hdt_int
                hdt_json, hdt_named_point, hdt_string, hdt_time, hdt_vector ]

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        qry_string = self.get_query_string(start_time, duration, scenario_name, federate_name, data_name, data_type)
        if qry_string:
            with self.data_db.cursor() as cur:
                cur.execute(qry_string)
                column_names = [desc[0] for desc in cur.description]
                data = cur.fetchall()
                dataframe = pd.DataFrame(data, columns=column_names)
                return dataframe
        return None

    def query_scenario_all_times(self, scenario_name: str, data_type: str) -> None | pd.DataFrame:
        """This function queries data from the logger database filtered only by scenario_name and data_name

        Args:
            scenario_name (string) - the name of the scenario to filter the query results by
            data_type (string) - the id of the database table that will be queried. Must be

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if type(scenario_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        scenario = self.get_scenario(scenario_name)
        scheme_name = scenario.schema_name

        qry_string = f"SELECT * FROM {scheme_name}.{data_type} WHERE scenario='{scenario_name}';"
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    def query_scheme_all_times(self, scheme_name: str, data_type: str) -> None:
        raise NotImplementedError("method query_scheme_all_times is not implemented yet")

    def query_scheme_federate_all_times(self, scheme_name: str, federate_name: str, data_type) ->  None | pd.DataFrame:
        """This function queries data from the logger database filtered only by federate_name and data_name
        and data_type

        TODO: Rename "query_scheme_federate_all_times" to "query_

        Args:
            scheme_name (string) - the name of the schema to filter the query results by
            federate_name (string) - the name of the Federate to filter the query results by
            data_type (string) - the id of the database table that will be queried. Must be

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if type(scheme_name) is not str:
            return None
        if type(federate_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        # Todo: check against meta_db to see if schema name exist?
        qry_string = f"SELECT * FROM {scheme_name}.{data_type} WHERE federate='{federate_name}'"
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    def get_schema_list(self) -> None:
        # Todo: get schema from scenario documents
        raise NotImplementedError(f"method get_schema_list is not implemented yet")

    def get_scenario_list(self, scheme_name: str, data_type: str) ->  None | pd.DataFrame:
        """This function queries the distinct list of scenario names from the database table
        defined by scheme_name and data_type

        Args:
            scheme_name (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried.

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if type(scheme_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        # Todo: check against meta_db to see if schema name exist?
        # This should take from the meta documents and verify
        qry_string = f"SELECT DISTINCT scenario FROM {scheme_name}.{data_type};"
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["scenario"]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    def get_federate_list(self, scheme_name: str, data_type: str) ->  None | pd.DataFrame:
        """This function queries the distinct list of federate names from the database table
        defined by scheme_name and data_type

        Args:
            scheme_name (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried.

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if type(scheme_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        # Todo: check against meta_db to see if schema name exist?
        qry_string = f"SELECT DISTINCT federate FROM {scheme_name}.{data_type};"
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["federate"]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    def get_data_name_list(self, scheme_name: str, data_type: str) ->  None | pd.DataFrame:
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
        # Todo: check against meta_db to see if schema name exist?
        qry_string = f"SELECT DISTINCT data_name FROM {scheme_name}.{data_type};"
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["data_name"]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    def get_time_range(self, scheme_name: str, data_type: str, scenario_name: str, federate_name: str) ->  None | pd.DataFrame:
        """This function queries the minimum and maximum of time from the database
            table defined by scheme_name, data_type, scenario_name, and federate

        Args:
            scheme_name (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried. Must be
            scenario_name (string) - the name of the Scenario to filter the query results by
            federate_name (string) - the name of the Federate to filter the query results by

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if type(scheme_name) is not str:
            return None
        if type(data_type) is not str:
            return None
        qry_string = f"SELECT MIN(sim_time), MAX(sim_time) FROM {scheme_name}.{data_type}"
        if scenario_name is not None and federate_name is None:
            if type(scenario_name) is str:
                qry_string += f" WHERE scenario='{scenario_name}';"
        if scenario_name is None and federate_name is not None:
            if type(federate_name) is str:
                qry_string += f" WHERE federate='{federate_name}';"
        if scenario_name is not None and federate_name is not None:
            if type(scenario_name) is str and type(scenario_name) is str:
                qry_string += f" WHERE federate='{federate_name}' AND scenario='{scenario_name}';"
        else:
            qry_string += ";"
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["min", "max"]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    @staticmethod
    def set_time_stamps(dataframe: pd.DataFrame, date_time: str) -> None | pd.DataFrame:
        """This function calculates the time stamp for each time step in the dataframe and adds them
            to the dataframe in a column named time_stamp

        Args:
            dataframe (pandas dataframe) - the dataframe for which contains the time steps in seconds to
            be used in the calculation of the time stamps
            date_time (datetime) - the base time stamp that will be used to calculate the time step
            time stamps

        Returns:
            # TODO: is ts a pd.Timestamp or something else?
            ts(pandas time series) - time series that contains the result records
            returned from the query of the database
        """
        time_list = []
        for x in range(len(dataframe)):
            trow = dataframe.iloc[x]
            sec_time = trow.time
            time_list.append(date_time + timedelta(seconds=sec_time))
        dataframe['time_stamp'] = time_list
        ts = dataframe.set_index('time_stamp')
        return ts
