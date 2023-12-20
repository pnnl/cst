"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""

import Federate as Fed
import pos
import psycopg2

open log
with open(file_name, 'r', encoding='utf-8') as json_file:
    config = json.load(json_file)
conn = psycopg2.connect("dbname=suppliers user=postgres password=postgres")

def update_internal_model(self):
    pass


if __name__ == "__main__":
    test_fed = Fed.Federate()
    test_fed.update_internal_model = update_internal_model
    test_fed.connect_to_metadataDB()
    test_fed.create_federate(test_fed.scenario_name)
    test_fed.run_cosim_loop()
    test_fed.destroy_federate()
