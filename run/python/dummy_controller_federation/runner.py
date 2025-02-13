"""
Created on 3/11/2024

Create scenarios for testing dummy controller

@author: Shat Pratoomratana
shat.pratoomratana@pnnl.gov
"""

import cosim_toolbox as env
from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox.dockerRunner import DockerRunner
from cosim_toolbox.helicsConfig import HelicsMsg


class Runner:

    def __init__(self, scenario_name, schema_name, federation_name, docker=False):
        self.scenario_name = scenario_name
        self.schema_name = schema_name
        self.federation_name = federation_name
        self.docker = docker
        self.db = DBConfigs(env.cst_mongo, env.cst_mongo_db)

    def define_scenario(self):
        names = ["Controller", "Market"]

        # Controller federate
        t1 = HelicsMsg(names[0], 30)
        if self.docker:
            t1.config("brokeraddress", "10.5.0.2")
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("period", 30)
        t1.config("uninterruptible", False)
        t1.config("terminate_on_error", True)

        t1.pubs_n(names[0] + "/DAM_bid", "string")
        t1.subs_n(names[1] + "/DAM_clearing_info", "string")

        t1.pubs_n(names[0] + "/frequency_bid", "string")
        t1.subs_n(names[1] + "/frequency_clearing_info", "string")

        t1.pubs_n(names[0] + "/realtime_bid", "string")
        t1.subs_n(names[1] + "/realtime_clearing_info", "string")

        f1 = {
            "logger": False,
            "image": "cosim-python:latest",
            "command": f"python3 dummy_controller_fed.py {names[0]} {self.scenario_name}",
            "federate_type": "value",
            "time_step": 120,
            "HELICS_config": t1.write_json()
        }

        # Market federate
        t2 = HelicsMsg(names[1], 30)
        if self.docker:
            t2.config("brokeraddress", "10.5.0.2")
        t2.config("core_type", "zmq")
        t2.config("log_level", "warning")
        t2.config("period", 60)
        t2.config("uninterruptible", False)
        t2.config("terminate_on_error", True)
        #        t2.config("wait_for_current_time_update", True)

        t2.subs_e(names[0] + "/DAM_bid", "string", "")
        t2.pubs_e(names[1] + "/DAM_clearing_info", "string", "")

        t2.subs_e(names[0] + "/frequency_bid", "string", "")
        t2.pubs_e(names[1] + "/frequency_clearing_info", "string", "")

        t2.subs_e(names[0] + "/realtime_bid", "string", "")
        t2.pubs_e(names[1] + "/realtime_clearing_info", "string", "")
        f2 = {
            "logger": False,
            "image": "cosim-python:latest",
            "command": f"python3 dummy_market_fed.py {names[1]} {self.scenario_name}",
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

        self.db.remove_document(env.cst_federations, None, self.federation_name)
        self.db.add_dict(env.cst_federations, self.federation_name, diction)
        # print(env.cst_federations, self.db.get_collection_document_names(env.cst_federations))

        scenario = self.db.scenario(self.schema_name,
                                    self.federation_name,
                                    "2023-12-07T15:31:27",
                                    "2023-12-08T15:31:27",
                                    self.docker)
        self.db.remove_document(env.cst_scenarios, None, self.scenario_name)
        self.db.add_dict(env.cst_scenarios, self.scenario_name, scenario)
        # print(env.cst_scenarios, self.db.get_collection_document_names(env.cst_scenarios))

def main():
    remote = False
    with_docker = False
    _scenario_name = "test_DummyController"
    _schema_name = "test_DummyControllerSchema"
    _federation_name = "test_ControllerMarketFederation"
    r = Runner(_scenario_name, _schema_name, _federation_name, with_docker)
    r.define_scenario()
    # print(r.db.get_collection_document_names(env.cst_scenarios))
    # print(r.db.get_collection_document_names(env.cst_federations))
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