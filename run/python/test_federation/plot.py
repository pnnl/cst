"""
Created on 12/14/2023

Simple plot that defines the basic operations of
Python-based logger federate in CoSimulation Toolbox.

@author: Mitch Pelton
"""

from os import environ
import matplotlib.pyplot as plt
import psycopg2

import cosim_toolbox as env

def open_logger():
    try:
        return psycopg2.connect(**env.cst_data_db)
    except Exception as ex:
        return


_federate_name = "Battery"
_scenario_name = "test_scenario"
_schema_name = "test_schema"

names = ["Battery", "EVehicle"]
items = ["current", "voltage"]
_data_name = names[0] + "/" + items[0]

qry = f"SELECT sim_time, data_value FROM {_schema_name}.HDT_DOUBLE WHERE " \
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
