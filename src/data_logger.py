"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""

import Federate as Fed


def update_internal_model(self):
    pass


if __name__ == "__main__":
    test_fed = Fed.Federate()
    test_fed.update_internal_model = update_internal_model
    test_fed.connect_to_metadataDB()
    test_fed.create_federate(test_fed.scenario_name)
    test_fed.run_cosim_loop()
    test_fed.destroy_federate()
