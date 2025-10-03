"""
cst_experiment_creator.py is responsible for setting up the scalability tests by:

-Creating the folder structure for each scenario
-Configuration JSONs for the federates
-federate_*.json for each scenario
-federation_*.json for each scenario
-scenario_*.json for each scenario
-scalability_*.json for each scenario
-Loading all of the above in the metadataDB or directory given the particular test
"""
import json
import os
import shutil
import stat
import sys

import cosim_toolbox as env
from cosim_toolbox.sims import HelicsMsg, Collect
from cosim_toolbox.dbms import create_metadata_manager

class Runner:

    def __init__(self, scalability_name, docker=False):
        self.cst_scalability = scalability_name
        self.docker = docker
        print(env.cst_mongo)

        # Uncomment the next three lines for debug for removal of dictionaries
        # with create_metadata_manager("mongo") as mgr:
        #     mgr.helper.get_collection("cst_scale_z1").drop()

    @staticmethod
    def define_runner():
        script = """
IMAGE="cosim-cst:latest"

docker images -q ${IMAGE} > docker_version
hostname > hostname

docker run \\
    -itd \\
    --rm --name test_cst \\
    --network=none \\
    -e LOCAL_UID=$LOCAL_UID \\
    -e LOCAL_USER=$LOCAL_USER \\
    -e CST_HOST=$CST_HOST \\
    -e POSTGRES_HOST=$POSTGRES_HOST \\
    -e MONGO_HOST=$MONGO_HOST \\
    -e MONGO_PORT:$MONGO_PORT \\
    -w=/home/worker/case \\
    --mount type=bind,source=".",destination="/home/worker/case" \\
    ${IMAGE} \\
    /bin/bash -c "./run.sh"
"""
        # Write runner file
        sh_file = "docker_run.sh"
        op = open(sh_file, 'w')
        op.write(script)
        op.close()

        # Change mode to executable for shell file
        st = os.stat(sh_file)
        os.chmod(sh_file, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    @staticmethod
    def define_shell(scenario_name: str, scenario_def: dict,
                     scalability_def: dict,
                     federation_def: dict) -> None:
        """Create the shell for the provided scenario

        Args:
            scenario_name (str): Name of the scenario diction
            scenario_def (dictionary): Definition of the scenario diction
            scalability_def (dictionary): Definition of the scalability diction
            federation_def (dictionary): Definition of the federation diction
        """

        analysis_name = scenario_def["analysis"]
        federation = federation_def["federation"]
        script = '#!/bin/bash\n\n'

        # Add profiling
        bf = ""
        if scalability_def["use profiling"]:
#            bf = "export BENCH_PROFILE=1 && "
            script += "export BENCH_PROFILE=1\n"

        # script += "source /home/worker/venv/bin/activate\n"

        # Add helics broker federate
        cnt = 0
        # if scalability_def["use CST logger"]:
        #     cnt += 1
        fed_cnt = federation.__len__() + cnt
        script += f"(exec helics_broker -f {fed_cnt} --loglevel=warning --name=broker &> broker.log &)\n"

        # Add cst federate
        for name in federation:
            script += f"({bf}{federation[name]['command']} &> {name}.log &)\n"

        # Add data logger federate
        # if scalability_def["use CST logger"]:
        #     script += f"(exec python3 -c \"import cosim_toolbox.sims.federateLogger as datalog; " \
        #               f"datalog.main('FederateLogger', '{analysis_name}', '{scenario_name}')\" &> logger.log &)\n"

        # add monitor to set semaphore
        script += f"(exec ../../monitor.sh &)\n"

        # Write runner file
        sh_file = scenario_name + ".sh"
        op = open(sh_file, 'w')
        op.write(script)
        op.close()

        # Change mode to executable for shell file
        st = os.stat(sh_file)
        os.chmod(sh_file, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def add_federation(self, count: int, federate_size: int, subs_size: int, endpoints: bool, cst_logger: bool, profiling: bool):
        # Collect all outputs
        collect = Collect.YES

        analysis_name = f"{self.cst_scalability}_f{federate_size}_s{subs_size}"
        scalability_name = f"{self.cst_scalability}_{count}"
        scenario_name = f"{self.cst_scalability}_s_{count}"
        federation_name = f"{self.cst_scalability}_f_{count}"  #_f{federate_size}_s{subs_size}_{endpoints}_{cst_logger}_{profiling}"

        # Uncomment the next three lines for debug for removal of dictionaries
        # sn = f"scale_t1_s_{count}"
        # fn = f"scale_t1_f_{count}"

        _p = "fed_"
        os.makedirs("federate_outputs")
        federation = { "federation": {} }
        prv = federate_size - 1
        for _f in range(federate_size):
            name = f"{_p}{_f}"
            t1 = HelicsMsg(name, period=30)
            if self.docker:
                t1.config("broker_address", "10.5.0.2")
            t1.config("log_level", "warning")
            t1.config("terminate_on_error", True)
            #        t1.config("wait_for_current_time_update", True)
            t1.collect(collect)

            for _s in range(subs_size):
                t1.pubs_e(f"{_p}{_f}/v_{_s}", "double", "V", True, collect)
                t1.subs_e(f"{_p}{prv}/v_{_s}", "double", "V")
                if endpoints:
                    if False:  # cst_logger:
                        t1.endpt(f"{_p}{_f}/pt_{_s}", [f"{_p}{prv}/pt_{_s}", f"FederateLogger/pt_{_s}"], True, collect)
                    else:
                        t1.endpt(f"{_p}{_f}/pt_{_s}", f"{_p}{prv}/pt_{_s}", True, collect)

            command = f"exec python3 ../../cst_federate.py {name} {scenario_name} {cst_logger}"
            federation["federation"][name] = {
                "logger": False,
                "image": "cosim-cst:latest",
                "command": command,
                "federate_type": "combo",
                "HELICS_config": t1.write_json()
            }
            if prv == federate_size-1:
                prv = 0
            else:
                prv += 1
        # Uncomment the next three lines for debug
        #     print(diction)
        #     with open(f"{name}.json", "w") as f:
        #         json.dump(t1.write_json(), f, ensure_ascii=False, indent=2)

        scenario = {
            "analysis": analysis_name,
            "federation": federation_name,
            "start_time": "2023-12-07T15:31:27",
            "stop_time": "2023-12-07T16:31:27",
            "docker": self.docker
        }

        scalability = {
            "number of feds": federate_size,
            "number of pubs": subs_size,
            "use endpoints": endpoints,
            "use CST logger": cst_logger,
            "use profiling": profiling,
            "results": {}
        }

        if cst_logger:
            backend = "mongo"
            # # Always output federation file to disk:
            # with open(f"{federation_name}.json", "w") as f:
            #     json.dump(federation['federation'], f, ensure_ascii=False, indent=2)
            # # Always output scenario file to disk:
            # with open(f"{scenario_name}.json", "w") as f:
            #     json.dump(scenario, f, ensure_ascii=False, indent=2)
            # # Always output scalability file to disk:
            # with open(f"{scalability_name}.json", "w") as f:
            #     json.dump(scalability, f, ensure_ascii=False, indent=2)
        else:
            backend = "json"

        with create_metadata_manager(backend) as mgr:
            print(f"Writing configuration files to '{mgr.location}'...")
            mgr.write_federation(federation_name, federation, overwrite=True)
            mgr.write_scenario(scenario_name, scenario, overwrite=True)
            mgr.write(self.cst_scalability, scalability_name, scalability, overwrite=True)

            # Uncomment the next three lines for debug for removal of dictionaries
            # mgr.delete_federation(f"cst_scale_z1_f_{count}")
            # mgr.delete_scenario(f"cst_scale_z1_s_{count}")

            print("Configuration files written successfully.")

        self.define_shell(scenario_name, scenario, scalability, federation)
#        self.define_runner()
#        DockerRunner.define_yaml(scenario_name)

    def define_scenarios(self):
        federates = [5, 50, 500]
        subs_pubs = [1, 10, 100]
        endpoints = [True, False]
        cst_logger = [True, False]
        profiling = [True, False]

        if os.path.isdir(self.cst_scalability):
            print("experiment folder already exists, deleting and moving on...")
            shutil.rmtree(self.cst_scalability)
        os.makedirs(self.cst_scalability)
        os.chdir(self.cst_scalability)

        cnt = 1
        for _f in federates:
            for _s in subs_pubs:
                for _e in endpoints:
                    for _d in cst_logger:
                        for _p in profiling:
                            scenario_name = f"test_{cnt}"
                            label = f"Scalability name:{scenario_name}\n" \
                                    f"  Settings-> feds:{_f}, subs:{_s}, end_pts:{_e}, cst_log:{_d}, profile:{_p}"
                            print(label)
                            os.makedirs(scenario_name)
                            os.chdir(scenario_name)
                            self.add_federation(cnt, _f, _s, _e, _d, _p)
                            cnt += 1
                            os.chdir("..")


def create_tests(scalability_name: str):
    tmp_docker = False
    if len(sys.argv) > 1:
        scalability_name = sys.argv[1]
    r = Runner(scalability_name, tmp_docker)
    r.define_scenarios()


if __name__ == "__main__":
    test_name="cst_scale1"
    create_tests(test_name)