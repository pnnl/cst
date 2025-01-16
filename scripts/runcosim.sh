#!/bin/bash

# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: runcosim

if [[ -z ${SIM_DIR} ]]; then
  echo "Edit cosim.env in the Co-Simulation directory"
  echo "Run 'source cosim.env' in that same directory"
  exit
fi

IMAGE=cosim-python:latest

echo "Should always confirm that you are logged in to docker using 'docker login'"

if [[ -z $1 ]] ; then
  echo "Running foreground image $IMAGE"
  docker run -it --rm \
         --name foregroundWorker \
         -e LOCAL_USER_ID=${SIM_UID} \
         --mount type=bind,source="$SIM_DIR/run",destination="$COSIM_HOME/run" \
         -w=$COSIM_HOME \
         $IMAGE \
         bash
else
  echo "Running background image $IMAGE"
  docker run -itd --rm \
         --name backgroundWorker \
         -e LOCAL_USER_ID=${SIM_UID} \
         --mount type=bind,source="$SIM_DIR/run",destination="$COSIM_HOME/run" \
         -w=$SIM_HOME \
         $IMAGE \
         bash -c "$1"
fi