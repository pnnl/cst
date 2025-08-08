# Copyright (c) 2022-2025 Battelle Memorial Institute
# file: __init__.py
""" CoSimulation Toolbox (CoSimToolbox)
Contains the python packages for the 'cosim_toolbox'

"""
from os import environ

local_uid: str = environ.get("LOCAL_UID", "1001")
local_user: str = environ.get("LOCAL_USER", "worker")

cst_host: str = environ.get("CST_HOST", "localhost")
wsl_host: str = environ.get("CST_WSL_HOST")
if wsl_host:
    wsl_port: str = environ.get("CST_WSL_PORT", "2222")

# login credentials for group, user, pwd and home in docker
cst_gid: str = environ.get("CST_GID", "9002")
cst_grp: str = environ.get("CST_GRP", "runner")
cst_uid: str = environ.get("CST_UID", "9001")
cst_user: str = environ.get("CST_USER", "worker")
cst_password: str = environ.get("CST_PASSWORD", cst_user)

# database, same name for mongo/postgres cst pair
cst_db: str = environ.get("CST_DB", "copper")

# postgresql database
cst_mg_host = environ.get("MONGO_HOST", "mongodb://" + cst_host)
cst_mg_port = environ.get("MONGO_PORT", "27017")
cst_mongo = cst_mg_host + ":" + cst_mg_port
cst_mongo_db = environ.get("CST_MONGO_DB", cst_db)

# mongo database
cst_pg_host = environ.get("POSTGRES_HOST", cst_host)
cst_pg_port = environ.get("POSTGRES_PORT", "5432")
cst_postgres = cst_pg_host + ":" + cst_pg_port
cst_postgres_db = environ.get("CST_POSTGRES_DB", cst_db)

cst_federations: str = "federations"
cst_scenarios: str = "scenarios"

cst_data_db = {
    "host": cst_pg_host,
    "port": cst_pg_port,
    "dbname": cst_db,
    "user": cst_user,
    "password": cst_password
}

cst_meta_db = {
    "host": cst_mg_host,
    "port": cst_mg_port,
    "dbname": cst_db,
    "user": cst_user,
    "password": cst_password
}
