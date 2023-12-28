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


class SimpleFederate(Federate):
    def __init__(self, fed_name="", schema="default", **kwargs):
        super().__init__(fed_name="", **kwargs)

    def update_internal_model(self):
        """
        This is entirely user-defined code and is intended to be defined by
        sub-classing and overloading.
        """
        if not self.debug:
            raise NotImplementedError("Subclass from Federate and write code to update internal model")
        # Doing something silly for testing purposes
        # Get a value from an arbitrary input; I hope it is a number
        if len(self.data_from_federation["inputs"].keys()) >= 1:
            key = list(self.data_from_federation["inputs"].keys())[0]
            dummy_value = self.data_from_federation["inputs"][key]
        else:
            dummy_value = 0

        # Increment for arbitrary reasons. This is the actual model
        # that is being updated in this example.
        dummy_value += 1
        print(dummy_value)

        # Send out incremented value on arbitrary publication
        # Clear out values published last time
        for pub in self.data_to_federation["publications"]:
            self.data_to_federation["publications"][pub] = None
        for ep in self.data_to_federation["endpoints"]:
            self.data_to_federation["endpoints"][ep] = None
        if len(self.data_to_federation["publications"].keys()) >= 1:
            pub = self.hfed.get_publication_by_index(0)
            self.data_to_federation["publications"][pub.name] = dummy_value


if __name__ == "__main__":
    conn = open_logger()
    check_version()

    if sys.argv.__len__() > 2:
        test_fed = SimpleFederate(sys.argv[1])
        test_fed.create_federate(sys.argv[2])
        test_fed.run_cosim_loop()
        test_fed.destroy_federate()
