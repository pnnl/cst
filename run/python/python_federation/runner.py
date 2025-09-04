"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author:
mitch.pelton@pnnl.gov
"""
from cosim_toolbox.helicsConfig import HelicsMsg
from cosim_toolbox.dockerRunner import DockerRunner
from data_management.factories import create_metadata_manager


class Runner:

    def __init__(self, scenario_name, analysis_name, federation_name, docker=False):
        self.scenario_name = scenario_name
        self.analysis_name = analysis_name
        self.federation_name = federation_name
        self.docker = docker

    def define_scenario(self):
        names = ["Battery", "EVehicle"]
        t1 = HelicsMsg(names[0], period=60)
        if self.docker:
            t1.config("broker_address", "10.5.0.2")
        t1.config("log_level", "warning")
        t1.config("terminate_on_error", True)
#        t1.config("wait_for_current_time_update", True)
        t1.pubs_e(names[0] + "/EV1_current", "double", "A", True)
        t1.subs_e(names[1] + "/EV1_voltage", "double", "V")
        t1 = {
            "logger": False,
            "image": "cosim-cst:latest",
            "command": f"python3 simple_federate.py {names[0]} {self.scenario_name}",
            "federate_type": "value",
            "HELICS_config": t1.write_json()
        }

        t2 = HelicsMsg(names[1], period=60)
        if self.docker:
            t2.config("broker_address", "10.5.0.2")
        t2.config("log_level", "warning")
        t2.config("terminate_on_error", True)
#        t2.config("wait_for_current_time_update", True)
        t2.subs_e(names[0] + "/EV1_current", "double", "A")
        t2.pubs_e(names[1] + "/EV1_voltage", "double", "V", True)
        t2 = {
            "logger": False,
            "image": "cosim-cst:latest",
            "command": f"python3 simple_federate.py {names[1]} {self.scenario_name}",
            "federate_type": "value",
            "HELICS_config": t2.write_json()
        }
        diction = {
            "federation": {
                names[0]: t1,
                names[1]: t2
            }
        }
        # print(diction)

        scenario = {
            "analysis": self.analysis_name,
            "federation": self.federation_name,
            "start_time": "2023-12-07T15:31:27",
            "stop_time": "2023-12-08T15:31:27",
            "docker": self.docker
        }

        with create_metadata_manager() as mgr:
            print(f"Writing configuration files to '{mgr.location}'...")
            mgr.write_federation(self.federation_name, diction, overwrite=True)
            mgr.write_scenario(self.scenario_name, scenario, overwrite=True)
            print("Configuration files written successfully.")


def main():
    remote = False
    with_docker = False
    r = Runner("MyScenario", "MyAnalysis", "MyFederation", with_docker)
    r.define_scenario()
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