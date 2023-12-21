import sys
import os
from pathlib import Path
sys.path.insert(1, os.path.join(Path(__file__).parent,'..','..', 'src'))
from Federate import Federate
from metadataDB import MetaDB
import helics as h
import multiprocessing as mp

# create two federate classes with their own step functions
class Python_Fed(Federate):
    
    def update_internal_model(self):
        # grab data from other federate
        val_to_add = self.data_from_federation['inputs']['pyjl_fed/mult_val']
        if val_to_add == None:
            val_to_add = 1
        
        # perform work on model
        val_to_add += 1
        
        self.data_to_federation['publications']['py_fed/add_val'] = val_to_add
        
class PyJulia_Fed(Federate):
    def __init__(self):
            importlib = __import__('importlib')
            self.jl_function = importlib.import_module('julia.Main')
            self.jl_function.include("jl_functions.jl")
    
    def update_internal_model(self):
        # grab data from other federate
        val_to_mult = self.data_from_federation['inputs']['py_fed/add_val']
        if val_to_mult == None:
            val_to_mult = 1
        
        # perform work on model
        val_to_mult =self.jl_function.multiply_value(val_to_mult)
        
        self.data_to_federation['publications']['pyjl_fed/mult_val'] = val_to_mult

# create a db for a simple federation
local_default_uri = 'mongodb://localhost:27017'
metadb = MetaDB(uri_string=local_default_uri)
MAX_TIME = 5

# store all dictionaries for the collection
collection_name = "main"
federation_name = "pyjulia_federation"
py_federate_dict = {
    "image": "nothing_pth",
    "federate type": "value",
    "sim step size": 1,
    "max sim time": MAX_TIME,
    "HELICS config":{
      "name": "py_fed",
      "core_type": "zmq",
      "log_level": "warning",
      "period": 1,
      "uninterruptible": False,
      "terminate_on_error": True,
      "wait_for_current_time_update": True,
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
    "HELICS config":{
      "name": "pyjl_fed",
      "core_type": "zmq",
      "log_level": "warning",
      "period": 1,
      "uninterruptible": False,
      "terminate_on_error": True,
      "wait_for_current_time_update": True,
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

collection_scenarios = {"current scenario": federation_name}
# add a DB collection for all tests
try:
    metadb.add_dict(collection_name, dict_to_add=collection_scenarios, dict_name="current scenario")
except NameError as e:
    metadb.remove_collection(collection_name)
    metadb.add_collection(collection_name)
    metadb.add_dict(collection_name, dict_to_add=collection_scenarios, dict_name="current scenario")
# create and begin a broker for the cosim
broker = h.helicsCreateBroker("zmq", "mainbroker", f"-f 2")
#  add a DB collection for the first test federation, and add the federation to the collection
try:
    metadb.add_collection(federation_name)
    metadb.add_dict(federation_name, "federation", federation_dict)
except NameError as e:
    metadb.remove_collection(federation_name)
    metadb.add_collection(federation_name)
    metadb.add_dict(federation_name, "federation", federation_dict)
# create the federates
py_fed = Python_Fed(fed_name = 'py_fed')
py_fed.connect_to_metadataDB()
jl_fed = PyJulia_Fed(fed_name = 'jl_fed')
jl_fed.connect_to_metadataDB()
py_fed.create_federate()
jl_fed.create_federate()