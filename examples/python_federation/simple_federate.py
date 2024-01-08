"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""
import sys
import psycopg2

from cosim_toolbox.federate import Federate


def open_logger():
    #    "host": os.environ.get("POSTGRES_HOST"),
    connection = {
        "host": "gage.pnl.gov",
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
        self.dummy = 0
        super().__init__(fed_name, **kwargs)

    def update_internal_model(self):
        """
        This is entirely user-defined code and is intended to be defined by
        sub-classing and overloading.
        """
        if not self.debug:
            raise NotImplementedError("Subclass from Federate and write code to update internal model")

        for key in self.data_from_federation["inputs"]:
            print(self.data_from_federation["inputs"][key])
            self.dummy += 1

        # Send out incremented value on arbitrary publication
        # Clear out values published last time
        for key in self.data_to_federation["publications"]:
            self.data_to_federation["publications"][key] = None
        for key in self.data_to_federation["endpoints"]:
            self.data_to_federation["endpoints"][key] = None

        for key in self.data_to_federation["publications"]:
            self.data_to_federation["publications"][key] = self.dummy + 1


if __name__ == "__main__":
    conn = open_logger()
    check_version()

    if sys.argv.__len__() > 2:
        test_fed = SimpleFederate(sys.argv[1])
        test_fed.create_federate(sys.argv[2])
        test_fed.run_cosim_loop()
        test_fed.destroy_federate()
