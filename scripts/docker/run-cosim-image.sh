#!/bin/bash

DOCKER_NAME="cosim-docker"
#IMAGE_NAME="ubuntu:20.04"
#IMAGE_NAME="cosim-airflow:latest"
#IMAGE_NAME="cosim-jupyter:latest"
#IMAGE_NAME="cosim-library:latest"
#IMAGE_NAME="cosim-build:latest"
#IMAGE_NAME="cosim-helics:latest"
#IMAGE_NAME="cosim-gridlabd:latest"
#IMAGE_NAME="cosim-eplus:latest"
#IMAGE_NAME="cosim-ns3:latest"
#IMAGE_NAME="cosim-python:latest"
IMAGE_NAME="cosim-tespapi:latest"
#IMAGE_NAME="cosim-julia:latest"
#IMAGE_NAME="cosim-mespapi:latest"

names=(
  "jupyter"
  "airflow"
  "library"
  "build"
  "helics"
  "gridlabd"
  "eplus"
  "ns3"
  "python"
  "tespapi"
  "julia"
  "mespapi"
)

builds=(
  1
  1
  0
  0
  0
  0
  0
  0
  1
  1
  1
  1
)


COSIM_USER=airflow
#COSIM_USER=jovyan
#COSIM_USER=worker
COSIM_HOME=/home/$COSIM_USER
CONTENT=/home/d3j331/tesp/repository/copper/src/cosim_toolbox

#           -w=${COSIM_HOME} \
#           -v $CONTENT:/copper \
#           -e env_var=value <imageName>
clear
LOCAL_TESP="$HOME/tesp/repository/tesp/examples/analysis/dsot"

docker run -it --rm \
           --mount type=bind,source="$LOCAL_TESP",destination="/home/worker/tesp/dsot" \
           --name ${DOCKER_NAME} ${IMAGE_NAME} bash

#for i in "${!names[@]}"; do
#  IMAGE_NAME="cosim-${names[$i]}:latest"
#
#  if [ "${builds[$i]}" -eq 1 ]; then
#    docker run -e SIM_HOST=gage.pnl.gov ${IMAGE_NAME}
#  fi
#done