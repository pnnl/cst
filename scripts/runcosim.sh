#!/bin/bash

# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: runcosim.sh

if [[ -z ${CST_ROOT} ]]; then
  echo "Edit cosim.env in the CoSimulation Toolbox directory"
  echo "Run 'source cosim.env' in that same directory"
  exit
fi

# standard use
cst_ver=$(cat "${CST_ROOT}/scripts/cst_version")
grid_ver=$(cat "${CST_ROOT}/scripts/grid_version")
docker_tag=${cst_ver}_ubuntu_${grid_ver}
IMAGE=pnnl/cst:${docker_tag}

# for custom use
#IMAGE=cosim-ubuntu:cst_${grid_ver}
#IMAGE=cosim-library:cst_${grid_ver}
#IMAGE=cosim-build:cst_${grid_ver}
IMAGE=cosim-cplex:cst_${grid_ver}
#IMAGE=cosim-user:cst_${grid_ver}

IMAGE=cosim-python:latest

echo "Should always confirm that you are logged in to docker using 'docker login'"

if [[ -z $1 ]] ; then
  echo "Running foreground image $IMAGE"
  docker run -it --rm \
         -e LOCAL_UID=${LOCAL_UID} \
         --mount type=bind,source="$CST_ROOT/run",destination="$CST_HOME/run" \
         -w=$CST_HOME \
         $IMAGE \
         bash
else
  echo "Running background image $IMAGE"
  docker run -itd --rm \
         -e LOCAL_UID=${LOCAL_UID} \
         --mount type=bind,source="$CST_ROOT/run",destination="$CST_HOME/run" \
         -w=$CST_HOME \
         $IMAGE \
         bash -c "$1"
fi