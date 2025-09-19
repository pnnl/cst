import os
import sys
import time
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from cosim_toolbox.dbms import create_metadata_manager


def get_times(cst_scalability: str, run_only: list):
    dir_scalability = Path("./"+cst_scalability)
    mdf = pd.DataFrame(data=[],
                       columns=["name", "n_feds", "n_subs", "n_fedsxsubs", "use_epts", "use_db", "use_pf", "time"])
    change = False
    cur = os.getcwd()
    for scenario_dir_path in dir_scalability.iterdir():
        if not scenario_dir_path.is_dir():
            continue
        scenario_dir_name = scenario_dir_path.name
        cnt = int(scenario_dir_name.split("_")[-1])
        if cnt not in run_only:
            continue
        scenario_name = f"{cst_scalability}_s_{cnt}"
        scalability_name = f"{cst_scalability}_{cnt}"
        if (scenario_dir_path / Path("meta_store")).is_dir():
            change = True
            os.chdir(scenario_dir_path)
            mgr = create_metadata_manager("json")
        else:
            mgr = create_metadata_manager("mongo")
        mgr.connect()

        scalability = mgr.read(cst_scalability, scalability_name)
        n_feds = scalability["number of feds"]
        n_subs = scalability["number of pubs"]
        use_epts = scalability["use endpoints"]
        use_db = scalability["use CST logger"]
        use_pf = scalability["use profiling"]
        results = scalability.get("results", {})
        proc_time = results.get("max_and_total", {}).get("federate_process_time")
        wall_time = results.get("max_and_total", {}).get("federate_wall_time")
        data = [[cnt, n_feds, n_subs, n_feds * n_subs, use_epts, use_db, use_pf, wall_time]]
        mdf = pd.concat([pd.DataFrame(data, columns=mdf.columns), mdf], ignore_index=True)
        if change:
            change = False
            os.chdir(cur)

    return mdf

def plot_times(name: str, run_only):
    tic = time.perf_counter()
    df = get_times(test_name, run_only)
    df = df.sort_values(by="name", ignore_index=True)
    toc = time.perf_counter()
    print(f"elapsed time: {toc - tic}")

    df.to_csv(f"{test_name}_timing_data.csv")
    N = end-beg
    flop = 0
    colors = []
    for i in range(0, N):
        if flop < 2:
            colors.append('b')
            flop = flop+1
        else:
            colors.append('r')
            flop = flop+1
            if flop == 4:
                flop = 0

    plt.scatter("time", "name", data=df, c=colors)
    plt.show()

    plt.bar("time", "name", width=0.1, data=df, color=colors)
    plt.show()

if __name__ == '__main__':
    beg = 1
    end = 49
    runs = list(range(beg, end))
    test_name = "cst_scale1"
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
    plot_times(test_name, runs)