#!/bin/bash

DOCKER_NAME="cosim-docker"

#IMAGE_NAME="cosim-ubuntu:latest"
IMAGE_NAME="cosim-cst:latest"
#IMAGE_NAME="cosim-airflow:latest"
#IMAGE_NAME="cosim-jupyter:latest"
#IMAGE_NAME="cosim-tesp-library:latest"
#IMAGE_NAME="cosim-tesp-build:latest"
#IMAGE_NAME="cosim-tesp-api:latest"
#IMAGE_NAME="cosim-julia:latest"
#IMAGE_NAME="cosim-mespapi:latest"

names=(
  "ubuntu"
  "cst"
  "airflow"
  "jupyter"
  "library"
  "build"
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
  1
  1
  1
  1
)


CST_USER=airflow
#CST_USER=jovyan
#CST_USER=worker
CST_HOME=/home/$CST_USER
CONTENT=/home/d3j331/tesp/repository/copper/src/cosim_toolbox

#           -w=${CST_HOME} \
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
#    docker run -e CST_HOST=gage.pnl.gov ${IMAGE_NAME}
#  fi
#done