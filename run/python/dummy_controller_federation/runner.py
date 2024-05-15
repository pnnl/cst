"""
Created on 3/11/2024

Create scenarios for testing dummy controller

@author: Shat Pratoomratana
shat.pratoomratana@pnnl.gov
"""

import cosim_toolbox.metadataDB as mDB
from cosim_toolbox.helics_config import HelicsMsg


class Runner:

    def __init__(self, scenario_name, schema_name, federation_name, docker=False):
        self.scenario_name = scenario_name
        self.schema_name = schema_name
        self.federation_name = federation_name
        self.docker = docker
        self.db = mDB.MetaDB(mDB.cosim_mongo_host, mDB.cosim_mongo_db)

    def define_scenario(self):
        prefix = "source /home/worker/venv/bin/activate && exec python3 "
        names = ["Controller", "Market"]
        
        #Controller federate 
        t1 = HelicsMsg(names[0], 30)
        if self.docker:
            t1.config("brokeraddress", "10.5.0.2")
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("period", 30)
        t1.config("uninterruptible", False)
        t1.config("terminate_on_error", True)
        

        t1.pubs_n(True, names[0] + "/DAM_bid", "string") 
        t1.subs_n(True, names[1] + "/DAM_clearing_info", "string")
        
        t1.pubs_n(True, names[0] + "/frequency_bid", "string") 
        t1.subs_n(True, names[1] + "/frequency_clearing_info", "string")
        
        t1.pubs_n(True, names[0] + "/realtime_bid", "string") 
        t1.subs_n(True, names[1] + "/realtime_clearing_info", "string")
        

        f1 = {
            "image": "cosim-python:latest",
            "command": prefix + "dummy_controller_fed.py " + names[0] + " " + self.scenario_name,
            "federate_type": "value",
            "time_step": 120,
            "HELICS_config": t1.write_json()
        }

        #Market federate
        t2 = HelicsMsg(names[1], 30)
        if self.docker:
            t2.config("brokeraddress", "10.5.0.2")
        t2.config("core_type", "zmq")
        t2.config("log_level", "warning")
        t2.config("period", 60)
        t2.config("uninterruptible", False)
        t2.config("terminate_on_error", True)
#        t2.config("wait_for_current_time_update", True)

        t2.subs_e(True, names[0] + "/DAM_bid", "string")
        t2.pubs_e(True, names[1] + "/DAM_clearing_info", "string")

        t2.subs_e(True, names[0] + "/frequency_bid", "string")
        t2.pubs_e(True, names[1] + "/frequency_clearing_info", "string")

        t2.subs_e(True, names[0] + "/realtime_bid", "string")
        t2.pubs_e(True, names[1] + "/realtime_clearing_info", "string")


        f2 = {
            "image": "cosim-python:latest",
            "command": prefix + "dummy_market_fed.py " + names[1] + " " + self.scenario_name,
            "env": "",
            "federate_type": "value",
            "time_step": 120,
            "HELICS_config": t2.write_json()
        }
        diction = {
            "federation": {
                names[0]: f1,
                names[1]: f2
            }
        }

        self.db.remove_document(mDB.cu_federations, None, self.federation_name)
        self.db.add_dict(mDB.cu_federations, self.federation_name, diction)
        # print(mDB.cu_federations, self.db.get_collection_document_names(mDB.cu_federations))

        scenario = self.db.scenario(self.schema_name,
                                    self.federation_name,
                                    "2023-12-07T15:31:27",
                                    "2023-12-08T15:31:27",
                                    self.docker)
        self.db.remove_document(mDB.cu_scenarios, None, self.scenario_name)
        self.db.add_dict(mDB.cu_scenarios, self.scenario_name, scenario)
        # print(mDB.cu_scenarios, self.db.get_collection_document_names(mDB.cu_scenarios))


if __name__ == "__main__":
    remote = True
    _scenario_name = "test_DummyController"
    _schema_name = "test_DummyControllerSchema"
    _federation_name = "test_ControllerMarketFederation"
    r = Runner(_scenario_name, _schema_name, _federation_name, True)
    r.define_scenario()
    mDB.Docker.define_yaml(r.scenario_name)
    if remote:
        mDB.Docker.run_remote_yaml(_scenario_name)
    else:
        mDB.Docker.run_yaml(_scenario_name)
