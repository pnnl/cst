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

"""
from os import environ
import logging
import pandas as pd
import datetime as dt
import psycopg2 as pg

import cosim_toolbox.metadataDB as mDB

logger = logging.getLogger(__name__)

# TODO: The databases referenced in these APIs should be "metadata"
# and "time_series" and should be updated across the codebase.

# TODO: Does this HELICS stuff need to stay in here? If so, make it a 
# comment (not a string) and add explanation for why it's here.
"""
    HELICS_DATA_TYPE_UNKNOWN = -1,
    /** a sequence of characters*/
    HELICS_DATA_TYPE_STRING = 0,
    /** a double precision floating point number*/
    HELICS_DATA_TYPE_DOUBLE = 1,
    /** a 64 bit integer*/
    HELICS_DATA_TYPE_INT = 2,
    /** a pair of doubles representing a complex number*/
    HELICS_DATA_TYPE_COMPLEX = 3,
    /** an array of doubles*/
    HELICS_DATA_TYPE_VECTOR = 4,
    /** a complex vector object*/
    HELICS_DATA_TYPE_COMPLEX_VECTOR = 5,
    /** a named point consisting of a string and a double*/
    HELICS_DATA_TYPE_NAMED_POINT = 6,
    /** a boolean data type*/
    HELICS_DATA_TYPE_BOOLEAN = 7,
    /** time data type*/
    HELICS_DATA_TYPE_TIME = 8,
    /** raw data type*/
    HELICS_DATA_TYPE_RAW = 25,
    /** type converts to a valid json string*/
    HELICS_DATA_TYPE_JSON = 30,
    /** the data type can change*/
    HELICS_DATA_TYPE_MULTI = 33,
    /** open type that can be anything*/
    HELICS_DATA_TYPE_ANY = 25262
