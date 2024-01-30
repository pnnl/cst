"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""
from os import environ
import sys
import psycopg2

from cosim_toolbox.helics_config import HelicsMsg
from cosim_toolbox.federate import Federate


def open_logger():
    connection = {
        "host": environ.get("POSTGRES_HOST", "localhost"),
        "port": environ.get("POSTGRES_PORT", 5432),
        "dbname": environ.get("COSIM_DB", "copper"),
        "user": environ.get("COSIM_USER", "worker"),
        "password": environ.get("COSIM_PASSWORD", "worker")
    }
    print(connection)
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
    query = "CREATE SCHEMA IF NOT EXISTS " + schema_name + ";"
    cur = conn.cursor()
    cur.execute(query)
    cur.close()


def drop_schema(conn, schema_name: str):
    query = "DROP SCHEMA IF EXISTS " + schema_name + ";"
    cur = conn.cursor()
    cur.execute(query)
    cur.close()


class DataLogger(Federate):
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

    def __init__(self, fed_name="", schema_name="default", clear=True, **kwargs):
        super().__init__(fed_name, **kwargs)
        self.conn = open_logger()
        check_version(self.conn)
        self.schema_name = schema_name
        # uncomment debug
        # drop_schema(self.conn, self.schema_name)
        create_schema(self.conn, self.schema_name)
        self.make_logger_database()
        if clear:
            self.remove_scenario()
        self.conn.commit()

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

    def remove_scenario(self):
        query = ""
        for key in self.hdt_type:
            query += f"DELETE FROM {self.schema_name}.{key} WHERE scenario='{self.scenario_name}'; "
        cur = self.conn.cursor()
        cur.execute(query)
        cur.close()

    def create_table(self, table_name: str, data_type: str):
        return ("CREATE TABLE IF NOT EXISTS "
                f"{self.schema_name}.{table_name} ("
                "time double precision NOT NULL, "
                "scenario VARCHAR (255) NOT NULL, "
                "federate VARCHAR (255) NOT NULL, "
                "data_name VARCHAR (255) NOT NULL, "
                f"data_value {data_type} NOT NULL);")

    def make_logger_database(self):
        # scheme is a set of like scenario (like DSOT bau, battery, flex load)
        query = ""
        for key in self.hdt_type:
            query += self.create_table(key, self.hdt_type[key])
        cur = self.conn.cursor()
        cur.execute(query)
        cur.close()

    def connect_to_helics_config(self):
        self.federate_type = "combo"
        self.time_step = 30
        publications = []

        for fed in self.federation:
            config = self.federation[fed]["HELICS_config"]
            if "publications" in config.keys():
                for pub in config["publications"]:
                    publications.append(pub)

        t1 = HelicsMsg(self.federate_name, self.time_step)
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("terminate_on_error", True)
        if self.scenario["docker"]:
            t1.config("brokeraddress", "10.5.0.2")
        self.config = t1.config("subscriptions", publications)

    def update_internal_model(self):
        query = ""
        for key in self.data_from_federation["inputs"]:
            qry = ""
            value = self.data_from_federation["inputs"][key]
            for table in self.hdt_type.keys():
                if self.inputs[key]['type'].lower() in table.lower():
                    qry = (f"INSERT INTO {self.schema_name}.{table} (time, scenario, federate, data_name, data_value)"
                           f" VALUES({self.granted_time}, '{self.scenario_name}', '{self.federate_name}', '{key}', ")
                    if type(value) is str or type(value) is complex or type(value) is list:
                        qry += f" '{value}'); "
                    else:
                        qry += f" {value}); "
                    break
            query += qry

            # add to logger database
        try:
            if query != "":
                cur = self.conn.cursor()
                cur.execute(query)
                cur.close()
        except:
            print("Bad data type in update_internal_model")
        self.conn.commit()


def main(federate_name, schema_name, scenario_name):
    datalogger = DataLogger(federate_name, schema_name)
    datalogger.create_federate(scenario_name)
    datalogger.run_cosim_loop()
    datalogger.destroy_federate()
    if datalogger.conn:
        datalogger.conn.close()


if __name__ == "__main__":
    if sys.argv.__len__() > 3:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
