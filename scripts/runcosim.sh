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
#IMAGE=cosim-ubuntu:latest
#IMAGE=cosim-build:latest
#IMAGE=cosim-helics:latest
#IMAGE=cosim-python:latest
#IMAGE=osw_test_scenario:latest
IMAGE=cosim-osw:latest

echo "Should always confirm that you are logged in to docker using 'docker login'"

# Once attached to a container, users can detach from it and
# leave it running using the using CTRL-p CTRL-q key sequence.
# To running docker
#   docker attach [name] or [ID]

# Setting mount point for pnnl/cst docker
# For best results $SRC_DIR should be derivative of user $CST_ROOT directory
# and DES_DIR should be derivative of docker $CST_HOME directory.
SRC_DIR="${CST_ROOT}/run"
DES_DIR="${CST_HOME}/run"

# For best results $WORKDIR should be path
# relative and subdirectory to $CST_HOME
WORKDIR=""

# Set chown working directory for sharing
chown -fR ${CST_UID}:${CST_GID} "${SRC_DIR}${WORKDIR}"
#chmod -fR 775 "${SRC_DIR}${WORKDIR}" > /dev/null

# if in git repo, so we don't change mode
git config core.fileMode false

if [[ -z $1 ]] ; then
  echo "Running foreground image $IMAGE"
  docker run -it --rm \
         -e LOCAL_UID=${LOCAL_UID} \
         --mount type=bind,source="${SRC_DIR}",destination="${DES_DIR}" \
         -w="$DES_DIR$WORKDIR" \
         $IMAGE \
         bash
else
  echo "Running background image $IMAGE"
  docker run -itd --rm \
         -e LOCAL_UID=${LOCAL_UID} \
         --mount type=bind,source="${SRC_DIR}",destination="${DES_DIR}" \
         -w="$DES_DIR$WORKDIR" \
         $IMAGE \
         bash -c "$1"
fi

# Set chown user directory for sharing
chown -fR ${UID} "${SRC_DIR}${WORKDIR}"
