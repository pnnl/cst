import helics as h
import multiprocessing as mp

from cosim_toolbox.dbConfigs import DBConfigs
from pyjulia_federates import Python_Fed, PyJulia_Fed

"""
This example use case demonstrates how to use julia functions in a Federate using PyJulia. 
The Federate subclasses can be found in pyjulia_federates, and the julia functions can be found in jl_functions.
"""

# create a db for a simple federation
local_default_uri = 'mongodb://localhost:27017'
metadb = DBConfigs(uri=local_default_uri)
MAX_TIME = 5

# store all dictionaries for the collection
collection_name = "main"
federation_name = "pyjulia_federation"
py_federate_dict = {
    "image": "nothing_pth",
    "federate type": "value",
    "sim step size": 1,
    "max sim time": MAX_TIME,
    "HELICS config": {
        "name": "py_fed",
        "core_type": "zmq",
        "log_level": "warning",
        "period": 1,
        "uninterruptible": False,
        "terminate_on_error": True,
        "publications": [
            {
                "global": True,
                "key": "py_fed/add_val",
                "type": "double"
            }
        ],
        "subscriptions": [
            {
                "gloabl": True,
                "key": "pyjl_fed/mult_val",
                "type": "double"
            }
        ]
    }
}
pyjl_federate_dict = {
    "image": "nothing_pth",
    "federate type": "value",
    "sim step size": 1,
    "max sim time": MAX_TIME,
    "HELICS config": {
        "name": "pyjl_fed",
        "core_type": "zmq",
        "log_level": "warning",
        "period": 1,
        "uninterruptible": False,
        "terminate_on_error": True,
        "publications": [
            {
                "global": True,
                "key": "pyjl_fed/mult_val",
                "type": "double"
            }
        ],
        "subscriptions": [
            {
                "gloabl": True,
                "key": "py_fed/add_val",
                "type": "double"
            }
        ]
    }
}
federation_dict = {
    "name": federation_name,
    "max sim time": MAX_TIME,
    "broker": True,
    "federates": [
        {
            "directory": ".",
            "host": "localhost",
            "name": "py_fed"
        },
        {
            "directory": ".",
            "host": "localhost",
            "name": "pyjl_fed"
        }
    ],
    "py_fed": py_federate_dict,
    "jl_fed": pyjl_federate_dict
}

# def federate_cosim(fed:Federate):
#   fed.connect_to_metadataDB()
#   fed.create_federate()
#   fed.run_cosim_loop()
#   fed.destroy_federate()
#   return

if __name__ == "__main__":
    collection_scenarios = {"current scenario": federation_name}
    # add a DB collection for all tests
    try:
        metadb.add_collection(collection_name)
        metadb.add_dict(collection_name, dict_to_add=collection_scenarios, dict_name="current scenario")
    except NameError as e:
        metadb.remove_scenario(collection_name)
        metadb.add_collection(collection_name)
        metadb.add_dict(collection_name, dict_to_add=collection_scenarios, dict_name="current scenario")
    # create and begin a broker for the cosim
    broker = h.helicsCreateBroker("zmq", "mainbroker", f"-f 2")
    #  add a DB collection for the first test federation, and add the federation to the collection
    try:
        metadb.add_collection(federation_name)
        metadb.add_dict(federation_name, "federation", federation_dict)
    except NameError as e:
        metadb.remove_scenario(federation_name)
        metadb.add_collection(federation_name)
        metadb.add_dict(federation_name, "federation", federation_dict)
    # create the federates
    py_fed = Python_Fed(fed_name='py_fed')
    jl_fed = PyJulia_Fed(fed_name='jl_fed')

    # connect both federates to the cosim and begin
    py_process = mp.Process(target=py_fed.run_cosim_loop, args=())
    jl_process = mp.Process(target=jl_fed.run_cosim_loop, args=())
    py_process.start()
    jl_process.start()
    py_process.join()
    jl_process.join()
    # cleanup the cosim
    metadb.remove_scenario(collection_name)
    metadb.remove_scenario(federation_name)
    h.helicsBrokerDestroy(broker)
