"""
Created on 12/14/2023

Simple plot that defines the basic operations of
Python-based logger federate in CoSimulation Toolbox.

@author: Mitch Pelton
"""

from os import environ
import matplotlib.pyplot as plt
import psycopg2


def open_logger():
    connection = {
        "host": environ.get("POSTGRES_HOST", "localhost"),
        "port": environ.get("POSTGRES_PORT", 5432),
        "dbname": environ.get("COSIM_DB", "copper"),
        "user": environ.get("COSIM_USER", "worker"),
        "password": environ.get("COSIM_PASSWORD", "worker")
    }
    try:
        return psycopg2.connect(**connection)
    except:
        return


_federate_name = "FederateLogger"   # TODO: fix the proper federated name
_scenario_name = "test_MyTest"
_schema_name = "test_MySchema2"
_federation_name = "test_MyFederation"

names = ["Battery", "EVehicle"]
items = ["current", "voltage"]
_data_name = names[0] + "/" + items[0]

qry = f"SELECT time, data_value FROM {_schema_name}.HDT_DOUBLE WHERE " \
      f"time > 30 AND " \
      f"scenario = '{_scenario_name}' AND " \
      f"federate = '{_federate_name}' AND " \
      f"data_name = '{names[0]}/{items[0]}';"

conn = open_logger()
cur = conn.cursor()
cur.execute(qry)
records = cur.fetchall()
fig, ax = plt.subplots()
ax.scatter(*zip(*records))

plt.show()
cur.close()
