"""
Create the initial version of cst_results_validator.py.

This script runs after the co-simulation is complete and validates
that all data that was published was correctly logged. This will
require either querying the time-series database or reading CSVs
written by the scalability federates. This can be included as part
of the test post-processing.

See full definition in "scalability_testing.md" in the "docs" folder
in the repo.

"""
import json
import logging
import os
import subprocess
import sys
import time
import psutil

from cst_federate import CST_Time

logger = logging.getLogger(__name__)

def run_scenarios(cst_scalability: str):
    lt = CST_Time()
    rt = CST_Time()
    semaphore = "finished.txt"
    run_only = list(range(1, 4))
    # run_only = list(range(49, 73))
    # run_only = list(range(1, 73))
    os.chdir(cst_scalability)
    for run in run_only:
        scenario_dir_name = f"test_{run}"
        with open('progress.log', 'w') as file:
            file.write(f"Scenario name: {scenario_dir_name}")

        print("~~~~~~~~~~ Running the scenario ~~~~~~~~~~", flush=True)
        # change to scenario directory to run test
        os.chdir(scenario_dir_name)
        scenario_name = f"{cst_scalability}_s_{run}"
        name = f"{cst_scalability}_{run}.json"
        with open(name, "r") as f:
            scalability = json.load(f)
            _f = scalability["number of feds"]
            _s = scalability["number of pubs"]
            _e = scalability["use endpoints"]
            _d = scalability["use CST logger"]
            _p = scalability["use profiling"]

        print(f"  Scalability name:{scenario_name}", flush=True)
        print(f"    Running settings: feds:{_f}, subs:{_s}, end_pts:{_e}, cst_log:{_d}, profile:{_p}", flush=True)

        kill_helics()
        if os.path.isfile(semaphore):
            os.remove(semaphore)
        try:
            lt.timing(True)
            pid = subprocess.run(["/bin/bash", f"./{scenario_name}.sh"])
            lt.timing(False)
            print(f"    Launch total wall time {lt.wall_time}", flush=True)
            print(f"    Launch total process time {lt.proc_time}", flush=True)

            rt.timing(True)
            while not os.path.exists(semaphore):
                time.sleep(60)
            rt.timing(False)
            print(f"    Total scenario run wall time {rt.wall_time}", flush=True)
            print(f"    Total scenario run process time {rt.proc_time}", flush=True)

        except Exception as ex:
            print("********** Exception **********", flush=True)
            print(ex, flush=True)
            continue

        print("  Gathering federate timing results", flush=True)
        # change to federate outputs directory to gather results
        os.chdir('federate_outputs')
        wtime = 0
        ptime = 0
        timing = {}
        for _ft in range(_f):
            name = f"fed_{_ft}"
            with open(name + "_timing.json", "r") as f:
                data = json.load(f)
                timing[name] = data
                if data['process_time'] > ptime:
                    ptime = data['process_time']
                if data['wall_time'] > wtime:
                    wtime = data['wall_time']
        timing['max_and_total'] = {
            'federate_process_time': ptime,
            'federate_wall_time': wtime,
            'launch_wall_time': lt.wall_time,
            'launch_process_time': lt.proc_time,
            'run_wall_time': rt.wall_time,
            'run_process_time': rt.proc_time
        }
        print(f"    Total wall time {wtime}", flush=True)
        print(f"    Total process time {ptime}", flush=True)

        # return to scenario directory to write results
        os.chdir("..")
        scalability = {}
        name = f"{cst_scalability}_{run}.json"
        with open(name, "r") as f:
            scalability = json.load(f)
            scalability['results'] = timing
        with open(name, "w") as f:
            json.dump(scalability, f, ensure_ascii=False, indent=2)

        # return to root experiment directory
        os.chdir("..")
        print("~~~~~~~~~~ Done with scenario ~~~~~~~~~~~~", flush=True)

    # return to root directory
    os.chdir("..")

def wait_for_helics():
    helics_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        if proc.info["name"] == "helics_broker":
            helics_procs.append(proc)
    psutil.wait_procs(helics_procs)

def kill_helics():
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        if proc.info["name"] == "helics_broker":
            proc.kill()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_scenarios(sys.argv[1])
    else:
        run_scenarios('cst_scale_z1')
