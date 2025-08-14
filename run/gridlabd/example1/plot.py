import plotly.express as px
from cosim_toolbox.readResults import ReadResults
import numpy as np

data_reader = ReadResults("gld2")
df = data_reader.complex_df
print(df.head())
df.data_value = df.data_value.astype(complex)
df["data_value_imag"] = df.data_value.apply(np.imag)
fig = px.scatter(df.loc[df.data_name=="node_3_load_A"], x="real_time", y="data_value_imag")
fig.write_html("node_3.html")
