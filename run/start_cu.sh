#!/bin/bash

source env

# Install yq (https://github.com/mikefarah/yq/#install) to parse the YAML file and retrieve the network name
#NETWORK_NAME=$(yq eval '.networks' postgres-docker-compose.yaml | cut -f 1 -d':')
#docker network create $NETWORK_NAME
# or hardcode the network name from the YAML file

#docker network create cu_net
#docker volume create cu_vol_user
#docker volume create cu_vol_admin

# docker-compose -f airflow-docker-compose.yaml up airflow-init

docker-compose --env-file ./.env -f postgres-docker-compose.yaml up -d
docker-compose -f airflow-docker-compose.yaml up -d





