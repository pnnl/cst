#!/bin/bash

# Copyright (c) 2022-2025 Battelle Memorial Institute
# file: runcosim.sh

if [[ -z ${CST_ROOT} ]]; then
  echo "Edit cosim.env in the CoSimulation Toolbox directory"
  echo "Run 'source cosim.env' in that same directory"
  exit
fi

# standard use
cst_ver=$(cosim_toolbox --version)
grid_ver=$(cat "${CST_ROOT}/scripts/grid_version")

# distributed version
#IMAGE=pnnl/cst:ubuntu-${cst_ver}
#IMAGE=pnnl/cst:cst-${cst_ver}
#IMAGE=pnnl/cst:gridlabd-${cst_ver}

# for custom use
#IMAGE=cosim-ubuntu:latest
IMAGE=cosim-cst:latest
#IMAGE=cosim-griblabd:latest
#IMAGE=cosim-cplex:latest

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