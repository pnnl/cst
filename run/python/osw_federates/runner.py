"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
adapted by Molly 8/29/24
mollyrose.kelly-gorham@pnnl.gov
"""

import cosim_toolbox as env
from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox.dbResults import DBResults
from cosim_toolbox.dockerRunner import DockerRunner
from cosim_toolbox.helicsConfig import HelicsMsg, Collect
from gridtune.pcm import h5fun
import os, json

class Runner:

    def __init__(self, scenario_name, schema_name, federation_name, docker=False):
        self.scenario_name = scenario_name
        self.schema_name = schema_name
        self.federation_name = federation_name
        self.docker = docker
        self.db = DBConfigs(env.cst_mg_host, env.cst_mongo_db)

        # error check for scenario results
        self.dl = DBResults()
        self.dl.open_database_connections()
        if self.dl.schema_exist(self.schema_name):
            df = self.dl.get_scenario_list(self.schema_name, "hdt_string")
            if df.shape[0] > 0:
                print(f"There are results in this scenario-> {scenario_name}, and this schema-> {schema_name}")
                choice = input(f"Want to remove these scenario results? (Yy/Nn)")
                if choice in ['y', 'Y', 'yes', 'YES']:
                    self.dl.remove_scenario(self.schema_name, self.scenario_name)
                else:
                    print(f"Runner has ended, no output was generated, rename or remove scenario and/or schema")
                    exit()

        # uncomment debug, clears schema
        # which means all scenarios are gone in that scheme
        # self.dl.drop_schema(self.scheme_name)

    def define_scenario(self, h5filepath, b_time, e_time):
        h5 = h5fun.H5(h5filepath)
        generators = h5("/mdb/Generator")
        buses = h5("/mdb/Bus")
        # h5.close()

        names = ["OSW_TSO", "OSW_Plant"]
        # Reserve prices by area and product
        reserve_keys = ['regulation_up', 'regulation_down', 'flexible_ramp_up',
                      'flexible_ramp_down']
        # TODO: call areas from the h5 file
        area_keys = ['CALIFORN', 'MEXICO', 'NORTH', 'SOUTH']
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

        ###########################################################
        ############# TSO publications list #######################
        ###########################################################
        # Publish json-formatted string with model results
        t1.pubs_e(f"{names[0]}/da_model_results", "string", "json")
        t1.pubs_e(f"{names[0]}/rt_model_results", "string", "json")
        # Wind forecast for OSW farm
        t1.pubs_e(names[0] + "/windforecast", "string", "mps", True, Collect.YES)  # collect into logger or not.
        # Dispatch values by generator
        for g in generators["GeneratorName"]:
            t1.pubs_e(f"{names[0]}/rt_dispatch_{g}", "string", "MW")
            t1.pubs_e(f"{names[0]}/da_dispatch_{g}", "string", "MW")
            # Unique dispatch for each reserve (save DA for now)
            for key in reserve_keys:
                t1.pubs_e(f"{names[0]}/da_{key}_dispatch_{g}", "string", "MW")

        # Bus LMPs
        for b in buses["BusID"]:    
            t1.pubs_e(f"{names[0]}/da_price_{b}", "string", "$")    
            t1.pubs_e(f"{names[0]}/rt_price_{b}", "string", "$")
        for area in area_keys:    
            for key in reserve_keys:
                # price_dict[area + ' ' + key] = da_results.data["elements"]["area"][area][key]        
                t1.pubs_e(f"{names[0]}/da_{key}_price_{area}", "string", "$")

        f1 = {
            "logger": False,
            "image": "cosim-python:latest",
            "h5filepath": h5filepath,
            "command": f"python3 osw_tso.py {names[0]} {self.scenario_name} {h5filepath} {b_time} {e_time}",
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

        ###########################################################
        ########## OSW publications/subscriptions list ############
        ###########################################################
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

        self.db.remove_document(env.cst_federations, None, self.federation_name)
        self.db.add_dict(env.cst_federations, self.federation_name, diction)
        # print(cst.cu_federations, self.db.get_collection_document_names(cst.cu_federations))
        # print(self.federation_name, self.db.get_dict(cst.cu_federations, None, self.federation_name))

        scenario = self.db.scenario(self.schema_name,
                                    self.federation_name,
                                    b_time,
                                    e_time,
                                    self.docker)
        self.db.remove_document(env.cst_scenarios, None, self.scenario_name)
        self.db.add_dict(env.cst_scenarios, self.scenario_name, scenario)
        # print(cst.cu_scenarios, self.db.get_collection_document_names(cst.cu_scenarios))
        # print(self.scenario_name, self.db.get_dict(cst.cu_scenarios, None, self.scenario_name))

def get_config():
    """Creates a json configuration file. This can be edited to allow users to change options
       without affecting runner.py
    """
    if not os.path.exists("runner_config.json"):
        default_config = {
            "scenario_name": "osw_test_scenario",
            "schema_name": "osw_test_schema",
            "federation_name": "osw_test_federation",
            "h5path": "/Users/lill771/Documents/Data/GridView/WECC240_20240807.h5",
            "beginning_time": "2032-01-01T00:00:00",
            "ending_time": "2032-01-03T00:00:00",
        }
        with open('runner_config.json', 'w') as f:
            json.dump(default_config, f, indent=4)
        print("Created file `runner_config.json` with default settings."
              "\nEdit this file to customize your run scenario settings.")
        exit(0)
    else:
        with open('runner_config.json', 'r') as f:
            config = json.load(f)
    return config

def main(config, remote=False, with_docker=False):
    r = Runner(config["scenario_name"], config["schema_name"], config["federation_name"], with_docker)
    r.define_scenario(config["h5path"], config["beginning_time"], config["ending_time"])
    print(r.db.get_collection_document_names(env.cst_scenarios))
    print(r.db.get_collection_document_names(env.cst_federations))
    if with_docker:
        DockerRunner.define_yaml(r.scenario_name)
        if remote:
            DockerRunner.run_remote_yaml(r.scenario_name)
        else:
            DockerRunner.run_yaml(r.scenario_name)
    else:
        DockerRunner.define_sh(r.scenario_name)


if __name__ == "__main__":
    config = get_config()
    main(config)