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

        print(f"Scenario: {scenario_name} Test: {scenario_dir_path} -> results:{results}")
        data = [[cnt, n_feds, n_subs, n_feds * n_subs, use_epts, use_db, use_pf, wall_time]]
        mdf = pd.concat([pd.DataFrame(data, columns=mdf.columns), mdf], ignore_index=True)
        if change:
            change = False
            os.chdir(cur)

    return mdf

def plot_times(name: str, run_only):
    tic = time.perf_counter()
    df = get_times(name, run_only)
    toc = time.perf_counter()
    print(f"elapsed time: {toc - tic}")

    df.to_csv(f"{name}/timing_data.csv")

    colors = {True: 'red', False: 'blue'}
    ax = df.plot(kind='scatter', x="time", y="name", c=df['use_db'].map(colors))
    ax.set_xlabel('Time(secs)')
    ax.set_ylabel('Scenario')
    plt.show()

    ax = df.plot(kind='scatter', x="n_fedsxsubs", y="time", c=df['use_db'].map(colors))
    ax.set_xlabel('Number of Outputs')
    ax.set_ylabel('Time(secs)')
    plt.show()

    df = df.sort_values(by=["use_epts", "n_fedsxsubs", "use_db", "use_pf"], ignore_index=True)
    print(df)
    ax = df.plot(kind='bar', x="name", y="time", width=0.3, color=df['use_db'].map(colors))
    ax.set_ylabel('Time(secs)')
    ax.set_xlabel('Scenario')
    plt.show()

if __name__ == '__main__':
    beg = 1
    end = 41
    runs = list(range(beg, end))
    test_name = "cst_scale1"
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
    plot_times(test_name, runs)