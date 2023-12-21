"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""
import os
import psycopg2

import Federate as Fed


def open_logger():
    #    "host": os.environ.get("POSTGRES_HOST"),
    connection = {
        "host": "gage",
        "dbname": "copper",
        "user": "postgres",
        "password": "postgres",
        "port": 5432
    }

#    with open(file_name, 'r', encoding='utf-8') as json_file:
#        config = json.load(json_file)
    conn = None
    try:
        conn = psycopg2.connect(**connection)
    except:
        return
    return conn


def check_version():
    cur = conn.cursor()
    print('PostgreSQL database version:')
    cur.execute('SELECT version()')
    # display the PostgreSQL database server version
    db_version = cur.fetchone()
    print(db_version)
    # close the communication with the PostgreSQL
    cur.close()


def update_internal_model(self):

    pass


if __name__ == "__main__":
    conn = open_logger()
    check_version()

    test_fed = Fed.Federate()
    test_fed.create_federate("TE30", "cu_logger")
    test_fed.update_internal_model = update_internal_model
    test_fed.run_cosim_loop()
    test_fed.destroy_federate()
