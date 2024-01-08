#!/bin/bash

mkdir -p ./dags ./logs ./plugins ./config ./python
# make wide open for now
chmod -R 777 ./dags ./logs ./plugins ./config ./python

cat > ".env" << EOF
POSTGRES_DB=copper
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=database
POSTGRES_PORT=5432
# add user id for linux
AIRFLOW_UID=$(id -u)
# add user id for windows
# AIRFLOW_UID=50000
AIRFLOW_GID=0
# AIRFLOW_PROJ_DIR=.
# _AIRFLOW_WWW_USER_USERNAME=
# _AIRFLOW_WWW_USER_PASSWORD=
EOF
