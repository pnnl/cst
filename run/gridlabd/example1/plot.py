import plotly.express as px
import numpy as np
from data_management.factories import create_timeseries_manager


# --- Configuration Section ---
# This makes it easy to switch between different data sources.
# The schema_name corresponds to the 'analysis name' used by the federates.
SCHEMA_NAME = "gld2"

# Choose your backend and provide its configuration.
# Option 1: PostgreSQL Backend
BACKEND_TYPE = "postgresql"
BACKEND_CONFIG = {
    "location": "localhost",
    "database": "copper",
    "user": "worker",
    "password": "worker",
    "port": "5432"
}

# Option 2: CSV File Backend (uncomment to use)
# BACKEND_TYPE = "csv"
# BACKEND_CONFIG = {
#     "location": "./timeseries_output"  # Path to the directory with CSV files
# }


# --- Data Loading Section ---
print(f"Loading data for schema '{SCHEMA_NAME}' from '{BACKEND_TYPE}' backend...")

# Use a context manager to handle connection and disconnection.
with create_timeseries_manager(
    backend=BACKEND_TYPE,
    schema_name=SCHEMA_NAME,
    **BACKEND_CONFIG
) as ts_manager:
    # Fetch the data. We specify the data_type to get only complex values,
    # which is equivalent to the old `.complex_df`.
    df = ts_manager.read_as_dataframe(data_type="complex")

# --- Data Processing and Plotting Section ---
print("Data loaded successfully. Head of DataFrame:")
print(df.head())

# Convert the 'data_value' column from string/object to actual complex numbers.
df['data_value'] = df['data_value'].astype(complex)
df["data_value_imag"] = df.data_value.apply(np.imag)
plot_df = df.loc[df.data_name == "node_3_load_A"]
fig = px.scatter(
    plot_df,
    x="real_time",
    y="data_value_imag",
    title="Imaginary Part of Current at node_3_load_A"
)

# Save the plot to an HTML file.
output_filename = "node_3.html"
fig.write_html(output_filename)
print(f"Plot successfully saved to {output_filename}")
