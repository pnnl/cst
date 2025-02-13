# %%
import json
import os
import time
from pathlib import Path

import pandas as pd


def get_times(cst_scalability: str):
    cst_scalability = Path(cst_scalability)
    test_num = int(cst_scalability.name[-1])
    mdf = pd.DataFrame(data=[],
                      columns=["name", "n_feds", "n_subs", "n_fedsxsubs", "use_epts", "use_db", "use_pf", "time"])
    for scenario_dir_path in cst_scalability.iterdir():
        if not scenario_dir_path.is_dir():
            continue
        scenario_dir_name = scenario_dir_path.name
        cnt = int(scenario_dir_name.split("_")[-1])
        scenario_name = f"scale_test{test_num}_s_{cnt}"
        name = scenario_dir_path / Path(f"scale_test{test_num}_{cnt}.json")
        with open(name, "r") as f:
            scalability = json.load(f)
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
    return mdf


# %%

if __name__ == '__main__':
    os.chdir("C:\\Users\\gray570\\workspace\\copper\\run\\python\\test_scalabilty")
    tic = time.perf_counter()
    test_name = "scale_test9"
    df = get_times(test_name)
    toc = time.perf_counter()
    print(f"elapsed time: {toc - tic}")
    # %%
    df.to_csv(f"{test_name}_timing_data.csv")
