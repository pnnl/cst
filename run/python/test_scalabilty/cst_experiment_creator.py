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
from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox.helicsConfig import HelicsMsg, Collect

class Runner:

    def __init__(self, scalability_name, docker=False):
        self.cst_scalability = scalability_name
        self.docker = docker
        print(env.cst_mongo)
        self.db = DBConfigs(env.cst_mongo, env.cst_mongo_db)

        # Uncomment the next three lines for debug
        # DBConfigs.federation_database(True)
        # self.db.db[self.cst_scalability].drop()
        # self.db.add_collection(self.cst_scalability)

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
        #     script += f"(exec python3 -c \"import cosim_toolbox.federateLogger as datalog; " \
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

        _p = "fed_"
        os.makedirs("federate_outputs")
        federation = { "federation": {} }
        prv = federate_size - 1
        for _f in range(federate_size):
            name = f"{_p}{_f}"
            t1 = HelicsMsg(name, period=30)
            if self.docker:
                t1.config("broker_address", "10.5.0.2")
            t1.config("core_type", "zmq")
            t1.config("log_level", "warning")
            t1.config("period", 30)  # maybe different interval for testing
            t1.config("uninterruptible", False)
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
                "image": "cosim-cst:latest",
                "command": command,
                "federate_type": "combo",
                "time_step": 120,
                "profile": profiling,
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

        # Always output federation file to disk:
        with open(f"{federation_name}.json", "w") as f:
            json.dump(federation['federation'], f, ensure_ascii=False, indent=2)
        if cst_logger:
            self.db.remove_dict(env.cst_federations, None, federation_name)
            self.db.add_dict(env.cst_federations, federation_name, federation)
            # Uncomment for debug
            # print(env.cst_federations, self.db.get_dict_names_in_collection(env.cst_federations))

        scenario = self.db.scenario(analysis_name,
                                    federation_name,
                                    "2023-12-07T15:31:27",
                                    "2023-12-07T16:31:27",
                                    self.docker)
        # Always output scenario file to disk:
        with open(f"{scenario_name}.json", "w") as f:
            json.dump(scenario, f, ensure_ascii=False, indent=2)
        if cst_logger:
            self.db.remove_dict(env.cst_scenarios, None, scenario_name)
            self.db.add_dict(env.cst_scenarios, scenario_name, scenario)
            # Uncomment the next two lines for debug
            # print(env.cst_scenarios, self.db.get_dict_names_in_collection(env.cst_scenarios))
            # print(scenario_name, self.db.get_dict(env.cst_scenarios, None, scenario_name))

        scalability = {
            "number of feds": federate_size,
            "number of pubs": subs_size,
            "use endpoints": endpoints,
            "use CST logger": cst_logger,
            "use profiling": profiling,
            "results": {}
        }
        # Always output scalability file to disk:
        with open(f"{scalability_name}.json", "w") as f:
            json.dump(scalability, f, ensure_ascii=False, indent=2)
        if cst_logger:
            self.db.remove_dict(self.cst_scalability, None, scalability_name)
            self.db.add_dict(self.cst_scalability, scalability_name, scalability)
            # Uncomment the next two lines for debug
            # print(self.cst_scalability, self.db.get_dict_names_in_collection(self.cst_scalability))
            # print(scenario_name, self.db.get_dict(self.cst_scalability, None, scenario_name))

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


def main():
    if len(sys.argv) > 2:
        tmp_docker = True
        if sys.argv[2].lower() in ['false', '0', 'f', 'n', 'no', 'nope', 'nada', 'noway', 'uh-uh']:
            tmp_docker = False
        r = Runner(sys.argv[1], tmp_docker)
    else:
        r = Runner("cst_scale_z1", False)
    r.define_scenarios()
    print(r.db.get_dict_names_in_collection(env.cst_scenarios))
    print(r.db.get_dict_names_in_collection(r.cst_scalability))
    print(r.db.get_dict_names_in_collection(env.cst_federations))


if __name__ == "__main__":
    main()