#!/bin/bash

if [[ -z ${SIM_DIR} ]]; then
  echo "Please run 'source cosim.env' in the root Co-Simulation directory"
  echo "Then run this script in this directory"
  exit
fi

# Install yq (https://github.com/mikefarah/yq/#install) to parse the YAML file and retrieve the network name
#NETWORK_NAME=$(yq eval '.networks' postgres-docker-compose.yaml | cut -f 1 -d':')
#docker network create $NETWORK_NAME
# or hardcode the network name from the YAML file

image1=$(docker images -q "cosim-airflow:latest")
if [[ $image1 == "" ]]; then
  echo "Please build-cosim-images in scripts/docker"
  echo "Then run this script in this directory"
  exit
fi

cd "$SIM_DIR/run" || exit
docker compose -f $STACK_DIR/postgres-docker-compose.yaml -f $STACK_DIR/docker-compose.yaml up -d --remove-orphans
