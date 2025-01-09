"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""
import cosim_toolbox as cst
from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox.dockerRunner import DockerRunner
from cosim_toolbox.helicsConfig import HelicsMsg, Collect


class Runner:

    def __init__(self, scenario_name, schema_name, federation_name, docker=False):
        self.scenario_name = scenario_name
        self.schema_name = schema_name
        self.federation_name = federation_name
        self.docker = docker
        self.db = DBConfigs(cst.cosim_mongo, cst.cosim_mongo_db)

    def define_scenario(self):
        names = ["Battery", "EVehicle"]
        t1 = HelicsMsg(names[0], 30)
        if self.docker:
            t1.config("brokeraddress", "10.5.0.2")
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("period", 30)
        t1.config("uninterruptible", False)
        t1.config("terminate_on_error", True)
        # t1.config("wait_for_current_time_update", True)
        t1.collect(Collect.YES)

        t1.pubs_e(names[0] + "/current", "double", "V", True, Collect.YES)
        t1.subs_e(names[1] + "/voltage", "double", "V")
        t1.pubs_e(names[0] + "/current2", "integer", "A", True, Collect.NO)
        t1.subs_e(names[1] + "/voltage2", "integer", "V")
        t1.pubs_e(names[0] + "/current3", "boolean", "A")
        t1.subs_e(names[1] + "/voltage3", "boolean", "V")
        t1.pubs_e(names[0] + "/current4", "string", "A")
        t1.subs_e(names[1] + "/voltage4", "string", "V")
        t1.pubs_e(names[0] + "/current5", "complex", "A", True, Collect.MAYBE)
        t1.subs_e(names[1] + "/voltage5", "complex", "V")
        t1.pubs_e(names[0] + "/current6", "vector", "A", True, Collect.NO)
        t1.subs_e(names[1] + "/voltage6", "vector", "V")
        t1.endpt(names[0] + "/current1", names[1] + "/voltage1", True, Collect.YES)

        t2 = HelicsMsg(names[1], 30)
        if self.docker:
            t2.config("brokeraddress", "10.5.0.2")
        t2.config("core_type", "zmq")
        t2.config("log_level", "warning")
        t2.config("period", 60)
        t2.config("uninterruptible", False)
        t2.config("terminate_on_error", True)
        # t2.config("wait_for_current_time_update", True)

        t2.subs_e(names[0] + "/current", "double", "V")
        t2.pubs_e(names[1] + "/voltage", "double", "V")
        t2.subs_e(names[0] + "/current2", "integer", "A")
        t2.pubs_e(names[1] + "/voltage2", "integer", "V")
        t2.subs_e(names[0] + "/current3", "boolean", "A")
        t2.pubs_e(names[1] + "/voltage3", "boolean", "V", True, Collect.NO)
        t2.subs_e(names[0] + "/current4", "string", "A")
        t2.pubs_e(names[1] + "/voltage4", "string", "V")
        t2.subs_e(names[0] + "/current5", "complex", "A")
        t2.pubs_e(names[1] + "/voltage5", "complex", "V")
        t2.subs_e(names[0] + "/current6", "vector", "A")
        t2.pubs_e(names[1] + "/voltage6", "vector", "V")
        t2.endpt(names[1] + "/voltage1", names[0] + "/current1", True, Collect.YES)

        f1 = {
            "logger": False,
            "image": "cosim-python:latest",
            "command": f"python3 simple_federate.py {names[0]} {self.scenario_name}",
            "federate_type": "combo",
            "time_step": 120,
            "HELICS_config": t1.write_json()
        }
        f2 = {
            "logger": False,
            "image": "cosim-python:latest",
            "command": f"python3 simple_federate2.py {names[1]} {self.scenario_name}",
            "federate_type": "combo",
            "time_step": 120,
            "HELICS_config": t2.write_json()
        }
        diction = {
            "federation": {
                names[0]: f1,
                names[1]: f2
            }
        }

        # print(diction)
        t1.write_file(names[0] + ".json")
        t2.write_file(names[1] + ".json")

        self.db.remove_document(cst.cu_federations, None, self.federation_name)
        self.db.add_dict(cst.cu_federations, self.federation_name, diction)
        # print(cst.cu_federations, self.db.get_collection_document_names(cst.cu_federations))
        # print(self.federation_name, self.db.get_dict(cst.cu_federations, None, self.federation_name))

        scenario = self.db.scenario(self.schema_name,
                                    self.federation_name,
                                    "2023-12-07T15:31:27",
                                    "2023-12-08T15:31:27",
                                    self.docker)
        self.db.remove_document(cst.cu_scenarios, None, self.scenario_name)
        self.db.add_dict(cst.cu_scenarios, self.scenario_name, scenario)
        # print(cst.cu_scenarios, self.db.get_collection_document_names(cst.cu_scenarios))
        # print(self.scenario_name, self.db.get_dict(cst.cu_scenarios, None, self.scenario_name))


def main():
    remote = False
    with_docker = False
    r = Runner("test_scenario", "test_schema", "test_federation", with_docker)
    r.define_scenario()
    print(r.db.get_collection_document_names(cst.cu_scenarios))
    print(r.db.get_collection_document_names(cst.cu_federations))
    if with_docker:
        DockerRunner.define_yaml(r.scenario_name)
        if remote:
            DockerRunner.run_remote_yaml(r.scenario_name)
        else:
            DockerRunner.run_yaml(r.scenario_name)
    else:
        DockerRunner.define_sh(r.scenario_name)

if __name__ == "__main__":
    main()