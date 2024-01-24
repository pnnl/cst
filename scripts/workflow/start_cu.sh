#!/bin/bash

if [[ -z ${CSTBDIR} ]]; then
  . "${CSTBDIR}/cosim.env"
fi

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

cd "$CSTBDIR/run" || exit
mkdir -p ./dags ./logs ./plugins ./config ./python
# make wide open for now
sudo chmod -R 777 ./dags ./logs ./plugins ./config ./python ../src
docker-compose -f $WORKFLOW/postgres-docker-compose.yaml up -d
docker-compose -f $WORKFLOW/docker-compose.yaml up -d
