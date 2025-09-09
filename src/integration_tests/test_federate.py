# setup and definitions
import threading
import helics as h
import collections

collections.Callable = collections.abc.Callable

from cosim_toolbox.sims import Federate
from cosim_toolbox.sims import DBConfigs

# create a db for a simple federation
local_default_uri = 'mongodb://localhost:27017'
collection_name = "main"
metadb = DBConfigs(local_default_uri, collection_name)
MAX_TIME = 5

# store all dictionaries for the collection
single_federation_name = "test_federation_1"
multiple_federation_name = "test_federation_2"
pub_federate_dict = {
    "image": "nothing_pth",
    "federate type": "value",
    "sim step size": 1,
    "max sim time": MAX_TIME,
    "HELICS config": {
        "name": "test_pub_fed",
        "core_type": "zmq",
        "log_level": "warning",
        "period": 1,
        "uninterruptible": False,
        "terminate_on_error": True,
        "wait_for_current_time_update": True,
        "publications": [
            {
                "global": True,
                "key": "test_pub_fed/test_pub",
                "type": "double"
            }
        ]
    }
}
sub_federate_dict = {
    "image": "nothing_pth",
    "federate type": "value",
    "sim step size": 1,
    "max sim time": MAX_TIME,
    "HELICS config": {
        "name": "test_sub_fed",
        "core_type": "zmq",
        "log_level": "warning",
        "period": 1,
        "uninterruptible": False,
        "terminate_on_error": True,
        "wait_for_current_time_update": True,
        "subscriptions": [
            {
                "global": True,
                "key": "test_pub_fed/test_pub",
                "type": "double"
            }
        ]
    }
}
single_federation_dict = {
    "name": single_federation_name,
    "max sim time": MAX_TIME,
    "broker": True,
    "federates": [
        {
            "directory": ".",
            "host": "localhost",
            "name": "test_pub_fed"
        }
    ],
    "test_pub_fed": pub_federate_dict
}
multiple_federation_dict = {
    "name": multiple_federation_name,
    "max sim time": MAX_TIME,
    "broker": True,
    "federates": [
        {
            "directory": ".",
            "host": "localhost",
            "name": "test_pub_fed"
        },
        {
            "directory": ".",
            "host": "localhost",
            "name": "test_sub_fed"
        }
    ],
    "test_pub_fed": pub_federate_dict,
    "test_sub_fed": sub_federate_dict
}


# helper functions
def setup_cosim(test_federation_name):
    collection_scenarios = {"current scenario": test_federation_name}
    # add a DB collection for all tests
    try:
        metadb.add_dict(collection_name, dict_to_add=collection_scenarios, dict_name="current scenario")
    except NameError as _e:
        metadb.remove_collection(collection_name)
        metadb.add_collection(collection_name)
        metadb.add_dict(collection_name, dict_to_add=collection_scenarios, dict_name="current scenario")


def add_federation_collection(test_federation_name, test_federation_dict, num_feds):
    # create and begin a broker for the cosim
    broker = h.helicsCreateBroker("zmq", "mainbroker", f"-f {num_feds}")
    #  add a DB collection for the first test federation, and add the federation to the collection
    try:
        metadb.add_collection(test_federation_name)
        metadb.add_dict(test_federation_name, "federation", test_federation_dict)
    except NameError as _e:
        metadb.remove_collection(test_federation_name)
        metadb.add_collection(test_federation_name)
        metadb.add_dict(test_federation_name, "federation", test_federation_dict)
    return broker


def federate_cosim(fed: Federate):
    fed.run_cosim_loop()
    fed.destroy_federate()
    return


def cleanup(broker, test_federation_name):
    # cleanup
    metadb.remove_collection(collection_name)
    metadb.remove_collection(test_federation_name)
    h.helicsBrokerDestroy(broker)


# cosimulation tests  
def run_single_federate():
    # set up database and cosim
    setup_cosim(single_federation_name)
    broker = add_federation_collection(single_federation_name, single_federation_dict, 1)
    # create a federate object
    fed = Federate(fed_name="test_pub_fed")
    # fed.connect_to_metadataDB()
    fed.create_federate("scenario")

    # run federate and cleanup
    federate_cosim(fed)
    cleanup(broker, single_federation_name)


def run_multiple_federates():
    # set up database and cosim
    setup_cosim(multiple_federation_name)
    broker = add_federation_collection(multiple_federation_name, multiple_federation_dict, 1)
    # create both federate objects
    pub = Federate(fed_name="test_pub_fed")
    sub = Federate(fed_name="test_sub_fed")
    pub.connect_to_metadataDB()
    sub.connect_to_metadataDB()
    pub.create_federate()
    sub.create_federate()

    # run federate and cleanup
    pub_thread = threading.Thread(target=federate_cosim, args=(pub,))
    sub_thread = threading.Thread(target=federate_cosim, args=(sub,))
    pub_thread.start()
    sub_thread.start()
    pub_thread.join()
    sub_thread.join()
    cleanup(broker, multiple_federation_name)


if __name__ == "__main__":
    try:
        metadb.add_collection(collection_name)
    except NameError as e:
        metadb.remove_collection(collection_name)
        metadb.add_collection(collection_name)
    run_single_federate()