"""


class DataLogger:
    """Methos for writing to and reading from the time-series database. This
    class does not provide HELICS federate functionality.

    Returns:
        None
    """
    hdt_type = {'HDT_STRING': 'text',
                'HDT_DOUBLE': 'double precision',
                'HDT_INTEGER': 'bigint',
                'HDT_COMPLEX': 'VARCHAR (30)',
                'HDT_VECTOR': 'text',
                'HDT_COMPLEX_VECTOR': 'text',
                'HDT_NAMED_POINT': 'VARCHAR (255)',
                'HDT_BOOLEAN': 'boolean',
                'HDT_TIME': 'TIMESTAMP',
                'HDT_JSON': 'text'}

    def __init__(self):
        self.federation: dict = None
        self.federation_name: str = None
        self.scenario: dict = None
        self.scenario_name: str = None
        self.meta_db: mDB.MetaDB = None
        self.data_db = None

    def _connect_logger_database(self, connection: dict = None):
        """This method defines and then opens a connection to the datalogger 
        database
        

        Returns:
            psycopg2 connection object - connection object that provides
            access to the postgres database
        """
        if connection is None:
            connection = {
                "host": environ.get("POSTGRES_HOST", "localhost"),
                "port": environ.get("POSTGRES_PORT", 5432),
                "dbname": environ.get("COSIM_DB", "copper"),
                "user": environ.get("COSIM_USER", "worker"),
                "password": environ.get("COSIM_PASSWORD", "worker")
            }
        logger.info(connection)
        try:
            return pg.connect(**connection)
        except:
            return None

    def _connect_scenario_database(self, connection: dict = None):
        """This function defines and then opens a connection to the metadata
        database

        Returns:
            metadataDB object - connection object that provides
            access to the mongo database
        """
        if connection is None:
            connection = {
                "host": environ.get("MONGO_HOST", "mongo://localhost"),
                "port": environ.get("MONGO_POST", 27017),
                "dbname": environ.get("COSIM_DB", "copper"),
                "user": environ.get("COSIM_USER", "worker"),
                "password": environ.get("COSIM_PASSWORD", "worker")
            }
        logger.info(connection)
        try:
            uri = f"{connection['host']}:{connection['port']}"
            return mDB.MetaDB(uri=uri, db_name=connection["dbname"])
        except Exception:
            logger.exception("Failed to create MetaDB instance.")
            return None

    def close_database_connections(self, commit: bool = True) -> None:
        """Closes connections to the the time-series and metadata databases

        Args:
            commit (bool, optional): Flag to indicate whether data should be
            committed to the time-series DB prior to closing the connection.
            Defaults to True.
        """
        self.meta_db = None
        if self.data_db:
            if commit:
                self.data_db.commit()
            self.data_db.close()
        self.data_db = None

    def open_database_connections(self, meta_connection: dict = None, data_connection: dict = None) -> bool:
        """Opens connections to the time-series and metadata databases

        Args:
            meta_connection (dict, optional): Defines connection to metadata
            database. Defaults to None.
            data_connection (dict, optional): Defines connection to time-series
            database. Defaults to None.

        Returns:
            bool: _description_
        """
        self.meta_db = self._connect_scenario_database(meta_connection)
        self.data_db = self._connect_logger_database(data_connection)
        if self.meta_db is None or self.data_db is None:
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
        query = f"CREATE SCHEMA IF NOT EXISTS {scheme_name};"
        query += f" GRANT USAGE ON SCHEMA {scheme_name} TO reader;"
        with self.data_db.cursor() as cur:
            cur.execute(query)

    def drop_schema(self, scheme_name: str) -> None:
        """Removes the scheme from the database.

        Args:
            scheme_name (str): _description_
        """
        query = f"DROP SCHEMA IF EXISTS {scheme_name} CASCADE;"
        with self.data_db.cursor() as cur:
            cur.execute(query)

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

    def table_exist(self, analysis_name: str, table_name: str) -> None:
        """Checks to see if the specified tables exist in the specified analysis

        Args:
            analysis_name (str): Name of analysis where table may exist
            table_name (str): Table name whose existance is being checked

        Returns:
            _type_: _description_
        """
        query = ("SELECT EXISTS ( SELECT FROM pg_tables WHERE "
                 f"schemaname = '{analysis_name}' AND tablename = '{table_name}');")
        with self.data_db.cursor() as cur:
            cur.execute(query)
            result = cur.fetchone()
            return result[0]

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
                      "sim_name VARCHAR (255) NOT NULL, "
                      f"sim_value {self.hdt_type[key]} NOT NULL);")
        query += f" GRANT SELECT ON ALL TABLES IN SCHEMA {analysis_name} TO reader;"
        query += f" GRANT USAGE ON ALL SEQUENCES IN SCHEMA {analysis_name} TO reader;"
        query += f" GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {analysis_name} TO reader;"
        query += f" ALTER ROLE reader SET search_path = {analysis_name};"
        with self.data_db.cursor() as cur:
            cur.execute(query)

    def get_scenario_document(self, scenario_name: str) -> dict:
        """Gets the metadata associated with the specified scenario from the
        metadata database.

        TODO: Rename "get_scenario_document" to "get_scenario_metadata"
        Args:
            scenario_name (str): Name of scenario for which the metadata
            is to be retrieved

        Returns:
            dict: scenario metadata requested
        """
        if self.scenario_name != scenario_name:
            self.scenario = self.meta_db.get_dict(mDB.cu_scenarios, None, scenario_name)
        return self.scenario

    def get_federation_document(self, federation_name: str) -> dict:
        """Gets the metadata for the specified federation from the metadata
        database.

        TODO: Rename "get_federation_document" to "get_federation_metadata"
        Args:
            federation_name (str): Name of federation for which the metdata
            is being collected

        Returns:
            dict: Requested metadata for federation
        """
        if self.federation_name != federation_name:
            self.federation = self.meta_db.get_dict(mDB.cu_federations, None, federation_name)
        return self.federation

    def get_select_string(self, scheme_name: str, data_type: str) -> str:
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

    def get_time_select_string(self, start_time: int, duration: int) -> str:
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
                         sim_name: str, 
                         data_type: str) -> str:
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
            sim_name (string) - the name of the data to filter the query results by. If
            None is entered for the sim_name the query will not use sim_name as a filter
            data_type (string) - the id of the database table that will be queried. Must be
            one of the following options:
                [ hdt_boolean, hdt_complex, hdt_complex_vector, hdt_double, hdt_integer
                hdt_json, hdt_named_point, hdt_string, hdt_time, hdt_vector ]

        Returns:
            qry_string (string) - string representing the query to be used in pulling time series
            data from logger database
        """
        scheme = self.get_scenario_document(scenario_name)
        scheme_name = scheme["schema"]
        qry_string = self.get_select_string(scheme_name, data_type)
        time_string = self.get_time_select_string(start_time, duration)
        scenario_string = f"scenario='{scenario_name}'" if scenario_name is not None and scenario_name != "" else ""
        federate_string = f"federate='{federate_name}'" if federate_name is not None and federate_name != "" else ""
        data_string = f"sim_name='{sim_name}'" if sim_name is not None and sim_name != "" else ""
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
                                      sim_name: str, 
                                      data_type: str) -> pd.DataFrame:
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
            sim_name (string) - the name of the data to filter the query results by. If
            None is entered for the sim_name the query will not use sim_name as a filter
            data_type (string) - the id of the database table that will be queried. Must be
            one of the following options:
                [ hdt_boolean, hdt_complex, hdt_complex_vector, hdt_double, hdt_int
                hdt_json, hdt_named_point, hdt_string, hdt_time, hdt_vector ]

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        qry_string = self.get_query_string(start_time, duration, scenario_name, federate_name, sim_name, data_type)
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    def query_scenario_all_times(self, scenario_name: str, data_type: str) -> pd.DataFrame:
        """This method queries data from the logger database filtered only by scenario_name and sim_name

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
        scheme = self.get_scenario_document(scenario_name)
        scheme_name = scheme["schema"]
        qry_string = f"SELECT * FROM {scheme_name}.{data_type} WHERE scenario='{scenario_name}'"
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    def query_scheme_all_times(self, scheme_name: str, data_type: str) -> None:
        pass

    def query_scheme_federate_all_times(self, scheme_name: str, federate_name: str, data_type) -> pd.DataFrame:
        """This method queries data from the logger database filtered only by federate_name and sim_name
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
        qry_string = f"SELECT * FROM {scheme_name}.{data_type} WHERE federate='{federate_name}'";
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    def get_schema_list(self) -> None:
        # Todo: get schema from scenario documents
        pass

    def get_scenario_list(self, scheme_name: str, data_type: str) -> pd.DataFrame:
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

    def get_federate_list(self, scheme_name: str, data_type: str) -> pd.DataFrame:
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

    def get_sim_name_list(self, scheme_name: str, data_type: str) -> pd.DataFrame:
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
        qry_string = f"SELECT DISTINCT sim_name FROM {scheme_name}.{data_type};"
        with self.data_db.cursor() as cur:
            cur.execute(qry_string)
            column_names = ["sim_name"]
            data = cur.fetchall()
            dataframe = pd.DataFrame(data, columns=column_names)
            return dataframe

    def get_time_range(self, scheme_name: str, data_type: str, scenario_name: str, federate_name: str) -> pd.DataFrame:
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

    def set_time_stamps(self, dataframe: pd.DataFrame, date_time: str):
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
            time_list.append(date_time + dt.timedelta(seconds=sec_time))
        dataframe['time_stamp'] = time_list
        ts = dataframe.set_index('time_stamp')
        return ts


