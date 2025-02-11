"""
Created on 03/13/2024

Simple plot that defines the basic operations of
Python-based logger federate in CoSimulation Toolbox.

@author: Mitch Pelton
modified by: Shat Pratoomratana
"""

from os import environ
import matplotlib.pyplot as plt
import psycopg2

import cosim_toolbox as env

def open_logger():
    try:
        return psycopg2.connect(**env.cst_data_db)
    except:
        return


_federate_name = "Controller"
_scenario_name = "test_DummyController"
_schema_name = "test_DummyControllerSchema"

names = ["Controller", "Market"]
items = ["DAM_bid", "DAM_clearing_info"]
_data_name = names[0] + "/" + items[0]

qry = f"SELECT sim_time, data_value FROM {_schema_name}.HDT_STRING WHERE " \
      f"sim_time > 30 AND " \
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
