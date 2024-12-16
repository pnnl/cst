# Copyright (c) 2024-2024 Battelle Memorial Institute
# file: __init__.py
""" CoSimulation Toolbox (CoSimToolbox)
Contains the python packages for the cosim_toolbox

"""
import os

sim_user: str = os.environ.get("SIM_USER", "worker")
sim_host: str = os.environ.get("SIM_HOST", "localhost")

wsl_host: str = os.environ.get("SIM_WSL_HOST")
if wsl_host:
    wsl_port: str = os.environ.get("SIM_WSL_PORT", "2222")

cosim_mg_host = os.environ.get("MONGO_HOST", "mongodb://localhost")
cosim_mg_port = os.environ.get("MONGO_PORT", "27017")
cosim_mongo_host = cosim_mg_host + ":" + cosim_mg_port
cosim_mongo_db = os.environ.get("COSIM_MONGO_DB", "copper")

cosim_pg_host = os.environ.get("POSTGRES_HOST", "localhost")
cosim_pg_db = os.environ.get("COSIM_POSTGRES_DB", "copper")

# Same credentials for both databases
cosim_user = os.environ.get("COSIM_USER", "worker")
cosim_password = os.environ.get("COSIM_PASSWORD", "worker")

cu_federations: str = "federations"
cu_scenarios: str = "scenarios"
cu_logger: str = "cu_logger"