#!/bin/bash

DOCKER_NAME="cosim-docker"
#IMAGE_NAME="ubuntu:20.04"
IMAGE_NAME="cosim-jupyter:latest"
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

#USER_NAME=jovyan
USER_NAME=worker
USER_HOME=/home/$USER_NAME
CONTENT=/home/d3j331/tesp/repository/copper/examples

clear
docker run -it --rm \
           -v $CONTENT:$USER_HOME/copper \
           -w=${USER_HOME} \
           --name ${DOCKER_NAME} ${IMAGE_NAME} bash
