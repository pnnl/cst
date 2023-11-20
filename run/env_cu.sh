#!/bin/bash

mkdir -p ./dags ./logs ./plugins
chmod -R 777 ./dags ./logs ./plugins

echo -e "POSTGRES_DB=copper" > env
echo -e "POSTGRES_USER=postgres" >> .env
echo -e "POSTGRES_PASSWORD=postgres" >> .env
echo -e "POSTGRES_HOST=database" >> .env
echo -e "POSTGRES_PORT=5432" >> .env
echo -e "AIRFLOW_UID=$(id -u)" >> .env
echo -e "AIRFLOW_GID=0" >> .env

docker-compose -f airflow-docker-compose.yaml up airflow-init