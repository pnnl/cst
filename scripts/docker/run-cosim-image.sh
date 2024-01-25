#!/bin/bash

DOCKER_NAME="cosim-docker"
#IMAGE_NAME="ubuntu:20.04"
IMAGE_NAME="cosim-airflow:latest"
#IMAGE_NAME="cosim-jupyter:latest"
#IMAGE_NAME="cosim-library:latest"
#IMAGE_NAME="cosim-build:latest"
#IMAGE_NAME="cosim-helics:latest"
#IMAGE_NAME="cosim-gridlabd:latest"
#IMAGE_NAME="cosim-eplus:latest"
#IMAGE_NAME="cosim-ns3:latest"
#IMAGE_NAME="cosim-python:latest"
#IMAGE_NAME="cosim-tespapi:latest"
#IMAGE_NAME="cosim-julia:latest"
#IMAGE_NAME="cosim-mespapi:latest"

COSIM_USER=airflow
#COSIM_USER=jovyan
#COSIM_USER=worker
COSIM_HOME=/home/$COSIM_USER
CONTENT=/home/d3j331/tesp/repository/copper/src/cosim_toolbox

#           -w=${COSIM_HOME} \
#           -v $CONTENT:/copper \

clear
docker run -it --rm \
           -v $CONTENT:/copper \
           --name ${DOCKER_NAME} ${IMAGE_NAME} bash
