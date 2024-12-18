import plotly.express as px
import plotly.graph_objs as go
import pandas as pd
import numpy as np

def read_time5x():
    df9 = pd.read_csv(f"scale_test9_read_test5x.csv")
    df7 = pd.read_csv(f"scale_test7_read_test5x.csv")
    df8 = pd.read_csv(f"scale_test8_read_test5x.csv")
    df9["time_scale"] = 0
    df7["time_scale"] = 1
    df8["time_scale"] = 1
    df9["test"] = 9
    df7["test"] = 7
    df8["test"] = 8
    df9["ts_indexes"] = 0
    df7["ts_indexes"] = 1
    df8["ts_indexes"] = 2
    df = pd.concat([df9, df7, df8], ignore_index=True)
    print(df.head())
    df.loc[df.federate == "fed_0", "federate"] = "one"
    df.loc[df.federate == "fed_1", "federate"] = "one"
    df.loc[df.federate == "fed_2", "federate"] = "one"
    df.loc[df.federate == "fed_3", "federate"] = "one"
    df.loc[df.federate == "fed_4", "federate"] = "one"
    df.loc[df.federate == "3 feds", "federate"] = "three"
    df = df.groupby(["scenario", "schema", "schema_rows", "selected_rows", "time_scale", "test", "ts_indexes",
                "federate"]).time.mean().rename_axis().reset_index()
    df['t'] = df["time"] - 0.0548
    df["per_schema_row"] = df.time/df.schema_rows
    df["per_selected_row"] = df.time/df.selected_rows
    df["a"] = df.t/df.schema_rows
    df["id"] = df.scenario.str[12:]
    dfp = df.pivot(index=["id", "schema_rows", "selected_rows", "federate"],
             columns="ts_indexes", values="time").rename_axis(columns=None).reset_index()
    dfp["mult"] = dfp[1]/dfp[0]
    dfp["mult2"] = dfp[2]/dfp[0]
    print(df.head())
    fig = px.histogram(
        dfp,
        x=["mult", "mult2"],
        color="federate",
        nbins=100,
        barmode="group",
        labels={"mult": "1 index", "mult2": "2 index", "value": "Slowdown"}
    )
    fig.show(renderer="browser")
    # fig = px.scatter_matrix(df, dimensions=["time_scale", "ts_indexes", "schema_rows", "selected_rows", "time", "per_schema_row", "per_selected_row"])
    # fig.show(renderer="browser")
    # corr = df.loc[:, ["time_scale", "ts_indexes", "schema_rows", "selected_rows", "time", "per_schema_row", "per_selected_row"]].corr().time
    # corr = corr.loc[["time_scale", "ts_indexes", "schema_rows", "selected_rows", "per_schema_row", "per_selected_row"]]
    # fig = px.bar(corr)
    # fig.show(renderer="browser")
    fig = px.histogram(
        df,
        # x="schema_rows",
        x="per_schema_row",
        color="ts_indexes",
        nbins=100,
        barmode="group",
    )
    fig.show(renderer="browser")
    df.ts_indexes = df.ts_indexes.astype(str)
    fig = px.scatter(
        df,
        x="schema_rows",
        y="per_schema_row",
        color="ts_indexes",
        symbol="ts_indexes",
        log_y=False,
        log_x=True,
        labels={"schema_rows": "Schema Rows", "per_schema_row": "Query Time Per Row in Schema"},
    )
    fig.show(renderer="browser")
    df.ts_indexes = df.ts_indexes.astype(str)
    fig = px.scatter(
        df,
        x="schema_rows",
        y="time",
        color="ts_indexes",
        symbol="ts_indexes",
        log_y=True,
        log_x=True,
        labels={"schema_rows": "Schema Rows", "per_schema_row": "Query Time Per Row in Schema"},
    )
    x = 240*10**(np.array(list(range(1, 6, 1))))
    y1 = 4.6e-7*x+0.0548
    y2 = 6.7e-7*x+0.064
    # y3 = 7.5e-7*x+0.17
    y3 = 7.5e-7*x+0.1
    y4 = 5.6e-7*x+0.0548

    # fig.add_trace(go.Scatter(x=x, y=y1))
    # fig.add_trace(go.Scatter(x=x, y=y2))
    fig.add_trace(go.Scatter(x=x, y=y3, name="7.5e-7*x+0.1"))
    fig.add_trace(go.Scatter(x=x, y=y4, name="5.6e-7*x+0.0548"))
    fig.show(renderer="browser")



