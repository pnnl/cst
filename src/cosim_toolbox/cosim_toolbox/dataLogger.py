"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based data logger in
Co-Simulation Toolbox.

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
    hdt_type = {'HDT_STRING': 'text',
                'HDT_DOUBLE': 'double precision',
                'HDT_INT': 'bigint',
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

    def _connect_logger_database(self, connection: dict = None) -> object | None:
        """This function defines the connection to the datalogger database
        and opens a connection to the postgres database

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

    def _connect_scenario_database(self, connection: dict = None) -> mDB.MetaDB | None:
        """This function defines the connection to the meta database
        and opens a connection to the mongo database

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
            # TODO use connection correctly
            return mDB.MetaDB()
        except:
            return None

    def close_database_connections(self, commit: bool = True) -> None:
        self.meta_db = None
        if commit:
            self.data_db.commit()
        self.data_db.close()

    def open_database_connections(self, meta_connection: dict = None, data_connection: dict = None) -> bool:
        self.meta_db = self._connect_scenario_database(meta_connection)
        self.data_db = self._connect_logger_database(data_connection)
        if self.meta_db is None or self.data_db is None:
            return False
        else:
            return True

    def check_version(self) -> None:
        cur = self.data_db.cursor()
        logger.info('PostgresSQL database version:')
        cur.execute('SELECT version()')
        # display the PostgresSQL database server version
        db_version = cur.fetchone()
        logger.info(db_version)
        # close the communication with the PostgresSQL
        cur.close()

    def create_schema(self, scheme_name: str) -> None:
        query = "CREATE SCHEMA IF NOT EXISTS " + scheme_name + ";"
        cur = self.data_db.cursor()
        cur.execute(query)
        cur.close()

    def drop_schema(self, scheme_name: str) -> None:
        query = "DROP SCHEMA IF EXISTS " + scheme_name + ";"
        cur = self.data_db.cursor()
        cur.execute(query)
        cur.close()

    def remove_scenario(self, scheme_name: str, scenario_name: str) -> None:
        query = ""
        for key in self.hdt_type:
            query += f"DELETE FROM {scheme_name}.{key} WHERE scenario='{scenario_name}'; "
        cur = self.data_db.cursor()
        cur.execute(query)
        cur.close()

    def table_exist(self, scheme_name: str, table_name: str) -> None:
        query = ("SELECT EXISTS ( SELECT FROM pg_tables WHERE "
                 "schemaname = '" + scheme_name + "' AND tablename = '" + table_name + "');")
        cur = self.data_db.cursor()
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        return result[0]

    def make_logger_database(self, scheme_name: str) -> None:
        # scheme is a set of like scenario (like DSOT bau, battery, flex load)
        query = ""
        for key in self.hdt_type:
            query += ("CREATE TABLE IF NOT EXISTS "
                      f"{scheme_name}.{key} ("
                      "time double precision NOT NULL, "
                      "scenario VARCHAR (255) NOT NULL, "
                      "federate VARCHAR (255) NOT NULL, "
                      "data_name VARCHAR (255) NOT NULL, "
                      f"data_value {self.hdt_type[key]} NOT NULL);")
        cur = self.data_db.cursor()
        cur.execute(query)
        cur.close()

    def get_scenario_document(self, scenario_name: str) -> dict:
        if self.scenario_name != scenario_name:
            self.scenario = self.meta_db.get_dict(mDB.cu_scenarios, None, scenario_name)
        return self.scenario

    def get_federation_document(self, federation_name: str) -> dict:
        if self.federation_name != federation_name:
            self.federation = self.meta_db.get_dict(mDB.cu_federations, None, federation_name)
        return self.federation

    def get_select_string(self, scheme_name: str, data_type: str) -> str | None:
        """This function creates the SELECT portion of the query string

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
        """This function creates the time filter portion of the query string

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
            'time>=start_time AND time<= end_time'
        """
        if start_time is None and duration is None:
            return ""
        elif start_time is not None and duration is None:
            return "time>=" + str(start_time)
        elif start_time is None and duration is not None:
            return "time<=" + str(duration)
        else:
            end_time = start_time + duration
        return "time>=" + str(start_time) + " AND time<=" + str(end_time)

    def get_scenario_select_string(self, scenario_name: str) -> str:
        """This function creates the scenario filter portion of the query string

        Args:
            scenario_name (string) - the name of the scenario which the data will be filtered on
            If None is entered, data will not be filtered based upon the scenario field

        Returns:
            qry_string (string) - string containing the scenario filter portion of the sql query
            'scenario=scenario'
        """
        if scenario_name is None or scenario_name == "":
            return ""
        return f"scenario='{scenario_name}'"

    def get_federate_select_string(self, federate_name: str) -> str:
        """This function creates the federate filter portion of the query string

        Args:
            federate_name (string) - the name of the Federate which the data will be filtered on
            If None is entered, data will not be filtered based upon the federate field

        Returns:
            qry_string (string) - string containing the federate filter portion of the sql query
            'federate=federate_name'
        """
        if federate_name is None or federate_name == "":
            return ""
        return f"federate='{federate_name}'"

    def get_data_name_select_string(self, data_name: str) -> str:
        """This function creates the data_name filter portion of the query string

        Args:
            data_name (string) - the name of the data which will be used to filter the return data
            If None is entered, data will not be filtered based upon the data_name field

        Returns:
            qry_string (string) - string containing the data_name filter portion of the sql query
            'data_name=data_name'
        """
        if data_name is None or data_name == "":
            return ""
        return f"data_name='{data_name}'"

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
                [ hdt_boolean, hdt_complex, hdt_complex_vector, hdt_double, hdt_int
                hdt_json, hdt_named_point, hdt_string, hdt_time, hdt_vector ]

        Returns:
            qry_string (string) - string representing the query to be used in pulling time series
            data from logger database
        """
        scheme = self.get_scenario_document(scenario_name)
        scheme_name = scheme["schema"]
        qry_string = self.get_select_string(scheme_name, data_type)
        time_string = self.get_time_select_string(start_time, duration)
        scenario_string = self.get_scenario_select_string(scenario_name)
        federate_string = self.get_federate_select_string(federate_name)
        data_string = self.get_data_name_select_string(data_name)
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
                                      data_type: str) -> pd.DataFrame:
        """This function queries time series data from the logger database and
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
        cur = self.data_db.cursor()
        cur.execute(qry_string)
        column_names = [desc[0] for desc in cur.description]
        data = cur.fetchall()
        dataframe = pd.DataFrame(data, columns=column_names)
        return dataframe

    def query_scenario_all_times(self, scenario_name: str, data_type: str) -> pd.DataFrame:
        """This function queries data from the logger database filtered only by scenario_name and data_name

        Args:
            scenario_name (string) - the name of the scenario to filter the query results by
            data_type (string) - the id of the database table that will be queried. Must be

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        scheme = self.get_scenario_document(scenario_name)
        scheme_name = scheme["schema"]
        cur = self.data_db.cursor()
        qry_string = ("SELECT * FROM " + scheme_name + "." + data_type +
                      " WHERE Scenario='" + scenario_name + "'")
        cur.execute(qry_string)
        column_names = [desc[0] for desc in cur.description]
        data = cur.fetchall()
        dataframe = pd.DataFrame(data, columns=column_names)
        return dataframe

    def query_scheme_all_times(self, scheme_name: str, data_type: str) -> None:
        pass

    def query_scheme_federate_all_times(self, scheme_name: str, federate_name: str, data_type) -> pd.DataFrame | None:
        """This function queries data from the logger database filtered only by federate_name and data_name
        and data_type

        Args:
            scheme_name (string) - the name of the schema to filter the query results by
            federate_name (string) - the name of the Federate to filter the query results by
            data_type (string) - the id of the database table that will be queried. Must be

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if (scheme_name is None) or (federate_name is None) or (data_type is None):
            return None
        cur = self.data_db.cursor()
        # Todo: check against meta_db to see if schema name exist?
        qry_string = ("SELECT * FROM " + scheme_name + "." + data_type +
                      " WHERE Federate='" + federate_name + "'")
        cur.execute(qry_string)
        column_names = [desc[0] for desc in cur.description]
        data = cur.fetchall()
        dataframe = pd.DataFrame(data, columns=column_names)
        return dataframe

    def get_schema_list(self) -> None:
        # Todo: get schema from scenario documents
        pass

    def get_scenario_list(self, scheme_name: str, data_type: str) -> pd.DataFrame | None:
        """This function queries the distinct list of scenario names from the database table
        defined by scheme_name and data_type

        Args:
            scheme_name (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried. 

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if (scheme_name is None) or (data_type is None):
            return None
        # Todo: check against meta_db to see if schema name exist?
        # This should take from the meta documents and verify
        qry_string = "SELECT DISTINCT scenario FROM " + scheme_name + "." + data_type
        cur = self.data_db.cursor()
        cur.execute(qry_string)
        column_names = ["scenario"]
        data = cur.fetchall()
        dataframe = pd.DataFrame(data, columns=column_names)
        return dataframe

    def get_federate_list(self, scheme_name: str, data_type: str) -> pd.DataFrame | None:
        """This function queries the distinct list of federate names from the database table
        defined by scheme_name and data_type

        Args:
            scheme_name (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried. 

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if (scheme_name is None) or (data_type is None):
            return None
        # Todo: check against meta_db to see if schema name exist?
        qry_string = "SELECT DISTINCT federate FROM " + scheme_name + "." + data_type
        cur = self.data_db.cursor()
        cur.execute(qry_string)
        column_names = ["federate"]
        data = cur.fetchall()
        dataframe = pd.DataFrame(data, columns=column_names)
        return dataframe

    def get_data_name_list(self, scheme_name: str, data_type: str) -> pd.DataFrame | None:
        """This function queries the distinct list of data names from the database table
        defined by scheme_name and data_type

        Args:
            scheme_name (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried. Must be

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if (scheme_name is None) or (data_type is None):
            return None
        # Todo: check against meta_db to see if schema name exist?
        qry_string = "SELECT DISTINCT data_name FROM " + scheme_name + "." + data_type
        cur = self.data_db.cursor()
        cur.execute(qry_string)
        column_names = ["data_name"]
        data = cur.fetchall()
        dataframe = pd.DataFrame(data, columns=column_names)
        return dataframe

    def get_time_range(self, scheme_name: str, data_type: str, scenario_name: str, federate_name: str) -> pd.DataFrame | None:
        """This function queries the minimum and maximum of time from the database
            table defined by scheme_name, data_type, scenario_name, and federate

        Args:
            scheme_name (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried. Must be
            scenario_name (string) - the name of the scenario to filter the query results by
            federate_name (string) - the name of the Federate to filter the query results by

        Returns:
            dataframe (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        qry_string = ""
        if (scheme_name is None) or (data_type is None):
            return None
        if (scenario_name is None) and (federate_name is None):
            return None
        if scenario_name is not None and federate_name is None:
            qry_string = ("SELECT MIN(time), MAX(time) FROM " + scheme_name + "." + data_type +
                          " WHERE scenario='" + scenario_name + "'")
        if federate_name is not None and scenario_name is None:
            qry_string = ("SELECT MIN(time), MAX(time) FROM " + scheme_name + "." + data_type +
                          " WHERE federate='" + federate_name + "'")
        if scenario_name is not None and federate_name is not None:
            qry_string = ("SELECT MIN(time), MAX(time) FROM " + scheme_name + "." + data_type +
                          " WHERE federate='" + federate_name + "' AND scenario='" + scenario_name + "'")
        cur = self.data_db.cursor()
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
    df = logger_data.query_scenario_federate_times(500, 1000, "test_Scenario", "DataLogger",
                                                   "Battery/current3", "hdt_boolean")
    print(df)
    logger_data.close_database_connections()

    # t_data = db.scenario()
    # print(db)
    # df = get_scenario_list("test_Scenario", "hdt_boolean")
    # print(df)
    # df = get_federate_list("test_Scenario", "hdt_boolean")
    # print(df)
    # df = get_data_name_list("test_Scenario", "hdt_boolean")
    # print(df)
    # df = get_table_data(conn, "hdt_string")
    # df = query_time_series(780, 250, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_string")
    # df = query_time_series(None, 1000, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_boolean")
    # print(df)
    # df = query_time_series(None, 1000, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_int")
    # print(df)
    # df = query_time_series(None, 1000, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_double")
    # print(df)
    # df = query_time_series(None, 1000, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_complex")
    # print(df)
    # df = query_time_series(None, 1000, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_complex_vector")
    # print(df)
    # df = query_time_series(None, 1000, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_string")
    # print(df)
    # df = query_time_series(None, 1000, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_json")
    # print(df)
    # df = query_time_series(None, 1000, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_vector")
    # print(df)
    # df = query_time_series(None, 1000, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_time")
    # print(df)
    # df = query_time_series(None, 1000, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_named_point")
    # print(df)
    # df = query_time_series(25000, None, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_boolean")
    # df = query_time_series(None, 1020, "test_Scenario", "FederateLogger", "EVehicle/voltage4", "hdt_string")
    # print(df)
