#!/bin/bash

if [[ -z ${SIM_DIR} ]]; then
  echo "Edit cosim.env in the Co-Simulation directory"
  echo "Run 'source cosim.env' in that same directory"
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
#docker compose -f $STACK_DIR/timescale-docker-compose.yaml -f $STACK_DIR/docker-compose.yaml up -d --remove-orphans
# For development no need to run airflow, comment above, un-comment below
docker compose -f $STACK_DIR/timescale-docker-compose.yaml up -d --remove-orphans