def read_time():
    df5 = pd.read_csv(f"scale_test5_read_test.csv")
    df6 = pd.read_csv(f"scale_test6_read_test.csv")
    df7 = pd.read_csv(f"scale_test7_read_test.csv")
    df8 = pd.read_csv(f"scale_test8_read_test.csv")
    df9 = pd.read_csv(f"scale_test9_read_test.csv")
    df5["time_scale"] = 1
    df6["time_scale"] = 0
    df7["time_scale"] = 1
    df8["time_scale"] = 1
    df9["time_scale"] = 0
    df5["test"] = 5
    df6["test"] = 6
    df7["test"] = 7
    df8["test"] = 8
    df9["test"] = 9
    df5["ts_indexes"] = 1
    df6["ts_indexes"] = 0
    df7["ts_indexes"] = 1
    df8["ts_indexes"] = 2
    df9["ts_indexes"] = 0
    df = pd.concat([df5, df6, df7, df8, df9], ignore_index=True)
    df["per_schema_row"] = df.time/df.schema_rows
    df["per_selected_row"] = df.time/df.selected_rows
    print("max")
    print(f"test5 {df.loc[df.test==5, 'per_schema_row'].max():.3g}")
    print(f"test6 {df.loc[df.test==6, 'per_schema_row'].max():.3g}")
    print(f"test7 {df.loc[df.test==7, 'per_schema_row'].max():.3g}")
    print(f"test8 {df.loc[df.test==8, 'per_schema_row'].max():.3g}")
    print(f"test9 {df.loc[df.test==9, 'per_schema_row'].max():.3g}")
    print("min")
    print(f"test5 {df.loc[df.test==5, 'per_schema_row'].min():.3g}")
    print(f"test6 {df.loc[df.test==6, 'per_schema_row'].min():.3g}")
    print(f"test7 {df.loc[df.test==7, 'per_schema_row'].min():.3g}")
    print(f"test8 {df.loc[df.test==8, 'per_schema_row'].min():.3g}")
    print(f"test9 {df.loc[df.test==9, 'per_schema_row'].min():.3g}")
    print("mean")
    print(f"test5 {df.loc[df.test==5, 'per_schema_row'].mean():.3g}")
    print(f"test6 {df.loc[df.test==6, 'per_schema_row'].mean():.3g}")
    print(f"test7 {df.loc[df.test==7, 'per_schema_row'].mean():.3g}")
    print(f"test8 {df.loc[df.test==8, 'per_schema_row'].mean():.3g}")
    print(f"test9 {df.loc[df.test==9, 'per_schema_row'].mean():.3g}")

    fig = px.scatter_matrix(df, dimensions=["time_scale", "ts_indexes", "schema_rows", "selected_rows", "time", "per_schema_row", "per_selected_row"])
    fig.show(renderer="browser")
    corr = df.loc[:, ["time_scale", "ts_indexes", "schema_rows", "selected_rows", "time", "per_schema_row", "per_selected_row"]].corr().time
    corr = corr.loc[["time_scale", "ts_indexes", "schema_rows", "selected_rows", "per_schema_row", "per_selected_row"]]
    fig = px.bar(corr)
    fig.show(renderer="browser")
    fig = px.histogram(
        df,
        # x="schema_rows",
        x="per_schema_row",
        color="ts_indexes",
        nbins=100,
        barmode="group",
    )
    fig.show(renderer="browser")
    df.ts_indexes = df.ts_indexes.astype(str)
    fig = px.scatter(
        df,
        x="schema_rows",
        y="time",
        color="ts_indexes",
        symbol="ts_indexes",
        log_y=True,
        log_x=True,
    )
    fig.show(renderer="browser")

def analyze_run_time_db_vs_csv():
    df5 = pd.read_csv(f"scale_test5_timing_data.csv")
    df6 = pd.read_csv(f"scale_test6_timing_data.csv")
    df7 = pd.read_csv(f"scale_test7_timing_data.csv")
    df8 = pd.read_csv(f"scale_test8_timing_data.csv")
    df9 = pd.read_csv(f"scale_test9_timing_data.csv")
    df5["time_scale"] = 1
    df6["time_scale"] = 0
    df7["time_scale"] = 1
    df8["time_scale"] = 1
    df9["time_scale"] = 0
    df5["test"] = 5
    df6["test"] = 6
    df7["test"] = 7
    df8["test"] = 8
    df9["test"] = 9
    df5["ts_indexes"] = 1
    df6["ts_indexes"] = 0
    df7["ts_indexes"] = 1
    df8["ts_indexes"] = 2
    df9["ts_indexes"] = 0
    df = pd.concat([df5, df6, df7, df8, df9], ignore_index=True)
    df = df.pivot(index=["n_feds", "n_subs", "n_fedsxsubs", "use_epts", "use_pf", "time_scale", "test", "ts_indexes"],
             columns="use_db", values="time").rename_axis(columns=None).reset_index()
    df["total_inputs"] = df.n_fedsxsubs + df.use_epts*df.n_fedsxsubs
    df["inputs_per_fed"] = df.n_subs + df.use_epts*df.n_subs
    df["diff"] = df[True] - df[False]
    df["mult"] = df[True] / df[False]
    print(df.head())
    df.n_feds = df.n_feds.astype(str)
    # Remove outliers
    fig = px.scatter(
        df.loc[df.mult < 10],
        x="inputs_per_fed",
        y="mult",
        # facet_col="use_epts",
        hover_data=["n_feds", "n_subs", "use_pf", True, False],
        color="n_feds",
        log_x=True, log_y=False,
        # title=f"Scale test {i}",
        title="Database slowdown relative to csv output",
        marginal_y="histogram",
        labels={"mult": "Slowdown", "total_inputs": "Total Federation Inputs", "inputs_per_fed": "Inputs per Fed"},

    )
    fig.update_layout(
        margin={"l": 10, "r": 10, "b": 10, "t": 50},
    )
    fig.show(renderer="browser")


