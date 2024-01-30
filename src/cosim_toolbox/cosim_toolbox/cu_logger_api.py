import os
import sys

import psycopg2 as psy
import pandas   as pd
import numpy    as np
import datetime as dt
from pymongo import MongoClient
from cosim_toolbox.metadataDB import MetaDB

# from pathlib import Path

# sys.path.insert(1, os.path.join(Path(__file__).parent, '..', '..', 'src'))



class Cu_Logger_Data_API:





    def __init__(self):
        self.cu_uri = 'mongodb://gage.pnl.gov:27017'
        self.cu_database = "copper"
        self.cu_federations = "federations"
        self.cu_scenarios = "scenarios"
        self.cu_logger = "cu_logger"
        self.logger_host_name = "gage"
        self.logger_db_name = "copper"
        self.logger_user_name = "postgres"
        self.logger_pssword = "postgres"
        self.logger_port_id = 5432
        self.mongo_connection = None
        self.logger_db_conn = None

    def connect_logger_database(self):
        """This function defines the connection to the logger database
        and opens a connection to the postgres database

        Args:
            host_name (string) - the host name of the database server
            db_name (string) - the name of the database
            user_name (string) - the user name to be used for the connection
            pssword (string) - the pass word used to connect to the database
            port_id (integer) - the id of the port to be used by the connection

        Returns:
            db_conn (psycog2 connection object) - connection object that provides
            access to the postgres database
        """
        connection = {
            "host": self.logger_host_name,
            "dbname": self.logger_db_name,
            "user": self.logger_user_name,
            "password": self.logger_pssword,
            "port": self.logger_port_id
        }
        print(connection)
        self.logger_db_conn = None
        try:
            self.logger_db_conn = psy.connect(**connection)
        except:
            return None
        return self.logger_db_conn

    def connect_scenario_database(self):
        self.mongo_connection = MetaDB(self.cu_uri, self.cu_database)
        return self.mongo_connection

    def close_database_connections(self):
        self.logger_db_conn.close()
        #self.mongo_connection.close()

    def open_database_connections(self):
        self.connect_logger_database()
        self.connect_scenario_database()



# def open_logger(host_name, db_name, user_name, pssword, port_id):
#     """This function defines the connection to the logger database
#         and opens a connection to the postgres database

#     Args:
#         host_name (string) - the host name of the database server
#         db_name (string) - the name of the database
#         user_name (string) - the user name to be used for the connection
#         pssword (string) - the pass word used to connect to the database
#         port_id (integer) - the id of the port to be used by the connection

