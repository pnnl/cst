"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
adapted by Molly 8/29/24
mollyrose.kelly-gorham@pnnl.gov
"""
import cosim_toolbox.metadataDB as mDB
from cosim_toolbox.helicsConfig import HelicsMsg, Collect

import pandas as pd
from pnnlpcm import h5fun
 
h5filepath = '/Users/lill771/Documents/Data/GridView/WECC240_20240807.h5'
h5 = h5fun.H5(h5filepath)
buses = h5("/mdb/Bus")

class Runner:

    def __init__(self, scenario_name, schema_name, federation_name, docker=False):
        self.scenario_name = scenario_name
        self.schema_name = schema_name
        self.federation_name = federation_name
        self.docker = docker
        print(mDB.cosim_mongo_host)
        self.db = mDB.MetaDB(mDB.cosim_mongo_host, mDB.cosim_mongo_db)

    def define_scenario(self):
        prefix = "exec python3 "
        names = ["OSW_TSO", "OSW_Plant"]
        t1 = HelicsMsg(names[0], 30)
        if self.docker:
            t1.config("brokeraddress", "10.5.0.2")
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("period", 30)
        t1.config("uninterruptible", False)
        t1.config("terminate_on_error", True)
        #        t1.config("wait_for_current_time_update", True)
        t1.collect(Collect.YES)

        t1.pubs_e(names[0] + "/rt_dispatch", "string", "MW")
        #t1.subs_e(names[1] + "/rt_bids", "list", "V")
        t1.pubs_e(names[0] + "/da_dispatch", "string", "MW")
        #t1.subs_e(names[1] + "/da_bids", "list", "V")
        t1.pubs_e(names[0] + "/res_dispatch", "string", "MW")
        #t1.subs_e(names[1] + "/res_bids", "list", "V")
        t1.pubs_e(names[0] + "/windforecast", "string", "mps", True, Collect.YES)# collect into logger or not.
        for b in buses["BusID"]:
            t1.pubs_e(f"{names[0]}/da_price_{b}", "string", "$")
            t1.pubs_e(f"{names[0]}/rt_price_{b}", "string", "$")
        

        f1 = {
            "image": "cosim-python:latest",
            "command": prefix + "osw_tso.py " + names[0] + " " + self.scenario_name,
            "federate_type": "value", # if endpoints involved this needs to be different
            "time_step": 120,
            "HELICS_config": t1.write_json()
        }

        t2 = HelicsMsg(names[1], 30) # 30 seconds == how frequently HELICS checks if there's any update from federate
        if self.docker:
            t2.config("brokeraddress", "10.5.0.2")
        t2.config("core_type", "zmq")
        t2.config("log_level", "warning")
        t2.config("period", 60)
        t2.config("uninterruptible", False)
        t2.config("terminate_on_error", True)
#        t2.config("wait_for_current_time_update", True)

        t2.subs_e(names[0] + "/rt_dispatch", "list", "MW")
        t2.pubs_e(names[1] + "/rt_bids", "list", "MW")
        t2.subs_e(names[0] + "/da_dispatch", "list", "MW")
        t2.pubs_e(names[1] + "/da_bids", "list", "MW")
        t2.subs_e(names[0] + "/res_dispatch", "list", "MW")
        t2.pubs_e(names[1] + "/res_bids", "list", "MW")
        t2.subs_e(names[0] + "/wind_forecasts", "list", "mps") # meters per second

        f2 = {
            "image": "cosim-python:latest",
            "command": prefix + "osw_plant.py " + names[1] + " " + self.scenario_name, #### TO-DO OSW plant file name -- make sure in the same directory!!
            "env": "",
            "federate_type": "value",
            "time_step": 120,
            "HELICS_config": t2.write_json()
        } # time_step is in seconds
        diction = {
            "federation": {
                names[0]: f1 ,
                names[1]: f2
            }
        }
        print(diction)

        self.db.remove_document(mDB.cu_federations, None, self.federation_name)
        self.db.add_dict(mDB.cu_federations, self.federation_name, diction)
        # print(mDB.cu_federations, self.db.get_collection_document_names(mDB.cu_federations))
        # print(self.federation_name, self.db.get_dict(mDB.cu_federations, None, self.federation_name))

        scenario = self.db.scenario(self.schema_name,
                                    self.federation_name,
                                    "2032-01-01T00:00:00",
                                    "2032-01-03T00:00:00",
                                    self.docker)
        self.db.remove_document(mDB.cu_scenarios, None, self.scenario_name)
        self.db.add_dict(mDB.cu_scenarios, self.scenario_name, scenario)
        # print(mDB.cu_scenarios, self.db.get_collection_document_names(mDB.cu_scenarios))
        # print(self.scenario_name, self.db.get_dict(mDB.cu_scenarios, None, self.scenario_name))


if __name__ == "__main__":
    remote = True
    _scenario_name = "osw_lmp_test_scenario"
    _schema_name = "osw_test_schema"
    _federation_name = "osw_test_federation"
    r = Runner(_scenario_name, _schema_name, _federation_name, False)
    r.define_scenario()
    # print(r.db.get_collection_document_names(mDB.cu_scenarios))
    # print(r.db.get_collection_document_names(mDB.cu_federations))
    mDB.Docker.define_yaml(r.scenario_name)
    # if remote:
    #     mDB.Docker.run_remote_yaml(_scenario_name)
    # else:
    #     mDB.Docker.run_yaml(_scenario_name)
