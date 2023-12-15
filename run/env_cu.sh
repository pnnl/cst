#!/bin/bash

mkdir -p ./dags ./logs ./plugins
chmod -R 777 ./dags ./logs ./plugins

cat > ".env" << EOF
POSTGRES_DB=copper
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=database
POSTGRES_PORT=5432
AIRFLOW_UID=$(id -u)
AIRFLOW_GID=0
EOF

docker-compose -f airflow-docker-compose.yaml up airflow-init
