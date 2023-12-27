"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""
import os
import sys
import psycopg2
from pathlib import Path

sys.path.insert(1, os.path.join(Path(__file__).parent, '..', '..', 'src'))
from Federate import Federate


def open_logger():
    #    "host": os.environ.get("POSTGRES_HOST"),
    connection = {
        "host": "gage",
        "dbname": "copper",
        "user": "postgres",
        "password": "postgres",
        "port": 5432
    }
    try:
        return psycopg2.connect(**connection)
    except:
        return


def check_version(conn):
    cur = conn.cursor()
    print('PostgresSQL database version:')
    cur.execute('SELECT version()')
    # display the PostgresSQL database server version
    db_version = cur.fetchone()
    print(db_version)
    # close the communication with the PostgresSQL
    cur.close()


def write(conn, datatype, record):
    cur = conn.cursor()
    print('PostgresSQL database version:')
    cur.execute('SELECT ')
    # close the communication with the PostgresSQL
    cur.close()


def table_exist(conn, scheme_name: str, table_name: str):
    query = ("SELECT EXISTS ( SELECT FROM pg_tables WHERE "
             "schemaname = '" + scheme_name + "' AND tablename = '" + table_name + "');")
    cur = conn.cursor()
    cur.execute(query)
    result = cur.fetchone()
    cur.close()
    return result[0]


def create_schema(conn, schema_name: str):
    query = "CREATE SCHEMA " + schema_name + ";"
    cur = conn.cursor()
    cur.execute(query)
    cur.close()


def drop_schema(conn, schema_name: str):
    query = "DROP SCHEMA IF EXISTS " + schema_name + ";"
    cur = conn.cursor()
    cur.execute(query)
    cur.close()


class DataLogger(Federate):
    def __init__(self, fed_name="", **kwargs):
        super().__init__(fed_name="", **kwargs)
        self.conn = open_logger()
        check_version(self.conn)
        self.make_logger_database("mesp")


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

    def create_table(self, scheme_name: str, table_name: str, data_type: str):
        query = ("CREATE TABLE IF NOT EXISTS "
                 + scheme_name + "." + table_name +
                 "(time TIMESTAMP NOT NULL, "
                 "scenario VARCHAR (255) NOT NULL, "
                 "federate VARCHAR (255) NOT NULL, "
                 "data_name VARCHAR (255) NOT NULL, "
                 "data_value " + data_type + " NOT NULL);")
        cur = self.conn.cursor()
        cur.execute(query)
        cur.close()

    def make_logger_database(self, scheme_name: str):
        hdt_type = {'HDT_STRING': 'VARCHAR (255)',
                    'HDT_DOUBLE': 'double precision',
                    'HDT_INT': 'bigint',
                    'HDT_COMPLEX': 'VARCHAR (30)',
                    'HDT_VECTOR': 'VARCHAR (255)',
                    'HDT_COMPLEX_VECTOR': 'VARCHAR (255)',
                    'HDT_NAMED_POINT': 'VARCHAR (255)',
                    'HDT_BOOLEAN': 'boolean',
                    'HDT_TIME': 'TIMESTAMP',
                    'HDT_JSON': 'text'}
        # scheme is a set of like scenario (like DSOT bau, battery, flex load)
        for key in hdt_type:
            self.create_table(scheme_name, key, hdt_type[key])

    def update_internal_model(self):
        query = ""
        if len(self.data_from_federation["inputs"].keys()) >= 1:
            key = list(self.data_from_federation["inputs"].keys())[0]

            # add to logger database
            query += ("INSERT INTO {} (time, scenario, federate, data_name, data_value)"
                      "VALUES({}, {}, {}, {}, {})".format(table, time, scenario, federate, name, value))

        if query != "":
            cur = conn.cursor()
            cur.execute(query)
            cur.close()

        pass


if __name__ == "__main__":

    if sys.argv.__len__() > 1:
        my_conn = open_logger()
        check_version(my_conn)
        make_logger_database(my_conn, "mesp")

        mongo
        if self.fed_name == mDB.cu_logger:
            self.federate_type = "message"
            self.time_step = 30
            publications = []
            for fed in fed_def:
                config = fed_def[fed]["HELICS_config"]
                if "publications" in config.keys():
                    for pub in config["publications"]:
                        publications.append(pub)
            self.config = {
                "name": mDB.cu_logger,
                "period": 30,
                "log_level": "warning",
                "subscriptions": publications
            }

        test_fed = Fed.Federate("cu_logger")
        test_fed.create_federate(sys.argv[1])
        test_fed.update_internal_model = update_internal_model
        test_fed.run_cosim_loop()
        test_fed.destroy_federate()