if __name__ == "__main__":
    d_time = dt.datetime.now()
    logger_data = DataLogger()
    logger_data.open_database_connections()
    t_mongo_data = logger_data.meta_db
    print(t_mongo_data)
    df = logger_data.query_scenario_federate_times(500, 1000, "test_scenario", "Battery",
                                                   "Battery/current3", "hdt_boolean")
    print(df)
    logger_data.close_database_connections()

    # TODO: If we don't need this code any more we should delete it.
    # t_data = db.scenario()
    # print(db)
    # df = get_scenario_list("test_scenario", "hdt_boolean")
    # print(df)
    # df = get_federate_list("test_scenario", "hdt_boolean")
    # print(df)
    # df = get_sim_name_list("test_scenario", "hdt_boolean")
    # print(df)
    # df = get_table_data(conn, "hdt_string")
    # df = query_time_series(780, 250, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_string")
    # df = query_time_series(None, 1000, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_boolean")
    # print(df)
    # df = query_time_series(None, 1000, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_int")
    # print(df)
    # df = query_time_series(None, 1000, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_double")
    # print(df)
    # df = query_time_series(None, 1000, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_complex")
    # print(df)
    # df = query_time_series(None, 1000, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_complex_vector")
    # print(df)
    # df = query_time_series(None, 1000, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_string")
    # print(df)
    # df = query_time_series(None, 1000, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_json")
    # print(df)
    # df = query_time_series(None, 1000, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_vector")
    # print(df)
    # df = query_time_series(None, 1000, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_time")
    # print(df)
    # df = query_time_series(None, 1000, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_named_point")
    # print(df)
    # df = query_time_series(25000, None, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_boolean")
    # df = query_time_series(None, 1020, "test_scenario", "FederateLogger", "EVehicle/voltage4", "hdt_string")
    # print(df)
