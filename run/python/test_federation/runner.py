"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""
from cosim_toolbox.sims import DockerRunner
from cosim_toolbox.sims import HelicsMsg, Collect
from cosim_toolbox.dbms import create_metadata_manager


class Runner:

    def __init__(self, scenario_name, analysis_name, federation_name, docker=False):
        self.scenario_name = scenario_name
        self.analysis_name = analysis_name
        self.federation_name = federation_name
        self.docker = docker

    def define_scenario(self):
        names = ["Battery", "EVehicle"]
        t1 = HelicsMsg(names[0], period=30)
        if self.docker:
            t1.config("broker_address", "10.5.0.2")
        t1.config("terminate_on_error", True)
        # t1.config("wait_for_current_time_update", True)
        t1.collect(Collect.YES)

        t1.pubs_e(names[0] + "/current", "double", "A", True, Collect.YES)
        t1.subs_e(names[1] + "/voltage", "double", "V")
        t1.pubs_e(names[0] + "/current2", "integer", "A", True, Collect.NO)
        t1.subs_e(names[1] + "/voltage2", "integer", "V")
        t1.pubs_e("current3", "boolean", "A")
        t1.subs_e(names[1] + "/voltage3", "boolean", "V")
        t1.pubs_e("current4", "string", "A")
        t1.subs_e(names[1] + "/voltage4", "string", "V")
        t1.pubs_e(names[0] + "/current5", "complex", "A", True, Collect.MAYBE)
        t1.subs_e(names[1] + "/voltage5", "complex", "V")
        t1.pubs_e(names[0] + "/current6", "vector", "A", True, Collect.NO)
        t1.subs_e(names[1] + "/voltage6", "vector", "V")
        t1.endpt(names[0] + "/current1", names[1] + "/voltage1", True, Collect.YES)

        t2 = HelicsMsg(names[1], period=60)
        if self.docker:
            t2.config("broker_address", "10.5.0.2")
        t2.config("terminate_on_error", True)
        # t2.config("wait_for_current_time_update", True)
        t2.collect(Collect.NO)

        t2.subs_e(names[0] + "/current", "double", "A")
        t2.pubs_e("voltage", "double", "V")
        t2.subs_e(names[0] + "/current2", "integer", "A")
        t2.pubs_e("voltage2", "integer", "V")
        t2.subs_e(names[0] + "/current3", "boolean", "A")
        t2.pubs_e(names[1] + "/voltage3", "boolean", "V", True, Collect.NO)
        t2.subs_e(names[0] + "/current4", "string", "A")
        t2.pubs_e("voltage4", "string", "V")
        t2.subs_e(names[0] + "/current5", "complex", "A")
        t2.pubs_e("voltage5", "complex", "V")
        t2.subs_e(names[0] + "/current6", "vector", "A")
        t2.pubs_e("voltage6", "vector", "V")
        t2.endpt("voltage1", names[0] + "/current1", None, Collect.YES)

        f1 = {
            "logger": False,
            "image": "cosim-cst:latest",
            "command": f"python3 simple_federate.py {names[0]} {self.scenario_name}",
            "federate_type": "combo",
            "HELICS_config": t1.write_json()
        }
        f2 = {
            "logger": False,
            "image": "cosim-cst:latest",
            "command": f"python3 simple_federate2.py {names[1]} {self.scenario_name}",
            "federate_type": "combo",
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

        scenario = {
            "analysis": self.analysis_name,
            "federation": self.federation_name,
            "start_time": "2023-12-07T15:31:27",
            "stop_time": "2023-12-08T15:31:27",
            "docker": self.docker
        }

        with create_metadata_manager(backend="json") as mgr:
            print(f"Writing configuration files to '{mgr.location}'...")
            mgr.write_federation(self.federation_name, diction, overwrite=True)
            mgr.write_scenario(self.scenario_name, scenario, overwrite=True)
            print("Configuration files written successfully.")


def main():
    remote = False
    with_docker = False
    r = Runner("test_scenario", "test_analysis", "test_federation", with_docker)
    r.define_scenario()
    if with_docker:
        DockerRunner.define_yaml(r.scenario_name)
        if remote:
            DockerRunner.run_remote_yaml(r.scenario_name)
        else:
            DockerRunner.run_yaml(r.scenario_name)
    else:
        DockerRunner.define_sh(r.scenario_name, use_meta_db="json", use_data_db="csv")

if __name__ == "__main__":
    main()
