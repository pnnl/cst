#!/bin/bash

CODEDIR=/home/d3j331/tesp/repository/copper

cat > ".env" << EOF
CODEDIR=$CODEDIR
RUNFLOW=$CODEDIR/run
WORKFLOW=$CODEDIR/scripts/workflow
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
AIRFLOW_PROJ_DIR=$CODEDIR/run
# _AIRFLOW_WWW_USER_USERNAME=
# _AIRFLOW_WWW_USER_PASSWORD=
EOF

cd "$CODEDIR/run" || exit
mkdir -p ./dags ./logs ./plugins ./config ./python
# make wide open for now
sudo chmod -R 777 ./dags ./logs ./plugins ./config ./python ../src

