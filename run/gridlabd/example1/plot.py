import plotly.express as px
from cosim_toolbox.dataReader import DataReader
import numpy as np

data_reader = DataReader("gld2")
df = data_reader.complex_df
print(df.head())
df.sim_value = df.sim_value.astype(complex)
df["sim_value_imag"] = df.sim_value.apply(np.imag)
fig = px.scatter(df.loc[df.sim_name=="node_3_load_A"], x="real_time", y="sim_value_imag")
fig.write_html("node_3.html")
