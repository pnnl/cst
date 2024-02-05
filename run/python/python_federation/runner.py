"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author:
mitch.pelton@pnnl.gov
"""
import cosim_toolbox.metadataDB as mDB
from cosim_toolbox.helicsConfig import HelicsMsg


class Runner:

    def __init__(self, scenario_name, schema_name, federation_name, docker=False):
        self.scenario_name = scenario_name
        self.schema_name = schema_name
        self.federation_name = federation_name
        self.docker = docker
        self.db = mDB.MetaDB(mDB.cosim_mongo_host, mDB.cosim_mongo_db)

    def define_scenario(self):
        names = ["Battery", "EVehicle"]
        prefix = "source /home/worker/venv/bin/activate && exec python3 simple_federate.py "
        t1 = HelicsMsg(names[0], 30)
        if self.docker:
            t1.config("brokeraddress", "10.5.0.2")
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("period", 60)
        t1.config("uninterruptible", False)
        t1.config("terminate_on_error", True)
#        t1.config("wait_for_current_time_update", True)
        t1.pubs_e(True, names[0] + "/EV1_current", "double", "A")
        t1.subs_e(True, names[1] + "/EV1_voltage", "double", "V")
        t1 = {
            "image": "cosim-python:latest",
            "command": prefix + names[0] + " " + self.scenario_name,
            "federate_type": "value",
            "time_step": 120,
            "HELICS_config": t1.write_json()
        }

        t2 = HelicsMsg(names[1], 30)
        t2.config("core_type", "zmq")
        if self.docker:
            t2.config("brokeraddress", "10.5.0.2")
        t2.config("log_level", "warning")
        t2.config("period", 60)
        t2.config("uninterruptible", False)
        t2.config("terminate_on_error", True)
#        t2.config("wait_for_current_time_update", True)
        t2.subs_e(True, names[0] + "/EV1_current", "double", "A")
        t2.pubs_e(True, names[1] + "/EV1_voltage", "double", "V")
        t2 = {
            "image": "cosim-python:latest",
            "command": prefix + names[1] + " " + self.scenario_name,
            "env": "",
            "federate_type": "value",
            "time_step": 120,
            "HELICS_config": t2.write_json()
        }
        diction = {
            "federation": {
                names[0]: t1,
                names[1]: t2
            }
        }

        self.db.remove_document(mDB.cu_federations, None, self.federation_name)
        self.db.add_dict(mDB.cu_federations, self.federation_name, diction)
        print(mDB.cu_federations, self.db.get_collection_document_names(mDB.cu_federations))

        scenario = self.db.scenario(self.schema_name,
                                    self.federation_name,
                                    "2023-12-07T15:31:27",
                                    "2023-12-08T15:31:27",
                                    self.docker)
        self.db.remove_document(mDB.cu_scenarios, None, self.scenario_name)
        self.db.add_dict(mDB.cu_scenarios, self.scenario_name, scenario)
        print(mDB.cu_scenarios, self.db.get_collection_document_names(mDB.cu_scenarios))


if __name__ == "__main__":
    _scenario_name = "MyScenario"
    _schema_name = "MySchema"
    _federation_name = "MyFederation"
    r = Runner(_scenario_name, _schema_name, _federation_name, False)
    r.define_scenario()
    mDB.Docker.define_yaml(r.scenario_name)
    if False:
        mDB.Docker.run_yaml(_scenario_name)