def analyze_run_time_timescaledb():
    df5 = pd.read_csv(f"scale_test5_timing_data.csv")
    df6 = pd.read_csv(f"scale_test6_timing_data.csv")
    df7 = pd.read_csv(f"scale_test7_timing_data.csv")
    df8 = pd.read_csv(f"scale_test8_timing_data.csv")
    df9 = pd.read_csv(f"scale_test9_timing_data.csv")
    df5["time_scale"] = True
    df6["time_scale"] = False
    df7["time_scale"] = True
    df8["time_scale"] = True
    df9["time_scale"] = False
    df5["test"] = 5
    df6["test"] = 6
    df7["test"] = 7
    df8["test"] = 8
    df9["test"] = 9
    df5["ts_indexes"] = 1
    df6["ts_indexes"] = 0
    df7["ts_indexes"] = 1
    df8["ts_indexes"] = 2
    df9["ts_indexes"] = 0
    df = pd.concat([df7, df8, df9], ignore_index=True)
    df = df.loc[df.use_db]
    df = df.pivot(index=["n_feds", "n_subs", "n_fedsxsubs", "use_epts", "use_pf"],
             columns="ts_indexes", values="time").rename_axis(columns=None).reset_index()

    df["total_inputs"] = df.n_fedsxsubs + df.use_epts*df.n_fedsxsubs
    df["inputs_per_fed"] = df.n_subs + df.use_epts*df.n_subs
    df["diff"] = df[1] - df[0]
    df["mult"] = df[1] / df[0]
    df["diff2"] = df[2] - df[0]
    df["mult2"] = df[2] / df[0]
    df.n_feds = df.n_feds.astype(str)
    # Remove outliers
    fig = px.scatter(
        df,
        x="inputs_per_fed",
        y="mult",
        # facet_col="use_epts",
        hover_data=["n_feds", "n_subs", "use_pf", True, False],
        color="n_feds",
        log_x=True, log_y=False,
        # title=f"Scale test {i}",
        title="TimescaleDB slowdown",
        marginal_y="histogram",
        labels={"mult": "Slowdown", "total_inputs": "Total Federation Inputs", "inputs_per_fed": "Inputs per Fed"},

    )
    fig.update_layout(
        margin={"l": 10, "r": 10, "b": 10, "t": 50},
    )
    fig.show(renderer="browser")
    print(df.head())
    print(df.mult.mean())


def run_time():
    for i in [5, 6, 7, 8, 9]:
        print(f"Test {i}")
        df = pd.read_csv(f"scale_test{i}_timing_data.csv")
        df = df.sort_values(by="name", ignore_index=True)
        df["total_inputs"] = df.n_fedsxsubs + df.use_epts*df.n_fedsxsubs
        df["log_time"] = df.time.apply(np.log)
        df["log_feds"] = df.n_feds.apply(np.log)
        df["log_subs"] = df.n_subs.apply(np.log)
        df["log_fedsxsubs"] = df.n_fedsxsubs.apply(np.log)
        df["log_inputs"] = df.total_inputs.apply(np.log)

        fig = px.scatter(
            df,
            x="total_inputs",
            y="time",
            # facet_col="use_epts",
            color="use_db",
            hover_data=["name", "n_feds", "n_subs", "use_db", "use_pf", "time"],
            symbol="n_feds",
            log_x=True, log_y=True,
            # title=f"Scale test {i}",
        )
        x = 10**(np.array(list(range(50)))/10)
        y1 = 1/5*np.exp(x*0.0001)
        y2 = 1/8*x
        y3 = 1/100*x
        y4 = (1/100*x)**2

        fig.add_trace(go.Scatter(x=x, y=y1))
        fig.add_trace(go.Scatter(x=x, y=y2))
        fig.add_trace(go.Scatter(x=x, y=y3))
        fig.add_trace(go.Scatter(x=x, y=y4))
        fig.show(renderer="browser")


if __name__ == '__main__':
    # analyze_run_time_db_vs_csv()
    # analyze_run_time_timescaledb()
    # read_time()
    read_time5x()