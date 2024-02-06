"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
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
        prefix = "source /home/worker/venv/bin/activate && exec python3 "
        names = ["Battery", "EVehicle"]
        t1 = HelicsMsg(names[0], 30)
        if self.docker:
            t1.config("brokeraddress", "10.5.0.2")
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("period", 30)
        t1.config("uninterruptible", False)
        t1.config("terminate_on_error", True)
#        t1.config("wait_for_current_time_update", True)

        t1.pubs_e(True, names[0] + "/current", "double", "V")
        t1.subs_e(True, names[1] + "/voltage", "double", "V")
        t1.pubs_e(True, names[0] + "/current2", "integer", "A")
        t1.subs_e(True, names[1] + "/voltage2", "integer", "V")
        t1.pubs_e(True, names[0] + "/current3", "boolean", "A")
        t1.subs_e(True, names[1] + "/voltage3", "boolean", "V")
        t1.pubs_e(True, names[0] + "/current4", "string", "A")
        t1.subs_e(True, names[1] + "/voltage4", "string", "V")
        t1.pubs_e(True, names[0] + "/current5", "complex", "A")
        t1.subs_e(True, names[1] + "/voltage5", "complex", "V")
        t1.pubs_e(True, names[0] + "/current6", "vector", "A")
        t1.subs_e(True, names[1] + "/voltage6", "vector", "V")
        f1 = {
            "image": "cosim-python:latest",
            "command": prefix + "simple_federate.py " + names[0] + " " + self.scenario_name,
            "federate_type": "value",
            "time_step": 120,
            "HELICS_config": t1.write_json()
        }

        t2 = HelicsMsg(names[1], 30)
        if self.docker:
            t2.config("brokeraddress", "10.5.0.2")
        t2.config("core_type", "zmq")
        t2.config("log_level", "warning")
        t2.config("period", 60)
        t2.config("uninterruptible", False)
        t2.config("terminate_on_error", True)
#        t2.config("wait_for_current_time_update", True)

        t2.subs_e(True, names[0] + "/current", "double", "V")
        t2.pubs_e(True, names[1] + "/voltage", "double", "V")
        t2.subs_e(True, names[0] + "/current2", "integer", "A")
        t2.pubs_e(True, names[1] + "/voltage2", "integer", "V")
        t2.subs_e(True, names[0] + "/current3", "boolean", "A")
        t2.pubs_e(True, names[1] + "/voltage3", "boolean", "V")
        t2.subs_e(True, names[0] + "/current4", "string", "A")
        t2.pubs_e(True, names[1] + "/voltage4", "string", "V")
        t2.subs_e(True, names[0] + "/current5", "complex", "A")
        t2.pubs_e(True, names[1] + "/voltage5", "complex", "V")
        t2.subs_e(True, names[0] + "/current6", "vector", "A")
        t2.pubs_e(True, names[1] + "/voltage6", "vector", "V")
        f2 = {
            "image": "cosim-python:latest",
            "command": prefix + "simple_federate2.py " + names[1] + " " + self.scenario_name,
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
        # print(self.federation_name, self.db.get_dict(mDB.cu_federations, None, self.federation_name))

        scenario = self.db.scenario(self.schema_name,
                                    self.federation_name,
                                    "2023-12-07T15:31:27",
                                    "2023-12-08T15:31:27",
                                    self.docker)
        self.db.remove_document(mDB.cu_scenarios, None, self.scenario_name)
        self.db.add_dict(mDB.cu_scenarios, self.scenario_name, scenario)
        # print(mDB.cu_scenarios, self.db.get_collection_document_names(mDB.cu_scenarios))
        # print(self.scenario_name, self.db.get_dict(mDB.cu_scenarios, None, self.scenario_name))


if __name__ == "__main__":
    remote = True
    _scenario_name = "test_Scenario"
    _schema_name = "test_Schema"
    _federation_name = "test_Federation"
    r = Runner(_scenario_name, _schema_name, _federation_name, False)
    r.define_scenario()
    # print(r.db.get_collection_document_names(mDB.cu_scenarios))
    # print(r.db.get_collection_document_names(mDB.cu_federations))
    mDB.Docker.define_yaml(r.scenario_name)
    # if remote:
    #     mDB.Docker.run_remote_yaml(_scenario_name)
    # else:
    #     mDB.Docker.run_yaml(_scenario_name)