#     Returns:
#         db_conn (psycog2 connection object) - connection object that provides
#         access to the postgres database
#     """
#     connection = {
#         "host": host_name,
#         "dbname": db_name,
#         "user": user_name,
#         "password": pssword,
#         "port": port_id
#     }
#     print(connection)
#     conn = None
#     try:
#         conn = psy.connect(**connection)
#     except:
#         return
#     return conn

    def get_select_string(self, s_schema, data_type):
        """This function creates the SELECT portion of the query string

        Args:
            s_schema (string) - the name of the database to be queried
            data_type (string) - the name of the database table to be queried

        Returns:
            qry_string (string) - string containing the select portion of the sql query
            'SELECT * FROM s_schema.data_type WHERE'
        """
        if s_schema is None or s_schema == "":
            return None
        if data_type is None or data_type == "":
            return None
        qry_string = "SELECT * FROM " + s_schema + "." + data_type + " WHERE "
        return qry_string

    def get_time_select_string(self, start_time, duration):
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

    def get_scenario_select_string(self, scenario_name):
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
        return "scenario=" + "'" + scenario_name + "'"

    def get_federate_select_string(self, federate_name):
        """This function creates the federate filter portion of the query string

        Args:
            federate_name (string) - the name of the federate which the data will be filtered on
            If None is entered, data will not be filtered based upon the federate field

        Returns:
            qry_string (string) - string containing the federate filter portion of the sql query
            'federate=federate_name'
        """
        if federate_name is None or federate_name == "":
            return ""
        return "federate=" + "'" + federate_name + "'"

    def get_data_name_select_string(self, data_name):
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
        return "data_name=" + "'" + data_name + "'"


    def get_query_string(self, s_schema, start_time, duration, scenario_name, federate_name, data_name, data_type):
        """This function creates the query string to pull time series data from the logger database dependent upon the keys identified by the 
        user in input arguments.

        Args:
            s_schema (string) - the name of the logger database to be queried
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
            federate_name (string) - the name of the federate to filter the query results by. If
            None is entered for the federate_name the query will not use federate_name as a filter
            data_name (string) - the name of the data to filter the query results by. If
            None is entered for the data_name the query will not use data_name as a filter
            data_type (string) - the id of the database table that will be queried. Must be
            one of the following options:
                hdt_boolean
                hdt_complex
                hdt_complex_vector
                hdt_double
                hdt_int
                hdt_json
                hdt_named_point
                hdt_string
                hdt_time
                hdt_vector

        Returns:
            qry_string (string) - string representing the query to be used in pulling time series
            data from logger database
        """
        qry_string = self.get_select_string(s_schema, data_type)
        time_string = self.get_time_select_string(start_time, duration)
        scenario_string = self.get_scenario_select_string(scenario_name)
        federate_string = self.get_federate_select_string(federate_name)
        data_string = self.get_data_name_select_string(data_name)
        if time_string == "" and scenario_string == "" and federate_string == "" and data_string == "":
            qry_string = qry_string.replace(" WHERE ","")
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


    def query_logger_time_dataframe(self, s_schema, start_time, duration, scenario_name, federate_name, data_name, data_type):
        """This function queries time series data from the logger database dependent upon the keys identified by the 
        user in input arguments.

        Args:
            db_conn (psycog2 connection object) - connection object that provides
            access to the postgres database
            s_schema (string) - the name of the logger database to be queried
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
            federate_name (string) - the name of the federate to filter the query results by. If
            None is entered for the federate_name the query will not use federate_name as a filter
            data_name (string) - the name of the data to filter the query results by. If
            None is entered for the data_name the query will not use data_name as a filter
            data_type (string) - the id of the database table that will be queried. Must be
            one of the following options:
                hdt_boolean
                hdt_complex
                hdt_complex_vector
                hdt_double
                hdt_int
                hdt_json
                hdt_named_point
                hdt_string
                hdt_time
                hdt_vector

        Returns:
            df (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        cur = self.logger_db_conn.cursor()
        qry_string = self.get_query_string(s_schema, start_time, duration, scenario_name, federate_name, data_name, data_type)
        no_time = False
        print(qry_string)
        cur.execute(qry_string)
        column_names = [desc[0] for desc in cur.description]
        data = cur.fetchall()
        df = pd.DataFrame(data, columns=column_names)
        return df


    def query_logger_scenario_all_times(self, s_schema, scenario_name, data_type):
        """This function queries data from the logger database filtered only by scenario_name and data_name

        Args:
            db_conn (psycog2 connection object) - connection object that provides
            access to the postgres database
            scenario_name (string) - the name of the scenario to filter the query results by
            data_name (string) - the name of the data which will be used to filter the return data
            data_type (string) - the id of the database table that will be queried. Must be

        Returns:
            df (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        
        cur = self.logger_db_conn.cursor()
        qry_string = "SELECT * FROM " + s_schema + "." +data_type + " WHERE Scenario='" + scenario_name + "'"
        cur.execute(qry_string)
        column_names = [desc[0] for desc in cur.description]
        data = cur.fetchall()
        df = pd.DataFrame(data, columns=column_names)
        return df


    def query_logger_federate_all_times(self, s_schema, federate_name, data_type):
        """This function queries data from the logger database filtered only by federate_name and data_name
        and data_type

        Args:
            db_conn (psycog2 connection object) - connection object that provides
            access to the postgres database
            federate_name (string) - the name of the federate to filter the query results by
            data_name (string) - the name of the data which will be used to filter the return data
            data_type (string) - the id of the database table that will be queried. Must be

        Returns:
            df (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        cur = self.logger_db_conn.cursor()
        qry_string = "SELECT * FROM " + s_schema + "." + data_type + " WHERE Federate='" + federate_name +"'"
        cur.execute(qry_string)
        column_names = [desc[0] for desc in cur.description]
        data = cur.fetchall()
        df = pd.DataFrame(data, columns=column_names)
        return df


    def get_scenario_list(self, s_schema, data_type):
        """This function queries the distinct list of scenario names from the database table
        defined by s_schema and data_type

        Args:
            conn (psycog2 connection object) - connection object that provides
            access to the postgres database
            s_schema (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried. 

        Returns:
            df (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if s_schema is None:
            return None
        if data_type is None:
            return None
        qry_string = "SELECT DISTINCT scenario FROM " + s_schema + "." + data_type 
        cur =  self.logger_db_conn.cursor()
        cur.execute(qry_string)
        column_names = ["scenario"]
        data = cur.fetchall()
        df = pd.DataFrame(data, columns=column_names)
        return df

    def get_federate_list(self, s_schema, data_type):
        """This function queries the distinct list of federate names from the database table
        defined by s_schema and data_type

        Args:
            conn (psycog2 connection object) - connection object that provides
            access to the postgres database
            s_schema (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried. 

        Returns:
            df (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if s_schema is None:
            return None
        if data_type is None:
            return None
        qry_string = "SELECT DISTINCT federate FROM " + s_schema + "." + data_type 
        cur =  self.logger_db_conn.cursor()
        cur.execute(qry_string)
        column_names = ["federate"]
        data = cur.fetchall()
        df = pd.DataFrame(data, columns=column_names)
        return df

    def get_data_name_list(self, s_schema, data_type):
        """This function queries the distinct list of data names from the database table
        defined by s_schema and data_type

        Args:
            conn (psycog2 connection object) - connection object that provides
            access to the postgres database
            s_schema (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried. Must be

        Returns:
            df (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if s_schema is None:
            return None
        if data_type is None:
            return None
        qry_string = "SELECT DISTINCT data_name FROM " + s_schema + "." + data_type 
        cur =  self.logger_db_conn.cursor()
        cur.execute(qry_string)
        column_names = ["data_name"]
        data = cur.fetchall()
        df = pd.DataFrame(data, columns=column_names)
        return df

    def get_time_range(self, s_schema, data_type, scenario, federate):
        """This function queries the minimum and maximum of time from the database
            table defined by s_schema, data_type, scenario, and federate

        Args:
            conn (psycog2 connection object) - connection object that provides
            access to the postgres database
            s_schema (string) - the name of the schema to filter the query results by
            data_type (string) - the id of the database table that will be queried. Must be
            data_type (string) - the id of the database table that will be queried. Must be
            data_type (string) - the id of the database table that will be queried. Must be

        Returns:
            df (pandas dataframe object) - dataframe that contains the result records
            returned from the query of the database
        """
        if s_schema is None:
            return None
        if data_type is None:
            return None
        if scenario is None and federate is None:
            return None
        if scenario is not None and federate is None:
            qry_string = "SELECT MIN(time), MAX(time) FROM " + s_schema + "." + data_type + " WHERE scenario='" + scenario + "'"
        if federate is not None and scenario is None:
            qry_string = "SELECT MIN(time), MAX(time) FROM " + s_schema + "." + data_type + " WHERE federate='" + federate + "'"
        if scenario is not None and federate is not None:
            qry_string = "SELECT MIN(time), MAX(time) FROM " + s_schema + "." + data_type + " WHERE federate='" + federate + "' AND scenario='" + scenario + "'"
        cur =  self.logger_db_conn.cursor()
        cur.execute(qry_string)
        column_names = ["min","max"]
        data = cur.fetchall()
        df = pd.DataFrame(data, columns=column_names)
        return df

    def set_time_stamps(self, df, date_time):
        """This function calculates the time stamp for each time step in the dataframe and adds them
            to the dataframe in a column named time_stamp

        Args:
            df (pandas dataframe) - the dataframe for which contains the time steps in seconds to 
            be used in the calculation of the time stamps
            date_time (datetime) - the base time stamp that will be used to calculate the time step
            time stamps

        Returns:
            ts(pandas time series) - time series that contains the result records
            returned from the query of the database
        """
        tdf = df
        time_list = []
        for x in range(len(df)):
            trow = df.iloc[x]
            sec_time = trow.time
            time_list.append(date_time + dt.timedelta(seconds=sec_time))
            t_date_time = time_list[x]
        df['time_stamp'] = time_list
        print(df)
        ts = df.set_index('time_stamp')
        return ts


        #time_list.append(df)
        

# cu_uri = 'mongodb://gage.pnl.gov:27017'
# cu_database = "copper"
# cu_federations = "federations"
# cu_scenarios = "scenarios"
# cu_logger = "cu_logger"

if __name__ == "__main__":
    #db =  open_scenario_database(cu_uri, cu_database)
    #conn = open_logger("gage", "copper", "postgres", "postgres", 5432)
    #df = query_logger_time_dataframe(conn,"test_myschema2",500,1000,"test_MyTest","DataLogger","Battery/current3","hdt_boolean")
    #conn.close()
    #db.close()
    #df2 = set_real_time(df, d_time)
    
    # scenario_name = "TE30"
    # schema_name = "Tesp"
    # federate_name = "BT1_EV1"

    #scenario_name = "TE100"

# cu_uri = 'mongodb://gage.pnl.gov:27017'
# cu_database = "copper"
# cu_federations = "federations"
# cu_scenarios = "scenarios"
# cu_logger = "cu_logger"



    d_time = dt.datetime.now()
    logger_data = Cu_Logger_Data_API()
    logger_data.open_database_connections()
    t_mongo_data = logger_data.mongo_connection.db
    print(t_mongo_data)
    df = logger_data.query_logger_time_dataframe("test_myschema2",500,1000,"test_MyTest","DataLogger","Battery/current3","hdt_boolean")
    print(df)
    logger_data.close_database_connections()





    #t_data = db.scenario()
    #print(db)
    # df = get_scenario_list(conn, "test_myschema2", "hdt_boolean")
    # print(df)
    # df = get_federate_list(conn, "test_myschema2", "hdt_boolean")
    # print(df)
    # df = get_data_name_list(conn, "test_myschema2", "hdt_boolean")
    # print(df)
#    df = get_table_data(conn, "hdt_string")
    # df = query_logger_time_series(conn, "test_myschema2", 780, 250, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_string")
    # df = query_logger_time_series(conn, "test_myschema2", None, 1000, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_boolean")
    # print(df)
    # df = query_logger_time_series(conn, "test_myschema2", None, 1000, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_int")
    # print(df)
    # df = query_logger_time_series(conn, "test_myschema2", None, 1000, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_double")
    # print(df)
    # df = query_logger_time_series(conn, "test_myschema2", None, 1000, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_complex")
    # print(df)
    # df = query_logger_time_series(conn, "test_myschema2", None, 1000, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_complex_vector")
    # print(df)
    # df = query_logger_time_series(conn, "test_myschema2", None, 1000, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_string")
    # print(df)
    # df = query_logger_time_series(conn, "test_myschema2", None, 1000, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_json")
    # print(df)
    # df = query_logger_time_series(conn, "test_myschema2", None, 1000, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_vector")
    # print(df)
    # df = query_logger_time_series(conn, "test_myschema2", None, 1000, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_time")
    # print(df)
    # df = query_logger_time_series(conn, "test_myschema2", None, 1000, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_named_point")
    # print(df)
    # df = query_logger_time_series(conn, "test_myschema2", 25000, None, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_boolean")
    #df = query_logger_time_series(conn, "test_myschema2", None, 1020, "test_MyTest", "DataLogger", "EVehicle/voltage4", "hdt_string")
    # print(df)











