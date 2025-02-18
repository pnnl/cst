"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
adapted by Molly 8/29/24
mollyrose.kelly-gorham@pnnl.gov
"""

import cosim_toolbox as cst
from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox.dockerRunner import DockerRunner
from cosim_toolbox.helicsConfig import HelicsMsg, Collect

import pandas as pd
from gridtune.pcm import h5fun
 
h5filepath = '/home/worker/WECC240_20240807.h5'
h5 = h5fun.H5(h5filepath)
buses = h5("/mdb/Bus")

"""
python osw_tso.py 
 OSW_TSO 
 osw_lmp_test_scenario 
 /Users/lill771/Documents/Data/GridView/WECC240_20240807.h5 
 2032-1-01T00:00:00 
 2032-01-03T00:00:00
"""

class Runner:

    def __init__(self, scenario_name, schema_name, federation_name, docker=False):
        self.scenario_name = scenario_name
        self.schema_name = schema_name
        self.federation_name = federation_name
        self.docker = docker
        # self.db = DBConfigs(cst.cosim_mongo_host, cst.cosim_mongo_db)
        self.db = DBConfigs(cst.cst_mg_host, cst.cst_mongo_db)

    def define_scenario(self):
        prefix = "source /home/worker/venv/bin/activate"
        names = ["OSW_TSO", "OSW_Plant"]
        t1 = HelicsMsg(names[0], 30) #CHANGE FROM 30 SECONDS TO 15 MINUTES
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
        # Add reserve price names
        price_keys = ['regulation_up_price', 'regulation_down_price', 'flexible_ramp_up_price',
                      'flexible_ramp_down_price']
        # TODO: call areas from the h5 file
        area_keys = ['CALIFORN', 'MEXICO', 'NORTH', 'SOUTH']
        for area in area_keys:
            for key in price_keys:
                # price_dict[area + ' ' + key] = da_results.data["elements"]["area"][area][key]
                t1.pubs_e(f"{names[0]}/da_{key}_{area}", "string", "$")

        f1 = {
            "logger": False,
            "image": "cosim-python:latest",
            "prefix": prefix,
            "h5filepath": h5filepath,
            "command": "python3 osw_tso.py " + names[0] + " " + self.scenario_name,
            "federate_type": "combo",
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

        t2.subs_e(names[0] + "/rt_dispatch", "string", "MW")
        t2.pubs_e(names[1] + "/rt_bids", "string", "MW")
        t2.subs_e(names[0] + "/da_dispatch", "string", "MW")
        t2.pubs_e(names[1] + "/da_bids", "string", "MW")
        t2.subs_e(names[0] + "/res_dispatch", "string", "MW")
        t2.pubs_e(names[1] + "/res_bids", "string", "MW")
        t2.subs_e(names[0] + "/wind_forecasts", "string", "mps") # meters per second

        f2 = {
            "logger": False,
            "image": "cosim-python:latest",
            "prefix": prefix,
            "command": "python3 osw_plant.py " + names[1] + " " + self.scenario_name,
            "federate_type": "value",
            "time_step": 120,
            "HELICS_config": t2.write_json()
        }

        diction = {
            "federation": {
                names[0]: f1 ,
                # names[1]: f2
            }
        }
        print(diction)

        self.db.remove_document(cst.cst_federations, None, self.federation_name)
        self.db.add_dict(cst.cst_federations, self.federation_name, diction)
        # print(cst.cu_federations, self.db.get_collection_document_names(cst.cu_federations))
        # print(self.federation_name, self.db.get_dict(cst.cu_federations, None, self.federation_name))

        scenario = self.db.scenario(self.schema_name,
                                    self.federation_name,
                                    "2032-01-01T00:00:00",
                                    "2032-01-03T00:00:00",
                                    self.docker)
        self.db.remove_document(cst.cst_scenarios, None, self.scenario_name)
        self.db.add_dict(cst.cst_scenarios, self.scenario_name, scenario)
        # print(cst.cu_scenarios, self.db.get_collection_document_names(cst.cu_scenarios))
        # print(self.scenario_name, self.db.get_dict(cst.cu_scenarios, None, self.scenario_name))

def main():
    remote = False
    with_docker = False
    r = Runner("osw_lmp_test_scenario_kaitlynn", "osw_test_schema_kaitlynn", "osw_test_federation", with_docker)
    r.define_scenario()
    print(r.db.get_collection_document_names(cst.cst_scenarios))
    print(r.db.get_collection_document_names(cst.cst_federations))
    if with_docker:
        DockerRunner.define_yaml(r.scenario_name)
        if remote:
            DockerRunner.run_remote_yaml(r.scenario_name)
        else:
            DockerRunner.run_yaml(r.scenario_name)
    else:
        DockerRunner.define_sh(r.scenario_name)

    h5.close()

if __name__ == "__main__":
    main()