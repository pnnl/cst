#%%
import plotly.express as px
import pandas as pd
import json
import time
from pathlib import Path
import sys
import os

def get_times(cu_scalability: str):
    cu_scalability = Path(cu_scalability)
    test_num = int(cu_scalability.name[-1])
    df = pd.DataFrame(data=[], columns=["name", "n_feds", "n_subs", "n_fedsxsubs", "use_epts", "use_db", "use_pf", "time"])
    for scenario_dir_path in cu_scalability.iterdir():
        scenario_dir_name = scenario_dir_path.name
        cnt = int(scenario_dir_name.split("_")[-1])
        scenario_name = f"scenario_{cnt}"
        name = f"{scenario_dir_path}/scalability_{cnt}.json"
        with open(name, "r") as f:
            scalability = json.load(f)
        n_feds = scalability["number of feds"]
        n_subs = scalability["number of pubs"]
        use_epts = scalability["use endpoints"]
        use_db = scalability["use CST logger"]
        use_pf = scalability["use profiling"]
        results = scalability.get("results", {})
        proc_time = results.get("total", {}).get("process_time")
        wall_time = results.get("total", {}).get("wall_time")
        data = [[cnt, n_feds, n_subs, n_feds*n_subs, use_epts, use_db, use_pf, wall_time]]
        df = pd.concat([ pd.DataFrame(data, columns=df.columns), df], ignore_index=True)
    return df
#%%

if __name__ == '__main__':
    os.chdir("C:\\Users\\gray570\\workspace\\copper\\run\\python\\test_scalabilty")
    tic = time.perf_counter()
    df = get_times('scale_test2')
    toc = time.perf_counter()
    print(f"elapsed time: {toc - tic}")
    #%%
    df.to_csv("timing_data.csv")
    df = df.loc[df.name !=57]

    #%%
    px.scatter(df, x="n_fedsxsubs", y="time").show()
    #%%
    px.scatter_matrix(df).show()
    #%%
    corr = df.loc[df.name!=57].corr().time
    corr = corr.loc[["name", "n_feds", "n_subs", "n_fedsxsubs", "use_epts", "use_db", "use_pf"]]

    fig = px.bar(corr).show()
    #%%
    df1 = df.loc[:, ["name", "n_feds", "n_subs", "n_fedsxsubs", "use_epts", "use_db", "use_pf", "time"]]
    df1 = df1.sort_values(by="name", ignore_index=True)
    df1.to_csv("time_results.csv", index=False)
    #%%
    df_w_ept = df.loc[df.use_epts]
    df_wo_ept = df.loc[df.use_epts!=True]
    df_w_db = df.loc[df.use_db]
    df_wo_db = df.loc[df.use_db!=True]
    df_w_pf = df.loc[df.use_pf]
    df_wo_pf = df.loc[df.use_pf!=True]
