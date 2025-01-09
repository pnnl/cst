# Copyright (c) 2024-2024 Battelle Memorial Institute
# file: __init__.py
""" CoSimulation Toolbox (CoSimToolbox)
Contains the python packages for the cosim_toolbox

"""
from os import environ

sim_user: str = environ.get("SIM_USER", "worker")
sim_host: str = environ.get("SIM_HOST", "localhost")

wsl_host: str = environ.get("SIM_WSL_HOST")
if wsl_host:
    wsl_port: str = environ.get("SIM_WSL_PORT", "2222")

# Same db name and credentials for both postgresql and mongo databases
cosim_db: str = environ.get("COSIM_DB", "copper")
cosim_user: str = environ.get("COSIM_USER", sim_user)
cosim_password: str = environ.get("COSIM_PASSWORD", sim_user)

cosim_mg_host = environ.get("MONGO_HOST", "mongodb://" + sim_host)
cosim_mg_port = environ.get("MONGO_PORT", "27017")
cosim_mongo = cosim_mg_host + ":" + cosim_mg_port
cosim_mongo_db = environ.get("COSIM_MONGO_DB", cosim_db)

cosim_pg_host = environ.get("POSTGRES_HOST", sim_host)
cosim_pg_port = environ.get("POSTGRES_PORT", "5432")
cosim_postgres = cosim_pg_host + ":" + cosim_pg_port
cosim_postgres_db = environ.get("COSIM_POSTGRES_DB", cosim_db)

cu_federations: str = "federations"
cu_scenarios: str = "scenarios"
cu_logger: str = "cu_logger"

cu_data_db = {
    "host": cosim_pg_host,
    "port": cosim_pg_port,
    "dbname": cosim_db,
    "user": cosim_user,
    "password": cosim_password
}

cu_meta_db = {
    "host": cosim_mg_host,
    "port": cosim_mg_port,
    "dbname": cosim_db,
    "user": cosim_user,
    "password": cosim_password
}
