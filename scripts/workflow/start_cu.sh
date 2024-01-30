#!/bin/bash

CODEDIR=/home/d3j331/tesp/repository/copper

if [[ ! -e ".env" ]]; then
  $CODEDIR/scripts/workflow/env_cu.sh
fi
source .env

# Install yq (https://github.com/mikefarah/yq/#install) to parse the YAML file and retrieve the network name
#NETWORK_NAME=$(yq eval '.networks' postgres-docker-compose.yaml | cut -f 1 -d':')
#docker network create $NETWORK_NAME
# or hardcode the network name from the YAML file

#docker network create cu_net
#docker volume create cu_vol_user
#docker volume create cu_vol_admin

image1=$(docker images -q "cosim-airflow:latest")
if [[ $image1 == "" ]]; then
  echo "Please build-cosim-images in scripts/docker"
  exit
fi

cd "$CODEDIR/run" || exit
docker-compose -f $WORKFLOW/postgres-docker-compose.yaml up -d
docker-compose -f $WORKFLOW/docker-compose.yaml up -d
